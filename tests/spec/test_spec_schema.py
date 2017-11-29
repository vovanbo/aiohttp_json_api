import pytest
from aiohttp import hdrs

from aiohttp_json_api.common import JSONAPI_CONTENT_TYPE


@pytest.mark.parametrize(
    'resource_type',
    ('authors', 'books', 'chapters', 'photos', 'stores')
)
async def test_spec_schema(test_client, fantasy_app, jsonapi_validator,
                           resource_type):
    client = await test_client(fantasy_app)
    response = await client.get(f'/api/{resource_type}')
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
