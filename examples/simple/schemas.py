import logging
import random

from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.schema import BaseSchema, fields, relationships, sets
from aiohttp_json_api.schema.common import Event

from .models import Article, Comment, People

logger = logging.getLogger()


class SchemaWithStorage(BaseSchema):
    @property
    def storage(self):
        """Shortcut for application simple storage"""
        return self.app['storage'][self.resource_class]

    async def fetch_resource(self, resource_id, context, **kwargs):
        result = self.storage.get(
            self.registry.ensure_identifier({'type': self.type,
                                             'id': resource_id})
        )
        if result is None:
            raise ResourceNotFound(self.type, resource_id)

        logger.debug('Fetch resource %r from storage.', result)
        return result

    async def query_collection(self, context, **kwargs):
        return self.storage

    async def query_resource(self, resource_id, context, **kwargs):
        # Here can be added additional permission check, for example.
        # Without this, query_resource is almost the same as fetch_resource.
        return await self.fetch_resource(resource_id, context, **kwargs)

    async def create_resource(self, data, sp, context, **kwargs):
        initial_data = await super(SchemaWithStorage, self).create_resource(
            data, sp, context, **kwargs
        )
        new_resource = self.resource_class(id=random.randint(1000, 9999),
                                           **initial_data)

        new_resource_id = self.registry.ensure_identifier(new_resource)
        self.storage[new_resource_id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

    async def update_resource(self, resource_id, data, sp, context, **kwargs):
        resource, updated_resource = \
            await super(SchemaWithStorage, self).update_resource(
                resource_id, data, sp, context, **kwargs)

        updated_resource_id = self.registry.ensure_identifier(updated_resource)
        self.storage[updated_resource_id] = updated_resource

        logger.debug('%r is updated to %r.', resource, updated_resource)
        return resource, updated_resource

    async def delete_resource(self, resource_id, context, **kwargs):
        try:
            removed_resource = self.storage.pop(
                self.registry.ensure_identifier({'type': self.type,
                                                 'id': resource_id})
            )
        except KeyError:
            raise ResourceNotFound(self.type, resource_id)

        logger.debug('%r is removed.', removed_resource)


class PeopleSchema(SchemaWithStorage):
    type = 'people'
    resource_class = People

    first_name = fields.String(required=Event.CREATE, max_length=128)
    last_name = fields.String(required=Event.CREATE, allow_blank=True,
                              max_length=128)
    twitter = fields.String(allow_none=True, max_length=32)


class CommentSchema(SchemaWithStorage):
    resource_class = Comment  # type will be "comments"

    body = fields.String(required=Event.CREATE, max_length=1024)
    author = relationships.ToOne(required=Event.CREATE,
                                 foreign_types=(PeopleSchema.type,))

    async def create_resource(self, data, sp, context, **kwargs):
        initial_data = await super(SchemaWithStorage, self).create_resource(
            data, sp, context, **kwargs
        )

        author_resource_id = self.registry.ensure_identifier(
            initial_data['author']['data']
        )
        author = self.app['storage'][People].get(author_resource_id)
        if author is None:
            raise ResourceNotFound(author_resource_id.type,
                                   author_resource_id.id)

        new_resource = self.resource_class(
            id=random.randint(1000, 9999), body=initial_data['body'],
            author=author
        )

        new_resource_id = self.registry.ensure_identifier(new_resource)
        self.storage[new_resource_id] = new_resource

        logger.debug('%r is created.', new_resource)
        return new_resource

    @sets('author')
    async def set_author(self, field, resource, data, sp, context=None,
                         **kwargs):
        author_resource_id = self.registry.ensure_identifier(data['data'])
        author = self.app['storage'][People].get(author_resource_id)
        if author is None:
            raise ResourceNotFound(author_resource_id.type,
                                   author_resource_id.id)

        logger.debug('Set author of %r to %r.', resource, author)

        resource.author = author
        return resource


class ArticleSchema(SchemaWithStorage):
    resource_class = Article  # type will be "articles"

    title = fields.String(required=Event.CREATE, max_length=256)
    author = relationships.ToOne(required=Event.CREATE,
                                 foreign_types=(PeopleSchema.type,))
    comments = relationships.ToMany(foreign_types=(CommentSchema.type,))

    # TODO: Create, update, add/remove comments