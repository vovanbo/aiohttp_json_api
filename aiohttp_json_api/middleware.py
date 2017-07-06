"""
Middlewares
===========
"""
from .errors import Error, ErrorList
from .const import JSONAPI
from .log import logger
from .utils import error_to_response


async def jsonapi_middleware(app, handler):
    async def middleware_handler(request):
        try:
            route_name = request.match_info.route.name
            if route_name and route_name.startswith('jsonapi'):
                context_class = app[JSONAPI]['context_class']
                context = context_class(request)
                request[JSONAPI] = context
                if context.schema is None:
                    logger.warning('No schema for request %s', request.url)

            return await handler(request)
        except Exception as exc:
            if isinstance(exc, (Error, ErrorList)):
                if app[JSONAPI]['log_errors']:
                    logger.exception(exc)
                return error_to_response(request, exc)
            else:
                raise

    return middleware_handler
