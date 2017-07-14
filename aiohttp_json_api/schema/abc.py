"""
Abstract base classes
=====================
"""
from abc import abstractmethod


class FieldABC:
    @abstractmethod
    def serialize(self, schema, data, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, schema, data, sp, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def pre_validate(self, schema, data, sp, context):
        raise NotImplementedError

    @abstractmethod
    def post_validate(self, schema, data, sp, context):
        raise NotImplementedError


class SchemaABC(object):
    #: The JSON API *type*. (Leave it empty to derive it automatic from the
    #: resource class name or the schema name).
    type = None
    resource_class = None
    opts = None
    inflect = None

    @abstractmethod
    def default_getter(self, field, resource, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def default_setter(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def default_include(self, field, resources, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def default_query(self, field, resource, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def default_add(self, field, resource, data, sp):
        raise NotImplementedError

    @abstractmethod
    async def default_remove(self, field, resource, data, sp):
        raise NotImplementedError

    @abstractmethod
    def get_relationship_field(self, relation_name, source_parameter=None):
        raise NotImplementedError

    @abstractmethod
    def get_value(self, field, resource, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def set_value(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def serialize_resource(self, resource, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def serialize_relationship(self, relation_name, resource, *, pagination=None):
        raise NotImplementedError

    @abstractmethod
    def validate_resource_before_deserialization(self, data, sp, context, *,
                                                 expected_id=None):
        raise NotImplementedError

    @abstractmethod
    def validate_resource_after_deserialization(self, memo, context):
        raise NotImplementedError

    @abstractmethod
    def deserialize_resource(self, data, sp, *, context=None,
                             expected_id=None, validate=True,
                             validation_steps=()):
        raise NotImplementedError

    @abstractmethod
    async def create_resource(self, data, sp, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def update_resource(self, resource, data, sp, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def delete_resource(self, resource, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def update_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def add_relationship(self, relation_name, resource,
                               data, sp, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def remove_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def query_collection(self, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def query_resource(self, resource_id, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def query_relative(self, relation_name, resource, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def query_relatives(self, relation_name, resource, context, **kwargs):
        raise NotImplementedError

    @abstractmethod
    async def fetch_compound_documents(self, relation_name, resources, context,
                                       *, rest_path=None, **kwargs):
        raise NotImplementedError
