import logging

from .const import JSONAPI
from .context import RequestContext

logger = logging.getLogger(__name__)


async def jsonapi_middleware(app, handler):
    async def middleware_handler(request):
        route_name = request.match_info.route.name
        if route_name and route_name.startswith('jsonapi'):
            context = RequestContext(request)
            request[JSONAPI] = context
            if context.schema is None:
                logger.warning('No schema for request %s', request.url)

        return await handler(request)

    return middleware_handler
