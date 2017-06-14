#!/usr/bin/env python3

"""
Schema
======

This module contains the base schema which implements the encoding, decoding,
validation and update operations based on
:class:`fields <aiohttp_json_api.schema.base_fields.BaseField>`.
"""
import copy
import collections
import typing
from functools import partial

import inflection
from aiohttp import web

from .base_fields import (
    BaseField, LinksObjectMixin, Link, Attribute, Relationship
)
from .common import Event
from ..const import JSONAPI
from ..errors import (
    ValidationError, InvalidValue, InvalidType, HTTPConflict,
    HTTPBadRequest
)
from ..jsonpointer import JSONPointer

__all__ = (
    'SchemaMeta',
    'Schema'
)


class SchemaMeta(type):
    @classmethod
    def _assign_sp(cls, fields, sp: JSONPointer):
        """Sets the :attr:`BaseField.sp` (source pointer) property recursively
        for all child fields.
        """
        for field in fields:
            field.sp = sp / field.name
            if isinstance(field, LinksObjectMixin):
                cls._assign_sp(field.links.values(), field.sp / 'links')
        return None

    @classmethod
    def _sp_to_field(cls, fields):
        """
        Returns an ordered dictionary, which maps the source pointer of a
        field to the field. Nested fields are listed before the parent.
        """
        d = collections.OrderedDict()
        for field in fields:
            if isinstance(field, LinksObjectMixin):
                d.update(cls._sp_to_field(field.links.values()))
            d[field.sp] = field
        return d

    def __new__(cls, name, bases, attrs):
        """
        Detects all fields and wires everything up. These class attributes are
        defined here:

        *   *type*

            The JSON API typename

        *   *_fields_by_sp*

            Maps the source pointer of a field to the associated
            :class:`BaseField`.

        *   *_fields_by_key*

            Maps the key (schema property name) to the associated
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
        fields_by_key = dict()

        # Create a copy of the inherited fields.
        for base in reversed(bases):
            if issubclass(base, Schema):
                fields_by_key.update(base._fields_by_key)
        fields_by_key = copy.deepcopy(fields_by_key)

        for key, prop in attrs.items():
            if isinstance(prop, BaseField):
                prop.key = key
                prop.name = prop.name or key
                prop.mapped_key = prop.mapped_key or key
                fields_by_key[prop.key] = prop

        # Apply the decorators.
        # TODO: Use a more generic approach.
        for key, prop in attrs.items():
            if hasattr(prop, 'japi_getter'):
                field = fields_by_key[prop.japi_getter['field']]
                field.getter(prop)
            elif hasattr(prop, 'japi_setter'):
                field = fields_by_key[prop.japi_setter['field']]
                field.setter(prop)
            elif hasattr(prop, 'japi_validates'):
                field = fields_by_key[prop.japi_validates['field']]
                field.validator(
                    prop, step=prop.japi_validator['step'],
                    on=prop.japi_validator['on']
                )
            elif hasattr(prop, 'japi_adder'):
                field = fields_by_key[prop.japi_adder['field']]
                field.adder(prop)
            elif hasattr(prop, 'japi_remover'):
                field = fields_by_key[prop.japi_remover['field']]
                field.remover(prop)
            elif hasattr(prop, 'japi_includer'):
                field = fields_by_key[prop.japi_includer['field']]
                field.includer(prop)
            elif hasattr(prop, 'japi_query'):
                field = fields_by_key[prop.japi_query['field']]
                field.query_(prop)

        # Find nested fields (link_of, ...) and link them with
        # their parent.
        for key, field in fields_by_key.items():
            if getattr(field, 'link_of', None):
                parent = fields_by_key[field.link_of]
                parent.add_link(field)

        # Find the *top-level* attributes, relationships, links and meta fields.
        attributes = {
            key: field
            for key, field in fields_by_key.items()
            if isinstance(field, Attribute) and not field.meta
        }
        attributes.pop('id', None)
        cls._assign_sp(attributes.values(), JSONPointer('/attributes'))
        attrs['_attributes'] = attributes

        relationships = {
            key: field
            for key, field in fields_by_key.items()
            if isinstance(field, Relationship)
        }
        cls._assign_sp(
            relationships.values(), JSONPointer('/relationships')
        )
        attrs['_relationships'] = relationships

        links = {
            key: field
            for key, field in fields_by_key.items()
            if isinstance(field, Link) and not field.link_of
        }
        cls._assign_sp(links.values(), JSONPointer('/links'))
        attrs['_links'] = links

        meta = {
            key: field
            for key, field in fields_by_key.items()
            if isinstance(field, Attribute) and field.meta
        }
        cls._assign_sp(links.values(), JSONPointer('/meta'))
        attrs['_meta'] = meta

        # Collect all top level fields in a list.
        toplevel = list()
        toplevel.extend(attributes.values())
        toplevel.extend(relationships.values())
        toplevel.extend(links.values())
        toplevel.extend(meta.values())
        attrs['_toplevel'] = toplevel

        # Create the source pointer map.
        fields_by_sp = cls._sp_to_field(toplevel)
        attrs['_fields_by_sp'] = fields_by_sp
        attrs['_fields_by_key'] = fields_by_key

        # Determine 'type' name.
        if not attrs.get('type') and attrs.get('resource_class'):
            attrs['type'] = inflection.dasherize(
                inflection.tableize(attrs['resource_class'].__name__)
            )
        if not attrs.get('type'):
            attrs['type'] = name

        attrs['_id'] = fields_by_key.pop('id', None)

        return super().__new__(cls, name, bases, attrs)

    def __init__(cls, name, bases, attrs):
        """
        Initialise a new schema class.
        """
        super(SchemaMeta, cls).__init__(name, bases, attrs)

    def __call__(cls, *args):
        """
        Creates a new instance of a Schema class.
        """
        return super(SchemaMeta, cls).__call__(*args)


class Schema(metaclass=SchemaMeta):
    """
    A schema defines how we can encode a resource and patch it. It also allows
    to patch a resource. All in all, it defines a **controller** for a *type*
    in the JSON API.

    If you want, you can implement your own request handlers and only use
    the schema for validation and serialization.
    """

    # TODO: The options dictionary.
    opts = dict()
    opts['pagination'] = None

    #: The resource class associated with this schema.
    resource_class = None

    #: The JSON API *type*. (Leave it empty to derive it automatic from the
    #: resource class name or the schema name).
    type = ''
    inflect = partial(inflection.dasherize)

    def __init__(self, app: web.Application = None):
        self.app = app

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
        :arg ~aiohttp.web.Request request:
            The request context
        :rtype: str
        :returns:
            The id of the *resource*
        """
        if hasattr(resource, "id"):
            resource_id = resource.id() if callable(resource.id) else resource.id
        elif hasattr(resource, "get_id"):
            resource_id = resource.get_id()
        elif "id" in resource:
            resource_id = resource["id"]
        else:
            raise Exception("Could not determine the resource id.")
        return str(resource_id)

    # Encoding
    # --------

    async def _encode_field(self, field, resource, **kwargs):
        """
        Encodes the *field* and if has nested fields (e.g. inherits from
        :class:`LinksObjectMixin`), the nested fields are encoded first and
        passed to the encode method of the *field*.
        """
        links = None
        if isinstance(field, LinksObjectMixin):
            links = {
                self.inflect(link.name): link.encode(self, resource, **kwargs)
                for link in field.links.values()
            }

        data = await field.get(self, resource, **kwargs)
        return field.encode(self, data, links=links, **kwargs)

    async def encode_resource(self, resource, *,
                              is_data=False, is_included=False,
                              **kwargs) -> typing.MutableMapping:
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-objects

        :arg resource:
            A resource object
        :arg fieldset:
            *None* or a list with all fields that must be included. All other
            fields must not appear in the final document.
        :arg str context:
            Is either *data* or *included* and defines in which part of the
            JSON API document the resource object is placed.
        :arg list included:
            A list with all included relationships.
        """
        context = kwargs['context']
        fieldset = context.fields.get(self.type)

        result = {
            'type': self.type,
            'id': self._get_id(resource)
        }

        # JSON API attributes object
        attributes = {
            self.inflect(field.name):
                await self._encode_field(field, resource, **kwargs)
            for field in self._attributes.values()
            if fieldset is None or field.name in fieldset
        }
        if attributes:
            result['attributes'] = attributes

        # JSON API relationships object
        relationships = {
            self.inflect(field.name):
                await self._encode_field(field, resource, **kwargs)
            for field in self._relationships.values()
            if fieldset is None or field.name in fieldset
        }
        if relationships:
            result['relationships'] = relationships

        # JSON API meta object
        meta = {
            self.inflect(field.name):
                await self._encode_field(field, resource, **kwargs)
            for field in self._meta.values()
        }
        if meta:
            result['meta'] = meta

        # JSON API links object
        links = {
            self.inflect(field.name):
                await self._encode_field(field, resource, **kwargs)
            for field in self._links.values()
        }
        if 'self' not in links:
            self_url = self.app.router['jsonapi.resource'].url_for(
                **self.registry.ensure_identifier(resource, asdict=True)
            )
            if context.request is not None:
                self_url = context.request.url.join(self_url)  # Absolute URL
            links['self'] = str(self_url)
        result['links'] = links

        return result

    def encode_relationship(self, relname, resource, *, pagination=None):
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-object-relationships

        Creates the JSON API relationship object of the relationship *relname*.

        :arg str relname:
            The name of the relationship
        :arg resource:
            A resource object
        :arg ~aiohttp_json_api.pagination.BasePagination pagination:
            Describes the pagination in case of a *to-many* relationship.

        :rtype: dict
        :returns:
            The JSON API relationship object for the relationship *relname*
            of the *resource*
        """
        field = self._relationships[relname]

        kwargs = dict()
        if field.to_one and pagination:
            kwargs['pagination'] = pagination
        return self._encode_field(field, resource, **kwargs)

    # Validation (pre decode)
    # -----------------------

    def _validate_field_pre_decode(self, field, data, sp, context):
        """
        Validates the input data for a field, **before** it is decoded. If the
        field has nested fields, the nested fields are validated first.

        :arg BaseField field:
        :arg data:
            The input data for the field.
        :arg JSONPointer sp:
            The pointer to *data* in the original document. If *None*, there
            was no input data for this field.
        """
        writable = field.writable in (Event.ALWAYS, context.event)
        if not writable and sp is not None:
            detail = f"The field '{field.name}' is readonly."
            raise ValidationError(detail=detail, source_pointer=sp)

        required = field.required in (Event.ALWAYS, context.event)
        if required and data is None:
            detail = f"The field '{field.name}' is required."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if sp is not None:
            field.validate_pre_decode(self, data, sp, context)
        return None

    def validate_resource_pre_decode(self, data, sp, context, *,
                                     expected_id=""):
        """
        Validates a JSON API resource object received from an API client::

            schema.validate_resource_pre_decode(
                data=request.json["data"], sp="/data"
            )

        :arg data:
            The received JSON API resource object
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        if not isinstance(data, collections.Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        # JSON API id
        if (expected_id or context.event is Event.UPDATE) and 'id' not in data:
            detail = 'The "id" member is missing.'
            raise InvalidValue(detail=detail, source_pointer=sp / 'id')

        if expected_id:
            if data['id'] != expected_id:
                detail = f'The id "{data["id"]}" does not match the endpoint ' \
                         f'("{expected_id}").'
                raise HTTPConflict(detail=detail, source_pointer=sp / 'id')
            else:
                self._validate_field_pre_decode(
                    self._id, data['id'], sp / 'id', context
                )

        # JSON API attributes object
        attrs = data.get('attributes', {})
        attrs_sp = sp / 'attributes'

        if not isinstance(attrs, collections.Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=attrs_sp)

        for field in self._attributes.values():
            field_sp = attrs_sp / field.name if field.name in attrs else None
            field_data = attrs.get(field.name)
            self._validate_field_pre_decode(
                field, field_data, field_sp, context
            )

        # JSON API relationships object
        rels = data.get('relationships', {})
        rels_sp = sp / 'relationships'

        if not isinstance(rels, dict):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=rels_sp)

        for field in self._relationships.values():
            field_sp = rels_sp / field.name if field.name in rels else None
            field_data = rels.get(field.name)
            self._validate_field_pre_decode(
                field, field_data, field_sp, context
            )

        # JSON API meta object
        meta = data.get('meta', {})
        meta_sp = sp / 'meta'

        if not isinstance(meta, dict):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=meta_sp)

        for field in self._meta.values():
            field_sp = meta_sp / field.name if field.name in meta else None
            field_data = meta.get(field.name)
            self._validate_field_pre_decode(
                field, field_data, field_sp, context
            )

    # Decoding
    # --------

    def _decode_field(self, field, data, sp, *, memo=None, kwargs=None):
        """
        Decodes the input data for the *field*. If the *field* has nested
        fields, the nested fields are decoded first and passed to the
        decode method of the field.

        :arg ~aiohttp_json_api.schema.base_fields.BaseField field:
            The field whichs input data is decoded.
        :arg data:
            The input data for the field
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer:
            The JSON pointer to the source of *data*
        :arg dict memo:
            The decoded data will be stored additionaly in this dictionary
            with the key *field.key*.
        :arg dict kwargs:
            A dictionary with additional keyword arguments passed to
            :meth:`BaseField.decode`.
        """
        kwargs = kwargs or {}

        d = field.decode(self, data, sp, **kwargs)
        if memo is not None and field.key:
            memo[field.key] = (d, sp)
        return d

    def decode_resource(self, data, sp):
        """
        Decodes the JSON API resource object *data* and returns a dictionary
        which maps the key of a field to its decoded input data.

        :rtype: ~collections.OrderedDict
        :returns:
            An ordered dictionary which maps a fields key to a two tuple
            ``(data, sp)`` which contains the input data and the source pointer
            to it.
        """
        memo = collections.OrderedDict()

        # JSON API attributes object
        attrs = data.get('attributes', {})
        attrs_sp = sp / 'attributes'
        for field in self._attributes.values():
            field_sp = attrs_sp / field.name if field.name in attrs else None
            field_data = attrs.get(field.name)
            if field_data is None and field.required is Event.NEVER:
                continue
            self._decode_field(field, field_data, field_sp, memo=memo)

        # JSON API relationships object
        rels = data.get('relationships', {})
        rels_sp = sp / 'relationships'
        for field in self._relationships.values():
            field_sp = rels_sp / field.name if field.name in rels else None
            field_data = rels.get(field.name)
            self._decode_field(field, field_data, field_sp, memo=memo)

        # JSON API meta object
        meta = data.get('meta', {})
        meta_sp = sp / 'meta'
        for field in self._meta.values():
            field_sp = meta_sp / field.name if field.name in meta else None
            field_data = meta.get(field.name)
            self._decode_field(field, field_data, field_sp, memo=memo)
        return memo

    # Validate (post decode)
    # ----------------------

    def validate_resource_post_decode(self, memo, context):
        """
        Validates the decoded *data* of JSON API resource object.

        :arg ~collections.OrderedDict memo:
            The *memo* object returned from :meth:`decode_resource`.
        """
        # NOTE: The fields in *memo* are ordered, such that children are
        #       listed before their parent.
        for key, (data, sp) in memo.items():
            field = self._fields_by_key[key]
            field.validate_post_decode(self, data, sp, context)

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
        self.validate_resource_pre_decode(data, sp, context)
        memo = self.decode_resource(data, sp)
        self.validate_resource_post_decode(memo, context)

        # Map the property names on the resource instance to its initial data.
        initial_data = {
            self._fields_by_key[key].mapped_key: data
            for key, (data, sp) in memo.items()
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
        """
        if isinstance(resource, self.resource_class):
            resource_id = self._get_id(resource)
        else:
            resource_id = resource

        self.validate_resource_pre_decode(
            data, sp, context, expected_id=resource_id
        )
        memo = self.decode_resource(data, sp)
        self.validate_resource_post_decode(memo, context)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        for key, (data, sp) in memo.items():
            field = self._fields_by_key[key]
            await field.set(self, resource, data, sp, **kwargs)
        return None

    async def delete_resource(self, resource, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#crud-deleting

        Deletes the *resource*. **You must overridde this method.**

        :arg resource:
            The id of the resource or the resource instance
        """
        raise NotImplementedError()

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
        field = self._relationships[relation_name]

        self._validate_field_pre_decode(field, data, sp, context)
        decoded = self._decode_field(field, data, sp)
        # self._validate_field_post_decode(field, data, sp, context)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        await field.set(self, resource, decoded, sp, **kwargs)
        return resource

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
        field = self._relationships[relation_name]
        assert field.to_many

        self._validate_field_pre_decode(field, data, sp, context)
        decoded = self._decode_field(field, data, sp)
        # self._validate_field_post_decode(field, data, sp, context)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        await field.add(self, resource, decoded, sp, **kwargs)
        return resource

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
        field = self._relationships[relation_name]
        assert field.to_many

        self._validate_field_pre_decode(field, data, sp, context)
        decoded = self._decode_field(field, data, sp)
        # self._validate_field_post_decode(field, data, sp, context)

        if not isinstance(resource, self.resource_class):
            resource = await self.query_resource(resource, context, **kwargs)

        await field.remove(self, resource, decoded, sp, **kwargs)

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
        raise NotImplementedError()

    async def query_resource(self, id_, context, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching

        Fetches the resource with the id *id_*. **Must be overridden.**

        :arg str id_:
            The id of the requested resource.
        :arg list include:
            The list of relationships which will be included into the
            response. See also: :attr:`jsonapi.request.Request.japi_include`.
        :raises ~aiohttp_json_api.errors.ResourceNotFound:
            If there is no resource with the given *id_*.
        """
        raise NotImplementedError()

    async def query_relative(self, relation_name, resource, context, **kwargs):
        """
        Controller for the *related* endpoint of the to-one relationship with
        then name *relname*.

        Returns the related resource or ``None``.

        :arg str relation_name:
            The name of a to-one relationship.
        :arg str resource:
            The id of the resource or the resource instance.
        :arg list include:
            The list of relationships which will be included into the
            response. See also: :attr:`jsonapi.request.Request.japi_include`
        """
        field = self._relationships[relation_name]
        assert field.to_one

        relative = await field.query(self, resource, context, **kwargs)
        return relative

    async def query_relatives(self, relation_name, resource, context, **kwargs):
        """
        Controller for the *related* endpoint of the to-many relationship with
        then name *relname*.

        Because a to-many relationship represents a collection, this method
        accepts the same parameters as :meth:`query_collection`.

        Returns the related resource or ``None``.

        :arg str relation_name:
            The name of a to-one relationship.
        :arg str resource_id:
            The id of the resource or the resource instance.
        """
        field = self._relationships[relation_name]
        assert field.to_many

        relatives = await field.query(self, resource, context, **kwargs)
        return relatives

    async def fetch_include(self, relation_name, resources, context, *,
                            rest_path=None, **kwargs):
        """
        .. seealso::

            http://jsonapi.org/format/#fetching-includes

        Fetches the related resources. The default method uses the
        :meth:`~aiohttp_json_api.schema.base_fields.Relationship.include`
        method of the *Relationship* fields. **Can be overridden.**

        :arg resources:
            A list of resources.
        :arg str relation_name:
            The name of the relationship.
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
        field = self._relationships.get(relation_name)
        if field is None:
            raise HTTPBadRequest(
                detail=f"Wrong relation name '{relation_name}'.",
                source_parameter='include'
            )
        return await field.include(self, resources, context,
                                   rest_path=rest_path, **kwargs)
