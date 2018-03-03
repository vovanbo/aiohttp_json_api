#!/usr/bin/env python3

"""
Base schema
===========

This module contains the base schema which implements the encoding, decoding,
validation and update operations based on
:class:`fields <aiohttp_json_api.schema.base_fields.BaseField>`.
"""
import asyncio
import urllib.parse
from collections import MutableMapping, OrderedDict
from typing import Dict

from .abc.field import FieldABC
from .abc.schema import SchemaABC
from .fields.base import Attribute, Relationship
from .fields.decorators import Tag
from .common import Event, Relation, Step, JSONAPI
from .errors import (
    HTTPBadRequest, HTTPConflict, InvalidType, InvalidValue, ValidationError
)
from .helpers import MISSING, first, get_router_resource, get_processors

__all__ = (
    'BaseSchema',
)


class BaseSchema(SchemaABC):
    """
    A schema defines how we can serialize a resource and patch it.
    It also allows to patch a resource. All in all, it defines
    a **controller** for a *type* in the JSON API.

    If you want, you can implement your own request handlers and only use
    the schema for validation and serialization.
    """

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

    @classmethod
    def get_field(cls, key) -> FieldABC:
        return cls._declared_fields[key]

    @classmethod
    def get_relationship_field(cls, relation_name, source_parameter=None):
        try:
            return cls._relationships[cls.opts.deflect(relation_name)]
        except KeyError:
            raise HTTPBadRequest(
                detail=f"Wrong relationship name '{relation_name}'.",
                source_parameter=source_parameter
            )

    @staticmethod
    def default_getter(field, resource, **kwargs):
        if field.mapped_key:
            return getattr(resource, field.mapped_key)
        return None

    @staticmethod
    async def default_setter(field, resource, data, sp, **kwargs):
        if field.mapped_key:
            setattr(resource, field.mapped_key, data)

    def get_value(self, field, resource, **kwargs):
        getter, getter_kwargs = first(
            get_processors(self, Tag.GET, field, self.default_getter)
        )
        return getter(field, resource, **getter_kwargs, **kwargs)

    async def set_value(self, field, resource, data, sp, **kwargs):
        if field.writable is Event.NEVER:
            raise RuntimeError('Attempt to set value to read-only field.')

        setter, setter_kwargs = first(
            get_processors(self, Tag.SET, field, self.default_setter)
        )
        return await setter(field, resource, data, sp, **setter_kwargs,
                            **kwargs)

    def serialize_resource(self, resource, **kwargs) -> MutableMapping:
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-objects

        :arg resource:
            A resource object
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
            rid = self.ctx.registry.ensure_identifier(resource)
            route = get_router_resource(self.ctx.request.app, 'resource')
            route_url = route._formatter.format_map({'type': rid.type,
                                                     'id': rid.id})
            route_url = urllib.parse.urlunsplit(
                (self.ctx.request.scheme, self.ctx.request.host, route_url,
                 None, None)
            )
            result['links']['self'] = route_url

        return result

    # Validation (pre deserialize)
    # ----------------------------

    def serialize_relationship(self, relation_name, resource,
                               *, pagination=None):
        field = self.get_relationship_field(relation_name)

        kwargs = dict()
        if field.relation is Relation.TO_MANY and pagination:
            kwargs['pagination'] = pagination
        field_data = self.get_value(field, resource, **kwargs)
        return field.serialize(self, field_data, **kwargs)

    async def pre_validate_field(self, field, data, sp):
        writable = field.writable in (Event.ALWAYS, self.ctx.event)
        if data is not MISSING and not writable:
            detail = f"The field '{field.name}' is readonly."
            raise ValidationError(detail=detail, source_pointer=sp)

        if data is MISSING and field.required in (Event.ALWAYS,
                                                  self.ctx.event):
            if isinstance(field, Attribute):
                detail = f"Attribute '{field.name}' is required."
            elif isinstance(field, Relationship):
                detail = f"Relationship '{field.name}' is required."
            else:
                detail = f"The field '{field.name}' is required."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if data is not MISSING:
            if asyncio.iscoroutinefunction(field.pre_validate):
                await field.pre_validate(self, data, sp)
            else:
                field.pre_validate(self, data, sp)

            # Run custom pre-validators for field
            validators = get_processors(self, Tag.VALIDATE, field, None)
            for validator, validator_kwargs in validators:
                if validator_kwargs['step'] is not Step.BEFORE_DESERIALIZATION:
                    continue
                if validator_kwargs['on'] not in (Event.ALWAYS,
                                                  self.ctx.event):
                    continue

                if asyncio.iscoroutinefunction(validator):
                    await validator(self, field, data, sp)
                else:
                    validator(self, field, data, sp)

    # Validation (post deserialize)
    # -----------------------------

    async def pre_validate_resource(self, data, sp, *, expected_id=None):
        if not isinstance(data, MutableMapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        # JSON API id
        if ((expected_id or self.ctx.event is Event.UPDATE) and
            'id' not in data):
            detail = "The 'id' member is missing."
            raise InvalidValue(detail=detail, source_pointer=sp / 'id')

        if expected_id:
            if str(data['id']) == str(expected_id):
                if self._id is not None:
                    await self.pre_validate_field(self._id, data['id'],
                                                  sp / 'id')
            else:
                detail = (
                    f"The id '{data['id']}' does not match "
                    f"the endpoint id '{expected_id}'."
                )
                raise HTTPConflict(detail=detail, source_pointer=sp / 'id')

    async def post_validate_resource(self, data):
        # NOTE: The fields in *data* are ordered, such that children are
        #       listed before their parent.
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
                    await validator(field, field_data, field_sp,
                                    context=self.ctx)
                else:
                    validator(field, field_data, field_sp, context=self.ctx)

    async def deserialize_resource(self, data, sp, *, expected_id=None,
                                   validate=True, validation_steps=None):
        if validation_steps is None:
            validation_steps = (Step.BEFORE_DESERIALIZATION,
                                Step.AFTER_DESERIALIZATION)

        if validate and Step.BEFORE_DESERIALIZATION in validation_steps:
            await self.pre_validate_resource(data, sp, expected_id=expected_id)

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

                    if (validate and
                        Step.BEFORE_DESERIALIZATION in validation_steps):
                        await self.pre_validate_field(field, field_data,
                                                      field_sp)

                    if field_data is not MISSING:
                        result[field.key] = (
                            field.deserialize(self, field_data, field_sp),
                            field_sp
                        )

        if validate and Step.AFTER_DESERIALIZATION in validation_steps:
            await self.post_validate_resource(result)

        return result

    def map_data_to_schema(self, data) -> Dict:
        # Map the property names on the resource instance to its initial data.
        result = {
            self.get_field(key).mapped_key: field_data
            for key, (field_data, sp) in data.items()
        }
        if 'id' in data:
            result['id'] = data['id']
        return result
