import pytest
from aiohttp import hdrs
from jsonpointer import resolve_pointer

from aiohttp_json_api.common import JSONAPI_CONTENT_TYPE


@pytest.mark.parametrize(
    'resource_type',
    ('authors', 'books', 'chapters', 'photos', 'stores')
)
async def test_spec_schema(test_client, fantasy_app, jsonapi_validator,
                           resource_type):
    client = await test_client(fantasy_app)
    response = await client.get('/api/{}'.format(resource_type))
    json = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    assert jsonapi_validator.is_valid(json)


async def test_content_negotiation(test_client, fantasy_app):
    client = await test_client(fantasy_app)
    response = await client.get(
        '/api/books/1',
        headers={hdrs.ACCEPT: 'application/vnd.api+json'}
    )
    assert response.status == 200
    assert response.headers[hdrs.CONTENT_TYPE] == 'application/vnd.api+json'

    response = await client.get(
        '/api/books/1',
        headers={hdrs.CONTENT_TYPE: 'application/vnd.api+json; foo=bar'}
    )
    assert response.status == 415

    response = await client.get(
        '/api/books/1',
        headers={hdrs.ACCEPT: 'application/vnd.api+json; foo=bar'}
    )
    assert response.status == 406


async def test_fetch_single_resource(test_client, fantasy_app):
    client = await test_client(fantasy_app)
    response = await client.get(
        '/api/books/1',
        headers={hdrs.ACCEPT: 'application/vnd.api+json'}
    )
    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)

    assert response.status == 200
    assert resolve_pointer(data, '/data/type') == 'books'
    assert resolve_pointer(data, '/data/id') == '1'
    assert resolve_pointer(data, '/data/attributes/title') == \
           'The Fellowship of the Ring'
    assert resolve_pointer(data, '/data/relationships/author')
    assert resolve_pointer(data, '/data/relationships/series')
    assert resolve_pointer(data, '/data/links/self')


async def test_fetch_resource_not_found(test_client, fantasy_app):
    client = await test_client(fantasy_app)
    response = await client.get(
        '/api/books/999999',
        headers={hdrs.ACCEPT: 'application/vnd.api+json'}
    )
    assert response.status == 404


async def test_fetch_bad_request(test_client, fantasy_app):
    client = await test_client(fantasy_app)
    response = await client.get(
        '/api/books/foo',
        headers={hdrs.ACCEPT: 'application/vnd.api+json'}
    )
    assert response.status == 400
