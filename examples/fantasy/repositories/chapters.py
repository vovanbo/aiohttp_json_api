from collections import OrderedDict
from typing import Mapping, Any, Optional, Dict

from aiopg.sa import SAConnection
from more_itertools import first

import examples.fantasy.tables as tbl
from examples.fantasy.entities import Chapter, Book, Author
from examples.fantasy.repositories import Repository


class ChaptersRepository(Repository):
    table = tbl.chapters

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Chapter]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.get_many(conn, cte=cte)
        return first(results.values(), default=None)

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[Any, Any]:
        results: Dict[int, Chapter] = OrderedDict()
        cte = kwargs.get('cte')
        table = cls.table if cte is None else cte

        query = (
            table
            .join(
                tbl.books,
                table.c.book_id == tbl.books.c.id,
            )
            .join(
                tbl.authors,
                tbl.books.c.author_id == tbl.authors.c.id,
            )
            .select(use_labels=True)
        )

        async for row in conn.execute(query):
            chapter_id = row[table.c.id]
            chapter = results.get(chapter_id)
            if chapter is None:
                author = Author.from_row(row)
                book = Book.from_row(row, author=author)
                chapter = Chapter.from_row(row, book=book, alias=table)
                results[chapter_id] = chapter

        return results
