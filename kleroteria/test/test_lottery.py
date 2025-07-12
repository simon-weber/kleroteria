import itertools
import json

import pytest

from kleroteria import settings, lottery, generate_nonce


def test_full_lottery(botos):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')

    ids = [generate_nonce() for _ in range(10)]

    with addresses.batch_writer() as b:
        for id in ids:
            b.put_item(Item={'id': id, 'a': id + '@example.com'})

    choice, _ = lottery.pick_winner(botos, 5, sleep_secs=0)
    assert choice['Attributes']['a'].endswith('example.com')
    assert choice['Attributes']['w']

    with addresses.batch_writer() as b:
        for id in ids:
            b.delete_item(Key={'id': id})


def test_dupe_winner(botos):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')

    id = generate_nonce()
    addresses.put_item(Item={'id': id, 'a': id + '@example.com'})

    choice, _ = lottery.pick_winner(botos, 5, sleep_secs=0)
    assert choice['Attributes']['a'].endswith('example.com')
    assert choice['Attributes']['w']

    with pytest.raises(lottery.NoPossibleWinner):
        lottery.pick_winner(botos, 5, sleep_secs=0)

    addresses.delete_item(Key={'id': id})


def test_post_too_long(botos):
    with pytest.raises(lottery.PostTooLong):
        lottery.submit_post(botos, None, None, 'a' * 30001, 'valid subject')


def test_winner_verification(botos):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')

    id = generate_nonce()
    addresses.put_item(Item={'id': id, 'a': id + '@example.com'})
    lottery.pick_winner(botos, 5, sleep_secs=0)

    bad_combos = itertools.product(['id', id], ['nonce'])
    for bad_combo in bad_combos:
        bad_id, bad_nonce = bad_combo
        with pytest.raises(lottery.InvalidWinnerNonce):
            lottery.submit_post(botos, bad_id, bad_nonce, 'my post', 'my subject')

    addresses.delete_item(Key={'id': id})


def test_submit_post(botos):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')
    posts = botos.resource('dynamodb').Table('k8aPosts')

    id = generate_nonce()
    addresses.put_item(Item={'id': id, 'a': id + '@example.com', 's': "subject" + id})
    choice, _ = lottery.pick_winner(botos, 5, sleep_secs=0)

    winner_nonce, post_r, address_r = lottery.submit_post(botos, id, choice['Attributes']['w'], 'my post', 'my subject')
    assert post_r
    assert 'w' not in address_r['Attributes']

    addresses.delete_item(Key={'id': id})
    posts.delete_item(Key={'id': winner_nonce})


def test_send_no_approved_post(botos):
    with pytest.raises(lottery.NoApprovedPost):
        lottery.send_post(botos)

    posts = botos.resource('dynamodb').Table('k8aPosts')
    posts.put_item(Item={'id': generate_nonce(), 'c': 'contents', 'r': False, 's': 'subject'})

    with pytest.raises(lottery.NoApprovedPost):
        lottery.send_post(botos)


def test_send_post_dry_run(botos):
    posts = botos.resource('dynamodb').Table('k8aPosts')

    content = """Here's some html to escape: & < " \' >\n\nbest,\nSimon"""
    posts.put_item(Item={'id': generate_nonce(), 'c': content, 'r': True, 's': 'subject'})

    lottery.send_post(botos)


def test_lambda_submits(botos, post_ingest):
    addresses = botos.resource('dynamodb').Table('k8aAddresses2')
    posts = botos.resource('dynamodb').Table('k8aPosts')
    queue = botos.resource('sqs').Queue(settings.post_queue_url)

    # create winner
    id = generate_nonce()
    addresses.put_item(Item={'id': id, 'a': id + '@example.com'})
    choice, _ = lottery.pick_winner(botos, 5, sleep_secs=0)

    # submit
    queue.send_message(
        MessageBody=lottery.PostEvent('submit', id, choice['Attributes']['w'], 'some contents', 'subject').to_json(),
    )

    res = botos.client('lambda').invoke(
        FunctionName='post_ingest',
    )
    payload = res['Payload'].read()
    returned = json.loads(payload)['results']

    assert len(returned) == 1
    winner_nonce, post_r, address_r = returned[0]
    addresses.delete_item(Key={'id': address_r['Attributes']['id']})
    posts.delete_item(Key={'id': winner_nonce})

    assert queue.attributes['ApproximateNumberOfMessages'] == '0'
    assert queue.attributes['ApproximateNumberOfMessagesNotVisible'] == '0'
