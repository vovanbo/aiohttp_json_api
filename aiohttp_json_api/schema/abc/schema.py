"""
Schema abstract base classes
============================
"""

import inspect
import itertools
import abc
from collections import OrderedDict, defaultdict
from types import MappingProxyType

import inflection

from ...const import ALLOWED_MEMBER_NAME_REGEX
from ...jsonpointer import JSONPointer

from .field import FieldABC

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


class SchemaMeta(abc.ABCMeta):
    @classmethod
    def _assign_sp(mcs, fields, sp: JSONPointer):
        """Sets the :attr:`BaseField.sp` (source pointer) property recursively
        for all child fields.
        """
        from aiohttp_json_api.schema.base_fields import Relationship

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
        from aiohttp_json_api.schema.base_fields import Relationship

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
        from aiohttp_json_api.schema.base_fields import (
            Relationship, Attribute, Link
        )

        cls_fields = _get_fields(attrs, FieldABC, pop=True)
        klass = super(SchemaMeta, mcs).__new__(mcs, name, bases, attrs)
        inherited_fields = _get_fields_by_mro(klass, FieldABC)
        declared_fields = OrderedDict()

        for key, field in inherited_fields + cls_fields:
            field._key = key
            field.name = \
                field.name or (klass.inflect(key)
                               if callable(klass.inflect) else key)
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

        # Find the *top-level* attributes, relationships, links and meta fields.
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

        # Determine 'type' name.
        if not attrs.get('type') and attrs.get('resource_class'):
            klass.type = inflection.dasherize(
                inflection.tableize(attrs['resource_class'].__name__)
            )

        if not klass.type:
            klass.type = name

        if not ALLOWED_MEMBER_NAME_REGEX.fullmatch(klass.type):
            raise ValueError('Type "{}" is not allowed.'.format(klass.type))

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

    def _resolve_processors(cls):
        """
        Add in the decorated processors
        By doing this after constructing the class, we let standard inheritance
        do all the hard work.

        Almost the same as https://github.com/marshmallow-code/marshmallow/blob/dev/marshmallow/schema.py#L139-L174
        """
        mro = inspect.getmro(cls)
        cls._has_processors = False
        cls.__processors__ = defaultdict(list)
        for attr_name in dir(cls):
            # Need to look up the actual descriptor, not whatever might be
            # bound to the class. This needs to come from the __dict__ of the
            # declaring class.
            for parent in mro:
                try:
                    attr = parent.__dict__[attr_name]
                except KeyError:
                    continue
                else:
                    break
            else:
                # In case we didn't find the attribute and didn't break above.
                # We should never hit this - it's just here for completeness
                # to exclude the possibility of attr being undefined.
                continue

            try:
                processor_tags = attr.__processing_tags__
            except AttributeError:
                continue

            cls._has_processors = bool(processor_tags)
            for tag in processor_tags:
                # Use name here so we can get the bound method later, in case
                # the processor was a descriptor or something.
                cls.__processors__[tag].append(attr_name)


