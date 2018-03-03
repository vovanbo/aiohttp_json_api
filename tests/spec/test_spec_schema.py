from collections import MutableMapping

from aiohttp import hdrs
from jsonpointer import resolve_pointer

from aiohttp_json_api.common import JSONAPI_CONTENT_TYPE, JSONAPI
from aiohttp_json_api.helpers import MISSING, get_router_resource

GET_HEADERS = {hdrs.ACCEPT: JSONAPI_CONTENT_TYPE}


async def test_fetch_single_resource(fantasy_client):
    response = await fantasy_client.get('/api/books/1', headers=GET_HEADERS)
    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)

    assert response.status == 200
    assert isinstance(resolve_pointer(data, '/data'), MutableMapping)

    assert isinstance(resolve_pointer(data, '/data/type'), str)
    assert resolve_pointer(data, '/data/type') == 'books'

    assert isinstance(resolve_pointer(data, '/data/id'), str)
    assert resolve_pointer(data, '/data/id') == '1'

    assert resolve_pointer(data, '/data/attributes/title') == \
           'The Fellowship of the Ring'

    assert isinstance(resolve_pointer(data, '/data/relationships/author'),
                      MutableMapping)
    assert resolve_pointer(data, '/data/relationships/author')

    assert isinstance(resolve_pointer(data, '/data/relationships/series'),
                      MutableMapping)
    assert resolve_pointer(data, '/data/relationships/series')
    assert resolve_pointer(data, '/data/links/self')


async def test_fetch_resource_not_found(fantasy_client):
    response = await fantasy_client.get('/api/books/9999', headers=GET_HEADERS)
    assert response.status == 404


async def test_fetch_bad_request(fantasy_client):
    response = await fantasy_client.get('/api/books/foo', headers=GET_HEADERS)
    assert response.status == 400


async def test_fetch_collection(fantasy_client):
    response = await fantasy_client.get('/api/books', headers=GET_HEADERS)
    assert response.status == 200
    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    books = resolve_pointer(data, '/data')
    for index in range(len(books)):
        assert resolve_pointer(data, f'/data/{index}/type') == 'books'


async def test_fetch_single_resource_with_includes(fantasy_client):
    response = await fantasy_client.get('/api/books/1?include=author',
                                        headers=GET_HEADERS)
    assert response.status == 200

    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    assert resolve_pointer(data, '/data/type') == 'books'
    assert resolve_pointer(data, '/data/id') == '1'

    author_relationship = \
        resolve_pointer(data, '/data/relationships/author/data')
    assert author_relationship['id'] == '1'
    assert author_relationship['type'] == 'authors'

    assert resolve_pointer(data, '/data/relationships/series')

    author = resolve_pointer(data, '/included/0')
    assert author['id'] == author_relationship['id']
    assert author['type'] == author_relationship['type']


async def test_fetch_single_resource_with_includes_and_fields(fantasy_client):
    response = await fantasy_client.get(
        '/api/books/1?include=author&fields[books]=title',
        headers=GET_HEADERS
    )
    assert response.status == 200

    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    assert resolve_pointer(data, '/data/type') == 'books'
    assert resolve_pointer(data, '/data/id') == '1'
    assert resolve_pointer(data, '/data/attributes/title') == \
           'The Fellowship of the Ring'
    assert resolve_pointer(data, '/data/attributes/date_published', MISSING) \
           is MISSING

    for relationships in ('author', 'series'):
        assert resolve_pointer(
            data, f'/data/relationships/{relationships}', MISSING
        ) is MISSING

    author = resolve_pointer(data, '/included/0')
    assert author['id'] == '1'
    assert author['type'] == 'authors'


async def test_jsonapi_object_spec(fantasy_client):
    response = await fantasy_client.get('/api/books/1', headers=GET_HEADERS)
    assert response.status == 200

    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    assert resolve_pointer(data, '/jsonapi/version') == '1.0'


async def test_links_spec(fantasy_client, fantasy_app):
    response = await fantasy_client.get('/api/books/1', headers=GET_HEADERS)
    assert response.status == 200

    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    book_url = (
        get_router_resource(fantasy_app, 'resource')
        .url_for(type='books', id='1')
    )
    book_url = fantasy_client.make_url(book_url)

    assert resolve_pointer(data, '/links/self') == str(book_url)


async def test_meta_object(fantasy_client, fantasy_app):
    response = await fantasy_client.get('/api/books/1', headers=GET_HEADERS)
    assert response.status == 200

    data = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    meta_object = fantasy_app[JSONAPI]['meta']
    assert resolve_pointer(data, '/meta') == meta_object
    assert resolve_pointer(data, '/meta/fantasy/version') == '0.0.1'
