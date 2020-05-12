import abc
import copy
from typing import Any, List

from aiohttp_json_api.common import logger
from aiohttp_json_api.fields.decorators import Tag
from aiohttp_json_api.helpers import first, get_processors
from aiohttp_json_api.processors import ProcessorsMeta


class ControllerMeta(ProcessorsMeta):
    def __init__(cls, name, bases, attrs) -> None:
        """
        Initialise a new controller class.
        """
        super().__init__(name, bases, attrs)
        cls._resolve_processors()


class ControllerABC(abc.ABC, metaclass=ControllerMeta):
    def __init__(self, context) -> None:
        self.ctx = context

    @staticmethod
    @abc.abstractmethod
    async def default_include(field, resources, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    async def default_query(field, resource, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    async def default_add(field, resource, data, sp, **kwargs):
        pass

    @staticmethod
    @abc.abstractmethod
    async def default_remove(field, resource, data, sp, **kwargs):
        pass

    # CRUD (resource)
    # ---------------

    @abc.abstractmethod
    async def fetch_resource(self, resource_id, **kwargs):
        pass

    @abc.abstractmethod
    async def create_resource(self, data, **kwargs):
        """
        Creates a new resource instance and returns it.

        .. seealso::

            http://jsonapi.org/format/#crud-creating

        **You should override this method.**

        The default implementation passes the attributes, (dereferenced)
        relationships and meta data from the JSON API resource object
        *data* to the constructor of the resource class. If the primary
        key is *writable* on creation and a member of *data*, it is also
        passed to the constructor.

        :arg dict data:
            The JSON API deserialized data by schema.
        """
        pass

    @abc.abstractmethod
    async def update_resource(self, resource_id, data, sp, **kwargs):
        """
        Updates an existing *resource*. **You should overridde this method** in
        order to save the changes in the database.

        .. seealso::

            http://jsonapi.org/format/#crud-updating

        The default implementation uses the
        :class:`~aiohttp_json_api.schema.base_fields.BaseField`
        descriptors to update the resource.

        :arg resource_id:
            The id of the resource
        :arg dict data:
            The JSON API resource object with the update information
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.JSONAPIContext context:
            Request context instance
        """
        pass

    @abc.abstractmethod
    async def delete_resource(self, resource_id, **kwargs):
        """
        Deletes the *resource*.

        .. seealso::

            http://jsonapi.org/format/#crud-deleting

        **You must overridde this method.**

        :arg resource_id:
            The id of the resource or the resource instance
        :arg ~aiohttp_json_api.context.JSONAPIContext context:
            Request context instance
        """
        pass

    # CRUD (relationships)
    # --------------------

    @abc.abstractmethod
    async def update_relationship(self, field, resource, data, sp, **kwargs):
        """
        Updates the relationship with the JSON API name *relation_name*.

        .. seealso::

            http://jsonapi.org/format/#crud-updating-relationships

        :arg FieldABC field:
            Relationship field.
        :arg resource:
            Resource instance fetched by :meth:`~fetch_resource` in handler.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        pass

    @abc.abstractmethod
    async def add_relationship(self, field, resource, data, sp, **kwargs):
        """
        Adds the members specified in the JSON API relationship object *data*
        to the relationship, unless the relationships already exist.

        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        :arg FieldABC field:
            Relationship field.
        :arg resource:
            Resource instance fetched by :meth:`~fetch_resource` in handler.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        """
        pass

    @abc.abstractmethod
    async def remove_relationship(self, field, resource, data, sp, **kwargs):
        """
        Deletes the members specified in the JSON API relationship object
        *data* from the relationship.

        .. seealso::

            http://jsonapi.org/format/#crud-updating-to-many-relationships

        :arg FieldABC field:
            Relationship field.
        :arg resource:
            Resource instance fetched by :meth:`~fetch_resource` in handler.
        :arg str data:
            The JSON API relationship object with the update information.
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            The JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.JSONAPIContext context:
            Request context instance.
        """
        pass

    # Querying
    # --------

    @abc.abstractmethod
    async def query_collection(self, **kwargs):
        """
        Fetches a subset of the collection represented by this schema.
        **Must be overridden.**

        .. seealso::

            http://jsonapi.org/format/#fetching
        """
        pass

    @abc.abstractmethod
    async def query_resource(self, resource_id, **kwargs):
        """
        Fetches the resource with the id *id_*. **Must be overridden.**

        .. seealso::

            http://jsonapi.org/format/#fetching


        :arg str resource_id:
            The id of the requested resource.
        :raises ~aiohttp_json_api.errors.ResourceNotFound:
            If there is no resource with the given *id_*.
        """
        pass

    @abc.abstractmethod
    async def query_relatives(self, field, resource, **kwargs):
        """
        Controller for the *related* endpoint of the relationship with name *relation_name*.

        :arg FieldABC field:
            Relationship field.
        :arg resource:
            Resource instance fetched by :meth:`~fetch_resource` in handler.
        """
        pass

    @abc.abstractmethod
    async def fetch_compound_documents(self, field, resources, *, rest_path=None, **kwargs):
        """
        Fetches the related resources. The default method uses the controller's :meth:`~default_include`.

        .. seealso::

            http://jsonapi.org/format/#fetching-includes

        **Can be overridden.**

        :arg FieldABC field:
            Relationship field.
        :arg resources:
            A list of resources.
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
        pass


class BaseController(ControllerABC):
    @staticmethod
    async def default_include(field, resources, **kwargs):
        if not field.mapped_key:
            raise RuntimeError('No includer and mapped_key has been defined.')

        ctx = kwargs['context']
        compound_documents: List[Any] = []
        for resource in resources:
            compound_document = getattr(resource, field.mapped_key)
            if compound_document:
                compound_documents.extend(
                    (compound_document,)
                    if type(compound_document) in ctx.registry
                    else compound_document
                )
        return compound_documents

    @staticmethod
    async def default_query(field, resource, **kwargs):
        if not field.mapped_key:
            raise RuntimeError('No query method and mapped_key has been defined.')
        return getattr(resource, field.mapped_key)

    @staticmethod
    async def default_add(field, resource, data, sp, **kwargs):
        logger.warning('Default adder method should be overridden.')

        if not field.mapped_key:
            raise RuntimeError('No adder and mapped_key has been defined.')

        relatives = getattr(resource, field.mapped_key)
        relatives.extend(data)

    @staticmethod
    async def default_remove(field, resource, data, sp, **kwargs):
        logger.warning('Default remover method should be overridden.')

        if not field.mapped_key:
            raise RuntimeError('No remover and mapped_key has been defined.')

        relatives = getattr(resource, field.mapped_key)
        for relative in data:
            try:
                relatives.remove(relative)
            except ValueError:
                pass

    async def update_resource(self, resource, data, sp, **kwargs):
        updated_resource = copy.deepcopy(resource)
        for key, (field_data, sp) in data.items():
            field = self.ctx.schema.get_field(key)
            await self.ctx.schema.set_value(field, updated_resource, field_data, sp, **kwargs)

        return resource, updated_resource

    async def update_relationship(self, field, resource, data, sp, **kwargs):
        updated_resource = copy.deepcopy(resource)
        await self.ctx.schema.set_value(field, updated_resource, data, sp, **kwargs)
        return resource, updated_resource

    async def add_relationship(self, field, resource, data, sp, **kwargs):
        updated_resource = copy.deepcopy(resource)
        adder, adder_kwargs = first(
            get_processors(self, Tag.ADD, field, self.default_add)
        )
        await adder(field, updated_resource, data, sp, **adder_kwargs, **kwargs)
        return resource, updated_resource

    async def remove_relationship(self, field, resource, data, sp, **kwargs):
        updated_resource = copy.deepcopy(resource)
        remover, remover_kwargs = first(
            get_processors(self, Tag.REMOVE, field, self.default_remove)
        )
        await remover(field, updated_resource, data, sp, **remover_kwargs, **kwargs)
        return resource, updated_resource

    async def query_relatives(self, field, resource, **kwargs):
        query, query_kwargs = first(
            get_processors(self, Tag.QUERY, field, self.default_query)
        )
        return await query(field, resource, **query_kwargs, **kwargs)

    async def fetch_compound_documents(self, field, resources, **kwargs):
        include, include_kwargs = first(
            get_processors(self, Tag.INCLUDE, field, self.default_include)
        )
        return await include(field, resources, context=self.ctx, **include_kwargs, **kwargs)
