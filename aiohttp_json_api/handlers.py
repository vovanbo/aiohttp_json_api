"""Handlers."""

import collections.abc
from http import HTTPStatus

import trafaret as t
from aiohttp import hdrs, web

from aiohttp_json_api.common import Relation
from aiohttp_json_api.context import JSONAPIContext
from aiohttp_json_api.errors import InvalidType, ValidationError
from aiohttp_json_api.helpers import get_router_resource
from aiohttp_json_api.jsonpointer import JSONPointer
from aiohttp_json_api.schema import BaseSchema
from aiohttp_json_api.utils import get_compound_documents, jsonapi_response, render_document

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
    'get_related',
)


async def get_collection(request: web.Request) -> web.Response:
    """
    Fetch resources collection, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.query_collection`
    method of the schema to query the resources in the collection.

    :seealso: http://jsonapi.org/format/#fetching
    """
    ctx = JSONAPIContext(request)
    resources = await ctx.controller.query_collection()

    compound_documents = None
    if ctx.include and resources:
        compound_documents, relationships = await get_compound_documents(resources, ctx)

    result = await render_document(resources, ctx, included=compound_documents)
    return jsonapi_response(result)


async def post_resource(request: web.Request) -> web.Response:
    """
    Create resource, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.create_resource`
    method of the schema to create a new resource.

    :seealso: http://jsonapi.org/format/#crud-creating
    """
    raw_data = await request.json()
    if not isinstance(raw_data, collections.abc.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail)

    ctx = JSONAPIContext(request)

    deserialized_data = await ctx.schema.deserialize_resource(
        raw_data.get('data', {}), JSONPointer('/data')
    )
    data = ctx.schema.map_data_to_schema(deserialized_data)

    resource = await ctx.controller.create_resource(data)
    result = await render_document(resource, ctx)

    rid = ctx.registry.ensure_identifier(resource)
    location = request.url.join(
        get_router_resource(request.app, 'resource').url_for(**rid._asdict())
    )
    return jsonapi_response(result, status=HTTPStatus.CREATED, headers={hdrs.LOCATION: str(location)})


async def get_resource(request: web.Request) -> web.Response:
    """
    Get single resource, render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.query_resource`
    method of the schema to query the requested resource.

    :seealso: http://jsonapi.org/format/#fetching-resources
    """
    ctx = JSONAPIContext(request)
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    resource = await ctx.controller.query_resource(resource_id)

    compound_documents = None
    if ctx.include and resource:
        compound_documents, relationships = await get_compound_documents(resource, ctx)

    result = await render_document(resource, ctx, included=compound_documents)
    return jsonapi_response(result)


async def patch_resource(request: web.Request) -> web.Response:
    """
    Update resource (via PATCH), render JSON API document and return response.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.update_resource`
    method of the schema to update a resource.

    :seealso: http://jsonapi.org/format/#crud-updating
    """
    ctx = JSONAPIContext(request)
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    raw_data = await request.json()
    if not isinstance(raw_data, collections.abc.Mapping):
        detail = 'Must be an object.'
        raise InvalidType(detail=detail)

    sp = JSONPointer('/data')
    deserialized_data = await ctx.schema.deserialize_resource(raw_data.get('data', {}), sp, expected_id=resource_id)

    resource = await ctx.controller.fetch_resource(resource_id)
    old_resource, new_resource = await ctx.controller.update_resource(resource, deserialized_data, sp)

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = await render_document(new_resource, ctx)
    return jsonapi_response(result)


async def delete_resource(request: web.Request) -> web.Response:
    """
    Remove resource.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.delete_resource`
    method of the schema to delete a resource.

    :seealso: http://jsonapi.org/format/#crud-deleting
    """
    ctx = JSONAPIContext(request)
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    await ctx.controller.delete_resource(resource_id)
    return web.HTTPNoContent()


async def get_relationship(request: web.Request) -> web.Response:
    """
    Get relationships of resource.

    :param request: Request instance
    :return: Response
    """
    relation_name = request.match_info['relation']
    ctx = JSONAPIContext(request)

    relation_field = ctx.schema.get_relationship_field(relation_name, source_parameter='URI')
    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    resource = await ctx.controller.query_resource(resource_id)
    result = ctx.schema.serialize_relationship(relation_name, resource, pagination=pagination)
    return jsonapi_response(result)


