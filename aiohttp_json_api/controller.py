import copy

from .abc.contoller import ControllerABC
from .common import Relation, logger
from .fields.decorators import Tag
from .helpers import first, get_processors


class DefaultController(ControllerABC):
    @staticmethod
    async def default_include(field, resources, **kwargs):
        if field.mapped_key:
            ctx = kwargs['context']
            compound_documents = []
            for resource in resources:
                compound_document = getattr(resource, field.mapped_key)
                if compound_document:
                    compound_documents.extend(
                        (compound_document,)
                        if type(compound_document) in ctx.registry
                        else compound_document
                    )
            return compound_documents
        raise RuntimeError('No includer and mapped_key have been defined.')

    @staticmethod
    async def default_query(field, resource, **kwargs):
        if field.mapped_key:
            return getattr(resource, field.mapped_key)
        raise RuntimeError('No query method and mapped_key have been defined.')

    @staticmethod
    async def default_add(field, resource, data, sp, **kwargs):
        logger.warning('You should override the adder.')

        if not field.mapped_key:
            raise RuntimeError('No adder and mapped_key have been defined.')

        relatives = getattr(resource, field.mapped_key)
        relatives.extend(data)

    @staticmethod
    async def default_remove(field, resource, data, sp, **kwargs):
        logger.warning('You should override the remover.')

        if not field.mapped_key:
            raise RuntimeError('No remover and mapped_key have been defined.')

        relatives = getattr(resource, field.mapped_key)
        for relative in data:
            try:
                relatives.remove(relative)
            except ValueError:
                pass

    async def create_resource(self, data, sp, **kwargs):
        return self.ctx.schema.map_data_to_schema(
            await self.ctx.schema.deserialize_resource(data, sp)
        )

    async def update_resource(self, resource_id, data, sp, **kwargs):
        deserialized_data = \
            await self.ctx.schema.deserialize_resource(data, sp,
                                                       expected_id=resource_id)

        resource = await self.fetch_resource(resource_id, **kwargs)

        updated_resource = copy.deepcopy(resource)
        for key, (data, sp) in deserialized_data.items():
            field = self.ctx.schema._declared_fields[key]
            await self.ctx.schema.set_value(field, updated_resource, data, sp,
                                            **kwargs)

        return resource, updated_resource

    async def update_relationship(self, relation_name, resource_id,
                                  data, sp, **kwargs):
        field = self.ctx.schema.get_relationship_field(relation_name)

        await self.ctx.schema._pre_validate_field(field, data, sp)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, **kwargs)

        updated_resource = copy.deepcopy(resource)
        await self.ctx.schema.set_value(field, updated_resource, decoded, sp,
                                        **kwargs)
        return resource, updated_resource

    async def add_relationship(self, relation_name, resource_id,
                               data, sp, **kwargs):
        field = self.ctx.schema.get_relationship_field(relation_name)
        if field.relation is not Relation.TO_MANY:
            raise RuntimeError('Wrong relationship field.'
                               'Relation to-many is required.')

        await self.ctx.schema._pre_validate_field(field, data, sp)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, **kwargs)

        updated_resource = copy.deepcopy(resource)
        adder, adder_kwargs = first(
            get_processors(self, Tag.ADD, field, self.default_add)
        )
        await adder(field, updated_resource, decoded, sp,
                    **adder_kwargs, **kwargs)
        return resource, updated_resource

    async def remove_relationship(self, relation_name, resource_id,
                                  data, sp, **kwargs):
        field = self.ctx.schema.get_relationship_field(relation_name)
        if field.relation is not Relation.TO_MANY:
            raise RuntimeError('Wrong relationship field.'
                               'Relation to-many is required.')

        await self.ctx.schema._pre_validate_field(field, data, sp)
        decoded = field.deserialize(self, data, sp, **kwargs)

        resource = await self.fetch_resource(resource_id, **kwargs)

        updated_resource = copy.deepcopy(resource)
        remover, remover_kwargs = first(
            get_processors(self, Tag.REMOVE, field, self.default_remove)
        )
        await remover(field, updated_resource, decoded, sp,
                      **remover_kwargs, **kwargs)
        return resource, updated_resource

    async def query_relatives(self, relation_name, resource_id, **kwargs):
        field = self.ctx.schema.get_relationship_field(relation_name)

        resource = await self.fetch_resource(resource_id, **kwargs)
        query, query_kwargs = first(
            get_processors(self, Tag.QUERY, field, self.default_query)
        )
        return await query(field, resource, **query_kwargs, **kwargs)

    async def fetch_compound_documents(self, relation_name, resources,
                                       **kwargs):
        field = self.ctx.schema.get_relationship_field(
            relation_name, source_parameter='include'
        )
        include, include_kwargs = first(
            get_processors(self, Tag.INCLUDE, field, self.default_include)
        )
        return await include(field, resources, context=self.ctx,
                             **include_kwargs, **kwargs)
