class FieldABC:
    def encode(self, schema, data, **kwargs):
        raise NotImplementedError

    def decode(self, schema, data, sp, **kwargs):
        raise NotImplementedError

    def pre_validate(self, schema, data, sp, context):
        raise NotImplementedError

    def post_validate(self, schema, data, sp, context):
        raise NotImplementedError


class SchemaABC(object):
    #: The JSON API *type*. (Leave it empty to derive it automatic from the
    #: resource class name or the schema name).
    type = None
    resource_class = None
    opts = None
    inflect = None

    def default_getter(self, field, resource, **kwargs):
        raise NotImplementedError

    def default_setter(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    async def default_include(self, field, resources, context, **kwargs):
        raise NotImplementedError

    async def default_query(self, field, resource, context, **kwargs):
        raise NotImplementedError

    async def default_add(self, field, resource, data, sp):
        raise NotImplementedError

    async def default_remove(self, field, resource, data, sp):
        raise NotImplementedError

    def get_relationship_field(self, relation_name, source_parameter=None):
        raise NotImplementedError

    def get_value(self, field, resource, **kwargs):
        raise NotImplementedError

    def set_value(self, field, resource, data, sp, **kwargs):
        raise NotImplementedError

    def serialize_resource(self, resource, **kwargs):
        raise NotImplementedError

    def serialize_relationship(self, relation_name, resource, *, pagination=None):
        raise NotImplementedError

    def validate_resource_before_deserialization(self, data, sp, context, *,
                                                 expected_id=None):
        raise NotImplementedError

    def validate_resource_after_deserialization(self, memo, context):
        raise NotImplementedError

    def deserialize_resource(self, data, sp, *, context=None,
                             expected_id=None, validate=True,
                             validation_steps=()):
        raise NotImplementedError

    async def create_resource(self, data, sp, context, **kwargs):
        raise NotImplementedError

    async def update_resource(self, resource, data, sp, context, **kwargs):
        raise NotImplementedError

    async def delete_resource(self, resource, context, **kwargs):
        raise NotImplementedError

    async def update_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        raise NotImplementedError

    async def add_relationship(self, relation_name, resource,
                               data, sp, context, **kwargs):
        raise NotImplementedError

    async def remove_relationship(self, relation_name, resource,
                                  data, sp, context, **kwargs):
        raise NotImplementedError

    async def query_collection(self, context, **kwargs):
        raise NotImplementedError

    async def query_resource(self, resource_id, context, **kwargs):
        raise NotImplementedError

    async def query_relative(self, relation_name, resource, context, **kwargs):
        raise NotImplementedError

    async def query_relatives(self, relation_name, resource, context, **kwargs):
        raise NotImplementedError

    async def fetch_compound_documents(self, relation_name, resources, context,
                                       *, rest_path=None, **kwargs):
        raise NotImplementedError
