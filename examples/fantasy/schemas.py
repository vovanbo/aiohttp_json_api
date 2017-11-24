from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.schema import BaseSchema, fields, relationships, sets
from aiohttp_json_api.common import Event

from examples.fantasy.models import Author, Store, Book, Series, Photo, Chapter


class CommonQueryMixin:
    async def fetch_resource(self, resource_id, context, **kwargs):
        async with self.app['db'].acquire() as connection:
            result = await self.resource_class.fetch_one(connection,
                                                         resource_id)

        if result is None:
            raise ResourceNotFound(type=self.type, id=resource_id)

        return result

    async def query_collection(self, context, **kwargs):
        async with self.app['db'].acquire() as connection:
            results = await self.resource_class.fetch_many(connection)

        return results.values()

    async def query_resource(self, resource_id, context, **kwargs):
        return await self.fetch_resource(resource_id, context, **kwargs)


class AuthorSchema(CommonQueryMixin, BaseSchema):
    resource_class = Author
    type = 'authors'

    name = fields.String()
    date_of_birth = fields.Date()
    date_of_death = fields.Date(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class BookSchema(CommonQueryMixin, BaseSchema):
    resource_class = Book
    type = 'books'

    title = fields.String()
    date_published = fields.Date()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    author = relationships.ToOne(foreign_types=('author',))
    series = relationships.ToOne(foreign_types=('series',), allow_none=True)
    chapters = relationships.ToMany(foreign_types=('chapters',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class ChapterSchema(CommonQueryMixin, BaseSchema):
    resource_class = Chapter
    type = 'chapter'

    title = fields.String()
    ordering = fields.Integer()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    book = relationships.ToOne(foreign_types=('books',))

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class PhotoSchema(CommonQueryMixin, BaseSchema):
    resource_class = Photo
    type = 'photos'

    title = fields.String()
    uri = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    imageable = relationships.ToOne(
        foreign_types=('authors', 'books', 'series')  # polymorphic
    )

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class SeriesSchema(CommonQueryMixin, BaseSchema):
    resource_class = Series
    type = 'series'

    title = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',))

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class StoreSchema(CommonQueryMixin, BaseSchema):
    resource_class = Store
    type = 'stores'

    name = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)
    books = relationships.ToMany(foreign_types=('books',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass
