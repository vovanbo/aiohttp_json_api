#!/usr/bin/env python3

"""
BaseSchema
==========

This module contains the base schema which implements the encoding, decoding,
validation and update operations based on
:class:`fields <aiohttp_json_api.schema.base_fields.BaseField>`.
"""
import asyncio
import copy
import typing
from collections import OrderedDict, MutableMapping
from functools import partial

import inflection
from aiohttp import web

from .abc.schema import SchemaABC
from .base_fields import BaseField, Attribute, Relationship
from .common import Event, Step, Relation
from .decorators import Tag
from ..const import JSONAPI
from ..errors import (
    ValidationError, InvalidValue, InvalidType, HTTPConflict,
    HTTPBadRequest
)
from ..helpers import MISSING, first, get_router_resource, ensure_collection
from ..jsonpointer import JSONPointer
from ..log import logger

__all__ = (
    'BaseSchema',
)

Callee = typing.Union[typing.Callable, typing.Coroutine]


class BaseSchema(SchemaABC):
    """
    A schema defines how we can serialize a resource and patch it.
    It also allows to patch a resource. All in all, it defines
    a **controller** for a *type* in the JSON API.

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

    @staticmethod
    def get_object_id(resource) -> str:
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
            return self._relationships[inflection.underscore(relation_name)]
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
                    compound_documents.extend(
                        ensure_collection(compound_document)
                    )
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
                        default: typing.Optional[Callee] = None):
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
        if field.writable is Event.NEVER:
            raise RuntimeError('Attempt to set value to read-only field.')

        setter, setter_kwargs = first(
            self._get_processors(Tag.SET, field, self.default_setter)
        )
        return await setter(field, resource, data, sp, **setter_kwargs,
                            **kwargs)

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

        result = OrderedDict((
            ('type', self.type),
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
                            link.name: link.serialize(self, resource, **kwargs)
                            for link in field.links.values()
                        }
                    # TODO: Validation steps for pre/post serialization
                    result.setdefault(key, OrderedDict())
                    result[key][field.name] = \
                        field.serialize(self, field_data, links=links,
                                        **kwargs)

        result.setdefault('links', OrderedDict())
        if 'self' not in result['links']:
            self_url = get_router_resource(self.app, 'resource').url_for(
                **self.registry.ensure_identifier(resource, asdict=True)
            )
            if context.request is not None:
                self_url = context.request.url.join(self_url)  # Absolute URL
            result['links']['self'] = str(self_url)

        return result

    def serialize_relationship(self, relation_name, resource,
                               *, pagination=None):
        field = self.get_relationship_field(relation_name)

        kwargs = dict()
        if field.relation is Relation.TO_ONE and pagination:
            kwargs['pagination'] = pagination
        field_data = self.get_value(field, resource, **kwargs)
        return field.serialize(self, field_data, **kwargs)

    # Validation (pre deserialize)
    # -----------------------

    async def _pre_validate_field(self, field, data, sp, context):
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
        if data is not MISSING and not writable:
            detail = "The field '{}' is readonly.".format(field.name)
            raise ValidationError(detail=detail, source_pointer=sp)

        if data is MISSING and field.required in (Event.ALWAYS, context.event):
            if isinstance(field, Attribute):
                detail = "Attribute '{}' is required.".format(field.name)
            elif isinstance(field, Relationship):
                detail = "Relationship '{}' is required.".format(field.name)
            else:
                detail = "The field '{}' is required.".format(field.name)
            raise InvalidValue(detail=detail, source_pointer=sp)

        if data is not MISSING:
            if asyncio.iscoroutinefunction(field.pre_validate):
                await field.pre_validate(self, data, sp, context)
            else:
                field.pre_validate(self, data, sp, context)

            # Run custom pre-validators for field
            validators = self._get_processors(Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.BEFORE_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS, context.event):
                    continue

                if asyncio.iscoroutinefunction(validator):
                    await validator(self, field, data, sp, context=context)
                else:
                    validator(self, field, data, sp, context=context)

    async def pre_validate_resource(self, data, sp, context,
                                    *, expected_id=None):
        if not isinstance(data, MutableMapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        # JSON API id
        if (expected_id or context.event is Event.UPDATE) and 'id' not in data:
            detail = "The 'id' member is missing."
            raise InvalidValue(detail=detail, source_pointer=sp / 'id')

        if expected_id:
            if str(data['id']) == str(expected_id):
                if self._id is not None:
                    await self._pre_validate_field(self._id, data['id'],
                                                   sp / 'id', context)
            else:
                detail = "The id '{}' does not match the endpoint id " \
                         "'{}'.".format(data['id'], expected_id)
                raise HTTPConflict(detail=detail, source_pointer=sp / 'id')

    async def post_validate_resource(self, data, context):
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

                if asyncio.iscoroutinefunction(validator):
                    await validator(field, field_data, field_sp,
                                    context=context)
                else:
                    validator(field, field_data, field_sp, context=context)

    async def deserialize_resource(self, data, sp, context, *,
                                   expected_id=None, validate=True,
                                   validation_steps=None):
        if validation_steps is None:
            validation_steps = (Step.BEFORE_DESERIALIZATION,
                                Step.AFTER_DESERIALIZATION)

        if validate and Step.BEFORE_DESERIALIZATION in validation_steps:
            await self.pre_validate_resource(
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

            if validate and not isinstance(data_for_fields, MutableMapping):
                detail = 'Must be an object.'
                raise InvalidType(detail=detail, source_pointer=sp / key)

            for field in fields.values():
                field_data = data_for_fields.get(field.name, MISSING)

                if field.key:
                    field_sp = sp / key / field.name

                    if validate and \
                            Step.BEFORE_DESERIALIZATION in validation_steps:
                        await self._pre_validate_field(
                            field, field_data, field_sp, context
                        )

                    if field_data is not MISSING:
                        result[field.key] = (
                            field.deserialize(self, field_data, field_sp),
                            field_sp
                        )

        if validate and Step.AFTER_DESERIALIZATION in validation_steps:
            await self.post_validate_resource(result, context)

        return result

    def map_data_to_schema(self, data) -> typing.Dict:
        # Map the property names on the resource instance to its initial data.
        result = {
            self._declared_fields[key].mapped_key: field_data
            for key, (field_data, sp) in data.items()
        }
        if 'id' in data:
            result['id'] = data['id']
        return result

    async def create_resource(self, data, sp, context, **kwargs):
        return self.map_data_to_schema(
            await self.deserialize_resource(data, sp, context)
        )

    async def update_resource(self, resource_id, data, sp, context, **kwargs):
        deserialized_data = \
            await self.deserialize_resource(data, sp, context,
                                            expected_id=resource_id)

        resource = await self.fetch_resource(resource_id, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        for key, (data, sp) in deserialized_data.items():
            field = self._declared_fields[key]
            await self.set_value(field, updated_resource, data, sp,
                                 context=context, **kwargs)

        return resource, updated_resource

    async def update_relationship(self, relation_name, resource_id,
                                  data, sp, context, **kwargs):
        field = self.get_relationship_field(relation_name)

        await self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        await self.set_value(field, updated_resource, decoded, sp,
                             context=context, **kwargs)
        return resource, updated_resource

    async def add_relationship(self, relation_name, resource_id,
                               data, sp, context, **kwargs):
        field = self.get_relationship_field(relation_name)
        if field.relation is not Relation.TO_MANY:
            raise RuntimeError('Wrong relationship field.'
                               'Relation to-many is required.')

        await self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        adder, adder_kwargs = first(
            self._get_processors(Tag.ADD, field, self.default_add)
        )
        await adder(field, updated_resource, decoded, sp,
                    context=context, **adder_kwargs, **kwargs)
        return resource, updated_resource

    async def remove_relationship(self, relation_name, resource_id,
                                  data, sp, context, **kwargs):
        field = self.get_relationship_field(relation_name)
        if field.relation is not Relation.TO_MANY:
            raise RuntimeError('Wrong relationship field.'
                               'Relation to-many is required.')

        await self._pre_validate_field(field, data, sp, context)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, context, **kwargs)

        updated_resource = copy.deepcopy(resource)
        remover, remover_kwargs = first(
            self._get_processors(Tag.REMOVE, field, self.default_remove)
        )
        await remover(field, updated_resource, decoded, sp,
                      context=context, **remover_kwargs, **kwargs)
        return resource, updated_resource

    async def query_relatives(self, relation_name, resource_id, context,
                              **kwargs):
        field = self.get_relationship_field(relation_name)

        resource = await self.fetch_resource(resource_id, context, **kwargs)
        query, query_kwargs = first(
            self._get_processors(Tag.QUERY, field, self.default_query)
        )
        return await query(field, resource, context,
                           **query_kwargs, **kwargs)

    async def fetch_compound_documents(self, relation_name, resources, context,
                                       **kwargs):
        field = self.get_relationship_field(relation_name,
                                            source_parameter='include')
        include, include_kwargs = first(
            self._get_processors(Tag.INCLUDE, field, self.default_include)
        )
        return await include(field, resources, context,
                             **include_kwargs, **kwargs)
