import collections
from http import HTTPStatus

from aiohttp import web, hdrs

from .jsonpointer import JSONPointer
from .const import JSONAPI
from .context import RequestContext
from .decorators import jsonapi_content
from .errors import InvalidType, HTTPNotFound
from .utils import (
    jsonapi_response,
    get_data_from_request,
    render_document, get_compound_documents,
    validate_uri_resource_id
)

__all__ = (
    'get_collection',
    'post_resource',
    'get_resource',
    'patch_resource',
    'delete_resource',
    'get_relationship',
    'post_relationship',
    'patch_relationship',
    'delete_relationship',
    'get_related'
)


async def get_collection(request: web.Request):
    """
    Uses the :meth:`~core.jsonapi.schema.schema.Schema.query_collection`
    method of the schema to query the resources in the collection.

    :seealso: http://jsonapi.org/format/#fetching
    """
    context: RequestContext = request[JSONAPI]
    schema = context.schema

    if schema is None:
        raise HTTPNotFound()

    async with request.app['db'].acquire() as conn:
        resources = await schema.query_collection(conn, context)

        compound_documents = None
        if context.include and resources:
            compound_documents, relationships = \
                await get_compound_documents(conn, resources.values(), context)

        result = await render_document(resources.values(),
                                       compound_documents,
                                       context)

    return jsonapi_response(result)


@jsonapi_content
async def post_resource(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.create_resource`
    method of the schema to create a new resource.

    :seealso: http://jsonapi.org/format/#crud-creating
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    registry = request.app[JSONAPI]

    data = await get_data_from_request(request)
    if not isinstance(data, collections.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail, source_pointer='')

    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            resource = await schema.create_resource(
                conn,
                data=data.get('data', {}),
                sp=JSONPointer('/data'),
                context=context
            )

            result = await render_document(resource, None, context)
            location = request.url.join(
                request.app.router['jsonapi.resource'].url_for(
                    **registry.ensure_identifier(resource, asdict=True)
                )
            )

    return jsonapi_response(result,
                            status=HTTPStatus.CREATED.value,
                            headers={hdrs.LOCATION: str(location)})


async def get_resource(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.query_resource` method
    of the schema to query the requested resource.

    :seealso: http://jsonapi.org/format/#fetching-resources
    """
    context = request[JSONAPI]
    schema = context.schema

    if schema is None:
        raise HTTPNotFound()

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    async with request.app['db'].acquire() as conn:
        resource = await schema.query_resource(
            conn, resource_id, context
        )

        compound_documents = None
        if context.include and resource:
            compound_documents, relationships = \
                await get_compound_documents(conn, resource, context)

        result = await render_document(resource, compound_documents, context)

    return jsonapi_response(result)


async def patch_resource(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.update_resource` method
    of the schema to update a resource.

    :seealso: http://jsonapi.org/format/#crud-updating
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    data = await get_data_from_request(request)
    if not isinstance(data, collections.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail, source_pointer='')

    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            resource = await schema.update_resource(
                resource=resource_id,
                data=data.get('data', {}),
                sp=JSONPointer('/data')
            )

            result = await render_document(resource, None, context)

    return jsonapi_response(result)


async def delete_resource(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.delete_resource` method
    of the schema to delete a resource.

    :seealso: http://jsonapi.org/format/#crud-deleting
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            await schema.delete_resource(conn, resource_id, context)

    return web.HTTPNoContent()


async def get_relationship(request: web.Request):
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    relation_type = request.match_info['relation']
    relation_field = schema._relationships[relation_type]

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    pagination = None
    if relation_field.to_many:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type.from_request(request)

    async with request.app['db'].acquire() as conn:
        resource = await schema.query_resource(conn, resource_id, context)
        relation = await relation_field.query(schema, conn, resource, context)
        result = relation_field.encode(schema, relation)

    return jsonapi_response(result)


async def post_relationship(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.add_relationship`
    method of the schemato add new relationships.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    relation_name = request.match_info['relation']
    relation_field = schema._relationships[relation_name]
    pagination = None

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    if relation_field.to_many:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type.from_request(request)

    data = await get_data_from_request(request)

    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            resource = await schema.add_relationship(
                conn,
                relation_name=relation_name,
                resource=resource_id,
                data=data,
                sp=JSONPointer('')
            )
            result = relation_field.encode(schema, resource)

    return jsonapi_response(result)


async def patch_relationship(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.update_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    relation_name = request.match_info['relation']
    relation_field = schema._relationships[relation_name]

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    pagination = None
    if relation_field.to_many:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type.from_request(request)

    data = await get_data_from_request(request)
    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            resource = await schema.update_relationship(
                conn,
                relation_name=relation_name,
                resource=resource_id,
                data=data,
                sp=JSONPointer('')
            )

        result = relation_field.encode(schema, resource)

    return jsonapi_response(result)


async def delete_relationship(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.update_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    relation_name = request.match_info['relation']

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    data = await get_data_from_request(request)
    async with request.app['db'].acquire() as conn:
        async with conn.begin():
            await schema.remove_relationship(
                conn,
                relation_name=relation_name,
                resource=resource_id,
                data=data,
                sp=JSONPointer('')
            )

    return web.HTTPNoContent()


async def get_related(request: web.Request):
    """
    Uses the :meth:`~jsonapi.schema.schema.Schema.query_relative` method
    of the schema to query the related resource.

    :seealso: http://jsonapi.org/format/#fetching
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    relation_name = request.match_info['relation']
    relation_field = schema._relationships[relation_name]
    compound_documents = None
    pagination = None

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    async with request.app['db'].acquire() as conn:
        if relation_field.to_many:
            pagination_type = relation_field.pagination
            if pagination_type:
                pagination = pagination_type.from_request(request)

            relatives = await schema.query_relatives(
                conn,
                relation_name=relation_name,
                resource=resource_id,
                context=context
            )
        else:
            relatives = await schema.query_relative(
                conn,
                relation_name=relation_name,
                resource=resource_id,
                context=context
            )

        if context.include and relatives:
            compound_documents, relationships = \
                await get_compound_documents(conn, relatives, context)

        result = await render_document(relatives, compound_documents, context,
                                       pagination=pagination)

    return jsonapi_response(result)
