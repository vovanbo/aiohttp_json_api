import abc
import inspect

from aiohttp import web

from .schema import SchemaABC
from ..common import JSONAPI


class ControllerABC(abc.ABC):
    def __init__(self, app: web.Application, schema_cls, resource_cls,
                 resource_type: str = None):
        self.app = app

        if not inspect.isclass(schema_cls):
            raise TypeError('Class (not instance) of schema is required.')

        if not issubclass(schema_cls, SchemaABC):
            raise TypeError('Subclass of SchemaABC is required. '
                            'Got: {}'.format(schema_cls))

        self.schema = schema_cls(resource_cls, resource_type)

    @property
    def registry(self):
        return self.app[JSONAPI]['registry']

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

        Creates a new resource instance and returns it.
        **You should override this method.**

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

        Deletes the members specified in the JSON API relationship object
        *data* from the relationship.

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
