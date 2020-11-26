import pytest


@pytest.fixture(scope='session', autouse=True)
def localstack():
    from localstack.services import infra
    infra.start_infra(
        asynchronous=True,
        apis=[
            'ses', 'lambda', 'sqs', 'dynamodb',
            'cloudwatch',  # required for lambda to work
        ],
    )
    yield
    infra.stop_infra()


@pytest.fixture(scope='session')
def botos():
    from kleroteria import settings
    from . import aws_fixtures
    aws_fixtures.create(settings.botos, with_lambda=False)
    return settings.botos


def _lambda_fixture(name):
    from kleroteria import settings
    from . import aws_fixtures
    aws_fixtures.create_lambda(settings.botos, names=[name])


@pytest.fixture(scope='session')
def list_ingest():
    _lambda_fixture('list_ingest')


@pytest.fixture(scope='session')
def post_ingest():
    _lambda_fixture('post_ingest')


@pytest.fixture(scope='session')
def manual_email():
    _lambda_fixture('manual_email')
