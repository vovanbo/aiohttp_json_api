"""Utilities related to JSON API."""

from collections import defaultdict, OrderedDict
from typing import Optional, Dict, Any, Union, Callable, Set, Collection, Tuple

import trafaret
from aiohttp import web
from aiohttp.typedefs import LooseHeaders

from aiohttp_json_api.common import JSONAPI, JSONAPI_CONTENT_TYPE, ResourceID
from aiohttp_json_api.context import JSONAPIContext
from aiohttp_json_api.encoder import json_dumps
from aiohttp_json_api.errors import Error, ErrorList, HTTPInternalServerError
from aiohttp_json_api.helpers import first, is_collection
from aiohttp_json_api.pagination import PaginationABC


def jsonapi_response(
    data: Dict[str, Any],
    *,
    status: int = web.HTTPOk.status_code,
    reason: Optional[str] = None,
    headers: Optional[LooseHeaders] = None,
    dumps: Callable[[Any], str] = None,
) -> web.Response:
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
    return web.Response(body=body, status=status, reason=reason, headers=headers, content_type=JSONAPI_CONTENT_TYPE)


async def get_compound_documents(
    resources: Collection[Any],
    ctx: JSONAPIContext,
) -> Tuple[Dict[ResourceID, Any], Dict[str, Set[Tuple[str, ...]]]]:
    """
    Get compound documents of resources. Fetches the relationship paths *paths*.

    .. seealso::

        http://jsonapi.org/format/#fetching-includes

    :param resources:
        A list with the primary data (resources) of the compound
        response document.
    :param ctx:
        A web Request context

    :returns:
        A two tuple with a list of the included resources and a dictionary,
        which maps each resource (primary and included) to a set with the
        names of the included relationships.
    """
    relationships: Dict[str, Set[Tuple[str, ...]]] = defaultdict(set)
    compound_documents: Dict[ResourceID, Any] = OrderedDict()

    collection: Collection[Any] = (resources,) if type(resources) in ctx.registry else resources
    for path in ctx.include:
        if path and collection:
            rest_path = path
            nested_collection = collection
            while rest_path and nested_collection:
                schema_cls, controller_cls = ctx.registry[first(nested_collection)]
                resource_type = schema_cls.opts.resource_type

                if rest_path in relationships[resource_type]:
                    break

                field = schema_cls.get_relationship_field(
                    rest_path[0], source_parameter='include'
                )

                controller = controller_cls(ctx)
                nested_collection = await controller.fetch_compound_documents(
                    field, nested_collection, rest_path=rest_path[1:]
                )

                for relative in nested_collection:
                    compound_documents.setdefault(
                        ctx.registry.ensure_identifier(relative),
                        relative
                    )

                relationships[resource_type].add(rest_path)
                rest_path = rest_path[1:]

    return compound_documents, relationships


def serialize_resource(resource: Any, ctx: JSONAPIContext) -> Dict[str, Any]:
    """
    Serialize resource by schema.

    :param resource: Resource instance
    :param ctx: Request context
    :return: Serialized resource
    """
    try:
        schema_cls, _ = ctx.registry[resource]
        return schema_cls(ctx).serialize_resource(resource)
    except trafaret.DataError as exc:
        raise HTTPInternalServerError(detail=json_dumps(exc.as_dict(value=True)))


async def render_document(
    data,
    included,
    ctx,
    *,
    pagination: Optional[PaginationABC] = None,
    links=None,
) -> Dict[str, Any]:
    """
    Render JSON API document.

    :param data: One or many resources
    :param included: Compound documents
    :param ctx: Request context
    :param pagination: Pagination instance
    :param links: Additional links
    :return: Rendered JSON API document
    """
    document: Dict[str, Any] = OrderedDict()

    if is_collection(data, exclude=(ctx.schema.opts.resource_cls,)):
        document['data'] = [serialize_resource(r, ctx) for r in data]
    else:
        document['data'] = serialize_resource(data, ctx) if data else None

    if ctx.include and included:
        document['included'] = [serialize_resource(r, ctx) for r in included.values()]

    document.setdefault('links', OrderedDict())
    document['links']['self'] = str(ctx.request.url)
    if links is not None:
        document['links'].update(links)

    meta_object = ctx.request.app[JSONAPI]['meta']
    pagination = pagination or ctx.pagination

    if pagination or meta_object:
        document.setdefault('meta', OrderedDict())

    if pagination is not None:
        document['links'].update(pagination.links())
        document['meta'].update(pagination.meta())

    if meta_object:
        document['meta'].update(meta_object)

    jsonapi_info = ctx.request.app[JSONAPI]['jsonapi']
    if jsonapi_info:
        document['jsonapi'] = jsonapi_info

    return document


def error_to_response(request: web.Request, error: Union[Error, ErrorList]) -> web.Response:
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
            'errors': [error.as_dict] if isinstance(error, Error) else error.json,
            'jsonapi': request.app[JSONAPI]['jsonapi']
        },
        status=error.status
    )
