from aiohttp import hdrs


class TestContentNegotiation:
    """Content Negotiation"""

    async def test_request_content_type(self, fantasy_client):
        """
        Clients **MUST** send all JSON API data in request documents with
        the header `Content-Type: application/vnd.api+json` without any media
        type parameters.
        """
        pass

    async def test_request_accept(self):
        """
        Clients that include the JSON API media type in their `Accept` header
        **MUST** specify the media type there at least once without any media
        type parameters.
        """
        pass

    async def test_response_ignore_parameters(self):
        """
        Clients **MUST** ignore any parameters for the
        `application/vnd.api+json` media type received in the `Content-Type`
        header of response documents.
        """
        pass

    async def test_response_content_type(self, fantasy_client):
        """
        Servers **MUST** send all JSON API data in response documents with
        the header `Content-Type: application/vnd.api+json` without any media
        type parameters.
        """
        response = await fantasy_client.get('/api/books/1')
        assert response.status == 200
        assert response.headers[hdrs.CONTENT_TYPE] == \
               'application/vnd.api+json'

    async def test_response_unsupported_media_type(self, fantasy_client):
        """
        Servers **MUST** respond with a `415 Unsupported Media Type` status
        code if a request specifies the header
        `Content-Type: application/vnd.api+json` with any media type
        parameters.
        """
        response = await fantasy_client.post(
            '/api/books',
            json={},
            headers={hdrs.CONTENT_TYPE: 'application/vnd.api+json; foo=bar'}
        )
        assert response.status == 415

    async def test_response_not_acceptable(self, fantasy_client):
        """
        Servers **MUST** respond with a `406 Not Acceptable` status code
        if a request's `Accept` header contains the JSON API media type and
        all instances of that media type are modified with media type
        parameters.
        """
        response = await fantasy_client.get(
            '/api/books/1',
            headers={hdrs.ACCEPT: 'application/vnd.api+json; foo=bar'}
        )
        assert response.status == 406

