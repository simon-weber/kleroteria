import json

import pytest

from kleroteria import settings, subscription


def test_lambda_subscriptions(botos, list_ingest):
    queue = botos.resource('sqs').Queue(settings.list_queue_url)

    # subscribe
    queue.send_message(
        MessageBody=json.dumps(['subscribe', 'test@example.com', None, '']),
    )

    res = botos.client('lambda').invoke(
        FunctionName='list_ingest',
    )
    returned = json.loads(res['Payload'].read())['results']

    assert len(returned) == 1
    assert returned[0][0]['a'] == 'test@example.com'
    assert returned[0][1]['ResponseMetadata']['HTTPStatusCode'] == 200

    assert queue.attributes['ApproximateNumberOfMessages'] == '0'
    assert queue.attributes['ApproximateNumberOfMessagesNotVisible'] == '0'

    # unsubscribe, address mismatch
    # not easily run through lambda since the exception doesn't propogate
    with pytest.raises(subscription.AddressMismatch):
        subscription.unsubscribe(botos, None, returned[0][0]['id'])

    # unsubscribe
    queue.send_message(
        MessageBody=json.dumps(['unsubscribe', returned[0][0]['a'], returned[0][0]['id']]),
    )

    res = botos.client('lambda').invoke(
        FunctionName='list_ingest',
    )
    returned = json.loads(res['Payload'].read())['results']

    assert len(returned) == 1
    assert returned[0]['ResponseMetadata']['HTTPStatusCode'] == 200

    assert queue.attributes['ApproximateNumberOfMessages'] == '0'
    assert queue.attributes['ApproximateNumberOfMessagesNotVisible'] == '0'


def test_unsub_link():
    assert subscription.create_unsub_link('test+foo@example.com', 'abcd') == \
        'http://127.0.0.1:4000/unsub?address=test%2Bfoo%40example.com&id=abcd'


def test_valid_email():
    assert subscription.is_valid_email('foo@example.com')
    assert subscription.is_valid_email('very.“(),:;<>[]”.VERY.“very@"very”.unusual@strange.example.com')

    assert not subscription.is_valid_email('')
    assert not subscription.is_valid_email('example.com')
    assert not subscription.is_valid_email('@example.com')
    assert not subscription.is_valid_email('foo@example')


def test_ignores_honeypotted_signup(botos):
    r = subscription.subscribe(botos, 'test@example.com', 'anything')
    assert r == (None, None, None)
    assert len(subscription.get_subscribers(botos)) == 0


def test_manual_email_dry_run(botos):
    item1, _, _ = subscription.subscribe(botos, 'test1@example.com')
    item2, _, _ = subscription.subscribe(botos, 'test2@example.com')
    assert len(subscription.get_subscribers(botos)) == 2

    results = subscription.send_manual_email(botos, 'sub', 'text', 'html')
    assert len(results) == 1

    results = subscription.send_manual_email(botos, 'sub', 'text', 'html', dry_run=False)
    assert len(results) == 2

    subscription.unsubscribe(botos, 'test1@example.com', item1['id'])
    subscription.unsubscribe(botos, 'test2@example.com', item2['id'])
    assert len(subscription.get_subscribers(botos)) == 0


def test_manual_email_lambda(botos, manual_email):
    item1, _, _ = subscription.subscribe(botos, 'test1@example.com')
    item2, _, _ = subscription.subscribe(botos, 'test2@example.com')
    assert len(subscription.get_subscribers(botos)) == 2

    res = botos.client('lambda').invoke(
        FunctionName='manual_email',
        Payload=json.dumps({'subject': 's', 'body_text': 't', 'body_html': 'h'})
    )
    returned = json.loads(res['Payload'].read())['results']
    assert len(returned) == 1

    res = botos.client('lambda').invoke(
        FunctionName='manual_email',
        Payload=json.dumps({'dry_run': False, 'subject': 's', 'body_text': 't', 'body_html': 'h'})
    )
    returned = json.loads(res['Payload'].read())['results']
    assert len(returned) == 2

    subscription.unsubscribe(botos, 'test1@example.com', item1['id'])
    subscription.unsubscribe(botos, 'test2@example.com', item2['id'])
    assert len(subscription.get_subscribers(botos)) == 0
