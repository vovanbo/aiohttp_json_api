#!/usr/bin/env python3

"""
Base schema
===========

This module contains the base schema which implements the encoding, decoding,
validation and update operations based on
:class:`fields <aiohttp_json_api.schema.base_fields.BaseField>`.
"""
import abc
import asyncio
import inspect
import itertools
import urllib.parse
from collections import MutableMapping, OrderedDict
from types import MappingProxyType
from typing import Dict, Any, Optional, Collection, Iterable, Mapping, Tuple, Type, Union, List

import inflection

from aiohttp_json_api.abc.processors import ProcessorsMeta
from aiohttp_json_api.context import JSONAPIContext

from aiohttp_json_api.fields.base import Attribute, Relationship, BaseField
from aiohttp_json_api.fields.decorators import Tag
from aiohttp_json_api.common import Event, Relation, Step
from aiohttp_json_api.errors import HTTPBadRequest, HTTPConflict, InvalidType, InvalidValue, ValidationError
from aiohttp_json_api.helpers import MISSING, first, get_router_resource, get_processors
from aiohttp_json_api.jsonpointer import JSONPointer
from aiohttp_json_api.pagination import PaginationABC

__all__ = (
    'BaseSchema',
)

_issubclass = issubclass


def issubclass(subclass: Type[Any], baseclass: Type[Any]) -> bool:
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


def _get_fields(attrs: Dict[str, Any], field_class: Type[BaseField], pop: bool = False) -> List[Tuple[str, Any]]:
    """
    Get fields from a class.

    :param attrs: Mapping of class attributes
    :param type field_class: Base field class
    :param bool pop: Remove matching fields
    """
    fields = [
        (field_name, field_value)
        for field_name, field_value in attrs.items()
        if issubclass(field_value, field_class) or isinstance(field_value, field_class)
    ]
    if pop:
        for field_name, _ in fields:
            del attrs[field_name]
    return fields


def _get_fields_by_mro(klass: Type['SchemaABC'], field_class: Type[BaseField]) -> List[Tuple[str, Any]]:
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


