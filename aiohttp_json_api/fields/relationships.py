"""
Relationships
=============
"""

from collections import Mapping, OrderedDict
from typing import Any, Dict, Optional

from aiohttp_json_api.context import JSONAPIContext
from aiohttp_json_api.fields.base import Relationship
from aiohttp_json_api.common import Relation
from aiohttp_json_api.errors import InvalidType
from aiohttp_json_api.helpers import is_collection
from aiohttp_json_api.jsonpointer import JSONPointer
from aiohttp_json_api.pagination import PaginationABC
from aiohttp_json_api.schema import BaseSchema

__all__ = (
    'ToOne',
    'ToMany',
)


class ToOne(Relationship):
    """
    .. seealso::

        *   http://jsonapi.org/format/#document-resource-object-relationships
        *   http://jsonapi.org/format/#document-resource-object-linkage

    Describes how to serialize, deserialize and update a *to-one* relationship.
    """
    relation = Relation.TO_ONE

    def validate_relationship_object(self, data: Any, sp: JSONPointer) -> None:
        """
        Checks additionaly to :meth:`Relationship.validate_relationship_object`
        that the *data* member is a valid resource linkage.
        """
        super(ToOne, self).validate_relationship_object(data, sp)
        if 'data' in data and data['data'] is not None:
            self.validate_resource_identifier(data['data'], sp / 'data')

    def serialize(self, data: Any, **kwargs: Any) -> Dict[str, Any]:
        """Composes the final relationships object."""
        context: JSONAPIContext = kwargs['context']
        document: Dict[str, Any] = OrderedDict()

        if data is None:
            document['data'] = data
        elif isinstance(data, Mapping):
            # JSON API resource linkage or JSON API relationships object
            if 'type' in data and 'id' in data:
                document['data'] = data
        else:
            # the related resource instance
            rid = context.registry.ensure_identifier(data)
            document['data'] = rid._asdict()

        links = kwargs.get('links')
        if links is not None:
            document['links'] = links

        return document


class ToMany(Relationship):
    """
    .. seealso::

        *   http://jsonapi.org/format/#document-resource-object-relationships
        *   http://jsonapi.org/format/#document-resource-object-linkage

    Describes how to serialize, deserialize and update a *to-many*
    relationship. Additionally to *to-one* relationships, *to-many*
    relationships must also support adding and removing relatives.

    :arg aiohttp_json_api.pagination.PaginationABC pagination:
        The pagination helper *class* used to paginate the *to-many*
        relationship.
    """
    relation = Relation.TO_MANY

    def __init__(self, *, pagination: Optional[PaginationABC] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.pagination = pagination

    def serialize(
        self,
        data: Any,
        links: Optional[Dict[str, str]] = None,
        pagination: Optional[PaginationABC] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Composes the final JSON API relationships object.

        :arg ~aiohttp_json_api.pagination.PaginationABC pagination:
            If not *None*, the links and meta members of the pagination
            helper are added to the final JSON API relationship object.
        """
        context: JSONAPIContext = kwargs['context']
        document: Dict[str, Any] = OrderedDict()

        if is_collection(data):
            document['data'] = [context.registry.ensure_identifier(item)._asdict() for item in data]

        if links is not None:
            document['links'] = links

        if pagination is not None:
            document['links'].update(pagination.links())
            document.setdefault('meta', OrderedDict())
            document['meta'].update(pagination.meta())

        return document

    def validate_relationship_object(self, data: Any, sp: JSONPointer) -> None:
        """
        Checks additionaly to :meth:`Relationship.validate_relationship_object`
        that the *data* member is a list of resource identifier objects.
        """
        super().validate_relationship_object(data, sp)
        if 'data' in data and not is_collection(data['data']):
            detail = 'The "data" must be an array of resource identifier objects.'
            raise InvalidType(detail=detail, source_pointer=sp / 'data')

        for index, item in enumerate(data['data']):
            self.validate_resource_identifier(item, sp / 'data' / str(index))
