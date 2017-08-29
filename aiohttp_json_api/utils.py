"""
Utilities
=========
"""
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


async def get_compound_documents(resources, context, **kwargs):
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

    async def fetch_recursively(collection, pths):
        """
        Fetches the relationship path *path* recursively.
        """
        if not pths or not collection:
            return

        relation_name, *rest_path = pths

        # Use schema of first collection's element to fetch
        schema = registry[registry.ensure_identifier(first(collection)).type]
        if relation_name in relationships[schema.type]:
            return

        relatives = await schema.fetch_compound_documents(
            relation_name, collection, context, rest_path=rest_path, **kwargs
        )

        if any(relatives):
            for relative in relatives:
                relative_id = registry.ensure_identifier(relative)
                if relative_id not in compound_documents:
                    compound_documents[relative_id] = relative

            relationships[schema.type].add(relation_name)
            await fetch_recursively(relatives, rest_path)

    collection = resources if is_collection(resources) else (resources,)
    for path in context.include:
        await fetch_recursively(collection, path)

    return compound_documents, relationships


def serialize_resource(resource, context):
    registry = context.request.app[JSONAPI]['registry']
    schema = registry[resource]
    return schema.serialize_resource(resource, context=context)


def render_document(data, included, context, *,
                    pagination=None, links=None) -> typing.MutableMapping:
    document = OrderedDict()

    if is_collection(data):
        document['data'] = [serialize_resource(r, context) for r in data]
    else:
        document['data'] = \
            serialize_resource(data, context) if data else None

    if context.include and included:
        document['included'] = [serialize_resource(r, context)
                                for r in included.values()]

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
            'errors': [error.json] if isinstance(error, Error) else error.json,
            'jsonapi': request.app[JSONAPI]['jsonapi']
        },
        status=error.status
    )


def validate_uri_resource_id(schema, resource_id, context):
    field = getattr(schema, '_id', None)
    if field is not None:
        try:
            field.pre_validate(schema, resource_id, sp=None, context=context)
        except ValidationError as e:
            e.source_parameter = 'id'
            raise e
