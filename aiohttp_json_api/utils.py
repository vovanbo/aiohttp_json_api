import json
import typing
from collections import OrderedDict, defaultdict
from http import HTTPStatus

import attr
import inflection
from aiohttp import web
from boltons.iterutils import remap, first

from .helpers import is_collection
from .const import JSONAPI, JSONAPI_CONTENT_TYPE
from .errors import Error, ErrorList, ValidationError

SENTINEL = object()


@attr.s(hash=True, frozen=True, cmp=False)
class Symbol:
    name = attr.ib(convert=str, default='', hash=True)


@attr.s
class Document:
    jsonapi = attr.ib(default=attr.Factory(dict))
    meta = attr.ib(default=attr.Factory(dict))
    data = attr.ib(default=None)
    included = attr.ib(default=attr.Factory(list))
    links = attr.ib(default=attr.Factory(dict))
    errors = attr.ib(default=attr.Factory(dict))

    def as_dict_without_empty_fields(self):
        required = ('errors',) if self.errors else ('data',)
        return attr.asdict(
            self,
            filter=lambda a, v: bool(v) if a.name not in required else True
        )


def jsonapi_response(data=SENTINEL, *, text=None, body=None,
                     status=web.HTTPOk.status_code,
                     reason=None, headers=None,
                     dumps=json.dumps):
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
        schema = registry.get_schema(
            registry.ensure_identifier(first(collection)).type
        )
        if relation_name in relationships[schema.type]:
            return

        relatives = await schema.fetch_include(relation_name,
                                               collection, context,
                                               rest_path=rest_path, **kwargs)

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


async def encode_resource(resource, context):
    registry = context.request.app[JSONAPI]['registry']
    schema = registry.get_schema(resource)
    return await schema.encode_resource(
        resource, is_data=True, context=context,
    )


async def render_document(resources, compound_documents, context, *,
                          pagination=None, links=None):
    document = Document()
    pagination = pagination or context.pagination

    if is_collection(resources):
        document.data = [await encode_resource(r, context) for r in resources]
    else:
        document.data = (
            await encode_resource(resources, context)
            if resources else None
        )

    if context.include and compound_documents:
        document.included = [
            await encode_resource(r, context)
            for r in compound_documents.values()
        ]

    document.links['self'] = str(context.request.url)
    if links is not None:
        document.links.update(links)

    if pagination is not None:
        document.links.update(pagination.links())
        document.meta.update(pagination.meta())

    document.jsonapi.update(context.request.app[JSONAPI]['jsonapi'])

    return document.as_dict_without_empty_fields()


async def get_data_from_request(request: web.Request):
    data = await request.json()
    return remap(
        data,
        lambda p, k, v: (
            inflection.underscore(k) if isinstance(k, str) else k, v
        )
    )


def error_to_response(request: web.Request,
                      error: typing.Union[Error, ErrorList]):
    """
    Converts an :class:`Error` to a :class:`~web.Response`.

    :arg web.Request request:
        The web request instance.
    :arg typing.Union[Error, ErrorList] error:
        The error, which is converted into a response.

    :rtype: web.Response
    """
    assert isinstance(error, (Error, ErrorList))

    document = Document()
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    if isinstance(error, Error):
        document.errors = [error.json]
        status = error.status
    elif isinstance(error, ErrorList):
        document.errors = error.json
        status = max(e.status for e in error.errors)

    document.jsonapi.update(request.app[JSONAPI]['jsonapi'])

    return jsonapi_response(
        document.as_dict_without_empty_fields(),
        status=status.value
    )


async def validate_uri_resource_id(schema, resource_id, context):
    field = schema._id
    if field:
        try:
            field.validate_pre_decode(schema, resource_id,
                                      sp=None, context=context)
        except ValidationError as e:
            e.source_parameter = 'id'
            raise e
