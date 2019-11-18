from typing import MutableMapping

import pytest

from aiohttp_json_api.common import JSONAPI_CONTENT_TYPE


@pytest.mark.parametrize('url', [
    '/api/books',
    '/api/books/1',
    '/api/books/1/author',
    '/api/books/1/chapters',
])
async def test_document_top_level_is_json_object(fantasy_client, url):
    """
    A JSON object **MUST** be at the root of every JSON API request and response containing data.
    This object defines a document's "top level".
    """
    response = await fantasy_client.get(url)
    json = await response.json(content_type=JSONAPI_CONTENT_TYPE)
    assert response.status == 200
    assert isinstance(json, MutableMapping)
