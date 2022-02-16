"""Functionality for picking winners and managing submissions."""

from collections import namedtuple
import html
import json
import logging
import random
from urllib.parse import urlencode

from . import generate_nonce, settings, subscription

logger = logging.getLogger(__name__)


class NoPossibleWinner(Exception):
    pass


class PostTooLong(Exception):
    pass


class InvalidWinnerNonce(Exception):
    pass


class NoApprovedPost(Exception):
    pass


class PostEvent(namedtuple('PostEvent', ('action', 'address_id', 'winner_nonce', 'post_contents', 'subject'))):
    __slots__ = ()

    @classmethod
    def from_json(cls, s):
        return cls(*json.loads(s))

    def to_json(self):
        return json.dumps(self)


def submit_post(botos, address_id, winner_nonce, post, subject):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')
    posts = botos.resource('dynamodb').Table('k8aPosts')

    if len(post) > 3000:
        raise PostTooLong

    winner = addresses.get_item(
        Key={'id': address_id},
    )

    address_item = winner.get('Item', {})
    found = (address_item.get('id'), address_item.get('w'))
    given = (address_id, winner_nonce)

    if found != given:
        raise InvalidWinnerNonce("given %s:%s; found %s:%s" % (given + found))

    logger.info("accepting post for %r with %r", address_item['a'], address_item['id'])

    post_item = {
        'id': winner_nonce,
        'c': post,
        'r': False,
        's': subject,
    }

    post_r = posts.put_item(
        Item=post_item,
    )

    address_r = addresses.update_item(
        Key={'id': address_id},
        UpdateExpression="REMOVE w",
        ReturnValues='ALL_NEW',
    )

    admin_email = "New submission received for nonce %r:\n\n%s\n\n%s\n\n%s" % (winner_nonce, subject, address_item['a'], post)
    botos.client('ses').send_email(
        Source=settings.noreply_k8a_email,
        ReplyToAddresses=[settings.reply_to_email],
        ReturnPath=settings.bounce_email,
        Destination={
            'ToAddresses': [settings.admin_email],
        },
        Message={
            'Subject': {
                'Data': '[k8a] new submission',
            },
            'Body': {
                'Text': {
                    'Data': admin_email,
                },
            },
        },
    )

    return winner_nonce, post_r, address_r


def create_winner_link(address_id, winner_nonce):
    return settings.url_prefix + '/submit?' + urlencode({'id': address_id, 'n': winner_nonce})


def pick_winner(botos, scan_limit=None, sleep_secs=1, winner_override_address=None):
    candidates = subscription.get_subscribers(botos, scan_limit, sleep_secs, skip_winners=True)

    if not candidates:
        raise NoPossibleWinner

    if winner_override_address:
        winner = [c for c in candidates if c['a']['S'] == winner_override_address][0]
        assert 'w' not in winner  # they should not have already won
        logger.info("overrode winner to %r", winner)
    else:
        winner = random.choice(candidates)
        logger.info("%s candidates, chose %r", len(candidates), winner)

    winner_nonce = generate_nonce()
    winner_id = winner['id']['S']
    winner_address = winner['a']['S']

    addresses = botos.resource('dynamodb').Table('k8aAddresses2')
    d_r = addresses.update_item(
        Key={'id': winner_id},
        UpdateExpression="SET w = if_not_exists(w, :w)",
        ExpressionAttributeValues={
            ':w': winner_nonce,
        },
        ReturnValues='ALL_NEW',
    )

    winner_link = create_winner_link(winner_id, winner_nonce)
    unsub_link = subscription.create_unsub_link(winner_address, winner_id)

    ses_r = botos.client('ses').send_email(
        Source=settings.noreply_k8a_email,
        ReplyToAddresses=[settings.reply_to_email],
        ReturnPath=settings.bounce_email,
        Destination={
            'ToAddresses': [winner_address],
        },
        Message={
            'Subject': {
                'Data': 'Kleroteria awaits your submission',
            },
            'Body': {
                'Text': {
                    'Data': ("You have been selected to write to Kleroteria. If you would like to submit a post, follow this link: %s"
                             "\n\nYour link does not expire."
                             " You may open it multiple times, but submitting from it will only work once."
                             " For more details on submitting, see the about page: https://www.kleroteria.org/about"
                             "\n\nTo unsubscribe, follow this link: %s") % (winner_link, unsub_link),
                },
                'Html': {
                    'Data': settings.email_template.format(
                        body=('You have been selected to write to <a href="https://kleroteria.org">Kleroteria</a>. If you would like to submit a post, follow <a href="%s">this link</a>.'
                              '<br/><br/> Your link does not expire.'
                              ' You may open it multiple times, but submitting from it will only work once.'
                              ' For more details on submitting, see <a href="https://www.kleroteria.org/about">the about page</a>.'
                              '<br/><br/>To unsubscribe, follow <a href="%s">this link</a>.') % (winner_link, unsub_link),
                    )
                }
            },
        },
    )

    return d_r, ses_r


