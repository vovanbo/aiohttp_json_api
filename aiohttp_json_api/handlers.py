"""Handlers."""

import collections
from http import HTTPStatus

from aiohttp import hdrs, web

from .context import RequestContext
from .common import Relation, JSONAPI
from .decorators import jsonapi_handler
from .errors import InvalidType
from .helpers import get_router_resource
from .jsonpointer import JSONPointer
from .utils import (get_compound_documents, jsonapi_response, render_document,
                    validate_uri_resource_id)

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
    Fetch resources collection, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.query_collection`
    method of the schema to query the resources in the collection.

    :seealso: http://jsonapi.org/format/#fetching
    """
    async with RequestContext(request) as ctx:
        resources = await ctx.controller.query_collection()

        compound_documents = None
        if ctx.include and resources:
            compound_documents, relationships = \
                await get_compound_documents(resources, ctx)

        result = await render_document(resources, compound_documents, ctx)

    return jsonapi_response(result)


async def post_resource(request: web.Request):
    """
    Create resource, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.create_resource`
    method of the schema to create a new resource.

    :seealso: http://jsonapi.org/format/#crud-creating
    """
    data = await request.json()
    if not isinstance(data, collections.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail, source_pointer='')

    resource = await controller.create_resource(
        data=data.get('data', {}),
        sp=JSONPointer('/data'),
        context=context
    )

    result = await render_document(resource, None, context)

    registry = request.app[JSONAPI]['registry']
    location = request.url.join(
        get_router_resource(request.app, 'resource').url_for(
            **registry.ensure_identifier(resource, asdict=True)
        )
    )

    return jsonapi_response(result, status=HTTPStatus.CREATED,
                            headers={hdrs.LOCATION: str(location)})


async def get_resource(request: web.Request):
    """
    Get single resource, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.query_resource`
    method of the schema to query the requested resource.

    :seealso: http://jsonapi.org/format/#fetching-resources
    """
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    resource = await controller.query_resource(resource_id, context)

    compound_documents = None
    if context.include and resource:
        compound_documents, relationships = \
            await get_compound_documents(resource, context)

    result = await render_document(resource, compound_documents, context)

    return jsonapi_response(result)


async def patch_resource(request: web.Request):
    """
    Update resource (via PATCH), render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.update_resource`
    method of the schema to update a resource.

    :seealso: http://jsonapi.org/format/#crud-updating
    """
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    data = await request.json()
    if not isinstance(data, collections.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail, source_pointer='')

    old_resource, new_resource = await controller.update_resource(
        resource_id, data.get('data', {}), JSONPointer('/data'),
        context=context
    )

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = await render_document(new_resource, None, context)
    return jsonapi_response(result)


async def delete_resource(request: web.Request):
    """
    Remove resource.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.delete_resource`
    method of the schema to delete a resource.

    :seealso: http://jsonapi.org/format/#crud-deleting
    """
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    await controller.delete_resource(resource_id, context)
    return web.HTTPNoContent()


async def get_relationship(request: web.Request):
    """
    Get relationships of resource.

    :param request: Request instance
    :param context: Request context instance
    :param schema: Schema instance
    :return: Response
    """
    relation_name = request.match_info['relation']
    relation_field = controller.schema.get_relationship_field(
        relation_name, source_parameter='URI'
    )

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    resource = await controller.query_resource(resource_id, context)
    result = controller.schema.serialize_relationship(relation_name, resource,
                                                      pagination=pagination)
    return jsonapi_response(result)


async def post_relationship(request: web.Request):
    """
    Create relationships of resource.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.add_relationship`
    method of the schemato add new relationships.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    relation_name = request.match_info['relation']
    relation_field = controller.schema.get_relationship_field(
        relation_name, source_parameter='URI'
    )
    pagination = None

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()

    old_resource, new_resource = await controller.add_relationship(
        relation_name, resource_id, data, JSONPointer(''), context
    )

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = controller.schema.serialize_relationship(relation_name,
                                                      new_resource,
                                                      pagination=pagination)
    return jsonapi_response(result)


async def patch_relationship(request: web.Request):
    """
    Update relationships of resource.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.update_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    relation_name = request.match_info['relation']
    relation_field = controller.schema.get_relationship_field(
        relation_name, source_parameter='URI'
    )

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()
    old_resource, new_resource = await controller.update_relationship(
        relation_name, resource_id, data, JSONPointer(''), context
    )

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = controller.schema.serialize_relationship(relation_name,
                                                      new_resource,
                                                      pagination=pagination)
    return jsonapi_response(result)


async def delete_relationship(request: web.Request):
    """
    Remove relationships of resource.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.delete_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    relation_name = request.match_info['relation']
    relation_field = controller.schema.get_relationship_field(
        relation_name, source_parameter='URI'
    )

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()
    old_resource, new_resource = await controller.remove_relationship(
        relation_name, resource_id, data, JSONPointer(''), context
    )

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = controller.schema.serialize_relationship(relation_name,
                                                      new_resource,
                                                      pagination=pagination)
    return jsonapi_response(result)


async def get_related(request: web.Request):
    """
    Get related resources.

    Uses the :meth:`~aiohttp_json_api.schema.BaseSchema.query_relative`
    method of the schema to query the related resource.

    :seealso: http://jsonapi.org/format/#fetching
    """
    relation_name = request.match_info['relation']
    relation_field = controller.schema.get_relationship_field(
        relation_name, source_parameter='URI'
    )
    compound_documents = None
    pagination = None

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(controller.schema, resource_id, context)

    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    relatives = await controller.query_relatives(relation_name, resource_id,
                                                 context)

    if context.include and relatives:
        compound_documents, relationships = \
            await get_compound_documents(relatives, context)

    result = await render_document(relatives, compound_documents, context,
                                   pagination=pagination)

    return jsonapi_response(result)
