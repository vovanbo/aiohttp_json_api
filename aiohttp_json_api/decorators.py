from functools import wraps

from boltons.iterutils import first

from .context import RequestContext
from .errors import HTTPUnsupportedMediaType
from .const import JSONAPI_CONTENT_TYPE


def jsonapi_content(handler):
    @wraps(handler)
    async def wrapper(*args, **kwargs):
        context = kwargs.get('context')
        if context is None:
            context = first(args, key=lambda v: isinstance(v, RequestContext))
        assert context

        if context.request.content_type != JSONAPI_CONTENT_TYPE:
            raise HTTPUnsupportedMediaType(
                detail=f"Only '{JSONAPI_CONTENT_TYPE}' "
                       f"content-type is acceptable."
            )
        return await handler(*args, **kwargs)
    return wrapper
