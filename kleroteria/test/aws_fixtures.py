import os

from aws_lambda import aws_lambda

from kleroteria import settings


def create_dynamo(botos):
    dbc = botos.client('dynamodb')
    dbc.create_table(
        TableName='k8aAddresses2',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH',
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )

    dbc.create_table(
        TableName='k8aPosts',
        KeySchema=[
            {
                'AttributeName': 'id',
                'KeyType': 'HASH',
            },
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'id',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1,
        }
    )


def create_sqs(botos):
    botos.client('sqs').create_queue(QueueName='k8aListQueue')
    botos.client('sqs').create_queue(QueueName='k8aPostQueue')


def create_lambda(botos, names=None):
    def local_get_client(c, *args, **kwargs):
        return botos.client(c)

    def local_get_account(*args, **kwargs):
        return '000000000000'

    aws_lambda.get_client = local_get_client
    aws_lambda.get_account_id = local_get_account

    here = os.path.dirname(os.path.realpath(__file__))

    if names is None:
        names = ['list_ingest', 'post_ingest', 'manual_email']

    for func_name in names:
        src = os.path.join(here, os.pardir, os.pardir, 'lambdas', func_name)
        requirements = os.path.join(here, os.pardir, os.pardir, 'lambda-requirements.txt')

        cfg = aws_lambda.read_cfg(os.path.join(src, 'config.yaml'), None)
        cfg['role'] = 'lambda-test-role'

        path_to_zip_file = aws_lambda.build(
            src, config_file='config.yaml',
            requirements=requirements,
        )
        aws_lambda.create_function(cfg, path_to_zip_file)


def create_ses(botos):
    ses = botos.client('ses')
    for sender_email in [settings.noreply_k8a_email, settings.admin_email]:
        ses.verify_email_identity(
            EmailAddress=sender_email,
        )
    ses.verify_domain_identity(
        Domain='kleroteria.org',
    )


def create(botos, with_lambda=True):
    create_ses(botos)
    create_dynamo(botos)
    create_sqs(botos)
    if with_lambda:
        create_lambda(botos)


if __name__ == '__main__':
    create(settings.botos)
