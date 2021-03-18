"""Functionality for managing the subscriber list."""

from collections import namedtuple
import json
import logging
import re
import time
from urllib.parse import urlencode

from boto3.dynamodb.conditions import Key
import botocore

from . import settings, generate_nonce

EMAIL_PATTERN = re.compile(r'^\S+@\S+\.\S+$')

logger = logging.getLogger(__name__)


class AddressMismatch(Exception):
    pass


class InvalidEmail(Exception):
    pass


class ListEvent(namedtuple('ListEvent', ('action', 'address', 'address_id', 'honeypot'))):
    __slots__ = ()

    @classmethod
    def from_json(cls, s):
        raw = json.loads(s)
        if len(raw) == 3:
            # default honeypot field
            raw.append(None)
        return cls(*raw)

    def to_json(self):
        return json.dumps(self)


def is_valid_email(address):
    return EMAIL_PATTERN.match(address)


def subscribe(botos, address, honeypot=None):
    logger.info("subscribe %r / %r", address, honeypot)

    if honeypot:
        logger.info("rejecting honeypotted signup: %r / %r", address, honeypot)
        return None, None, None

    if not is_valid_email(address):
        raise InvalidEmail(address)

    addresses = botos.resource('dynamodb').Table('k8aAddresses2')

    nonce = generate_nonce()
    item = {
        'id': nonce,
        'a': address,
    }

    # This doesn't enforce uniqueness of the list (it could, but it'd require a global index on address).
    r = addresses.put_item(
        Item=item,
    )

    sr = welcome(botos, address, nonce)

    return item, r, sr


def create_unsub_link(address, address_id):
    return settings.url_prefix + '/unsub?' + urlencode({'address': address, 'id': address_id})


def get_subscribers(botos, scan_limit=None, sleep_secs=1, skip_winners=False):
    client = botos.client('dynamodb')
    paginator = client.get_paginator('scan')
    kwargs = {
        'TableName': 'k8aAddresses2',
        'ConsistentRead': False,
        'ReturnConsumedCapacity': 'TOTAL',
    }

    if scan_limit is not None:
        kwargs['Limit'] = scan_limit

    items = []
    page_iterator = paginator.paginate(**kwargs)
    for page in page_iterator:
        logger.info("scan page")
        for item in page['Items']:
            if skip_winners and 'w' in item:
                logger.info("skipping winner %r", item)
                continue
            items.append(item)
        time.sleep(sleep_secs)

    return items


def send_manual_email(botos, subject, body_text, body_html, dry_run=True):
    if dry_run:
        address_and_ids = [(settings.admin_email, 'fakeid')]
    else:
        address_and_ids = [(s['a']['S'], s['id']['S']) for s in get_subscribers(botos)]

    results = []
    for address, id in address_and_ids:
        unsub_link = create_unsub_link(address, id)
        result = botos.client('ses').send_email(
            Source=settings.admin_email,
            ReplyToAddresses=[settings.reply_to_email],
            ReturnPath=settings.bounce_email,
            Destination={
                'ToAddresses': [address],
            },
            Message={
                'Subject': {
                    'Data': subject,
                },
                'Body': {
                    'Text': {
                        'Data': "%s\n\nTo unsubscribe, follow this link: %s" % (body_text, unsub_link),

                    },
                    'Html': {
                        'Data': '%s<br/><br/>To unsubscribe, follow <a href="%s">this link</a>.' % (
                            settings.email_template.format(body=body_html), unsub_link),
                    }
                },
            },
        )
        logger.info('sent manual email to %r: %r', address, result)
        results.append(result)

    return results


def welcome(botos, address, address_id):
    unsub_link = create_unsub_link(address, address_id)

    return botos.client('ses').send_email(
        Source=settings.noreply_k8a_email,
        ReplyToAddresses=[settings.reply_to_email],
        ReturnPath=settings.bounce_email,
        Destination={
            'ToAddresses': [address],
        },
        Message={
            'Subject': {
                'Data': 'Welcome to Kleroteria',
            },
            'Body': {
                'Text': {
                    'Data': ("You have subscribed to https://kleroteria.org."
                             "\n\nDidn't subscribe? Someone may have accidentally entered your email; please use this link to unsubscribe: %s") % unsub_link,
                },
                'Html': {
                    'Data': settings.email_template.format(
                        body=('You have subscribed to <a href="https://www.kleroteria.org/">Kleroteria</a>.'
                              "<br/><br/>Didn't subscribe? Someone may have accidentally entered your email;"
                              ' please use <a href="%s">this link</a> to unsubscribe.') % unsub_link,
                    )
                }
            },
        },
    )


def unsubscribe(botos, address, address_id):
    logger.info("unsubscribe %r %r", address, address_id)

    addresses = botos.resource('dynamodb').Table('k8aAddresses2')
    try:
        r = addresses.delete_item(
            Key={'id': address_id},
            ConditionExpression=Key('a').eq(address),
        )
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            raise AddressMismatch
        raise

    return r
