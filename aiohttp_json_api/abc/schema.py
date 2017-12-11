"""
Schema abstract base classes
============================
"""

import abc
import inspect
import itertools
from collections import OrderedDict
from types import MappingProxyType

import inflection

from .processors import MetaProcessors
from .field import FieldABC
from ..jsonpointer import JSONPointer

_issubclass = issubclass


def issubclass(subclass, baseclass):
    """Just like the built-in :func:`issubclass`, this function checks
    whether *subclass* is inherited from *baseclass*. Unlike the
    built-in function, this ``issubclass`` will simply return
    ``False`` if either argument is not suitable (e.g., if *subclass*
    is not an instance of :class:`type`), instead of raising
    :exc:`TypeError`.

    Args:
        subclass (type): The target class to check.
        baseclass (type): The base class *subclass* will be checked against.

    >>> class MyObject(object): pass
    ...
    >>> issubclass(MyObject, object)  # always a fun fact
    True
    >>> issubclass('hi', 'friend')
    False
    """
    try:
        return _issubclass(subclass, baseclass)
    except TypeError:
        return False


def _get_fields(attrs, field_class, pop=False):
    """
    Get fields from a class.

    :param attrs: Mapping of class attributes
    :param type field_class: Base field class
    :param bool pop: Remove matching fields
    """
    fields = [
        (field_name, field_value)
        for field_name, field_value in attrs.items()
        if issubclass(field_value, field_class) or
           isinstance(field_value, field_class)
    ]
    if pop:
        for field_name, _ in fields:
            del attrs[field_name]
    return fields


def _get_fields_by_mro(klass, field_class):
    """
    Collect fields from a class, following its method resolution order. The
    class itself is excluded from the search; only its parents are checked. Get
    fields from ``_declared_fields`` if available, else use ``__dict__``.
    :param type klass: Class whose fields to retrieve
    :param type field_class: Base field class
    """
    mro = inspect.getmro(klass)
    # Loop over mro in reverse to maintain correct order of fields
    return sum(
        (
            _get_fields(
                getattr(base, '_declared_fields', base.__dict__),
                field_class,
            )
            for base in mro[:0:-1]
        ),
        [],
    )


class SchemaMeta(abc.ABCMeta, MetaProcessors):
    @classmethod
    def _assign_sp(mcs, fields, sp: JSONPointer):
        """Sets the :attr:`BaseField.sp` (source pointer) property recursively
        for all child fields.
        """
        from aiohttp_json_api.fields.base import Relationship

        for field in fields:
            field._sp = sp / field.name
            if isinstance(field, Relationship):
                mcs._assign_sp(field.links.values(), field.sp / 'links')

    @classmethod
    def _sp_to_field(mcs, fields):
        """
        Returns an ordered dictionary, which maps the source pointer of a
        field to the field. Nested fields are listed before the parent.
        """
        from aiohttp_json_api.fields.base import Relationship

        result = OrderedDict()
        for field in fields:
            if isinstance(field, Relationship):
                result.update(mcs._sp_to_field(field.links.values()))
            result[field.sp] = field
        return MappingProxyType(result)

    def __new__(mcs, name, bases, attrs):
        """
        Detects all fields and wires everything up. These class attributes are
        defined here:

        *   *type*

            The JSON API typename

        *   *_declared_fields*

            Maps the key (schema property name) to the associated
            :class:`BaseField`.

        *   *_fields_by_sp*

            Maps the source pointer of a field to the associated
            :class:`BaseField`.

        *   *_attributes*

            Maps the JSON API attribute name to the :class:`Attribute`
            instance.

        *   *_relationships*

            Maps the JSON API relationship name to the :class:`Relationship`
            instance.

        *   *_links*

            Maps the JSON API link name to the :class:`Link` instance.

        *   *_meta*

            Maps the (top level) JSON API meta member to the associated
            :class:`Attribute` instance.

        *   *_toplevel*

            A list with all JSON API top level fields (attributes, ..., meta).

        :arg str name:
            The name of the schema class
        :arg tuple bases:
            The direct bases of the schema class
        :arg dict attrs:
            A dictionary with all properties defined on the schema class
            (attributes, methods, ...)
        """
        from aiohttp_json_api.fields.base import Relationship, Attribute, Link

        cls_fields = _get_fields(attrs, FieldABC, pop=True)
        klass = super(SchemaMeta, mcs).__new__(mcs, name, bases, attrs)
        inherited_fields = _get_fields_by_mro(klass, FieldABC)
        declared_fields = OrderedDict()

        options = getattr(klass, 'Options')
        klass.opts = klass.OPTIONS_CLASS(options)

        for key, field in inherited_fields + cls_fields:
            field._key = key
            field.name = (
                field.name or (klass.opts.inflect(key)
                               if callable(klass.opts.inflect)
                               else key)
            )
            field.mapped_key = field.mapped_key or key
            declared_fields[field.key] = field

        # Find nested fields (link_of, ...) and link them with
        # their parent.
        for key, field in declared_fields.items():
            if getattr(field, 'link_of', None):
                relationship = declared_fields[field.link_of]

                if not isinstance(relationship, Relationship):
                    raise TypeError('Links can be added only for '
                                    'relationships fields.')

                relationship.add_link(field)

        klass._id = declared_fields.pop('id', None)

        # Find the *top-level* attributes, relationships,
        # links and meta fields.
        attributes = OrderedDict(
            (key, field)
            for key, field in declared_fields.items()
            if isinstance(field, Attribute) and not field.meta
        )
        mcs._assign_sp(attributes.values(), JSONPointer('/attributes'))
        klass._attributes = MappingProxyType(attributes)

        relationships = OrderedDict(
            (key, field)
            for key, field in declared_fields.items()
            if isinstance(field, Relationship)
        )
        # TODO: Move default links to class initializer
        # It will allow to use custom namespace for Links
        for relationship in relationships.values():
            # Add the default links.
            relationship.links.update({
                'self': Link('jsonapi.relationships',
                             name='self', link_of=relationship.name),
                'related': Link('jsonapi.related',
                                name='related', link_of=relationship.name)

            })
        mcs._assign_sp(relationships.values(), JSONPointer('/relationships'))
        klass._relationships = MappingProxyType(relationships)

        links = OrderedDict(
            (key, field)
            for key, field in declared_fields.items()
            if isinstance(field, Link) and not field.link_of
        )
        mcs._assign_sp(links.values(), JSONPointer('/links'))
        klass._links = MappingProxyType(links)

        meta = OrderedDict(
            (key, field)
            for key, field in declared_fields.items()
            if isinstance(field, Attribute) and field.meta
        )
        mcs._assign_sp(links.values(), JSONPointer('/meta'))
        klass._meta = MappingProxyType(meta)

        # Collect all top level fields in a list.
        toplevel = tuple(
            itertools.chain(
                klass._attributes.values(),
                klass._relationships.values(),
                klass._links.values(),
                klass._meta.values()
            )
        )
        klass._toplevel = toplevel

        # Create the source pointer map.
        klass._fields_by_sp = mcs._sp_to_field(toplevel)

        klass._declared_fields = MappingProxyType(declared_fields)
        return klass

    def __init__(cls, name, bases, attrs):
        """
        Initialise a new schema class.
        """
        super(SchemaMeta, cls).__init__(name, bases, attrs)
        cls._resolve_processors()

    def __call__(cls, *args):
        """
        Creates a new instance of a BaseSchema class.
        """
        return super(SchemaMeta, cls).__call__(*args)



