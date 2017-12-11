"""Application registry."""

import collections
import inspect

from .common import ResourceID
from .typings import ResourceIdentifier


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
        return super(Registry, self).__getitem__(
            key if isinstance(key, str) or inspect.isclass(key) else type(key)
        )

    def ensure_identifier(self, obj, asdict=False) -> ResourceIdentifier:
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
            result = ResourceID(str(obj[0]), str(obj[1]))
        elif isinstance(obj, collections.Mapping):
            result = ResourceID(str(obj['type']), str(obj['id']))
        else:
            try:
                schema_cls, _ = self.data[type(obj)]
                result = ResourceID(schema_cls.opts.resource_type,
                                    schema_cls.get_object_id(obj))
            except KeyError:
                raise RuntimeError(
                    'Schema for %s is not found.' % obj.__class__.__name__
                )

        return result._asdict() if asdict and result else result
