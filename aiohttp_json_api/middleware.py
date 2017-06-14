"""
Middlewares
===========
"""
from .const import JSONAPI
from .log import logger


async def jsonapi_middleware(app, handler):
    async def middleware_handler(request):
        route_name = request.match_info.route.name
        if route_name and route_name.startswith('jsonapi'):
            context_class = app[JSONAPI]['context_class']
            context = context_class(request)
            request[JSONAPI] = context
            if context.schema is None:
                logger.warning('No schema for request %s', request.url)

        return await handler(request)

    return middleware_handler
