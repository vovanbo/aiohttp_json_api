from collections import OrderedDict
from typing import Dict, Optional

import trafaret as t
import sqlalchemy as sa
from aiopg.sa import SAConnection
from more_itertools import first
from sqlalchemy.sql.selectable import CTE
from trafaret.contrib.rfc_3339 import Date, DateTime

import examples.fantasy.tables as tbl
from examples.fantasy.entities import Author
from examples.fantasy.repositories import cte_constructor
from examples.fantasy.repositories.books import _get_book_from_row
from examples.fantasy.repositories.photos import _get_photo_from_row


def _get_author_from_row(row, alias: Optional[str] = None):
    table = tbl.authors if alias is None else alias
    return Author(
        id=t.Int().check(row[table.c.id]),
        name=t.String().check(row[table.c.name]),
        date_of_birth=Date().check(row[table.c.date_of_birth]),
        date_of_death=t.Or(Date, t.Null).check(row[table.c.date_of_death]),
        books=[],
        photos=[],
        created_at=DateTime().check(row[table.c.created_at]),
        updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
    )


async def fetch_many(conn: SAConnection, cte: Optional[CTE] = None):
    results: Dict[int, Author] = OrderedDict()
    table = tbl.authors if cte is None else cte

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

    books = {}
    photos = {}

    async for row in conn.execute(query):
        author_id = row[table.c.id]
        author = results.get(author_id)
        if author is None:
            author = _get_author_from_row(row, alias=table)
            results[author_id] = author

        book_id = row[tbl.books.c.id]
        if book_id:
            if book_id not in books:
                books[book_id] = book = _get_book_from_row(row, author=author)
            else:
                book = books[book_id]

            if book not in author.books:
                author.books.append(book)

        photo_id = row[tbl.photos.c.id]
        if photo_id:
            if photo_id not in photos:
                photos[photo_id] = photo = _get_photo_from_row(row, imageable=author)
            else:
                photo = photos[photo_id]

            if photo not in author.photos:
                author.photos.append(photo)

    return results


async def fetch_one(conn: SAConnection, author_id: int) -> Author:
    cte = cte_constructor(tbl.authors, where=(tbl.authors.c.id == author_id), limit=1)
    results = await fetch_many(conn, cte)
    return first(results.values())
