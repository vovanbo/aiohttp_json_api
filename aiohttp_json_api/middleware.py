"""Middleware."""
from aiohttp import hdrs

from .common import (
    JSONAPI, JSONAPI_CONTENT_TYPE, JSONAPI_CONTENT_TYPE_PARSED,
    logger
)
from .errors import (
    Error, ErrorList, HTTPUnsupportedMediaType, HTTPNotAcceptable
)
from .helpers import best_match, get_mime_type_params
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

                accept_header = request.headers.get(hdrs.ACCEPT, '*/*')
                matched_mt, parsed_mt = best_match(
                    (JSONAPI_CONTENT_TYPE,), accept_header
                )
                if matched_mt != JSONAPI_CONTENT_TYPE:
                    raise HTTPNotAcceptable()

                if JSONAPI_CONTENT_TYPE_PARSED[:2] == parsed_mt[:2]:
                    additional_params = get_mime_type_params(parsed_mt)
                    if additional_params:
                        formatted = ','.join(
                            '{}={}'.format(k, v)
                            for k, v in additional_params.items()
                        )
                        detail = (
                            'JSON API media type is modified with media '
                            'type parameters. ({})'.format(formatted)
                        )
                        raise HTTPNotAcceptable(detail=detail)

            return await handler(request)
        except Exception as exc:
            if isinstance(exc, (Error, ErrorList)):
                if app[JSONAPI]['log_errors']:
                    logger.exception(exc)
                return error_to_response(request, exc)
            else:
                raise

    return middleware_handler
