__author__ = """Vladimir Bolshakov"""
__email__ = 'vovanbo@gmail.com'
__version__ = '0.20.2'


def setup_jsonapi(app, schemas, *, base_path='/api', version='1.0.0',
                  meta=None, context_class=None, registry_class=None,
                  custom_handlers=None, log_errors=True,
                  routes_namespace=None):
    """
    Setup JSON API in aiohttp application

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
    :param str routes_namespace:
        Namespace of JSON API application routes
    :return:
        aiohttp Application instance with configured JSON API
    :rtype: ~aiohttp.web.Application
    """
    import inspect
    from collections import MutableMapping, Sequence

    from . import handlers as default_handlers
    from .const import JSONAPI, ALLOWED_MEMBER_NAME_RULE
    from .context import RequestContext
    from .log import logger
    from .middleware import jsonapi_middleware
    from .registry import Registry
    from .schema import Schema

    routes_namespace = routes_namespace \
        if isinstance(routes_namespace, str) and len(routes_namespace) > 0 \
        else JSONAPI

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
        logger.debug('Registered %s with resource class %s and type "%s"',
                     schema_cls.__name__,
                     schema.resource_class.__name__,
                     schema.type)

    app[JSONAPI] = {
        'context_class': context_class,
        'jsonapi': {
            'version': version,
            'meta': meta
        },
        'registry': app_registry,
        'log_errors': log_errors,
        'routes_namespace': routes_namespace
    }

    type_part = '{type:' + ALLOWED_MEMBER_NAME_RULE + '}'
    relation_part = '{relation:' + ALLOWED_MEMBER_NAME_RULE + '}'
    collection_resource = app.router.add_resource(
        '{base}/{type}'.format(base=base_path, type=type_part),
        name='{}.collection'.format(routes_namespace)
    )
    resource_resource = app.router.add_resource(
        '{base}/{type}/{{id}}'.format(base=base_path, type=type_part),
        name='{}.resource'.format(routes_namespace)
    )
    relationships_resource = app.router.add_resource(
        '{base}/{type}/{{id}}/relationships/{relation}'.format(
            base=base_path, type=type_part, relation=relation_part
        ),
        name='{}.relationships'.format(routes_namespace)
    )
    related_resource = app.router.add_resource(
        '{base}/{type}/{{id}}/{relation}'.format(
            base=base_path, type=type_part, relation=relation_part
        ),
        name='{}.related'.format(routes_namespace)
    )

    handlers = {
        name: handler
        for name, handler in inspect.getmembers(default_handlers,
                                                inspect.iscoroutinefunction)
        if name in default_handlers.__all__
    }
    if custom_handlers is not None:
        if isinstance(custom_handlers, MutableMapping):
            custom_handlers_iter = custom_handlers.items()
        elif isinstance(custom_handlers, Sequence):
            custom_handlers_iter = ((c.__name__, c) for c in custom_handlers)
        else:
            raise ValueError('Wrong value of "custom_handlers" parameter. '
                             'Mapping or sequence is expected.')

        for name, custom_handler in custom_handlers_iter:
            handler_name = custom_handler.__name__
            if name not in handlers:
                logger.warning('Custom handler %s is ignored.', name)
                continue
            if not inspect.iscoroutinefunction(custom_handler):
                logger.error('"%s" is not a coroutine function.', handler_name)
                continue

            handlers[name] = custom_handler
            logger.debug('Default handler "%s" is replaced '
                         'with coroutine "%s" (%s)',
                         name, handler_name, inspect.getmodule(custom_handler))

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

    logger.debug('Registered JSON API resources list:')
    for resource in filter(lambda r: r.name.startswith(routes_namespace),
                           app.router.resources()):
        logger.debug('%s -> %s',
                     [r.method for r in resource], resource.get_info())

    app.middlewares.append(jsonapi_middleware)

    return app
