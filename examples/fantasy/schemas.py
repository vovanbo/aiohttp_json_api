from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.schema import BaseSchema
from aiohttp_json_api.fields import attributes, relationships, decorators

import examples.fantasy.tables as tbl
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
    resource_cls = Author
    type = 'authors'

    name = attributes.String()
    date_of_birth = attributes.Date()
    date_of_death = attributes.Date(allow_none=True)
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class BookSchema(CommonQueryMixin, BaseSchema):
    resource_cls = Book
    type = 'books'

    title = attributes.String()
    date_published = attributes.Date()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    author = relationships.ToOne(foreign_types=('author',))
    series = relationships.ToOne(foreign_types=('series',), allow_none=True)
    chapters = relationships.ToMany(foreign_types=('chapters',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass

    @decorators.includes('author')
    async def include_authors(self, field, resources, context, **kwargs):
        authors_ids = set(r.author.id for r in resources)

        if not authors_ids:
            return ()

        cte = Author.cte(where=(tbl.authors.c.id.in_(authors_ids)))

        async with self.app['db'].acquire() as connection:
            results = await Author.fetch_many(connection, cte)

        return results.values()


class ChapterSchema(CommonQueryMixin, BaseSchema):
    resource_cls = Chapter
    type = 'chapters'

    title = attributes.String()
    ordering = attributes.Integer()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    book = relationships.ToOne(foreign_types=('books',))

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class PhotoSchema(CommonQueryMixin, BaseSchema):
    resource_cls = Photo
    type = 'photos'

    title = attributes.String()
    uri = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    imageable = relationships.ToOne(
        foreign_types=('authors', 'books', 'series')  # polymorphic
    )

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class SeriesSchema(CommonQueryMixin, BaseSchema):
    resource_cls = Series
    type = 'series'

    title = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',))

    async def delete_resource(self, resource_id, context, **kwargs):
        pass


class StoreSchema(CommonQueryMixin, BaseSchema):
    resource_cls = Store
    type = 'stores'

    name = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)
    books = relationships.ToMany(foreign_types=('books',), allow_none=True)

    async def delete_resource(self, resource_id, context, **kwargs):
        pass
