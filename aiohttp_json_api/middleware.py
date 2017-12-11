"""Middleware."""
from aiohttp import hdrs

from .common import JSONAPI, JSONAPI_CONTENT_TYPE, logger
from .errors import (
    Error, ErrorList, HTTPUnsupportedMediaType, HTTPNotAcceptable
)
from .utils import error_to_response


async def jsonapi_middleware(app, handler):
    """Middleware for handling JSON API errors."""
    async def middleware_handler(request):
        try:
            route_name = request.match_info.route.name
            namespace = request.app[JSONAPI]['routes_namespace']

            if route_name and route_name.startswith('%s.' % namespace):
                request_ct = request.headers.get(hdrs.CONTENT_TYPE)

                content_type_error = \
                    "Content-Type '{}' is required.".format(
                        JSONAPI_CONTENT_TYPE)

                if request_ct is None and request.has_body:
                    raise HTTPUnsupportedMediaType(detail=content_type_error)

                if (request_ct is not None and
                    request_ct != JSONAPI_CONTENT_TYPE):
                    raise HTTPUnsupportedMediaType(detail=content_type_error)

                request_accept = request.headers.get(hdrs.ACCEPT, '*/*')
                if (request_accept != '*/*' and
                    request_accept != JSONAPI_CONTENT_TYPE):
                    raise HTTPNotAcceptable()

            return await handler(request)
        except Exception as exc:
            if isinstance(exc, (Error, ErrorList)):
                if app[JSONAPI]['log_errors']:
                    logger.exception(exc)
                return error_to_response(request, exc)
            else:
                raise

    return middleware_handler
