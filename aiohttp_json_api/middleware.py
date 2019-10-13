"""Middleware."""
from aiohttp import hdrs, web, http

from aiohttp_json_api import VERSION
from aiohttp_json_api.common import JSONAPI, JSONAPI_CONTENT_TYPE, JSONAPI_CONTENT_TYPE_PARSED, logger
from aiohttp_json_api.errors import Error, ErrorList, HTTPUnsupportedMediaType, HTTPNotAcceptable
from aiohttp_json_api.helpers import best_match, get_mime_type_params
from aiohttp_json_api.typings import CallableHandler
from aiohttp_json_api.utils import error_to_response


@web.middleware
async def jsonapi_middleware(request: web.Request, handler: CallableHandler) -> web.StreamResponse:
    """Middleware for handling JSON API errors."""
    logger.debug('[aiohttp-json-api middleware] Start')
    try:
        route_name = request.match_info.route.name
        namespace = request.app[JSONAPI]['routes_namespace']

        valid_json_api_request = False

        if route_name and route_name.startswith(f'{namespace}.'):
            request_ct = request.headers.get(hdrs.CONTENT_TYPE)
            logger.debug('[aiohttp-json-api middleware] Route name: %s', route_name)

            content_type_error = f"Content-Type '{JSONAPI_CONTENT_TYPE}' is required."
            if request_ct is None and request.can_read_body:
                raise HTTPUnsupportedMediaType(detail=content_type_error)

            if request_ct is not None and request_ct != JSONAPI_CONTENT_TYPE:
                raise HTTPUnsupportedMediaType(detail=content_type_error)

            accept_header = request.headers.get(hdrs.ACCEPT, '*/*')
            matched_mt, parsed_mt = best_match((JSONAPI_CONTENT_TYPE,), accept_header)
            logger.debug(
                '[aiohttp-json-api middleware] Negotiation. Accept: %s. Matched: %s (%s)',
                accept_header, matched_mt, parsed_mt,
            )
            if matched_mt != JSONAPI_CONTENT_TYPE:
                raise HTTPNotAcceptable()

            if parsed_mt and JSONAPI_CONTENT_TYPE_PARSED[:2] == parsed_mt[:2]:
                additional_params = get_mime_type_params(parsed_mt)
                if additional_params:
                    formatted = ','.join(f'{k}={v}' for k, v in additional_params.items())
                    detail = f'JSON API media type is modified with media type parameters. ({formatted})'
                    raise HTTPNotAcceptable(detail=detail)

            logger.debug('[aiohttp-json-api middleware] Request is valid JSON API request.')
            valid_json_api_request = True

        response = await handler(request)

        if valid_json_api_request:
            response.headers.setdefault(hdrs.SERVER, f'{http.SERVER_SOFTWARE} aiohttp-json-api/{VERSION}')

        return response
    except Exception as exc:
        if isinstance(exc, (Error, ErrorList)):
            if request.app[JSONAPI]['log_errors']:
                logger.exception(exc)
            return error_to_response(request, exc)
        else:
            raise
