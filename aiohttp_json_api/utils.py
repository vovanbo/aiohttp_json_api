"""Utilities related to JSON API."""

import asyncio
import typing
from collections import defaultdict, OrderedDict

from aiohttp import web
from aiohttp.web_response import Response
import trafaret as t

from .common import JSONAPI, JSONAPI_CONTENT_TYPE
from .encoder import json_dumps
from .errors import Error, ErrorList, ValidationError
from .helpers import first, is_collection


def jsonapi_response(data, *, status=web.HTTPOk.status_code,
                     reason=None, headers=None, dumps=None):
    """
    Return JSON API response.

    :param data: Rendered JSON API document
    :param status: HTTP status of JSON API response
    :param reason: Readable reason of error response
    :param headers: Headers
    :param dumps: Custom JSON dumps callable
    :return: Response instance
    """
    if not callable(dumps):
        dumps = json_dumps

    body = dumps(data).encode('utf-8')
    return Response(body=body, status=status, reason=reason,
                    headers=headers, content_type=JSONAPI_CONTENT_TYPE)


async def get_compound_documents(resources, context):
    """
    Get compound documents of resources.

    .. seealso::

        http://jsonapi.org/format/#fetching-includes

    Fetches the relationship paths *paths*.

    :param resources:
        A list with the primary data (resources) of the compound
        response document.
    :param context:
        A web Request context

    :returns:
        A two tuple with a list of the included resources and a dictionary,
        which maps each resource (primary and included) to a set with the
        names of the included relationships.
    """
    registry = context.request.app[JSONAPI]['registry']
    relationships = defaultdict(set)
    compound_documents = OrderedDict()

    collection = (resources,) if type(resources) in registry else resources
    for path in context.include:
        if path and collection:
            rest_path = path
            nested_collection = collection
            while rest_path and nested_collection:
                schema = registry[first(nested_collection)]

                if rest_path in relationships[schema.type]:
                    break

                nested_collection = await schema.fetch_compound_documents(
                    relation_name=rest_path[0], resources=nested_collection,
                    context=context, rest_path=rest_path[1:]
                )

                for relative in nested_collection:
                    compound_documents.setdefault(
                        registry.ensure_identifier(relative),
                        relative
                    )

                relationships[schema.type].add(rest_path)
                rest_path = rest_path[1:]

    return compound_documents, relationships


async def serialize_resource(resource, context):
    """
    Serialize resource by schema.

    :param resource: Resource instance
    :param context: Request context
    :return: Serialized resource
    """
    registry = context.request.app[JSONAPI]['registry']
    schema = registry[resource]
    return schema.serialize_resource(resource, context=context)


async def render_document(data, included, context, *,
                          pagination=None,
                          links=None) -> typing.MutableMapping:
    """
    Render JSON API document.

    :param data: One or many resources
    :param included: Compound documents
    :param context: Request context
    :param pagination: Pagination instance
    :param links: Additional links
    :return: Rendered JSON API document
    """
    document = OrderedDict()

    if is_collection(data, exclude=(context.schema.resource_class,)):
        document['data'] = await asyncio.gather(
            *[serialize_resource(r, context) for r in data]
        )
    else:
        document['data'] = \
            await serialize_resource(data, context) if data else None

    if context.include and included:
        document['included'] = await asyncio.gather(
            *[serialize_resource(r, context) for r in included.values()]
        )

    document.setdefault('links', OrderedDict())
    document['links']['self'] = str(context.request.url)
    if links is not None:
        document['links'].update(links)

    meta_object = context.request.app[JSONAPI]['meta']
    pagination = pagination or context.pagination

    if pagination or meta_object:
        document.setdefault('meta', OrderedDict())

    if pagination is not None:
        document['links'].update(pagination.links())
        document['meta'].update(pagination.meta())

    if meta_object:
        document['meta'].update(meta_object)

    jsonapi_info = context.request.app[JSONAPI]['jsonapi']
    if jsonapi_info:
        document['jsonapi'] = jsonapi_info

    return document


def error_to_response(request: web.Request,
                      error: typing.Union[Error, ErrorList]):
    """
    Convert an :class:`Error` or :class:`ErrorList` to JSON API response.

    :arg ~aiohttp.web.Request request:
        The web request instance.
    :arg typing.Union[Error, ErrorList] error:
        The error, which is converted into a response.

    :rtype: ~aiohttp.web.Response
    """
    if not isinstance(error, (Error, ErrorList)):
        raise TypeError('Error or ErrorList instance is required.')

    return jsonapi_response(
        {
            'errors':
                [error.as_dict] if isinstance(error, Error) else error.as_dict,
            'jsonapi': request.app[JSONAPI]['jsonapi']
        },
        status=error.status
    )


def validate_uri_resource_id(schema, resource_id, context):
    """
    Validate resource ID from URI.

    :param schema: Resource schema
    :param resource_id: Resource ID
    :param context: Request context
    """
    field = getattr(schema, '_id', None)
    if field is None:
        try:
            t.Int().check(resource_id)
        except t.DataError as exc:
            raise ValidationError(detail=str(exc).capitalize(),
                                  source_parameter='id')
    else:
        try:
            field.pre_validate(schema, resource_id, sp=None, context=context)
        except ValidationError as exc:
            exc.source_parameter = 'id'
            raise exc
