from collections import OrderedDict
from typing import Optional, Mapping, Any, Dict

from aiopg.sa import SAConnection
from more_itertools import first

import examples.fantasy.tables as tbl
from examples.fantasy.entities import ImageableType, Photo, Author, Book, Series
from examples.fantasy.repositories import Repository


class PhotoRepository(Repository):
    table = tbl.photos

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Photo]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.fetch_many(conn, cte=cte)
        return first(results.values(), default=None)

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[Any, Any]:
        results: Dict[int, Photo] = OrderedDict()
        cte = kwargs.get('cte')
        table = cls.table if cte is None else cte

        imageable_map = {
            'authors': Author,
            'books': Book,
            'series': Series
        }

        query = table.select()

        async for row in conn.execute(query):
            photo_id = row[table.c.id]
            photo = results.get(photo_id)
            if photo is None:
                imageable_id = row[table.c.imageable_id]
                imageable_type = row[table.c.imageable_type]
                imageable_model = imageable_map[imageable_type]
                imageable = imageable_model.not_populated(imageable_id)
                photo = Photo.from_row(row, imageable=imageable, alias=table)
                results[photo_id] = photo

        return results
