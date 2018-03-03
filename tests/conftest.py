import json
import socket
import uuid

import docker as libdocker
import pathlib

import invoke
import psycopg2
import pytest
import time
from jsonschema import Draft4Validator

DSN_FORMAT = 'postgresql://{user}:{password}@{host}:{port}/{dbname}'


@pytest.fixture(scope='session')
def session_id():
    return str(uuid.uuid4())


@pytest.fixture(scope='session')
def docker():
    return libdocker.APIClient()


@pytest.fixture(scope='session')
def unused_port():
    def f():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]

    return f


@pytest.fixture(scope='session')
def here():
    return pathlib.Path(__file__).parent


@pytest.yield_fixture(scope='session')
def pg_server(unused_port, session_id, docker):
    docker_image = 'postgres:10-alpine'
    database = 'example'
    user = 'example'
    password = 'somepassword'

    port = unused_port()
    host_config_options = {'port_bindings': {5432: port}}

    host_config = dict(
        tmpfs={'/var/lib/postgresql/data': ''},
        **host_config_options
    )

    docker.pull(docker_image)
    container = docker.create_container(
        image=docker_image,
        name=f'test-fantasy-example-{session_id}',
        ports=[5432],
        detach=True,
        environment={
            'POSTGRES_USER': user,
            'POSTGRES_PASSWORD': password
        },
        host_config=docker.create_host_config(**host_config)
    )
    docker.start(container=container['Id'])

    host = '0.0.0.0'

    pg_params = dict(dbname=database,
                     user=user,
                     password=password,
                     host=host,
                     port=port,
                     connect_timeout=2)

    delay = 0.001
    for i in range(20):
        try:
            conn = psycopg2.connect(**pg_params)
            conn.close()
            break
        except psycopg2.Error:
            time.sleep(delay)
            delay *= 2
    else:
        pytest.fail("Cannot start postgres server")

    inspection = docker.inspect_container(container['Id'])
    container['host'] = inspection['NetworkSettings']['IPAddress']
    container['port'] = 5432
    container['pg_params'] = pg_params

    yield container

    docker.kill(container=container['Id'])
    docker.remove_container(container['Id'])


@pytest.fixture(scope='session')
def pg_params(pg_server):
    return dict(**pg_server['pg_params'])


@pytest.fixture(scope='session')
def populated_db(here, pg_params):
    from examples.fantasy.tasks import populate_db

    populate_db(
        invoke.context.Context(),
        data_folder=here.parent / 'examples' / 'fantasy' / 'fantasy-database',
        dsn=DSN_FORMAT.format(**pg_params)
    )


@pytest.fixture(scope='session')
def jsonapi_validator(here):
    path = here / 'integration' / 'schema.dms'
    with open(path) as fp:
        schema = json.load(fp)

    Draft4Validator.check_schema(schema)
    return Draft4Validator(schema)


@pytest.fixture
async def fantasy_app(loop, pg_params, populated_db):
    from examples.fantasy.main import init
    return await init(DSN_FORMAT.format(**pg_params), debug=False, loop=loop)


@pytest.fixture
async def fantasy_client(fantasy_app, test_client):
    return await test_client(fantasy_app)
