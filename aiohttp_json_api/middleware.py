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
            return await handler(request)
        except Exception as exc:
            if isinstance(exc, (Error, ErrorList)):
                if app[JSONAPI]['log_errors']:
                    logger.exception(exc)
                return error_to_response(request, exc)
            else:
                raise

    return middleware_handler
