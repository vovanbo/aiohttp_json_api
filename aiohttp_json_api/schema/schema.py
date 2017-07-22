#!/usr/bin/env python3

"""
Schema
======

This module contains the base schema which implements the encoding, decoding,
validation and update operations based on
:class:`fields <aiohttp_json_api.schema.base_fields.BaseField>`.
"""
import copy
import inspect
import typing
from collections import OrderedDict, Mapping, defaultdict
from functools import partial
from types import MappingProxyType

import inflection
import itertools
from aiohttp import web

from . import abc
from .base_fields import BaseField, Link, Attribute, Relationship
from .decorators import Tag
from .common import Event, Step
from ..helpers import is_instance_or_subclass, first
from ..const import JSONAPI, ALLOWED_MEMBER_NAME_REGEX
from ..errors import (
    ValidationError, InvalidValue, InvalidType, HTTPConflict,
    HTTPBadRequest
)
from ..log import logger
from ..jsonpointer import JSONPointer

__all__ = (
    'SchemaMeta',
    'Schema'
)


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
        if is_instance_or_subclass(field_value, field_class)
    ]
    if pop:
        for field_name, _ in fields:
            del attrs[field_name]
    return fields


# This function allows Schemas to inherit from non-Schema classes and ensures
#   inheritance according to the MRO
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


