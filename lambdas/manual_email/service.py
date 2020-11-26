# -*- coding: utf-8 -*-
import logging

from raven.contrib.awslambda import LambdaClient

from kleroteria import settings, subscription

# https://gist.github.com/niranjv/fb95e716151642e8ca553b0e38dd152e#gistcomment-2302572
FORMAT = '%(levelname)s: %(asctime)s - %(name)s (%(module)s:%(lineno)s): %(message)s'
logger = logging.getLogger()
for h in logger.handlers:
    h.setFormatter(logging.Formatter(FORMAT))
logger.setLevel(logging.WARNING)

logger = logging.getLogger('kleroteria.manual_email')

raven_client = LambdaClient(
    include_paths=['kleroteria', 'task'],
)


@raven_client.capture_exceptions
def handler(event, context):
    kwargs = event.copy()
    kwargs['botos'] = settings.botos

    logger.info('running with %r', kwargs)
    results = subscription.send_manual_email(**kwargs)
    return {'results': results}
