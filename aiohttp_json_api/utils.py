"""
Utilities
=========
"""
import asyncio
import typing
from collections import OrderedDict, defaultdict

from aiohttp import web

from .const import JSONAPI, JSONAPI_CONTENT_TYPE
from .helpers import SENTINEL, is_collection, first
from .encoder import json_dumps
from .errors import Error, ErrorList, ValidationError


def jsonapi_response(data=SENTINEL, *, text=None, body=None,
                     status=web.HTTPOk.status_code,
                     reason=None, headers=None,
                     dumps=None):
    if not callable(dumps):
        dumps = json_dumps

    return web.json_response(
        data=data, text=text, body=body, status=status,
        reason=reason, headers=headers, content_type=JSONAPI_CONTENT_TYPE,
        dumps=dumps
    )


async def get_compound_documents(resources, context):
    """
    .. seealso::

        http://jsonapi.org/format/#fetching-includes

    Fetches the relationship paths *paths*.

    :param typing.Sequence[Model] resources:
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

    collection = resources if is_collection(resources) else (resources,)
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
    registry = context.request.app[JSONAPI]['registry']
    schema = registry[resource]
    return schema.serialize_resource(resource, context=context)


async def render_document(data, included, context, *,
                          pagination=None, links=None) -> typing.MutableMapping:
    document = OrderedDict()

    if is_collection(data):
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

    pagination = pagination or context.pagination
    if pagination is not None:
        document['links'].update(pagination.links())
        document.setdefault('meta', OrderedDict())
        document['meta'].update(pagination.meta())

    jsonapi_info = context.request.app[JSONAPI]['jsonapi']
    if jsonapi_info:
        document['jsonapi'] = jsonapi_info

    return document


def error_to_response(request: web.Request,
                      error: typing.Union[Error, ErrorList]):
    """
    Converts an :class:`Error` or :class:`ErrorList`
    to a :class:`~aiohttp.web.Response`.

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
    field = getattr(schema, '_id', None)
    if field is not None:
        try:
            field.pre_validate(schema, resource_id, sp=None, context=context)
        except ValidationError as exc:
            exc.source_parameter = 'id'
            raise exc