class SchemaMeta(type):
    @classmethod
    def _assign_sp(mcs, fields, sp: JSONPointer):
        """Sets the :attr:`BaseField.sp` (source pointer) property recursively
        for all child fields.
        """
        for field in fields:
            field.sp = sp / field.name
            if isinstance(field, Relationship):
                mcs._assign_sp(field.links.values(), field.sp / 'links')

    @classmethod
    def _sp_to_field(mcs, fields):
        """
        Returns an ordered dictionary, which maps the source pointer of a
        field to the field. Nested fields are listed before the parent.
        """
        d = OrderedDict()
        for field in fields:
            if isinstance(field, Relationship):
                d.update(mcs._sp_to_field(field.links.values()))
            d[field.sp] = field
        return MappingProxyType(d)

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
        cls_fields = _get_fields(attrs, abc.FieldABC, pop=True)
        klass = super(SchemaMeta, mcs).__new__(mcs, name, bases, attrs)
        inherited_fields = _get_fields_by_mro(klass, abc.FieldABC)
        declared_fields = OrderedDict()

        for key, prop in inherited_fields + cls_fields:
            prop.key = key
            prop.name = \
                prop.name or (klass.inflect(key)
                              if callable(klass.inflect) else key)
            if not ALLOWED_MEMBER_NAME_REGEX.fullmatch(prop.name):
                raise ValueError(
                    'Field name "{}" is not allowed.'.format(prop.name)
                )
            prop.mapped_key = prop.mapped_key or key
            declared_fields[prop.key] = prop

        # Find nested fields (link_of, ...) and link them with
        # their parent.
        for key, field in declared_fields.items():
            if getattr(field, 'link_of', None):
                relationship = declared_fields[field.link_of]
                assert isinstance(relationship, Relationship), \
                    'Links can be added only for relationships.'
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
        for relationship in relationships.values():
            # Add the default links.
            relationship.links.update({
                'self': Link('jsonapi.relationships',
                             name='self', link_of=relationship.name),
                'related': Link('jsonapi.related',
                                name='related', link_of=relationship.name)

            })
        mcs._assign_sp(
            relationships.values(), JSONPointer('/relationships')
        )
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
        if not attrs.get('type'):
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
        Creates a new instance of a Schema class.
        """
        return super(SchemaMeta, cls).__call__(*args)

    def _resolve_processors(self):
        """
        Add in the decorated processors
        By doing this after constructing the class, we let standard inheritance
        do all the hard work.

        Almost the same as https://github.com/marshmallow-code/marshmallow/blob/dev/marshmallow/schema.py#L139-L174
        """
        mro = inspect.getmro(self)
        self._has_processors = False
        self.__processors__ = defaultdict(list)
        for attr_name in dir(self):
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

            self._has_processors = bool(processor_tags)
            for tag in processor_tags:
                # Use name here so we can get the bound method later, in case
                # the processor was a descriptor or something.
                self.__processors__[tag].append(attr_name)


class Schema(abc.SchemaABC, metaclass=SchemaMeta):
    """
    A schema defines how we can serialize a resource and patch it. It also allows
    to patch a resource. All in all, it defines a **controller** for a *type*
    in the JSON API.

    If you want, you can implement your own request handlers and only use
    the schema for validation and serialization.
    """
    inflect = partial(inflection.dasherize)

    def __init__(self, app: web.Application = None):
        self.app = app
        if self.opts is None:
            self.opts = {'pagination': None}

    @property
    def registry(self):
        return self.app[JSONAPI]['registry']

    # ID
    # --
    def _get_id(self, resource):
        """
        **Can be overridden**.

        Returns the id (string) of the resource. The default implementation
        looks for a property ``resource.id``, an id method ``resource.id()``,
        ``resource.get_id()`` or a key ``resource["id"]``.

        :arg resource:
            A resource object
        :rtype: str
        :returns:
            The id of the *resource*
        """
        if hasattr(resource, 'id'):
            resource_id = \
                resource.id() if callable(resource.id) else resource.id
        elif hasattr(resource, 'get_id'):
            resource_id = resource.get_id()
        elif 'id' in resource:
            resource_id = resource['id']
        else:
            raise Exception('Could not determine the resource id.')
        return str(resource_id)

    def get_relationship_field(self, relation_name, source_parameter=None):
        try:
            return self._relationships[relation_name]
        except KeyError:
            raise HTTPBadRequest(
                detail="Wrong relationship name '{}'.".format(relation_name),
                source_parameter=source_parameter
            )

    def default_getter(self, field, resource, **kwargs):
        if field.mapped_key:
            return getattr(resource, field.mapped_key)
        return None

    async def default_setter(self, field, resource, data, sp, **kwargs):
        if field.mapped_key:
            setattr(resource, field.mapped_key, data)

    async def default_include(self, field, resources, context, **kwargs):
        if field.mapped_key:
            compound_documents = []
            for resource in resources:
                compound_document = getattr(resource, field.mapped_key)
                if compound_document:
                    compound_documents.extend(compound_document)
            return compound_documents
        raise RuntimeError('No includer and mapped_key have been defined.')

    async def default_query(self, field, resource, context, **kwargs):
        if field.mapped_key:
            return getattr(resource, field.mapped_key)
        raise RuntimeError('No query method and mapped_key have been defined.')

    async def default_add(self, field, resource, data, sp):
        logger.warning('You should override the adder.')

        if not field.mapped_key:
            raise RuntimeError('No adder and mapped_key have been defined.')

        relatives = getattr(resource, field.mapped_key)
        relatives.extend(data)

    async def default_remove(self, field, resource, data, sp):
        logger.warning('You should override the remover.')

        if not field.mapped_key:
            raise RuntimeError('No remover and mapped_key have been defined.')

        relatives = getattr(resource, field.mapped_key)
        for relative in data:
            try:
                relatives.remove(relative)
            except ValueError:
                pass

    def _get_processors(self, tag: Tag, field: BaseField,
                        default: typing.Union[typing.Callable,
                                              typing.Coroutine] = None):
        if self._has_processors:
            processor_tag = tag, field.key
            processors = self.__processors__.get(processor_tag)
            if processors:
                for processor_name in processors:
                    processor = getattr(self, processor_name)
                    processor_kwargs = \
                        processor.__processing_kwargs__.get(processor_tag)
                    yield processor, processor_kwargs
                return

        if not callable(default):
            return

        yield default, {}

    def get_value(self, field, resource, **kwargs):
        getter, getter_kwargs = first(
            self._get_processors(Tag.GET, field, self.default_getter)
        )
        return getter(field, resource, **getter_kwargs, **kwargs)

    async def set_value(self, field, resource, data, sp, **kwargs):
        assert field.writable is not Event.NEVER
        setter, setter_kwargs = first(
            self._get_processors(Tag.SET, field, self.default_setter)
        )
        return await setter(
            field, resource, data, sp, **setter_kwargs, **kwargs
        )

    def serialize_resource(self, resource, **kwargs) -> typing.MutableMapping:
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-objects

        :arg resource:
            A resource object
        """
        context = kwargs['context']
        fieldset = context.fields.get(self.type)

        fields_map = (
            ('attributes', self._attributes),
            ('relationships', self._relationships),
            ('meta', self._meta),
            ('links', self._links)
        )

        result = OrderedDict()
        result['type'] = self.type
        result['id'] = self._get_id(resource)

        for key, fields in fields_map:
            result[key] = OrderedDict()
            for field in fields.values():
                if fieldset is None or field.name in fieldset:
                    field_data = self.get_value(field, resource, **kwargs)
                    links = None
                    if isinstance(field, Relationship):
                        links = {
                            link.name: link.serialize(self, resource, **kwargs)
                            for link in field.links.values()
                        }
                    # TODO: Validation steps for pre/post serialization
                    result[key][field.name] = \
                        field.serialize(self, field_data, links=links, **kwargs)

            # Filter out empty keys
            if not result.get(key):
                result.pop(key, None)

        if result.get('links') and 'self' not in result['links']:
            self_url = self.app.router['jsonapi.resource'].url_for(
                **self.registry.ensure_identifier(resource, asdict=True)
            )
            if context.request is not None:
                self_url = context.request.url.join(self_url)  # Absolute URL
            result['links']['self'] = str(self_url)

        return result

    def serialize_relationship(self, relation_name, resource,
                               *, pagination=None):
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-object-relationships

        Creates the JSON API relationship object of the relationship *relname*.

        :arg str relation_name:
            The name of the relationship
        :arg resource:
            A resource object
        :arg ~aiohttp_json_api.pagination.BasePagination pagination:
            Describes the pagination in case of a *to-many* relationship.

        :rtype: dict
        :returns:
            The JSON API relationship object for the relationship
            *relation_name* of the *resource*
        """
        field = self.get_relationship_field(relation_name)

        kwargs = dict()
        if field.to_one and pagination:
            kwargs['pagination'] = pagination
        field_data = self.get_value(field, resource, **kwargs)
        return field.serialize(self, field_data, **kwargs)

    # Validation (pre deserialize)
    # -----------------------

    def _pre_validate_field(self, field, data, sp, context):
        """
        Validates the input data for a field, **before** it is deserialized.
        If the field has nested fields, the nested fields are validated first.

        :arg BaseField field:
        :arg data:
            The input data for the field.
        :arg JSONPointer sp:
            The pointer to *data* in the original document. If *None*, there
            was no input data for this field.
        """
        writable = field.writable in (Event.ALWAYS, context.event)
        if not writable and sp is not None:
            detail = "The field '{}' is readonly.".format(field.name)
            raise ValidationError(detail=detail, source_pointer=sp)

        required = field.required in (Event.ALWAYS, context.event)
        if required and data is None:
            if isinstance(field, Attribute):
                detail = "Attribute '{}' is required.".format(field.name)
            elif isinstance(field, Relationship):
                detail = "Relationship '{}' is required.".format(field.name)
            else:
                detail = "The field '{}' is required.".format(field.name)
            raise InvalidValue(detail=detail, source_pointer=sp)

        if sp is not None:
            field.pre_validate(self, data, sp, context)

            # Run custom pre-validators for field
            validators = self._get_processors(Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.BEFORE_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS, context.event):
                    continue

                validator(self, field, data, sp, context=context)

    def validate_resource_before_deserialization(self, data, sp, context, *,
                                                 expected_id=None):
        """
        Validates a JSON API resource object received from an API client::

            schema.validate_resource_before_deserialization(
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
        if not isinstance(data, Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        # JSON API id
        if (expected_id or context.event is Event.UPDATE) and 'id' not in data:
            detail = 'The "id" member is missing.'
            raise InvalidValue(detail=detail, source_pointer=sp / 'id')

        if expected_id:
            if data['id'] != expected_id:
                detail = 'The id "{}" does not match the endpoint ' \
                         '("{}").'.format(data["id"], expected_id)
                raise HTTPConflict(detail=detail, source_pointer=sp / 'id')
            else:
                self._pre_validate_field(
                    self._id, data['id'], sp / 'id', context
                )

    def validate_resource_after_deserialization(self, data, context):
        """
        Validates the decoded *data* of JSON API resource object.

        :arg ~collections.OrderedDict data:
            The *memo* object returned from :meth:`deserialize_resource`.
        :arg RequestContext context:
            Request context instance
        """
        # NOTE: The fields in *data* are ordered, such that children are
        #       listed before their parent.
        for key, (field_data, field_sp) in data.items():
            field = self._declared_fields[key]
            field.post_validate(self, field_data, field_sp, context)

            # Run custom post-validators for field
            validators = self._get_processors(Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.AFTER_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS, context.event):
                    continue

                validator(self, field, field_data, field_sp, context=context)

    def deserialize_resource(self, data, sp, *, context=None,
                             expected_id=None, validate=True,
                             validation_steps=(Step.BEFORE_DESERIALIZATION,
                                               Step.AFTER_DESERIALIZATION)):
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
            If passed, then ID of resrouce will be compared with this value.
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
        if validate and Step.BEFORE_DESERIALIZATION in validation_steps:
            self.validate_resource_before_deserialization(
                data, sp, context, expected_id=expected_id
            )

        result = OrderedDict()
        fields_map = (
            ('attributes', self._attributes),
            ('relationships', self._relationships),
            ('meta', self._meta),
        )

        for key, fields in fields_map:
            data_for_fields = data.get(key, {})

            if validate and not isinstance(data_for_fields, Mapping):
                detail = 'Must be an object.'
                raise InvalidType(detail=detail, source_pointer=sp / key)

            for field in fields.values():
                field_data = data_for_fields.get(field.name)
                if field_data is None and field.required is Event.NEVER:
                    if not field.allow_none:
                        continue

                if field.key:
                    # field_sp = sp / key / field.name \
                    #     if field.name in data_for_fields \
                    #     else None
                    field_sp = sp / key / field.name

                    if validate and \
                            Step.BEFORE_DESERIALIZATION in validation_steps:
                        self._pre_validate_field(
                            field, field_data, field_sp, context
                        )

                    result[field.key] = \
                        field.deserialize(self, field_data, field_sp), field_sp

        if validate and Step.AFTER_DESERIALIZATION in validation_steps:
            self.validate_resource_after_deserialization(result, context)

        return result

    # CRUD (resource)
    # ---------------

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
        """
        deserialized_data = self.deserialize_resource(data, sp,
                                                      context=context)

        # Map the property names on the resource instance to its initial data.
        initial_data = {
            self._declared_fields[key].mapped_key: data
            for key, (data, sp) in deserialized_data.items()
        }
        if 'id' in data:
            initial_data['id'] = data['id']

        # Create a new object by calling the constructor.
        # resource = self.resource_class(**initial_data)
        return initial_data

    async def update_resource(self, resource, data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating

        Updates an existing *resource*. **You should overridde this method** in
        order to save the changes in the database.

        The default implementation uses the
        :class:`~aiohttp_json_api.schema.base_fields.BaseField`
        descriptors to update the resource.

        :arg resource:
            The id of the resource or the resource instance
        :arg dict data:
            The JSON API resource object with the update information
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg RequestContext context:
            Request context instance
        """
        if isinstance(resource, self.resource_class):
            resource_id = self._get_id(resource)
        else:
            resource_id = resource

        deserialized_data = self.deserialize_resource(data, sp,
                                                      context=context,
                                                      expected_id=resource_id)

        if not isinstance(resource, self.resource_class):
            resource = \
                await self.query_resource(resource, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        for key, (data, sp) in deserialized_data.items():
            field = self._declared_fields[key]
            await self.set_value(field, updated_resource, data, sp, **kwargs)

        return resource, updated_resource

    async def delete_resource(self, resource, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-deleting

        Deletes the *resource*. **You must overridde this method.**

        :arg resource:
            The id of the resource or the resource instance
        :arg RequestContext context:
            Request context instance
        """
        raise NotImplementedError

    # CRUD (relationships)
    # --------------------

    async def update_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-relationships

        Updates the relationship with the JSON API name *relation_name*.

        :arg str relation_name:
            The name of the relationship.
        :arg resource:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        field = self.get_relationship_field(relation_name)

        self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        await self.set_value(field, updated_resource, decoded, sp, **kwargs)
        return resource, updated_resource

    async def add_relationship(self, relation_name, resource,
                               data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        Adds the members specified in the JSON API relationship object *data*
        to the relationship, unless the relationships already exist.

        :arg str relation_name:
            The name of the relationship.
        :arg resource:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        field = self.get_relationship_field(relation_name)
        assert field.to_many

        self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        adder, adder_kwargs = first(
            self._get_processors(Tag.ADD, field, self.default_add)
        )
        await adder(field, updated_resource, decoded, sp,
                    context=context, **adder_kwargs, **kwargs)
        return resource, updated_resource

    async def remove_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        Deletes the members specified in the JSON API relationship object *data*
        from the relationship.

        :arg str relation_name:
            The name of the relationship.
        :arg resource:
            The id of the resource or the resource instance.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        field = self.get_relationship_field(relation_name)
        assert field.to_many

        self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        remover, remover_kwargs = first(
            self._get_processors(Tag.REMOVE, field, self.default_remove)
        )
        await remover(field, updated_resource, decoded, sp,
                      context=context, **remover_kwargs, **kwargs)
        return resource, updated_resource

    # Querying
    # --------

    async def query_collection(self, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching

        Fetches a subset of the collection represented by this schema.
        **Must be overridden.**

        :arg ~aiohttp_json_api.context.RequestContext context:
            Request context object.
        """
        raise NotImplementedError

    async def query_resource(self, resource_id, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching

        Fetches the resource with the id *id_*. **Must be overridden.**

        :arg str resource_id:
            The id of the requested resource.
        :arg list include:
            The list of relationships which will be included into the
            response. See also: :attr:`jsonapi.request.Request.japi_include`.
        :raises ~aiohttp_json_api.errors.ResourceNotFound:
            If there is no resource with the given *id_*.
        """
        raise NotImplementedError

    async def query_relatives(self, relation_name, resource, context, **kwargs):
        """
        Controller for the *related* endpoint of the to-many relationship with
        then name *relname*.

        Because a to-many relationship represents a collection, this method
        accepts the same parameters as :meth:`query_collection`.

        Returns the related resource or ``None``.

        :arg str relation_name:
            The name of a relationship.
        :arg str resource_id:
            The id of the resource or the resource instance.
        """
        field = self.get_relationship_field(relation_name)

        query, query_kwargs = first(
            self._get_processors(Tag.QUERY, field, self.default_query)
        )
        return await query(field, resource, context, **query_kwargs, **kwargs)

    async def fetch_compound_documents(self, relation_name, resources, context,
                                       **kwargs):
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
        field = self.get_relationship_field(relation_name,
                                            source_parameter='include')
        include, include_kwargs = first(
            self._get_processors(Tag.INCLUDE, field, self.default_include)
        )
        return await include(field, resources, context,
                             **include_kwargs, **kwargs)
