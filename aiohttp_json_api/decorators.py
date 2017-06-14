"""
Handlers decorators
===================
"""
from functools import wraps

from aiohttp import web
from boltons.iterutils import first

from .context import RequestContext
from .errors import HTTPUnsupportedMediaType
from .const import JSONAPI, JSONAPI_CONTENT_TYPE


def jsonapi_content(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        request = kwargs.get('request')
        if request is None:
            request = first(args, key=lambda v: isinstance(v, web.Request))
        context = request[JSONAPI]
        assert context and isinstance(context, RequestContext)

        if context.request.content_type != JSONAPI_CONTENT_TYPE:
            raise HTTPUnsupportedMediaType(
                detail=f"Only '{JSONAPI_CONTENT_TYPE}' "
                       f"content-type is acceptable."
            )
        return await handler(*args, **kwargs)
    return wrapper
