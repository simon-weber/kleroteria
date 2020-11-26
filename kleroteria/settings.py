import os

is_prod = os.environ.get('k8a_env') == 'production'

# TODO it's weird that these values are sometimes injected
# and sometimes referenced directly

noreply_k8a_email = '"Kleroteria" <noreply@kleroteria.org>'
bounce_email = os.environ['BOUNCE_EMAIL']
reply_to_email = '"noreply.zone" <noreply@devnull.noreply.zone>'

# Take care when sending to this email: it's forwarded so from/to may be unexpected.
# Prefer personal_email when testing sending.
admin_email = '"Simon at Kleroteria" <simon@kleroteria.org>'
personal_email = 'simon@simonmweber.com'

_here = os.path.dirname(os.path.realpath(__file__))
_template_path = os.path.join(_here, 'templates', 'email.html')
with open(_template_path) as f:
    email_template = f.read()

if is_prod:
    import boto3.session
    botos = boto3.session.Session()
    list_queue_url = 'https://sqs.us-east-1.amazonaws.com/022190504632/k8aListQueue'
    post_queue_url = 'https://sqs.us-east-1.amazonaws.com/022190504632/k8aPostQueue'
    url_prefix = 'https://kleroteria.org'
    queue_wait_secs = 10
    ingest_soft_timeout_secs = 30
else:
    import localstack_client.session
    botos = localstack_client.session.Session()
    list_queue_url = 'http://localhost:4576/queue/k8aListQueue'
    post_queue_url = 'http://localhost:4576/queue/k8aPostQueue'
    url_prefix = 'http://127.0.0.1:4000'
    queue_wait_secs = 1
    ingest_soft_timeout_secs = 1
