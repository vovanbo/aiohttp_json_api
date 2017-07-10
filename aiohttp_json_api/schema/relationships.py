"""
Relationships
=============
"""

import typing
from collections import OrderedDict, Mapping

from aiohttp_json_api.helpers import is_collection
from .base_fields import Relationship
from ..errors import InvalidType
from ..log import logger
from ..utils import filter_empty_fields

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
    to_one = True
    to_many = False

    def validate_relationship_object(self, schema, data, sp):
        """
        Checks additionaly to :meth:`Relationship.validate_relationship_object`
        that the *data* member is a valid resource linkage.
        """
        super(ToOne, self).validate_relationship_object(schema, data, sp)
        if 'data' in data and data['data'] is not None:
            self.validate_resource_identifier(schema, data['data'], sp / 'data')

    def serialize(self, schema, data, **kwargs) -> typing.MutableMapping:
        """Composes the final relationships object."""
        document = {'links': kwargs.get('links', {})}

        if data is None:
            document['data'] = data
        # JSON API resource linkage or JSON API relationships object
        elif isinstance(data, Mapping):
            if 'type' in data and 'id' in data:
                document['data'] = data
        # the related resource instance
        else:
            document['data'] = \
                schema.registry.ensure_identifier(data, asdict=True)

        return filter_empty_fields(document)


class ToMany(Relationship):
    """
    .. seealso::

        *   http://jsonapi.org/format/#document-resource-object-relationships
        *   http://jsonapi.org/format/#document-resource-object-linkage

    Describes how to serialize, deserialize and update a *to-many* relationship.
    Additionally to *to-one* relationships, *to-many* relationships must also
    support adding and removing relatives.

    :arg aiohttp_json_api.pagination.BasePagination pagination:
        The pagination helper *class* used to paginate the *to-many*
        relationship.
    """
    to_one = False
    to_many = True

    def __init__(self, *, pagination=None, **kwargs):
        super(ToMany, self).__init__(**kwargs)
        self.pagination = pagination

    def serialize(self, schema, data, **kwargs) -> typing.MutableMapping:
        """Composes the final JSON API relationships object.

        :arg ~aiohttp_json_api.pagination.BasePagination pagination:
            If not *None*, the links and meta members of the pagination
            helper are added to the final JSON API relationship object.
        """
        document = {
            'links': kwargs.get('links', {}),
            'meta': {}
        }

        if is_collection(data):
            document['data'] = [
                schema.registry.ensure_identifier(item, asdict=True)
                for item in data
            ]

        pagination = kwargs.get('pagination')
        if pagination:
            document['links'].update(pagination.links())
            document['meta'].update(pagination.meta())

        return filter_empty_fields(document)

    def validate_relationship_object(self, schema, data, sp):
        """
        Checks additionaly to :meth:`Relationship.validate_relationship_object`
        that the *data* member is a list of resource identifier objects.
        """
        super(ToMany, self).validate_relationship_object(schema, data, sp)
        if 'data' in data and not is_collection(data['data']):
            detail = 'The "data" must be an array ' \
                     'of resource identifier objects.'
            raise InvalidType(detail=detail, source_pointer=sp / 'data')

        for i, item in enumerate(data['data']):
            self.validate_resource_identifier(schema, item, sp / 'data' / i)
