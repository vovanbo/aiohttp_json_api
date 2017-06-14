"""
Setup
=====
"""

import inspect

import collections
from boltons.typeutils import issubclass

from .context import RequestContext
from .const import JSONAPI
from . import handlers as default_handlers
from .log import logger
from .middleware import jsonapi_middleware
from .registry import Registry
from .schema.schema import Schema


def setup_jsonapi(app, schemas, *, base_path='/api', version='1.0.0',
                  meta=None, context_class=None, custom_handlers=None):
    schema_by_type = {}
    schema_by_resource = {}

    for schema_cls in schemas:
        assert issubclass(schema_cls, Schema), \
            f'Schema class is required. Got: {schema_cls}'

        schema = schema_cls(app)
        schema_by_type[schema.type] = schema
        if schema.resource_class is None:
            logger.warning(
                'The schema "%s" is not bound to a resource class.',
                schema.type
            )
        else:
            schema_by_resource[schema.resource_class] = schema

    if context_class is not None:
        assert issubclass(context_class, RequestContext), \
            f'Subclass of RequestContext is required. Got: {context_class}'

    app[JSONAPI] = {
        'context_class': context_class or RequestContext,
        'jsonapi': {
            'version': version,
            'meta': meta
        },
        'registry': Registry(schema_by_type=schema_by_type,
                             schema_by_resource=schema_by_resource)
    }

    collection_resource = app.router.add_resource(
        f'{base_path}/{{type}}',
        name='jsonapi.collection'
    )
    resource_resource = app.router.add_resource(
        f'{base_path}/{{type}}/{{id}}',
        name='jsonapi.resource'
    )
    relationships_resource = app.router.add_resource(
        f'{base_path}/{{type}}/{{id}}/relationships/{{relation}}',
        name='jsonapi.relationships'
    )
    related_resource = app.router.add_resource(
        f'{base_path}/{{type}}/{{id}}/{{relation}}',
        name='jsonapi.related'
    )

    handlers = {
        i[0]: i[1]
        for i in inspect.getmembers(default_handlers,
                                    inspect.iscoroutinefunction)
        if i[0] in default_handlers.__all__
    }
    if custom_handlers is not None:
        if isinstance(custom_handlers, collections.MutableMapping):
            handlers.update(custom_handlers)
        elif isinstance(custom_handlers, collections.Sequence):
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

    app.middlewares.append(jsonapi_middleware)

    return app
