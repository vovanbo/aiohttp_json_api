from collections import OrderedDict
from typing import Dict, Optional, Mapping, Any

import sqlalchemy as sa
from aiopg.sa import SAConnection
from sqlalchemy.sql.selectable import CTE

import examples.fantasy.tables as tbl
from aiohttp_json_api.helpers import first
from examples.fantasy.entities import Author, Book, Photo
from examples.fantasy.repositories import Repository


class AuthorsRepository(Repository):
    table = tbl.authors

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Author]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.get_many(conn, cte=cte)
        return first(results.values())

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[int, Author]:
        results: Dict[int, Author] = OrderedDict()
        cte: Optional[CTE] = kwargs.get('cte')
        table = cls.table if cte is None else cte

        query = (
            table
            .outerjoin(
                tbl.books,
                tbl.books.c.author_id == table.c.id,
            )
            .outerjoin(
                tbl.photos,
                sa.and_(
                    tbl.photos.c.imageable_id == table.c.id,
                    tbl.photos.c.imageable_type == 'authors'
                )
            )
            .select(use_labels=True)
        )

        books: Dict[int, Book] = {}
        photos: Dict[int, Photo] = {}

        async for row in conn.execute(query):
            author_id = row[table.c.id]
            author = results.get(author_id)
            if author is None:
                author = Author.from_row(row, alias=table)
                results[author_id] = author

            book_id = row[tbl.books.c.id]
            if book_id:
                if book_id not in books:
                    books[book_id] = book = Book.from_row(row, author=author)
                else:
                    book = books[book_id]

                if book not in author.books:
                    author.books.append(book)

            photo_id = row[tbl.photos.c.id]
            if photo_id:
                if photo_id not in photos:
                    photos[photo_id] = photo = Photo.from_row(row, imageable=author)
                else:
                    photo = photos[photo_id]

                if photo not in author.photos:
                    author.photos.append(photo)

        return results
