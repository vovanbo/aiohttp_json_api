"""
Handlers decorators
===================
"""
from functools import partial, wraps

from aiohttp import web

from .const import JSONAPI
from .errors import HTTPUnsupportedMediaType, HTTPNotFound
from .log import logger


def jsonapi_handler(handler=None, resource_type=None, content_type=None):
    if handler is None:
        return partial(jsonapi_handler,
                       resource_type=resource_type, content_type=content_type)

    @wraps(handler)
    async def wrapper(request: web.Request):
        route_name = request.match_info.route.name
        namespace = request.app[JSONAPI]['routes_namespace']

        if not route_name or not route_name.startswith('%s.' % namespace):
            raise RuntimeError('Request route must be named and use namespace '
                               '"{}.*"'.format(namespace))

        context_class = request.app[JSONAPI]['context_class']
        type_ = resource_type or request.match_info.get('type', None)
        if type_ is None:
            # If type is not found in URI, and type is not passed
            # via decorator to custom handler, then raise HTTP 404
            raise HTTPNotFound()

        context = context_class(request, type_)
        if context.schema is None:
            logger.error('No schema for request %s', request.url)
            raise HTTPNotFound()

        request[JSONAPI] = context

        if content_type is not None and request.content_type != content_type:
            raise HTTPUnsupportedMediaType(
                detail="Only '{}' Content-Type is acceptable "
                       "for this method.".format(content_type)
            )
        return await handler(request, context, context.schema)
    return wrapper
