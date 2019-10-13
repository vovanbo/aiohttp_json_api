from collections import OrderedDict
from typing import Optional, Dict, Mapping

import sqlalchemy as sa
from aiopg.sa import SAConnection
from more_itertools import first

import examples.fantasy.tables as tbl
from examples.fantasy.entities import Author, Book, Chapter, Photo, Series
from examples.fantasy.repositories import Repository


class BooksRepository(Repository):
    table = tbl.books

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Book]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.get_many(conn, cte=cte)
        return first(results.values(), default=None)

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[int, Book]:
        results: Dict[int, Book] = OrderedDict()
        cte = kwargs.get('cte')
        table = cls.table if cte is None else cte

        query = (
            table
            .join(tbl.authors)
            .outerjoin(tbl.series)
            .outerjoin(tbl.chapters)
            .outerjoin(
                tbl.photos,
                sa.and_(
                    tbl.photos.c.imageable_id == table.c.id,
                    tbl.photos.c.imageable_type == 'books'
                ),
            )
            .select(use_labels=True)
        )

        photos = {}
        chapters = {}

        async for row in conn.execute(query):
            book_id = row[table.c.id]
            book = results.get(book_id)
            if book is None:
                book_author = Author.from_row(row)
                book_series_id = row[tbl.series.c.id]
                book_series = Series.from_row(row) if book_series_id else None
                book = Book.from_row(
                    row,
                    alias=table,
                    author=book_author,
                    chapters=[],
                    series=book_series,
                    photos=[],
                )
                results[book_id] = book

            photo_id = row[tbl.photos.c.id]
            if photo_id:
                if photo_id not in photos:
                    photos[photo_id] = photo = Photo.from_row(row, imageable=book)
                else:
                    photo = photos[photo_id]

                if photo not in book.photos:
                    book.photos.append(photo)

            chapter_id = row[tbl.chapters.c.id]
            if chapter_id:
                chapter = chapters.get(chapter_id, Chapter.from_row(row, book=book))
                if chapter not in book.chapters:
                    book.chapters.append(chapter)

        return results
