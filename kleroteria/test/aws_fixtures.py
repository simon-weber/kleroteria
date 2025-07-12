import os
import time

from aws_lambda import aws_lambda

from kleroteria import settings


def create_dynamo(botos):
    dbc = botos.client('dynamodb')

    try:
        dbc.delete_table(TableName='k8aAddresses2')
    except dbc.exceptions.ResourceNotFoundException:
        pass
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

    try:
        dbc.delete_table(TableName='k8aPosts')
    except dbc.exceptions.ResourceNotFoundException:
        pass
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
    sqsc = botos.client('sqs')

    res = sqsc.create_queue(QueueName='k8aListQueue')
    sqsc.purge_queue(QueueUrl=res['QueueUrl'])

    res = sqsc.create_queue(QueueName='k8aPostQueue')
    sqsc.purge_queue(QueueUrl=res['QueueUrl'])


def create_lambda(botos, names=None):
    def local_get_client(c, *args, **kwargs):
        return botos.client(c)

    def local_get_account(*args, **kwargs):
        return '000000000000'

    aws_lambda.get_client = local_get_client
    aws_lambda.get_account_id = local_get_account
    lc = botos.client('lambda')

    here = os.path.dirname(os.path.realpath(__file__))

    if names is None:
        names = ['list_ingest', 'post_ingest', 'manual_email']

    for func_name in names:
        exists = False
        try:
            lc.get_function(FunctionName=func_name)
        except lc.exceptions.ResourceNotFoundException:
            pass
        else:
            exists = True

        src = os.path.join(here, os.pardir, os.pardir, 'lambdas', func_name)
        requirements = os.path.join(here, os.pardir, os.pardir, 'lambda-requirements.txt')

        cfg = aws_lambda.read_cfg(os.path.join(src, 'config.yaml'), None)
        cfg['role'] = 'lambda-test-role'

        path_to_zip_file = aws_lambda.build(
            src, config_file='config.yaml',
            requirements=requirements,
        )
        if not exists:
            aws_lambda.create_function(cfg, path_to_zip_file)
        else:
            aws_lambda.update_function(cfg, path_to_zip_file, cfg)

    # Wait on the last function to be active.
    time.sleep(2)

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

def main():
    create(settings.botos)
