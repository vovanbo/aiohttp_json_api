"""Handlers decorators."""
from functools import partial, wraps

from aiohttp import hdrs, web

from .common import JSONAPI, JSONAPI_CONTENT_TYPE, logger
from .errors import HTTPNotAcceptable, HTTPNotFound, HTTPUnsupportedMediaType


def jsonapi_handler(handler=None, resource_type=None,
                    content_type=JSONAPI_CONTENT_TYPE):
    """Decorates JSON API handlers to pass request context etc."""
    if handler is None:
        return partial(jsonapi_handler,
                       resource_type=resource_type, content_type=content_type)

    @wraps(handler)
    async def wrapper(request: web.Request):
        """JSON API handler wrapper."""
        if request.method in ('POST', 'PATCH'):
            request_content_type = request.content_type
        else:
            request_content_type = request.headers.get(hdrs.ACCEPT,
                                                       request.content_type)

        if request_content_type.startswith(content_type) and \
            request_content_type != content_type:
            raise HTTPNotAcceptable()
        elif request_content_type != content_type:
            raise HTTPUnsupportedMediaType(
                detail="Content-Type '{}' is required.".format(content_type))

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
        return await handler(request, context, context.schema)
    return wrapper