def get_approved_post(botos):
    client = botos.client('dynamodb')
    paginator = client.get_paginator('scan')
    kwargs = {
        'TableName': 'k8aPosts',
        'ConsistentRead': False,
        'ReturnConsumedCapacity': 'TOTAL',
        'Limit': 1,
    }

    page_iterator = paginator.paginate(**kwargs)
    for page in page_iterator:
        logger.info("scan page")
        for item in page['Items']:
            if item['r']['BOOL']:
                return item


def send_post(botos, scan_limit=None, sleep_secs=1, dry_run=True):
    posts = botos.resource('dynamodb').Table('k8aPosts')
    post = get_approved_post(botos)
    if not post:
        raise NoApprovedPost

    if dry_run:
        subscribers = [
            {'a': {'S': settings.personal_email}, 'id': {'S': 'fakeid'}},
            {'a': {'S': settings.personal_email}, 'id': {'S': 'fakeid'}, 'w': {'S': 'fakewinner'}},
        ]
    else:
        subscribers = subscription.get_subscribers(botos, scan_limit, sleep_secs, skip_winners=False)

    subject = "[Kleroteria] %s" % post['s']['S']
    post_template_text = (
        "{post}"
        "\n- - -"
        "\nkleroteria.org"
        "\ntwitter.com/JoinKleroteria"
        "\nTo unsubscribe from future posts, follow {unsub_link}"
    )
    post_template_html = (
        '<pre style="font-family: serif; font-size: medium; white-space: pre-wrap;">'
        '{htmlsafe_post}'
        '</pre>'
        '<hr>'
        '<a href="https://www.kleroteria.org/">Kleroteria</a>'
        ' (<a href="{unsub_link}">unsubscribe</a>)'
        '<br/><a href="https://twitter.com/JoinKleroteria">@JoinKleroteria</a>'
    )
    winner_reminder_text = (
        "\n\nA reminder: you were previously selected to submit your own post."
        "\nYou may do so at {winner_link}"
    )
    winner_reminder_html = (
        '<br/><br/>A reminder: you were previously selected to submit your own post.'
        '<br/>You may <a href="{winner_link}">click here</a> to do so.'
    )

    for subscriber in subscribers:
        post_contents = post['c']['S']
        sub_address = subscriber['a']['S']
        sub_id = subscriber['id']['S']
        context = {
            'post': post_contents,
            'htmlsafe_post': html.escape(post_contents, quote=False),
            'unsub_link': subscription.create_unsub_link(sub_address, sub_id),
        }

        text_template = post_template_text
        html_template = post_template_html

        winner_nonce = subscriber.get('w', {}).get('S')
        if winner_nonce:
            text_template += winner_reminder_text
            html_template += winner_reminder_html
            context['winner_link'] = create_winner_link(sub_id, winner_nonce)

        text_body = text_template.format_map(context)
        html_body = html_template.format_map(context)

        logger.info("sending post to %r", sub_address)
        try:
            r = botos.client('ses').send_email(
                Source=settings.noreply_k8a_email,
                ReplyToAddresses=[settings.reply_to_email],
                ReturnPath=settings.bounce_email,
                Destination={
                    'ToAddresses': [sub_address],
                },
                Message={
                    'Subject': {
                        'Data': subject,
                    },
                    'Body': {
                        'Text': {
                            'Data': text_body,
                        },
                        'Html': {
                            'Data': html_body,
                        }
                    },
                },
            )
            logger.info("post ses response: %r", r)
        except Exception:
            logger.exception("failed to send post to %r", sub_address)

    if not dry_run:
        posts.delete_item(Key={'id': post['id']['S']})
        logger.info("deleted post: %r", post)
