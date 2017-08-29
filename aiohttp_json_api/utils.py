"""
Utilities
=========
"""
import typing
from collections import OrderedDict, defaultdict
from http import HTTPStatus

from aiohttp import web

from .const import JSONAPI, JSONAPI_CONTENT_TYPE
from .helpers import SENTINEL, is_collection, first
from .encoder import json_dumps
from .errors import Error, ErrorList, ValidationError



def filter_empty_fields(data: typing.MutableMapping) -> typing.MutableMapping:
    required = ('errors',) if data.get('errors') else ('data',)
    return {
        key: value
        for key, value in data.items()
        if key in required or value
    }


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


def render_document(resources, compound_documents, context, *,
                    pagination=None, links=None) -> typing.MutableMapping:
    document = {'links': {}, 'meta': {}}
    pagination = pagination or context.pagination

    if is_collection(resources):
        document['data'] = [serialize_resource(r, context) for r in resources]
    else:
        document['data'] = \
            serialize_resource(resources, context) if resources else None

    if context.include and compound_documents:
        document['included'] = [serialize_resource(r, context)
                                for r in compound_documents.values()]

    document['links']['self'] = str(context.request.url)
    if links is not None:
        document['links'].update(links)

    if pagination is not None:
        document['links'].update(pagination.links())
        document['meta'].update(pagination.meta())

    document['jsonapi'] = context.request.app[JSONAPI]['jsonapi']

    return filter_empty_fields(document)


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
    assert isinstance(error, (Error, ErrorList))

    document = {}
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    if isinstance(error, Error):
        document['errors'] = [error.json]
        status = error.status
    elif isinstance(error, ErrorList):
        document['errors'] = error.json
        status = error.status

    document['jsonapi'] = request.app[JSONAPI]['jsonapi']

    return jsonapi_response(
        filter_empty_fields(document),
        status=status.value
    )


def validate_uri_resource_id(schema, resource_id, context):
    field = schema._id
    if field:
        try:
            field.pre_validate(schema, resource_id,
                               sp=None, context=context)
        except ValidationError as e:
            e.source_parameter = 'id'
            raise e
