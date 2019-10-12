import logging

from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.fields.decorators import sets
from aiohttp_json_api.schema import BaseSchema
from aiohttp_json_api.fields import attributes, relationships
from aiohttp_json_api.common import Event

from .models import Article, Comment, People

logger = logging.getLogger()


class PeopleSchema(BaseSchema):
    first_name = attributes.String(required=Event.CREATE, max_length=128)
    last_name = attributes.String(required=Event.CREATE, allow_blank=True, max_length=128)
    twitter = attributes.String(allow_none=True, max_length=32)

    class Options:
        resource_cls = People
        resource_type = 'people'


class CommentSchema(BaseSchema):
    body = attributes.String(required=Event.CREATE, max_length=1024)
    author = relationships.ToOne(required=Event.CREATE, foreign_types=('people',))

    class Options:
        resource_cls = Comment
        resource_type = 'comments'

    @sets('author')
    async def set_author(self, field, resource, data, sp, context=None, **kwargs):
        rid = self.ctx.registry.ensure_identifier(data['data'])
        storage = self.ctx.app['storage']
        author = storage[rid.type].get(rid.id)
        if author is None:
            raise ResourceNotFound(rid.type, rid.id)

        logger.debug('Set author of %r to %r.', resource, author)

        resource.author = author
        return resource


class ArticleSchema(BaseSchema):
    title = attributes.String(required=Event.CREATE, max_length=256)
    author = relationships.ToOne(required=Event.CREATE, foreign_types=('people',))
    comments = relationships.ToMany(foreign_types=('comments',))

    class Options:
        resource_cls = Article
        resource_type = 'articles'

    # TODO: Create, update, add/remove comments
