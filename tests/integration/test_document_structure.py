import pytest

from aiohttp_json_api.common import JSONAPI_CONTENT_TYPE


class TestDocumentStructure:
    """Document Structure"""

    @pytest.mark.parametrize(
        'resource_type',
        ('authors', 'books', 'chapters', 'photos', 'stores')
    )
    async def test_response_by_json_schema(self, fantasy_client,
                                           jsonapi_validator, resource_type):
        response = await fantasy_client.get('/api/{}'.format(resource_type))
        json = await response.json(content_type=JSONAPI_CONTENT_TYPE)
        assert jsonapi_validator.is_valid(json)


