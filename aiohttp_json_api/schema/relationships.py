"""
Relationships
=============
"""

import collections
import typing

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
        super(ToOne, self).validate_relationship_object(schema,
                                                        data, sp)
        if 'data' in data and data['data'] is not None:
            self.validate_resource_identifier(schema, data, sp / 'data')
        return None

    def encode(self, schema, data, **kwargs) -> typing.MutableMapping:
        """Composes the final relationships object."""
        document = {'links': {}}

        if data is None:
            document['data'] = data
        # JSON API resource linkage or JSON API relationships object
        elif isinstance(data, collections.Mapping):
            if 'type' in data and 'id' in data:
                document['data'] = data
        # the related resource instance
        else:
            document['data'] = schema.registry.ensure_identifier(data, asdict=True)

        links = kwargs.get('links', {})
        if links:
            document['links'].update(links)

        return filter_empty_fields(document)


class ToMany(Relationship):
    """
    .. seealso::

        *   http://jsonapi.org/format/#document-resource-object-relationships
        *   http://jsonapi.org/format/#document-resource-object-linkage

    Describes how to serialize, deserialize and update a *to-many* relationship.
    Additionally to *to-one* relationships, *to-many* relationships must also
    support adding and removing relatives.

    :arg callable fadd:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which adds new resources
        to the relationship ``fadd(self, resource, data, sp, **kwargs)``.
    :arg callable fremove:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which removes some resources
        from the relationship ``fremove(self, resource, data, sp, **kwargs)``.
    :arg aiohttp_json_api.pagination.BasePagination pagination:
        The pagination helper *class* used to paginate the *to-many*
        relationship.

    """
    to_one = False
    to_many = True

    def __init__(self, *, fadd=None, fremove=None, pagination=None, **kwargs):
        super(ToMany, self).__init__(**kwargs)
        self.fadd = fadd
        self.fremove = fremove
        self.pagination = pagination

    def adder(self, f):
        """
        Descriptor to change the adder.

        :seealso: :func:`~aiohttp_json_api.schema.decorators.adds`
        """
        self.fadd = f
        return self

    def remover(self, f):
        """
        Descriptor to change the remover.

        :seealso: :func:`~aiohttp_json_api.schema.decorators.removes`
        """
        self.fremove = f
        return self

    async def default_add(self, schema, resource, data, sp):
        """Used if no *adder* has been defined. **Should** be overridden."""
        logger.warning('You should override the adder.')

        if not self.mapped_key:
            raise RuntimeError('No adder and mapped_key have been defined.')

        relatives = getattr(resource, self.mapped_key)
        relatives.extend(data)
        return None

    async def default_remove(self, schema, resource, data, sp):
        """Used if not *remover* has been defined. **Should** be overridden."""
        logger.warning('You should override the remover.')

        if not self.mapped_key:
            raise RuntimeError('No remover and mapped_key have been defined.')

        relatives = getattr(resource, self.mapped_key)
        for relative in data:
            try:
                relatives.remove(relative)
            except ValueError:
                pass
        return None

    async def add(self, schema, resource, data, sp, **kwargs):
        """Adds new resources to the relationship."""
        f = self.fadd or self.default_add
        return await f(schema, resource, data, sp, **kwargs)

    async def remove(self, schema, resource, data, sp, **kwargs):
        """Removes resources from the relationship."""
        f = self.fremove or self.default_remove
        return await f(schema, resource, data, sp, **kwargs)

    def encode(self, schema, data, **kwargs) -> typing.MutableMapping:
        """Composes the final JSON API relationships object.

        :arg ~aiohttp_json_api.pagination.BasePagination pagination:
            If not *None*, the links and meta members of the pagination
            helper are added to the final JSON API relationship object.
        """
        document = {'links': {}, 'meta': {}}

        if isinstance(data, collections.Iterable):
            document['data'] = [
                schema.registry.ensure_identifier(item, asdict=True)
                for item in data
            ]

        links = kwargs.get('links', {})
        if links:
            document['links'].update(links)

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
        if 'data' in data:
            if not isinstance(data['data'], collections.Sequence):
                detail = 'The "data" must be an array of resource identifier ' \
                         'objects.'
                raise InvalidType(detail=detail, source_pointer=sp / 'data')

            for i, item in enumerate(data):
                self.validate_resource_identifier(schema, item, sp / 'data' / i)
