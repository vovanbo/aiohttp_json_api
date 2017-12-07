import logging

from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.fields.decorators import sets
from aiohttp_json_api.schema import BaseSchema
from aiohttp_json_api.fields import attributes, relationships
from aiohttp_json_api.common import Event, JSONAPI

from .models import People

logger = logging.getLogger()


class PeopleSchema(BaseSchema):
    first_name = attributes.String(required=Event.CREATE, max_length=128)
    last_name = attributes.String(required=Event.CREATE, allow_blank=True,
                                  max_length=128)
    twitter = attributes.String(allow_none=True, max_length=32)


class CommentSchema(BaseSchema):
    body = attributes.String(required=Event.CREATE, max_length=1024)
    author = relationships.ToOne(required=Event.CREATE,
                                 foreign_types=('people',))

    @sets('author')
    async def set_author(self, field, resource, data, sp, context=None,
                         **kwargs):
        registry = context.request.app[JSONAPI]['registry']
        author_resource_id = registry.ensure_identifier(data['data'])
        author = context.request.app['storage'][People].get(author_resource_id)
        if author is None:
            raise ResourceNotFound(author_resource_id.type,
                                   author_resource_id.id)

        logger.debug('Set author of %r to %r.', resource, author)

        resource.author = author
        return resource


class ArticleSchema(BaseSchema):
    title = attributes.String(required=Event.CREATE, max_length=256)
    author = relationships.ToOne(required=Event.CREATE,
                                 foreign_types=('people',))
    comments = relationships.ToMany(foreign_types=('comments',))

    # TODO: Create, update, add/remove comments