class SchemaABC(abc.ABC, metaclass=SchemaMeta):
    #: The JSON API *type*. (Leave it empty to derive it automatic from the
    #: resource class name or the schema name).
    type = None
    resource_class = None
    opts = None
    inflect = None

    @abc.abstractmethod
    def default_getter(self, field, resource, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def default_setter(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def default_include(self, field, resources, context, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def default_query(self, field, resource, context, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def default_add(self, field, resource, data, sp):
        raise NotImplementedError

    @abc.abstractmethod
    async def default_remove(self, field, resource, data, sp):
        raise NotImplementedError

    @abc.abstractmethod
    def get_relationship_field(self, relation_name, source_parameter=None):
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

    @abc.abstractmethod
    async def pre_validate_resource(self, data, sp, context,
                                    *, expected_id=None):
        """
        Validates a JSON API resource object received from an API client::

            schema.pre_validate_resource(
                data=request.json["data"], sp="/data"
            )

        :arg data:
            The received JSON API resource object
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg RequestContext context:
            Request context instance
        :arg str expected_id:
            If passed, then ID of resrouce will be compared with this value.
            This is required in update methods
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def post_validate_resource(self, data, context):
        """
        Validates the decoded *data* of JSON API resource object.

        :arg ~collections.OrderedDict data:
            The *memo* object returned from :meth:`deserialize_resource`.
        :arg RequestContext context:
            Request context instance
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def deserialize_resource(self, data, sp, context, *,
                                   expected_id=None, validate=True,
                                   validation_steps=None):
        """
        Decodes the JSON API resource object *data* and returns a dictionary
        which maps the key of a field to its decoded input data.

        :arg data:
            The received JSON API resource object
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg RequestContext context:
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

    # CRUD (resource)
    # ---------------

    @abc.abstractmethod
    async def fetch_resource(self, resource_id, context, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    async def create_resource(self, data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-creating

        Creates a new resource instance and returns it. **You should overridde
        this method.**

        The default implementation passes the attributes, (dereferenced)
        relationships and meta data from the JSON API resource object
        *data* to the constructor of the resource class. If the primary
        key is *writable* on creation and a member of *data*, it is also
        passed to the constructor.

        :arg dict data:
            The JSON API resource object with the initial data.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def update_resource(self, resource_id, data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating

        Updates an existing *resource*. **You should overridde this method** in
        order to save the changes in the database.

        The default implementation uses the
        :class:`~aiohttp_json_api.schema.base_fields.BaseField`
        descriptors to update the resource.

        :arg resource_id:
            The id of the resource
        :arg dict data:
            The JSON API resource object with the update information
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance
        """

        raise NotImplementedError

    @abc.abstractmethod
    async def delete_resource(self, resource_id, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-deleting

        Deletes the *resource*. **You must overridde this method.**

        :arg resource_id:
            The id of the resource or the resource instance
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance
        """
        raise NotImplementedError

    # CRUD (relationships)
    # --------------------

    @abc.abstractmethod
    async def update_relationship(self, relation_name, resource_id,
                                  data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-relationships

        Updates the relationship with the JSON API name *relation_name*.

        :arg str relation_name:
            The name of the relationship.
        :arg resource_id:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def add_relationship(self, relation_name, resource_id,
                               data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        Adds the members specified in the JSON API relationship object *data*
        to the relationship, unless the relationships already exist.

        :arg str relation_name:
            The name of the relationship.
        :arg resource_id:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def remove_relationship(self, relation_name, resource_id,
                                  data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        Deletes the members specified in the JSON API relationship object *data*
        from the relationship.

        :arg str relation_name:
            The name of the relationship.
        :arg resource_id:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance.
        """
        raise NotImplementedError

    # Querying
    # --------

    @abc.abstractmethod
    async def query_collection(self, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching

        Fetches a subset of the collection represented by this schema.
        **Must be overridden.**

        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context instance.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def query_resource(self, resource_id, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching

        Fetches the resource with the id *id_*. **Must be overridden.**

        :arg str resource_id:
            The id of the requested resource.
        :arg RequestContext context:
            A request context instance
        :raises ~aiohttp_json_api.errors.ResourceNotFound:
            If there is no resource with the given *id_*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def query_relatives(self, relation_name, resource_id, context,
                              **kwargs):
        """
        Controller for the *related* endpoint of the relationship with
        then name *relation_name*.

        :arg str relation_name:
            The name of a relationship.
        :arg str resource_id:
            The id of the resource_id or the resource_id instance.
        :arg RequestContext context:
            A request context instance
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def fetch_compound_documents(self, relation_name, resources, context,
                                       *, rest_path=None, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching-includes

        Fetches the related resources. The default method uses the
        :meth:`~aiohttp_json_api.schema.base_fields.Relationship.include`
        method of the *Relationship* fields. **Can be overridden.**

        :arg str relation_name:
            The name of the relationship.
        :arg resources:
            A list of resources.
        :arg RequestContext context:
            Request context instance.
        :arg list rest_path:
            The name of the relationships of the returned relatives, which
            will also be included.
        :rtype: list
        :returns:
            A list with the related resources. The list is empty or has
            exactly one element in the case of *to-one* relationships.
            If *to-many* relationships are paginated, the relatives from the
            first page should be returned.
        """
        raise NotImplementedError