class SchemaOpts(object):
    """class Meta options for the :class:`SchemaABC`. Defines defaults."""

    def __init__(self, options):
        self.resource_cls = getattr(options, 'resource_cls', None)
        self.resource_type = getattr(options, 'resource_type', None)
        self.pagination = getattr(options, 'pagination', None)
        self.inflect = getattr(options, 'inflect', inflection.dasherize)
        self.deflect = getattr(options, 'deflect', inflection.underscore)


class SchemaABC(abc.ABC, metaclass=SchemaMeta):
    OPTIONS_CLASS = SchemaOpts

    class Options:
        pass

    def __init__(self, context):
        """
        Initialize the schema.

        :param ~aiohttp_json_api.context.JSONAPIContext context:
            Resource context instance
        """
        self.ctx = context

    @staticmethod
    @abc.abstractmethod
    def default_getter(field, resource, **kwargs):
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    async def default_setter(field, resource, data, sp, **kwargs):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_field(cls, key) -> FieldABC:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_relationship_field(cls, relation_name, source_parameter=None):
        raise NotImplementedError

    @abc.abstractmethod
    def get_value(self, field, resource, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def set_value(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def serialize_resource(self, resource, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def serialize_relationship(self, relation_name, resource, *,
                               pagination=None):
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-object-relationships

        Creates the JSON API relationship object of the relationship
        *relation_name*.

        :arg str relation_name:
            The name of the relationship
        :arg resource:
            A resource object
        :arg ~aiohttp_json_api.pagination.PaginationABC pagination:
            Describes the pagination in case of a *to-many* relationship.

        :rtype: dict
        :returns:
            The JSON API relationship object for the relationship
            *relation_name* of the *resource*
        """
        raise NotImplementedError

    # Validation (pre deserialize)
    # -----------------------

    @abc.abstractmethod
    async def pre_validate_field(self, field, data, sp):
        """
        Validates the input data for a field, **before** it is deserialized.
        If the field has nested fields, the nested fields are validated first.

        :arg BaseField field:
        :arg data:
            The input data for the field.
        :arg aiohttp_json_api.jsonpointer.JSONPointer sp:
            The pointer to *data* in the original document. If *None*, there
            was no input data for this field.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def pre_validate_resource(self, data, sp, *, expected_id=None):
        """
        Validates a JSON API resource object received from an API client::

            schema.pre_validate_resource(
                data=request.json["data"], sp="/data"
            )

        :arg data:
            The received JSON API resource object
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg JSONAPIContext context:
            Request context instance
        :arg str expected_id:
            If passed, then ID of resrouce will be compared with this value.
            This is required in update methods
        """
        raise NotImplementedError

    # Validation (post deserialize)
    # -----------------------------

    @abc.abstractmethod
    async def post_validate_resource(self, data):
        """
        Validates the decoded *data* of JSON API resource object.

        :arg ~collections.OrderedDict data:
            The *memo* object returned from :meth:`deserialize_resource`.
        :arg JSONAPIContext context:
            Request context instance
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def deserialize_resource(self, data, sp, *, expected_id=None,
                                   validate=True, validation_steps=None):
        """
        Decodes the JSON API resource object *data* and returns a dictionary
        which maps the key of a field to its decoded input data.

        :arg data:
            The received JSON API resource object
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg JSONAPIContext context:
            Request context instance
        :arg str expected_id:
            If passed, then ID of resource will be compared with this value.
            This is required in update methods
        :arg bool validate:
            Is validation required?
        :arg tuple validation_steps:
            Required validation steps

        :rtype: ~collections.OrderedDict
        :returns:
            An ordered dictionary which maps a fields key to a two tuple
            ``(data, sp)`` which contains the input data and the source pointer
            to it.
        """
        raise NotImplementedError
