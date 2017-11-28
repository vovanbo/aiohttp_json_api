from collections import OrderedDict
from typing import NamedTuple, Union, Optional, List

import datetime

import inflection
import trafaret as t
import sqlalchemy as sa
from aiopg.sa import SAConnection
from sqlalchemy.sql.selectable import CTE
from trafaret.contrib.rfc_3339 import DateTime, Date

import examples.fantasy.tables as tbl

NON_POPULATED = object()
ImageableType = Union['Author', 'Book', 'Series']


class Author(NamedTuple):
    id: int
    name: str
    date_of_birth: datetime.datetime
    date_of_death: Optional[datetime.datetime]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    books: List['Book']
    photos: List['Photo']
    is_populated: bool = False

    class Options:
        db_table = tbl.authors

    @classmethod
    def from_row(cls, row, books: List['Book'], photos: List['Photo'],
                 alias=None):
        table = cls.Options.db_table if alias is None else alias
        return cls(
            id=t.Int().check(row[table.c.id]),
            name=t.String().check(row[table.c.name]),
            date_of_birth=Date().check(row[table.c.date_of_birth]),
            date_of_death=t.Or(Date, t.Null).check(row[table.c.date_of_death]),
            books=t.List(t.Type(Book)).check(books),
            photos=t.List(t.Type(Photo)).check(photos),
            created_at=DateTime().check(row[table.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   name=NON_POPULATED,
                   date_of_birth=NON_POPULATED,
                   date_of_death=NON_POPULATED,
                   books=NON_POPULATED,
                   photos=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_many(cls, conn: SAConnection, cte: CTE = None):
        results = OrderedDict()

        if cte is None:
            cte = cls.Options.db_table

        query = (
            cte
            .outerjoin(tbl.books,
                       tbl.books.c.author_id == cte.c.id)
            .outerjoin(tbl.photos,
                       sa.and_(
                           tbl.photos.c.imageable_id == cte.c.id,
                           tbl.photos.c.imageable_type == 'authors'
                       ))
            .select(use_labels=True)
        )

        books = {}
        photos = {}

        async for row in conn.execute(query):
            author_id = row[cte.c.id]
            author = results.get(author_id)
            if author is None:
                author = Author.from_row(row, books=[], photos=[], alias=cte)
                results[author_id] = author

            book_id = row[tbl.books.c.id]
            if book_id:
                book = books.get(book_id, Book.not_populated(book_id))

                if book not in author.books:
                    author.books.append(book)

            photo_id = row[tbl.photos.c.id]
            if photo_id:
                photo = photos.get(photo_id, Photo.not_populated(photo_id))

                if photo not in author.photos:
                    author.photos.append(photo)

        return results

    @classmethod
    async def fetch_one(cls, conn: SAConnection, author_id):
        cte = cls.cte(where=(cls.Options.db_table.c.id == author_id),
                      limit=1)
        results = await cls.fetch_many(conn, cte=cte)
        _, author = results.popitem(last=False)
        return author


class Book(NamedTuple):
    id: int
    title: str
    date_published: datetime.datetime
    author: 'Author'
    series: Optional['Series']
    photos: List['Photo']
    chapters: List['Chapter']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    is_populated: bool = False

    class Options:
        db_table = tbl.books

    @classmethod
    def from_row(cls, row, author: 'Author', photos: List['Photo'],
                 chapters: List['Chapter'], series: 'Series' = None,
                 alias=None):
        table = cls.Options.db_table if alias is None else alias
        return cls(
            id=t.Int().check(row[table.c.id]),
            title=t.String().check(row[table.c.title]),
            date_published=Date().check(row[table.c.date_published]),
            author=t.Type(Author).check(author),
            photos=t.List(t.Type(Photo)).check(photos),
            chapters=t.List(t.Type(Chapter)).check(chapters),
            series=t.Or(t.Type(Series), t.Null).check(series),
            created_at=DateTime().check(row[table.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   title=NON_POPULATED,
                   date_published=NON_POPULATED,
                   author=NON_POPULATED,
                   photos=NON_POPULATED,
                   chapters=NON_POPULATED,
                   series=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_many(cls, conn: SAConnection, cte: CTE = None):
        results = OrderedDict()

        if cte is None:
            cte = cls.Options.db_table

        query = (
            cte
            .join(tbl.authors)
            .outerjoin(tbl.series)
            .outerjoin(tbl.chapters)
            .outerjoin(tbl.photos,
                       sa.and_(
                           tbl.photos.c.imageable_id == cte.c.id,
                           tbl.photos.c.imageable_type == 'books'
                       ))
            .select(use_labels=True)
        )

        photos = {}
        chapters = {}

        async for row in conn.execute(query):
            book_id = row[cte.c.id]
            book = results.get(book_id)
            if book is None:
                book_author = Author.not_populated(row[tbl.authors.c.id])
                book_series_id = row[tbl.series.c.id]
                book_series = Series.not_populated(book_series_id) \
                    if book_series_id \
                    else None
                book = Book.from_row(row, author=book_author, chapters=[],
                                     series=book_series,
                                     photos=[], alias=cte)
                results[book_id] = book

            photo_id = row[tbl.photos.c.id]
            if photo_id:
                photo = photos.get(photo_id, Photo.not_populated(photo_id))

                if photo not in book.photos:
                    book.photos.append(photo)

            chapter_id = row[tbl.chapters.c.id]
            if chapter_id:
                chapter = chapters.get(chapter_id,
                                       Chapter.not_populated(chapter_id))

                if chapter not in book.chapters:
                    book.chapters.append(chapter)

        return results

    @classmethod
    async def fetch_one(cls, conn: SAConnection, book_id):
        cte = cls.cte(where=(cls.Options.db_table.c.id == book_id),
                      limit=1)
        results = await cls.fetch_many(conn, cte=cte)
        _, book = results.popitem(last=False)
        return book


class Chapter(NamedTuple):
    id: int
    title: str
    ordering: int
    book: Book
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    is_populated: bool = False

    class Options:
        db_table = tbl.chapters

    @classmethod
    def from_row(cls, row, book: 'Book', alias=None):
        table = cls.Options.db_table if alias is None else alias
        return cls(
            id=t.Int().check(row[table.c.id]),
            title=t.String().check(row[table.c.title]),
            ordering=t.Int().check(row[table.c.ordering]),
            book=t.Type(Book).check(book),
            created_at=DateTime().check(row[table.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   title=NON_POPULATED,
                   ordering=NON_POPULATED,
                   book=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_many(cls, conn: SAConnection, cte: CTE = None):
        results = OrderedDict()

        if cte is None:
            cte = cls.Options.db_table

        query = cte.select()

        async for row in conn.execute(query):
            chapter_id = row[cte.c.id]
            chapter = results.get(chapter_id)
            if chapter is None:
                chapter = \
                    cls.from_row(row,
                                 book=Book.not_populated(row[cte.c.book_id]),
                                 alias=cte)
                results[chapter_id] = chapter

        return results

    @classmethod
    async def fetch_one(cls, conn: SAConnection, chapter_id):
        query = (
            tbl.chapters.select()
            .where(tbl.chapters.c.id == chapter_id)
            .limit(1)
        )
        result = await conn.execute(query)
        row = await result.fetchone()
        chapter = cls.from_row(
            row, book=Book.not_populated(row[tbl.chapters.c.book_id])
        )
        return chapter


class Photo(NamedTuple):
    id: int
    title: str
    uri: str
    imageable: ImageableType
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    is_populated: bool = False

    class Options:
        db_table = tbl.photos

    @classmethod
    def from_row(cls, row, imageable: ImageableType, alias=None):
        table = cls.Options.db_table if alias is None else alias
        return cls(
            id=t.Int().check(row[table.c.id]),
            title=t.String().check(row[table.c.title]),
            uri=str(t.URL.check(row[table.c.uri])),
            imageable=t.Or(t.Type(Author),
                           t.Type(Book),
                           t.Type(Series)).check(imageable),
            created_at=DateTime().check(row[table.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   title=NON_POPULATED,
                   uri=NON_POPULATED,
                   imageable=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_many(cls, conn: SAConnection, cte: CTE = None):
        results = OrderedDict()

        imageable_map = {
            'authors': Author,
            'books': Book,
            'series': Series
        }

        if cte is None:
            cte = cls.Options.db_table

        query = cte.select()

        async for row in conn.execute(query):
            photo_id = row[cte.c.id]
            photo = results.get(photo_id)
            if photo is None:
                imageable_id = row[cte.c.imageable_id]
                imageable_type = row[cte.c.imageable_type]
                imageable_model = imageable_map[imageable_type]
                imageable = imageable_model.not_populated(imageable_id)
                photo = Photo.from_row(row, imageable=imageable, alias=cte)
                results[photo_id] = photo

        return results

    @classmethod
    async def fetch_one(cls, conn: SAConnection, photo_id):
        cte = cls.cte(where=(cls.Options.db_table.c.id == photo_id),
                      limit=1)
        results = await cls.fetch_many(conn, cte=cte)
        _, photo = results.popitem(last=False)
        return photo


class Store(NamedTuple):
    id: int
    name: str
    books: List['Book']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    is_populated: bool = False

    class Options:
        db_table = tbl.stores

    @classmethod
    def from_row(cls, row, books: List['Book'], alias=None):
        table = cls.Options.db_table if alias is None else alias
        return cls(
            id=t.Int().check(row[table.c.id]),
            name=t.String().check(row[table.c.name]),
            books=t.List(t.Type(Book)).check(books),
            created_at=DateTime().check(row[table.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   name=NON_POPULATED,
                   books=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_many(cls, conn: SAConnection, cte: CTE = None):
        results = OrderedDict()

        if cte is None:
            cte = cls.Options.db_table

        query = (
            cte
            .outerjoin(tbl.books_stores)
            .outerjoin(tbl.books,
                       tbl.books_stores.c.book_id == tbl.books.c.id)
            .select(use_labels=True)
        )

        books = {}

        async for row in conn.execute(query):
            store_id = row[cte.c.id]
            store = results.get(store_id)
            if store is None:
                store = Store.from_row(row, books=[], alias=cte)
                results[store_id] = store

            book_id = row[tbl.books.c.id]
            if book_id:
                book = books.get(book_id, Book.not_populated(book_id))

                if book not in store.books:
                    store.books.append(book)

        return results

    @classmethod
    async def fetch_one(cls, conn: SAConnection, store_id):
        cte = cls.cte(where=(cls.Options.db_table.c.id == store_id),
                      limit=1)
        results = await cls.fetch_many(conn, cte=cte)
        _, store = results.popitem(last=False)
        return store


class Series(NamedTuple):
    id: int
    title: str
    books: List['Book']
    photos: List['Photo']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    is_populated: bool = False

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   title=NON_POPULATED,
                   books=NON_POPULATED,
                   photos=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)


def cte_constructor(cls, where=None, limit=None, offset=None, name=None) -> CTE:
    query = cls.Options.db_table.select()
    if where is not None:
        query = query.where(where)
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    name = name or '{}_cte'.format(inflection.tableize(cls.__name__))
    return query.cte(name=name)


# With NamedTuple we can't use mixins normally,
# so use classmethod() call directly
for model in (Author, Book, Photo, Series, Store):
    model.cte = classmethod(cte_constructor)
