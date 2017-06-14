"""
Handlers
========
"""
import collections
from http import HTTPStatus

from aiohttp import web, hdrs

from .jsonpointer import JSONPointer
from .const import JSONAPI
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
    Uses the :meth:`~aiohttp_json_api.schema.Schema.query_collection`
    method of the schema to query the resources in the collection.

    :seealso: http://jsonapi.org/format/#fetching
    """
    context = request[JSONAPI]
    schema = context.schema

    if schema is None:
        raise HTTPNotFound()

    resources = await schema.query_collection(context=context)

    compound_documents = None
    if context.include and resources:
        compound_documents, relationships = \
            await get_compound_documents(resources.values(), context)

    result = await render_document(resources.values(),
                                   compound_documents,
                                   context)

    return jsonapi_response(result)


@jsonapi_content
async def post_resource(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.create_resource`
    method of the schema to create a new resource.

    :seealso: http://jsonapi.org/format/#crud-creating
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    registry = request.app[JSONAPI]['registry']

    data = await get_data_from_request(request)
    if not isinstance(data, collections.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail, source_pointer='')

    resource = await schema.create_resource(
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
    Uses the :meth:`~aiohttp_json_api.schema.Schema.query_resource`
    method of the schema to query the requested resource.

    :seealso: http://jsonapi.org/format/#fetching-resources
    """
    context = request[JSONAPI]
    schema = context.schema

    if schema is None:
        raise HTTPNotFound()

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    resource = await schema.query_resource(id_=resource_id, context=context)

    compound_documents = None
    if context.include and resource:
        compound_documents, relationships = \
            await get_compound_documents(resource, context)

    result = await render_document(resource, compound_documents, context)

    return jsonapi_response(result)


async def patch_resource(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.update_resource`
    method of the schema to update a resource.

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

    resource = await schema.update_resource(
        resource=resource_id,
        data=data.get('data', {}),
        sp=JSONPointer('/data'),
        context=context,
    )

    result = await render_document(resource, None, context)
    return jsonapi_response(result)


async def delete_resource(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.delete_resource`
    method of the schema to delete a resource.

    :seealso: http://jsonapi.org/format/#crud-deleting
    """
    context = request[JSONAPI]
    schema = context.schema
    if schema is None:
        raise HTTPNotFound()

    resource_id = request.match_info.get('id')
    await validate_uri_resource_id(schema, resource_id, context)

    await schema.delete_resource(resource=resource_id, context=context)
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

    resource = await schema.query_resource(id_=resource_id, context=context)
    relation = await relation_field.query(schema, resource, context)
    result = relation_field.encode(schema, relation)
    return jsonapi_response(result)


async def post_relationship(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.add_relationship`
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

    resource = await schema.add_relationship(
        relation_name=relation_name,
        resource=resource_id,
        data=data,
        sp=JSONPointer('')
    )
    result = relation_field.encode(schema, resource)
    return jsonapi_response(result)


async def patch_relationship(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.update_relationship`
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
    resource = await schema.update_relationship(
        relation_name=relation_name,
        resource=resource_id,
        data=data,
        sp=JSONPointer('')
    )

    result = relation_field.encode(schema, resource)
    return jsonapi_response(result)


async def delete_relationship(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.delete_relationship`
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
    await schema.remove_relationship(
        relation_name=relation_name,
        resource=resource_id,
        data=data,
        sp=JSONPointer(''),
        context=context
    )
    return web.HTTPNoContent()


async def get_related(request: web.Request):
    """
    Uses the :meth:`~aiohttp_json_api.schema.Schema.query_relative`
    method of the schema to query the related resource.

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

    if relation_field.to_many:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type.from_request(request)

        relatives = await schema.query_relatives(
            relation_name=relation_name,
            resource=resource_id,
            context=context
        )
    else:
        relatives = await schema.query_relative(
            relation_name=relation_name,
            resource=resource_id,
            context=context
        )

    if context.include and relatives:
        compound_documents, relationships = \
            await get_compound_documents(relatives, context)

    result = await render_document(relatives, compound_documents, context,
                                   pagination=pagination)

    return jsonapi_response(result)
