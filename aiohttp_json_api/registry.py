"""Application registry."""

import collections
import inspect
from typing import Any, Type, Tuple

from aiohttp_json_api.common import ResourceID


class Registry(collections.UserDict):
    """
    JSON API application registry.

    This is a dictionary created on JSON API application set up.
    It contains a mapping between types, resource classes and schemas.
    """
    __slots__ = ('data',)

    def __getitem__(self, key):
        """
        Get schema for type or resource class type.

        :param key: Type string or resource class.
        :return: Schema instance
        """
        item = key if isinstance(key, str) or inspect.isclass(key) else type(key)
        return super().__getitem__(item)

    def ensure_identifier(self, obj: Any) -> ResourceID:
        """
        Return the identifier object for the *resource*.

        (:class:`ResourceID <.common.ResourceID>`)

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
        if isinstance(obj, collections.Sequence) and len(obj) == 2:
            result = ResourceID(type=str(obj[0]), id=str(obj[1]))
        elif isinstance(obj, collections.Mapping):
            result = ResourceID(type=str(obj['type']), id=str(obj['id']))
        else:
            try:
                schema_cls, _ = self.data[type(obj)]
                result = ResourceID(type=schema_cls.opts.resource_type, id=schema_cls.get_object_id(obj))
            except KeyError:
                raise RuntimeError('Schema for %s is not found.' % obj.__class__.__name__)

        return result

    @property
    def classes(self) -> Tuple[Type[Any], ...]:
        return tuple(filter(inspect.isclass, self.keys()))
