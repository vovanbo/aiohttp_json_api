# -*- coding: utf-8 -*-
__author__ = """Vladimir Bolshakov"""
__email__ = 'vovanbo@gmail.com'
__version__ = '0.15.0'


def setup_jsonapi(app, schemas, *, base_path='/api', version='1.0.0',
                  meta=None, context_class=None, registry_class=None,
                  custom_handlers=None, log_errors=True):
    """
    Setup JSON API in aiohttp application

    Default setup of resources, routes and handlers:

    =====================  ======  =========================================  ======================================================
    Resource name          Method  Route                                      Handler
    =====================  ======  =========================================  ======================================================
    jsonapi.collection     GET     ``/{type}``                                :func:`~aiohttp_json_api.handlers.get_collection`
    jsonapi.collection     POST    ``/{type}``                                :func:`~aiohttp_json_api.handlers.post_resource`
    jsonapi.resource       GET     ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.get_resource`
    jsonapi.resource       PATCH   ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.patch_resource`
    jsonapi.resource       DELETE  ``/{type}/{id}``                           :func:`~aiohttp_json_api.handlers.delete_resource`
    jsonapi.relationships  GET     ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.get_relationship`
    jsonapi.relationships  POST    ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.post_relationship`
    jsonapi.relationships  PATCH   ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.patch_relationship`
    jsonapi.relationships  DELETE  ``/{type}/{id}/relationships/{relation}``  :func:`~aiohttp_json_api.handlers.delete_relationship`
    jsonapi.related        GET     ``/{type}/{id}/{relation}``                :func:`~aiohttp_json_api.handlers.get_related`
    =====================  ======  =========================================  ======================================================

    :param ~aiohttp.web.Application app:
        Application instance
    :param ~typing.Sequence[Schema] schemas:
        List of schema classes to register in JSON API
    :param str base_path:
        Prefix of JSON API routes paths
    :param str version:
        JSON API version (used in ``jsonapi`` key of document)
    :param dict meta:
        Meta information will added to response (``meta`` key of document)
    :param context_class:
        Override of RequestContext class
        (must be subclass of :class:`~aiohttp_json_api.context.RequestContext`)
    :param registry_class:
        Override of Registry class
        (must be subclass of :class:`~aiohttp_json_api.registry.Registry`)
    :param custom_handlers:
        Sequence or mapping with overrides of default JSON API handlers.

        If your custom handlers named in conform with convention
        of this application, then pass it as sequence::

            custom_handlers=(get_collection, patch_resource)

        If you have custom name of these handlers, then pass it as mapping::

            custom_handlers={
                'get_collection': some_handler_for_get_collection,
                'patch_resource': another_handler_to_patch_resource
            }

    :param bool log_errors:
        Log errors handled by
        :func:`~aiohttp_json_api.middleware.jsonapi_middleware`
    :return:
        aiohttp Application instance with configured JSON API
    :rtype: ~aiohttp.web.Application
    """
    import inspect
    from collections import MutableMapping, Sequence

    from . import handlers as default_handlers
    from .const import JSONAPI
    from .context import RequestContext
    from .log import logger
    from .middleware import jsonapi_middleware
    from .registry import Registry
    from .schema import Schema

    if registry_class is not None:
        assert issubclass(registry_class, Registry), \
            'Subclass of Registry is required. Got: {}'.format(registry_class)
    else:
        registry_class = Registry

    if context_class is not None:
        assert issubclass(context_class, RequestContext), \
            'Subclass of RequestContext is required. ' \
            'Got: {}'.format(context_class)
    else:
        context_class = RequestContext

    app_registry = registry_class()

    for schema_cls in schemas:
        assert inspect.isclass(schema_cls), \
            'Class (not instance) of schema is required.'
        assert issubclass(schema_cls, Schema), \
            'Subclass of Schema is required. Got: {}'.format(schema_cls)

        schema = schema_cls(app)
        assert isinstance(schema.type, str), 'Schema type must be a string.'

        app_registry[schema.type] = schema
        if schema.resource_class is None:
            logger.warning(
                'The schema "%s" is not bound to a resource class.',
                schema.type
            )
        else:
            assert inspect.isclass(schema.resource_class), \
                'Class (not instance) of resource is required.'
            app_registry[schema.resource_class] = schema

    app[JSONAPI] = {
        'context_class': context_class,
        'jsonapi': {
            'version': version,
            'meta': meta
        },
        'registry': app_registry,
        'log_errors': log_errors
    }

    collection_resource = app.router.add_resource(
        '{}/{{type}}'.format(base_path),
        name='jsonapi.collection'
    )
    resource_resource = app.router.add_resource(
        '{}/{{type}}/{{id}}'.format(base_path),
        name='jsonapi.resource'
    )
    relationships_resource = app.router.add_resource(
        '{}/{{type}}/{{id}}/relationships/{{relation}}'.format(base_path),
        name='jsonapi.relationships'
    )
    related_resource = app.router.add_resource(
        '{}/{{type}}/{{id}}/{{relation}}'.format(base_path),
        name='jsonapi.related'
    )

    handlers = {
        i[0]: i[1]
        for i in inspect.getmembers(default_handlers,
                                    inspect.iscoroutinefunction)
        if i[0] in default_handlers.__all__
    }
    if custom_handlers is not None:
        if isinstance(custom_handlers, MutableMapping):
            handlers.update(custom_handlers)
        elif isinstance(custom_handlers, Sequence):
            for custom_handler in custom_handlers:
                if inspect.iscoroutinefunction(custom_handler):
                    handlers[custom_handler.__name__] = custom_handler

    collection_resource.add_route('GET', handlers['get_collection'])
    collection_resource.add_route('POST', handlers['post_resource'])
    resource_resource.add_route('GET', handlers['get_resource'])
    resource_resource.add_route('PATCH', handlers['patch_resource'])
    resource_resource.add_route('DELETE', handlers['delete_resource'])
    relationships_resource.add_route('GET', handlers['get_relationship'])
    relationships_resource.add_route('POST', handlers['post_relationship'])
    relationships_resource.add_route('PATCH', handlers['patch_relationship'])
    relationships_resource.add_route('DELETE', handlers['delete_relationship'])
    related_resource.add_route('GET', handlers['get_related'])

    logger.debug('Registered JSON API related resources list:')
    for resource in filter(lambda r: r.name.startswith('jsonapi'),
                           app.router.resources()):
        logger.debug('%s -> %s',
                     [r.method for r in resource], resource.get_info())

    app.middlewares.append(jsonapi_middleware)

    return app
