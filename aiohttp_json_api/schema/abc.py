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
        :arg ~aiohttp_json_api.pagination.BasePagination pagination:
            Describes the pagination in case of a *to-many* relationship.

        :rtype: dict
        :returns:
            The JSON API relationship object for the relationship
            *relation_name* of the *resource*
        """
        raise NotImplementedError

    @abstractmethod
    async def validate_resource_before_deserialization(self, data, sp, context,
                                                       *, expected_id=None):
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
        raise NotImplementedError

    @abstractmethod
    async def validate_resource_after_deserialization(self, data, context):
        """
        Validates the decoded *data* of JSON API resource object.

        :arg ~collections.OrderedDict data:
            The *memo* object returned from :meth:`deserialize_resource`.
        :arg RequestContext context:
            Request context instance
        """
        raise NotImplementedError

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
    async def query_relative(self, relation_name, resource_id, context,
                             **kwargs):
        """
        Controller for the *related* endpoint of the to-one relationship with
        then name *relation_name*.

        Because a to-one relationship represents a resource, this method
        accepts the same parameters as :meth:`query_resource`.

        :arg str relation_name:
            The name of a relationship.
        :arg str resource_id:
            The id of the resource_id or the resource_id instance.
        :arg RequestContext context:
            A request context instance
        """
        raise NotImplementedError

    @abstractmethod
    async def query_relatives(self, relation_name, resource_id, context,
                              **kwargs):
        """
        Controller for the *related* endpoint of the to-many relationship with
        then name *relation_name*.

        Because a to-many relationship represents a collection, this method
        accepts the same parameters as :meth:`query_collection`.

        :arg str relation_name:
            The name of a relationship.
        :arg str resource_id:
            The id of the resource_id or the resource_id instance.
        :arg RequestContext context:
            A request context instance
        """
        raise NotImplementedError

    @abstractmethod
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
