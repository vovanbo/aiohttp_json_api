from aiohttp_json_api.schema import BaseSchema
from aiohttp_json_api.fields import attributes, relationships

from examples.fantasy.models import Author, Store, Book, Series, Photo, Chapter


class AuthorSchema(BaseSchema):
    name = attributes.String()
    date_of_birth = attributes.Date()
    date_of_death = attributes.Date(allow_none=True)
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    class Options:
        resource_cls = Author
        resource_type = 'authors'


class BookSchema(BaseSchema):
    title = attributes.String()
    date_published = attributes.Date()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    author = relationships.ToOne(foreign_types=('author',))
    series = relationships.ToOne(foreign_types=('series',), allow_none=True)
    chapters = relationships.ToMany(foreign_types=('chapters',))
    photos = relationships.ToMany(foreign_types=('photos',), allow_none=True)

    class Options:
        resource_cls = Book
        resource_type = 'books'


class ChapterSchema(BaseSchema):
    title = attributes.String()
    ordering = attributes.Integer()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    book = relationships.ToOne(foreign_types=('books',))

    class Options:
        resource_cls = Chapter
        resource_type = 'chapters'


class PhotoSchema(BaseSchema):
    title = attributes.String()
    uri = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    imageable = relationships.ToOne(
        foreign_types=('authors', 'books', 'series')  # polymorphic
    )

    class Options:
        resource_cls = Photo
        resource_type = 'photos'


class SeriesSchema(BaseSchema):
    title = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)

    books = relationships.ToMany(foreign_types=('books',))
    photos = relationships.ToMany(foreign_types=('photos',))

    class Options:
        resource_cls = Series
        resource_type = 'series'


class StoreSchema(BaseSchema):
    name = attributes.String()
    created_at = attributes.DateTime()
    updated_at = attributes.DateTime(allow_none=True)
    books = relationships.ToMany(foreign_types=('books',), allow_none=True)

    class Options:
        resource_cls = Store
        resource_type = 'stores'