async def post_relationship(request: web.Request) -> web.Response:
    """
    Create relationships of resource.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.add_relationship`
    method of the schemato add new relationships.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """

    relation_name = request.match_info['relation']
    ctx = JSONAPIContext(request)
    relation_field = ctx.schema.get_relationship_field(relation_name, source_parameter='URI')

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()

    sp = JSONPointer('')
    field = ctx.schema.get_relationship_field(relation_name)
    if field.relation is not Relation.TO_MANY:
        raise RuntimeError('Wrong relationship field. Relation to-many is required.')

    await ctx.schema.pre_validate_field(field, data, sp)
    deserialized_data = field.deserialize(ctx.schema, data, sp)

    resource = await ctx.controller.fetch_resource(resource_id)

    old_resource, new_resource = await ctx.controller.add_relationship(field, resource, deserialized_data, sp)

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = ctx.schema.serialize_relationship(relation_name, new_resource, pagination=pagination)
    return jsonapi_response(result)


async def patch_relationship(request: web.Request) -> web.Response:
    """
    Update relationships of resource.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.update_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    relation_name = request.match_info['relation']
    ctx = JSONAPIContext(request)
    relation_field = ctx.schema.get_relationship_field(relation_name, source_parameter='URI')

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()

    field = ctx.schema.get_relationship_field(relation_name)
    sp = JSONPointer('')

    await ctx.schema.pre_validate_field(field, data, sp)
    deserialized_data = field.deserialize(ctx.schema, data, sp)

    resource = await ctx.controller.fetch_resource(resource_id)

    old_resource, new_resource = await ctx.controller.update_relationship(field, resource, deserialized_data, sp)
    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = ctx.schema.serialize_relationship(relation_name, new_resource, pagination=pagination)
    return jsonapi_response(result)


async def delete_relationship(request: web.Request) -> web.Response:
    """
    Remove relationships of resource.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.delete_relationship`
    method of the schema to update the relationship.

    :seealso: http://jsonapi.org/format/#crud-updating-relationships
    """
    relation_name = request.match_info['relation']
    ctx = JSONAPIContext(request)
    relation_field = ctx.schema.get_relationship_field(relation_name, source_parameter='URI')

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    data = await request.json()

    sp = JSONPointer('')
    field = ctx.schema.get_relationship_field(relation_name)
    if field.relation is not Relation.TO_MANY:
        raise RuntimeError('Wrong relationship field.Relation to-many is required.')

    await ctx.schema.pre_validate_field(field, data, sp)
    deserialized_data = field.deserialize(ctx.schema, data, sp)

    resource = await ctx.controller.fetch_resource(resource_id)

    old_resource, new_resource = await ctx.controller.remove_relationship(field, resource, deserialized_data, sp)

    if old_resource == new_resource:
        return web.HTTPNoContent()

    result = ctx.schema.serialize_relationship(relation_name, new_resource, pagination=pagination)
    return jsonapi_response(result)


async def get_related(request: web.Request) -> web.Response:
    """
    Get related resources.

    Uses the :meth:`~aiohttp_json_api.controller.BaseController.query_relative`
    method of the schema to query the related resource.

    :seealso: http://jsonapi.org/format/#fetching
    """
    relation_name = request.match_info['relation']
    ctx = JSONAPIContext(request)

    resource_id = request.match_info.get('id')
    validate_uri_resource_id(ctx.schema, resource_id)

    relation_field = ctx.schema.get_relationship_field(relation_name, source_parameter='URI')
    pagination = None
    if relation_field.relation is Relation.TO_MANY:
        pagination_type = relation_field.pagination
        if pagination_type:
            pagination = pagination_type(request)

    field = ctx.schema.get_relationship_field(relation_name)
    resource = await ctx.controller.fetch_resource(resource_id)

    relatives = await ctx.controller.query_relatives(field, resource)

    compound_documents = None
    if ctx.include and relatives:
        compound_documents, relationships = await get_compound_documents(relatives, ctx)

    result = await render_document(relatives, ctx, included=compound_documents, pagination=pagination)
    return jsonapi_response(result)


def validate_uri_resource_id(schema: BaseSchema, resource_id: int) -> None:
    """
    Validate resource ID from URI.

    :param schema: Resource schema
    :param resource_id: Resource ID
    """
    field = getattr(schema, '_id', None)
    if field is None:
        try:
            t.Int().check(resource_id)
        except t.DataError as exc:
            raise ValidationError(detail=str(exc).capitalize(), source_parameter='id')
    else:
        try:
            field.pre_validate(schema, resource_id, sp=None)
        except ValidationError as exc:
            exc.source_parameter = 'id'
            raise exc
