# -*- coding: utf-8 -*-
import datetime
import logging

from raven.contrib.awslambda import LambdaClient

from kleroteria import settings, subscription  # noqa: E402

# https://gist.github.com/niranjv/fb95e716151642e8ca553b0e38dd152e#gistcomment-2302572
FORMAT = '%(levelname)s: %(asctime)s - %(name)s (%(module)s:%(lineno)s): %(message)s'
logger = logging.getLogger()
for h in logger.handlers:
    h.setFormatter(logging.Formatter(FORMAT))
logger.setLevel(logging.WARNING)

logger = logging.getLogger('kleroteria.list_ingest')

raven_client = LambdaClient(
    include_paths=['kleroteria', 'task'],
)


@raven_client.capture_exceptions
def handler(event, context):
    queue = settings.botos.resource('sqs').Queue(settings.list_queue_url)
    results = []

    start_time = datetime.datetime.now()
    while (datetime.datetime.now() - start_time).total_seconds() < settings.ingest_soft_timeout_secs:
        logger.info('receiving messages')
        messages = queue.receive_messages(
            MaxNumberOfMessages=10,
            WaitTimeSeconds=settings.queue_wait_secs,
            AttributeNames=['All'],
        )

        for message in messages:
            try:
                logger.info("attributes %r", message.attributes)
                body = message.body
                logger.info("body %r", body)
                event = subscription.ListEvent.from_json(body)
                logger.info("event is %r", event)
                if event.action == 'subscribe':
                    result = subscription.subscribe(settings.botos, event.address, event.honeypot)
                elif event.action == 'unsubscribe':
                    result = subscription.unsubscribe(settings.botos, event.address, event.address_id)
                else:
                    raise ValueError("unknown action: %r" % event.action)
            except subscription.InvalidEmail:
                logger.warning("skipping invalid email from %r", body)
                raven_client.captureException(
                    extra={'body': body},
                )
                message.delete()
            except:  # noqa: E722
                logger.exception("failed to process message %r", body)
                raven_client.captureException(
                    extra={'body': body},
                )
            else:
                message.delete()
                results.append(result)
                logger.info("handled %r successfully: %r", event, result)

    # I'm not sure if this is a localstack bug, but this needs to be a dict.
    return {'results': results}
