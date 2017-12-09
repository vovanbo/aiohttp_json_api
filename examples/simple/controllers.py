import logging
import random

from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.controller import DefaultController
from examples.simple.models import People

logger = logging.getLogger()


class SimpleController(DefaultController):
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

    async def create_resource(self, data, sp, **kwargs):
        initial_data = await super(SimpleController, self).create_resource(
            data, sp, **kwargs
        )
        new_resource = \
            self.ctx.schema.opts.resource_cls(id=random.randint(1000, 9999),
                                              **initial_data)

        new_resource_id = self.ctx.registry.ensure_identifier(new_resource)
        self.storage[new_resource_id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

    async def update_resource(self, resource_id, data, sp, **kwargs):
        resource, updated_resource = \
            await super(SimpleController, self).update_resource(
                resource_id, data, sp, **kwargs)

        updated_resource_id = \
            self.ctx.registry.ensure_identifier(updated_resource)
        self.storage[updated_resource_id] = updated_resource

        logger.debug('%r is updated to %r.', resource, updated_resource)
        return resource, updated_resource

    async def delete_resource(self, resource_id, **kwargs):
        try:
            removed_resource = self.storage.pop(
                self.ctx.registry.ensure_identifier(
                    {'type': self.ctx.resource_type, 'id': resource_id}
                )
            )
        except KeyError:
            raise ResourceNotFound(self.ctx.resource_type, resource_id)

        logger.debug('%r is removed.', removed_resource)


class CommentsController(SimpleController):
    async def create_resource(self, data, sp, **kwargs):
        initial_data = await super(SimpleController, self).create_resource(
            data, sp, **kwargs
        )

        author_resource_id = self.ctx.registry.ensure_identifier(
            initial_data['author']['data']
        )
        author = self.ctx.app['storage'][People].get(author_resource_id)
        if author is None:
            raise ResourceNotFound(author_resource_id.type,
                                   author_resource_id.id)

        new_resource = self.ctx.schema.opts.resource_cls(
            id=random.randint(1000, 9999), body=initial_data['body'],
            author=author
        )

        new_resource_id = self.ctx.registry.ensure_identifier(new_resource)
        self.storage[new_resource_id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