class SchemaMeta(ProcessorsMeta):
    @classmethod
    def _assign_sp(mcs, fields: Iterable[BaseField], sp: JSONPointer) -> None:
        """Sets the :attr:`BaseField.sp` (source pointer) property recursively
        for all child fields.
        """
        from aiohttp_json_api.fields.base import Relationship

        for field in fields:
            field._sp = sp / field.name
            if isinstance(field, Relationship):
                mcs._assign_sp(field.links.values(), field.sp / 'links')

    @classmethod
    def _sp_to_field(mcs, fields: Iterable[BaseField]) -> Mapping[JSONPointer, BaseField]:
        """
        Returns an ordered dictionary, which maps the source pointer of a
        field to the field. Nested fields are listed before the parent.
        """
        from aiohttp_json_api.fields.base import Relationship

        result: Dict[JSONPointer, BaseField] = OrderedDict()
        for field in fields:
            if isinstance(field, Relationship):
                result.update(mcs._sp_to_field(field.links.values()))
            result[field.sp] = field
        return MappingProxyType(result)

    def __new__(mcs, name: str, bases: Tuple[Type['SchemaABC'], ...], attrs: Dict[str, Any]) -> 'SchemaABC':
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

        cls_fields = _get_fields(attrs, BaseField, pop=True)
        klass = super(SchemaMeta, mcs).__new__(mcs, name, bases, attrs)
        inherited_fields = _get_fields_by_mro(klass, BaseField)
        declared_fields: Dict[str, Union[BaseField, Link]] = OrderedDict()

        options = getattr(klass, 'Options')
        klass.opts = klass.OPTIONS_CLASS(options)

        for key, field in inherited_fields + cls_fields:
            field._key = key
            field.name = (
                field.name or (klass.opts.inflect(key) if callable(klass.opts.inflect) else key)
            )
            field.mapped_key = field.mapped_key or key
            declared_fields[field.key] = field

        # Find nested fields (link_of, ...) and link them with
        # their parent.
        for key, field in declared_fields.items():
            if getattr(field, 'link_of', None):
                relationship = declared_fields[field.link_of]

                if not isinstance(relationship, Relationship):
                    raise TypeError('Links can be added only for relationships fields.')

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

        relationships: Dict[str, Relationship] = OrderedDict(
            (key, field)
            for key, field in declared_fields.items()
            if isinstance(field, Relationship)
        )
        # TODO: Move default links to class initializer
        # It will allow to use custom namespace for Links
        for relationship in relationships.values():
            # Add the default links.
            relationship.links.update({
                'self': Link('jsonapi.relationships', name='self', link_of=relationship.name),
                'related': Link('jsonapi.related', name='related', link_of=relationship.name)

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

    def __init__(cls, name: str, bases: Tuple['SchemaMeta', ...], attrs: Dict[str, Any]) -> None:
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


class SchemaOpts:
    """class Meta options for the :class:`SchemaABC`. Defines defaults."""
    def __init__(self, options: Type[Any]) -> None:
        self.resource_cls = getattr(options, 'resource_cls', None)
        self.resource_type = getattr(options, 'resource_type', None)
        self.pagination = getattr(options, 'pagination', None)
        self.inflect = getattr(options, 'inflect', inflection.dasherize)
        self.deflect = getattr(options, 'deflect', inflection.underscore)


class SchemaABC(abc.ABC, metaclass=SchemaMeta):
    OPTIONS_CLASS = SchemaOpts

    class Options:
        pass

    def __init__(self, context: JSONAPIContext) -> None:
        """
        Initialize the schema.

        :param ~aiohttp_json_api.context.JSONAPIContext context:
            Resource context instance
        """
        self.ctx = context

    @staticmethod
    @abc.abstractmethod
    def default_getter(field, resource, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    async def default_setter(field, resource, data, sp, **kwargs):
        pass

    @classmethod
    @abc.abstractmethod
    def get_field(cls, key) -> BaseField:
        pass

    @classmethod
    @abc.abstractmethod
    def get_relationship_field(cls, relation_name, source_parameter=None):
        pass

    @abc.abstractmethod
    def get_value(self, field, resource, **kwargs):
        pass

    @abc.abstractmethod
    async def set_value(self, field, resource, data, sp, **kwargs):
        pass

    @abc.abstractmethod
    def serialize_resource(self, resource, **kwargs):
        pass

    @abc.abstractmethod
    def serialize_relationship(
        self,
        relation_name: str,
        resource,
        *,
        pagination: Optional[PaginationABC] = None,
    ):
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
        pass

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
        pass

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
        pass

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
        pass

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
        pass


class BaseSchema(SchemaABC):
    """
    A schema defines how we can serialize a resource and patch it.
    It also allows to patch a resource. All in all, it defines
    a **controller** for a *type* in the JSON API.

    If you want, you can implement your own request handlers and only use
    the schema for validation and serialization.
    """

    @staticmethod
    def get_object_id(resource: Any) -> str:
        """
        **Can be overridden**.

        Returns the id (string) of the resource. The default implementation
        looks for a property ``resource.id``, an id method ``resource.id()``,
        ``resource.get_id()`` or a key ``resource["id"]``.

        :arg resource:
            A resource object
        :rtype: str
        :returns:
            The string representation of ID of the *resource*
        """
        if hasattr(resource, 'id'):
            resource_id = resource.id() if callable(resource.id) else resource.id
        elif hasattr(resource, 'get_id'):
            resource_id = resource.get_id()
        elif 'id' in resource:
            resource_id = resource['id']
        else:
            raise Exception('Could not determine the resource id.')
        return str(resource_id)

    @classmethod
    def get_field(cls, key: str) -> BaseField:
        return cls._declared_fields[key]

    @classmethod
    def get_relationship_field(cls, relation_name: str, source_parameter: Optional[str] = None) -> Relationship:
        try:
            return cls._relationships[cls.opts.deflect(relation_name)]
        except KeyError:
            raise HTTPBadRequest(
                detail=f"Wrong relationship name '{relation_name}'.",
                source_parameter=source_parameter
            )

    @staticmethod
    def default_getter(field: BaseField, resource: Any, **kwargs) -> Any:
        if field.mapped_key:
            return getattr(resource, field.mapped_key)
        return None

    @staticmethod
    async def default_setter(field: BaseField, resource: Any, data: Any, sp: JSONPointer, **kwargs) -> None:
        if field.mapped_key:
            setattr(resource, field.mapped_key, data)

    def get_value(self, field: BaseField, resource: Any, **kwargs) -> Any:
        getter, getter_kwargs = first(get_processors(self, Tag.GET, field, self.default_getter))
        return getter(field, resource, **getter_kwargs, **kwargs)

    async def set_value(self, field: BaseField, resource: Any, data: Any, sp: JSONPointer, **kwargs) -> Any:
        if field.writable is Event.NEVER:
            raise RuntimeError('Attempt to set value to read-only field.')

        setter, setter_kwargs = first(get_processors(self, Tag.SET, field, self.default_setter))
        return await setter(field, resource, data, sp, **setter_kwargs, **kwargs)

    def serialize_resource(self, resource: Any, **kwargs) -> Dict[str, Any]:
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-objects

        :arg resource: A resource object
        """
        fieldset = self.ctx.fields.get(self.opts.resource_type)

        fields_map = (
            ('attributes', self._attributes),
            ('relationships', self._relationships),
            ('meta', self._meta),
            ('links', self._links)
        )

        result = OrderedDict((
            ('type', self.opts.resource_type),
            ('id', self.get_object_id(resource)),
        ))

        for key, schema_fields in fields_map:
            for field in schema_fields.values():
                # Ignore 'load_only' field during serialization
                if getattr(field, 'load_only', False):
                    continue

                if fieldset is None or field.name in fieldset:
                    field_data = self.get_value(field, resource, **kwargs)
                    links = None
                    if isinstance(field, Relationship):
                        links = {
                            link.name: link.serialize(resource, context=self.ctx, **kwargs)
                            for link in field.links.values()
                        }
                    # TODO: Validation steps for pre/post serialization
                    result.setdefault(key, OrderedDict())
                    result[key][field.name] = field.serialize(
                        data=field_data,
                        links=links,
                        context=self.ctx,
                        **kwargs,
                    )

        result.setdefault('links', OrderedDict())
        if 'self' not in result['links']:
            rid = self.ctx.registry.ensure_identifier(resource)
            route = get_router_resource(self.ctx.request.app, 'resource')
            route_url = route._formatter.format_map({'type': rid.type, 'id': rid.id})
            route_url = urllib.parse.urlunsplit(
                (self.ctx.request.scheme, self.ctx.request.host, route_url, None, None)
            )
            result['links']['self'] = route_url

        return result

    # Validation (pre deserialize)
    # ----------------------------

    def serialize_relationship(
        self,
        relation_name: str,
        resource: Any,
        *,
        pagination: Optional[PaginationABC] = None,
    ) -> Any:
        field = self.get_relationship_field(relation_name)

        kwargs = dict()
        if field.relation is Relation.TO_MANY and pagination:
            kwargs['pagination'] = pagination
        field_data = self.get_value(field, resource, **kwargs)
        return field.serialize(field_data, context=self.ctx, **kwargs)

    async def pre_validate_field(self, field: BaseField, data: Any, sp: JSONPointer) -> None:
        writable = field.writable in (Event.ALWAYS, self.ctx.event)
        if data is not MISSING and not writable:
            detail = f"The field '{field.name}' is readonly."
            raise ValidationError(detail=detail, source_pointer=sp)

        if data is MISSING and field.required in (Event.ALWAYS, self.ctx.event):
            if isinstance(field, Attribute):
                detail = f"Attribute '{field.name}' is required."
            elif isinstance(field, Relationship):
                detail = f"Relationship '{field.name}' is required."
            else:
                detail = f"The field '{field.name}' is required."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if data is not MISSING:
            if asyncio.iscoroutinefunction(field.pre_validate):
                await field.pre_validate(data, sp)
            else:
                field.pre_validate(data, sp)

            # Run custom pre-validators for field
            validators = get_processors(self, Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.BEFORE_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS, self.ctx.event):
                    continue

                if asyncio.iscoroutinefunction(validator):
                    await validator(self, field, data, sp)
                else:
                    validator(self, field, data, sp)

    # Validation (post deserialize)
    # -----------------------------

    async def pre_validate_resource(self, data: Any, sp: JSONPointer, *, expected_id: Optional[int] = None) -> None:
        if not isinstance(data, MutableMapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        # JSON API id
        if (expected_id or self.ctx.event is Event.UPDATE) and 'id' not in data:
            detail = "The 'id' member is missing."
            raise InvalidValue(detail=detail, source_pointer=sp / 'id')

        if expected_id:
            if str(data['id']) == str(expected_id):
                if self._id is not None:
                    await self.pre_validate_field(self._id, data['id'], sp / 'id')
            else:
                detail = f"The id '{data['id']}' does not match the endpoint id '{expected_id}'."
                raise HTTPConflict(detail=detail, source_pointer=sp / 'id')

    async def post_validate_resource(self, data: Dict[str, Any]) -> None:
        # NOTE: The fields in *data* are ordered, such that children are listed before their parent.
        for key, (field_data, field_sp) in data.items():
            field = self.get_field(key)
            field.post_validate(self, field_data, field_sp)

            # Run custom post-validators for field
            validators = get_processors(self, Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.AFTER_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS, self.ctx.event):
                    continue

                if asyncio.iscoroutinefunction(validator):
                    await validator(field, field_data, field_sp, context=self.ctx)
                else:
                    validator(field, field_data, field_sp, context=self.ctx)

    async def deserialize_resource(
        self,
        data: Any,
        sp: JSONPointer,
        *,
        expected_id: Optional[int] = None,
        validate: bool = True,
        validation_steps: Optional[Collection[Step]] = None,
    ) -> Dict[str, Any]:
        if validation_steps is None:
            validation_steps = (Step.BEFORE_DESERIALIZATION, Step.AFTER_DESERIALIZATION)

        if validate and Step.BEFORE_DESERIALIZATION in validation_steps:
            await self.pre_validate_resource(data, sp, expected_id=expected_id)

        result: Dict[str, Any] = OrderedDict()
        fields_map = (
            ('attributes', self._attributes),
            ('relationships', self._relationships),
            ('meta', self._meta),
        )

        for key, fields in fields_map:
            data_for_fields = data.get(key, {})

            if validate and not isinstance(data_for_fields, MutableMapping):
                detail = 'Must be an object.'
                raise InvalidType(detail=detail, source_pointer=sp / key)

            for field in fields.values():
                field_data = data_for_fields.get(field.name, MISSING)

                if field.key:
                    field_sp = sp / key / field.name

                    if validate and Step.BEFORE_DESERIALIZATION in validation_steps:
                        await self.pre_validate_field(field, field_data, field_sp)

                    if field_data is not MISSING:
                        result[field.key] = (
                            field.deserialize(self, field_data, field_sp),
                            field_sp
                        )

        if validate and Step.AFTER_DESERIALIZATION in validation_steps:
            await self.post_validate_resource(result)

        return result

    def map_data_to_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Map the property names on the resource instance to its initial data.
        result: Dict[str, Any] = {
            self.get_field(key).mapped_key: field_data
            for key, (field_data, sp) in data.items()
        }
        if 'id' in data:
            result['id'] = data['id']
        return result
