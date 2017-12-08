"""Handlers decorators."""
from functools import wraps

from aiohttp import hdrs, web

from .common import JSONAPI, JSONAPI_CONTENT_TYPE
from .errors import HTTPNotAcceptable, HTTPUnsupportedMediaType


def jsonapi_handler(handler):
    """
    JSON API handler decorator.

    Used for content type negotiation, create request context,
    check existence of controller for current request.
    """
    @wraps(handler)
    async def wrapper(request: web.Request):
        """JSON API handler wrapper."""
        request_ct = request.headers.get(hdrs.CONTENT_TYPE)

        content_type_error = \
            "Content-Type '{}' is required.".format(JSONAPI_CONTENT_TYPE)
        mutation_methods = ('POST', 'PATCH', 'DELETE')

        if request_ct is None and request.method in mutation_methods:
            raise HTTPUnsupportedMediaType(detail=content_type_error)

        if request_ct is not None and request_ct != JSONAPI_CONTENT_TYPE:
            raise HTTPUnsupportedMediaType(detail=content_type_error)

        request_accept = request.headers.get(hdrs.ACCEPT, '*/*')
        if request_accept != '*/*' and request_accept != JSONAPI_CONTENT_TYPE:
            raise HTTPNotAcceptable()

        route_name = request.match_info.route.name
        namespace = request.app[JSONAPI]['routes_namespace']

        if not route_name or not route_name.startswith('%s.' % namespace):
            raise RuntimeError('Request route must be named and use namespace '
                               '"{0}.* (e.g. {0}.resource)"'.format(namespace))

        return await handler(request)

    return wrapper
