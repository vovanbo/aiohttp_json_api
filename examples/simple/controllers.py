import logging
import random

from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.controller import BaseController
from examples.simple.models import People

logger = logging.getLogger()


class SimpleController(BaseController):
    @property
    def storage(self):
        """Shortcut for application simple storage"""
        return self.ctx.app['storage']

    async def fetch_resource(self, resource_id, **kwargs):
        rid = self.ctx.registry.ensure_identifier(
            {'type': self.ctx.resource_type, 'id': resource_id}
        )
        result = self.storage[rid.type].get(rid.id)
        if result is None:
            raise ResourceNotFound(self.ctx.resource_type, resource_id)

        logger.debug('Fetch resource %r from storage.', result)
        return result

    async def query_collection(self, **kwargs):
        return self.storage[self.ctx.resource_type].values()

    async def query_resource(self, resource_id, **kwargs):
        # Here can be added additional permission check, for example.
        # Without this, query_resource is almost the same as fetch_resource.
        return await self.fetch_resource(resource_id, **kwargs)

    async def create_resource(self, data, **kwargs):
        resource_cls = self.ctx.schema.opts.resource_cls
        new_resource = resource_cls(id=random.randint(1000, 9999), **data)

        rid = self.ctx.registry.ensure_identifier(new_resource)
        self.storage[rid.type][rid.id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

    async def update_resource(self, resource, data, sp, **kwargs):
        resource, updated_resource = await super().update_resource(resource, data, sp, **kwargs)

        rid = self.ctx.registry.ensure_identifier(updated_resource)
        self.storage[rid.type][rid.id] = updated_resource

        logger.debug('%r is updated to %r.', resource, updated_resource)
        return resource, updated_resource

    async def delete_resource(self, resource_id, **kwargs):
        try:
            rid = self.ctx.registry.ensure_identifier(
                {'type': self.ctx.resource_type, 'id': resource_id}
            )
            removed_resource = self.storage[rid.type].pop(rid.id)
        except KeyError:
            raise ResourceNotFound(self.ctx.resource_type, resource_id)

        logger.debug('%r is removed.', removed_resource)


class CommentsController(SimpleController):
    async def create_resource(self, data, **kwargs):
        rid = self.ctx.registry.ensure_identifier(data['author']['data'])
        author = self.storage[rid.type].get(rid.id)
        if author is None:
            raise ResourceNotFound(rid.type, rid.id)

        resource_cls = self.ctx.schema.opts.resource_cls
        new_resource = resource_cls(
            id=random.randint(1000, 9999), body=data['body'],
            author=author
        )

        rid = self.ctx.registry.ensure_identifier(new_resource)
        self.storage[rid.type][rid.id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

