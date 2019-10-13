import inspect
from typing import MutableMapping, Sequence, Type, Dict, Union, Tuple, Iterable, Optional, Any

from aiohttp import web
from aiohttp_json_api import handlers as default_handlers
from aiohttp_json_api.schema import SchemaABC
from aiohttp_json_api.controller import ControllerABC
from aiohttp_json_api.common import ALLOWED_MEMBER_NAME_REGEX, ALLOWED_MEMBER_NAME_RULE, logger, JSONAPI
from aiohttp_json_api.context import JSONAPIContext
from aiohttp_json_api.middleware import jsonapi_middleware
from aiohttp_json_api.registry import Registry
from aiohttp_json_api.typings import CallableHandler


def setup_app_registry(
    *,
    config: Dict[Type[SchemaABC], Type[ControllerABC]],
    registry_class: Optional[Type[Registry]] = None,
) -> Registry:
    """Set up JSON API application registry."""
    if registry_class is not None:
        if not issubclass(registry_class, Registry):
            raise TypeError(f'Subclass of Registry is required. Got: {registry_class}')
    else:
        registry_class = Registry

    app_registry = registry_class()

    for schema_cls, controller_cls in config.items():
        resource_type = schema_cls.opts.resource_type
        resource_cls = schema_cls.opts.resource_cls

        if not inspect.isclass(controller_cls):
            raise TypeError('Class (not instance) of controller is required.')

        if not issubclass(controller_cls, ControllerABC):
            raise TypeError(f'Subclass of ControllerABC is required. Got: {controller_cls}')

        if not inspect.isclass(schema_cls):
            raise TypeError('Class (not instance) of schema is required.')

        if not issubclass(schema_cls, SchemaABC):
            raise TypeError(f'Subclass of SchemaABC is required. Got: {schema_cls}')

        if not inspect.isclass(schema_cls.opts.resource_cls):
            raise TypeError('Class (not instance) of resource is required.')

        if not ALLOWED_MEMBER_NAME_REGEX.fullmatch(resource_type):
            raise ValueError(f"Resource type '{resource_type}' is not allowed.")

        app_registry[resource_type] = schema_cls, controller_cls
        app_registry[resource_cls] = schema_cls, controller_cls

        logger.debug(
            'Registered %r (schema: %r, resource class: %r, type: %r)',
            controller_cls, schema_cls, resource_cls, resource_type,
        )

    return app_registry


def prepare_jsonapi_handlers(
    custom_handlers: Optional[Union[Dict[str, CallableHandler], Sequence[CallableHandler]]] = None,
) -> Dict[str, CallableHandler]:
    """Set up default and custom handlers for JSON API application."""
    handlers = {
        name: handler
        for name, handler in inspect.getmembers(default_handlers, inspect.iscoroutinefunction)
        if name in default_handlers.__all__
    }
    if custom_handlers is not None:
        if isinstance(custom_handlers, MutableMapping):
            custom_handlers_iter: Iterable[Tuple[str, CallableHandler]] = custom_handlers.items()
        elif isinstance(custom_handlers, Sequence):
            custom_handlers_iter = ((c.__name__, c) for c in custom_handlers)
        else:
            raise TypeError('Wrong type of "custom_handlers" parameter. Mapping or Sequence is expected.')

        for name, custom_handler in custom_handlers_iter:
            handler_name = custom_handler.__name__
            if name not in handlers:
                logger.warning('Custom handler %s is ignored.', name)
                continue
            if not inspect.iscoroutinefunction(custom_handler):
                logger.error('"%s" is not a co-routine function (ignored).', handler_name)
                continue

            handlers[name] = custom_handler
            logger.debug(
                'Default handler "%s" is replaced with co-routine "%s" (%s)',
                name, handler_name, inspect.getmodule(custom_handler),
            )
    return handlers


def setup_resources(
    app: web.Application,
    base_path: str,
    handlers: Dict[str, CallableHandler],
    routes_namespace: str,
) -> None:
    """Set up JSON API application resources."""
    type_part = '{type:' + ALLOWED_MEMBER_NAME_RULE + '}'
    relation_part = '{relation:' + ALLOWED_MEMBER_NAME_RULE + '}'
    collection_resource = app.router.add_resource(
        f'{base_path}/{type_part}',
        name=f'{routes_namespace}.collection'
    )
    resource_resource = app.router.add_resource(
        f'{base_path}/{type_part}/{{id}}',
        name=f'{routes_namespace}.resource'
    )
    relationships_resource = app.router.add_resource(
        f'{base_path}/{type_part}/{{id}}/relationships/{relation_part}',
        name=f'{routes_namespace}.relationships'
    )
    related_resource = app.router.add_resource(
        f'{base_path}/{type_part}/{{id}}/{relation_part}',
        name=f'{routes_namespace}.related'
    )
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


def setup_jsonapi(
    app: web.Application,
    config: Dict[Type[SchemaABC], Type[ControllerABC]],
    *,
    base_path: str = '/api',
    version: str = '1.0',
    meta: Optional[Dict[str, Any]] = None,
    context_cls: Optional[Type[JSONAPIContext]] = None,
    registry_class: Optional[Type[Registry]] = None,
    custom_handlers: Optional[Union[Dict[str, CallableHandler], Sequence[CallableHandler]]] = None,
    log_errors: bool = True,
    routes_namespace: str = JSONAPI,
) -> web.Application:
    """
    Set up JSON API in aiohttp application.

    This function will setup resources, handlers and middleware.

    :param ~aiohttp.web.Application app:
        Application instance
    :param str base_path:
        Prefix of JSON API routes paths
    :param str version:
        JSON API version (used in ``jsonapi`` key of document)
    :param dict meta:
        Meta information will added to response (``meta`` key of document)
    :param context_cls:
        Override of JSONAPIContext class
        (must be subclass of :class:`~aiohttp_json_api.context.JSONAPIContext`)
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
    if JSONAPI in app:
        logger.warning(
            'JSON API application is initialized already. '
            'Please check your aiohttp.web.Application instance does not have a "%s" dictionary key.',
            JSONAPI,
        )
        logger.error('Initialization of JSON API application is FAILED.')
        return app

    if context_cls is not None:
        if not issubclass(context_cls, JSONAPIContext):
            raise TypeError(f'Subclass of JSONAPIContext is required. Got: {context_cls}')
    else:
        context_cls = JSONAPIContext

    app[JSONAPI] = {
        'registry': setup_app_registry(config=config, registry_class=registry_class),
        'context_cls': context_cls,
        'meta': meta,
        'jsonapi': {
            'version': version,
        },
        'log_errors': log_errors,
        'routes_namespace': routes_namespace,
    }

    handlers = prepare_jsonapi_handlers(custom_handlers)
    setup_resources(app, base_path, handlers, routes_namespace)

    logger.debug('Registered JSON API resources list:')
    for resource in filter(lambda r: r.name and r.name.startswith(routes_namespace), app.router.resources()):
        logger.debug('%s -> %s', [r.method for r in resource], resource.get_info())

    app.middlewares.append(jsonapi_middleware)
    return app
