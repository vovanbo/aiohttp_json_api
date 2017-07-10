"""
Application registry
====================
"""
import collections
from typing import MutableMapping, Union

from .helpers import make_sentinel


ARG_DEFAULT = make_sentinel(var_name='ARG_DEFAULT')
ResourceID = collections.namedtuple('ResourceID', ['type', 'id'])


class Registry:
    __slots__ = ('schema_by_type', 'schema_by_resource')

    def __init__(self, *, schema_by_type: MutableMapping,
                 schema_by_resource: MutableMapping):
        assert isinstance(schema_by_type, MutableMapping)
        assert isinstance(schema_by_resource, MutableMapping)

        self.schema_by_type = schema_by_type
        self.schema_by_resource = schema_by_resource

    def get_schema(self, obj, default=ARG_DEFAULT):
        """
        Returns the :class:`~aiohttp_json_api.schema.Schema`
        associated with *obj*. *obj* must be either a typename,
        a resource class or resource object.

        :param obj:
            A typename, resource object or a resource class
        :param default:
            Returned if no schema for *obj* is found.
        :raises KeyError:
            If no schema for *o* is found and no *default* value is given.
        """
        schema = (
            self.schema_by_resource.get(type(obj)) or
            self.schema_by_resource.get(obj) or
            self.schema_by_type.get(obj)
        )

        if schema is not None:
            return schema
        if default != ARG_DEFAULT:
            return default
        raise KeyError()

    def ensure_identifier(self, obj, asdict=False) -> \
        Union[ResourceID, MutableMapping[str, str]]:
        """
        Returns the identifier object (:class:`ResourceID`) for the *resource*:

        .. code-block:: python3

            >>> registry.ensure_identifier({'type': 'something', 'id': 123})
            ResourceID(type='something', id='123')

        :arg obj:
            A two tuple ``(typename, id)``, a resource object or a resource
            document, which contains the *id* and *type* key
            ``{"type": ..., "id": ...}``.
        :arg bool asdict:
            Return ResourceID as dictionary if true
        """
        if isinstance(obj, collections.Sequence):
            assert len(obj) == 2
            result = ResourceID(str(obj[0]), str(obj[1]))
        elif isinstance(obj, collections.Mapping):
            result = ResourceID(str(obj['type']), str(obj['id']))
        else:
            schema = self.get_schema(obj)
            result = ResourceID(schema.type, str(schema._get_id(obj)))

        return result._asdict() if asdict and result else result
