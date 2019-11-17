from collections import OrderedDict
from typing import Optional, Mapping, Any, Dict, Type

import sqlalchemy as sa
from aiopg.sa import SAConnection

import examples.fantasy.tables as tbl
from aiohttp_json_api.helpers import first
from examples.fantasy.entities import ImageableType, Photo, Author, Book, Series
from examples.fantasy.repositories import Repository


class PhotoRepository(Repository):
    table = tbl.photos

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Photo]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.get_many(conn, cte=cte)
        return first(results.values())

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[Any, Any]:
        results: Dict[int, Photo] = OrderedDict()
        cte = kwargs.get('cte')
        table = cls.table if cte is None else cte

        imageable_map: Dict[str, Type[ImageableType]] = {
            'authors': Author,
            'books': Book,
            'series': Series,
        }
        book_authors_alias = tbl.authors.alias(name='book_authors')

        query = (
            table
            .outerjoin(
                tbl.authors,
                sa.and_(
                    table.c.imageable_type == 'authors',
                    table.c.imageable_id == tbl.authors.c.id,
                ),
            )
            .outerjoin(
                tbl.books,
                sa.and_(
                    table.c.imageable_type == 'books',
                    table.c.imageable_id == tbl.books.c.id,
                ),
            )
            .outerjoin(
                book_authors_alias,
                tbl.books.c.author_id == book_authors_alias.c.id,
            )
            .outerjoin(
                tbl.series,
                sa.and_(
                    table.c.imageable_type == 'series',
                    table.c.imageable_id == tbl.series.c.id,
                ),
            )
            .select(use_labels=True)
        )

        async for row in conn.execute(query):
            photo_id = row[table.c.id]
            photo = results.get(photo_id)
            if photo is None:
                imageable_id = row[table.c.imageable_id]
                imageable_type = row[table.c.imageable_type]
                imageable_model = imageable_map[imageable_type]
                if imageable_model is Book:
                    author = Author.from_row(row, alias=book_authors_alias)
                    imageable = imageable_model.from_row(row, author=author)
                else:
                    imageable = imageable_model.from_row(row)
                photo = Photo.from_row(row, imageable=imageable, alias=table)
                results[photo_id] = photo

        return results
