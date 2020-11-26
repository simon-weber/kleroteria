# -*- coding: utf-8 -*-
import collections
import datetime
import logging
import os

from raven.contrib.awslambda import LambdaClient

from kleroteria import settings, lottery  # noqa: E402

# https://gist.github.com/niranjv/fb95e716151642e8ca553b0e38dd152e#gistcomment-2302572
FORMAT = '%(levelname)s: %(asctime)s - %(name)s (%(module)s:%(lineno)s): %(message)s'
logger = logging.getLogger()
for h in logger.handlers:
    h.setFormatter(logging.Formatter(FORMAT))
logger.setLevel(logging.WARNING)

logger = logging.getLogger('kleroteria.post_ingest')

raven_client = LambdaClient(
    include_paths=['kleroteria', 'task'],
)


@raven_client.capture_exceptions
def handler(event, context):
    if isinstance(event, collections.Mapping) and event.get('action') == 'pick_winner':
        # TODO move these to another queue/function to avoid the need for a secret
        if event['secret'] != os.environ['winner_secret']:
            raise ValueError('pick_winner attempted with invalid shared secret')
        return lottery.pick_winner(settings.botos, winner_override_address=event.get('winner_override_address'))
    if isinstance(event, collections.Mapping) and event.get('action') == 'send_post':
        if event['secret'] != os.environ['winner_secret']:
            raise ValueError('send_post attempted with invalid shared secret')
        return lottery.send_post(settings.botos, dry_run=event.get('dry_run', True))

    queue = settings.botos.resource('sqs').Queue(settings.post_queue_url)
    results = []

    start_time = datetime.datetime.now()
    while (datetime.datetime.now() - start_time).total_seconds() < settings.ingest_soft_timeout_secs:
        logger.info('receiving messages')
        messages = queue.receive_messages(
            MaxNumberOfMessages=10,
            WaitTimeSeconds=settings.queue_wait_secs,
        )

        for message in messages:
            try:
                body = message.body
                logger.info("received %r", body)
                event = lottery.PostEvent.from_json(body)
                logger.info("event is %r", event)
                if event.action == 'submit':
                    result = lottery.submit_post(settings.botos, event.address_id, event.winner_nonce, event.post_contents, event.subject)
                else:
                    raise ValueError("unknown action: %r" % event.action)
            except:  # noqa: E722
                logger.exception("failed to process message %r", body)
                raven_client.captureException(
                    extra={'body': body},
                )
            else:
                message.delete()
                results.append(result)
                logger.info("handled %r successfully: %r", event, result)

    return {'results': results}
