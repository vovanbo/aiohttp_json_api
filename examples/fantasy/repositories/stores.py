from collections import OrderedDict
from typing import Mapping, Optional, Dict

from aiopg.sa import SAConnection

import examples.fantasy.tables as tbl
from aiohttp_json_api.helpers import first
from examples.fantasy.entities import Store, Book, Author
from examples.fantasy.repositories import Repository


class StoresRepository(Repository):
    table = tbl.stores

    @classmethod
    async def get_one(cls, conn: SAConnection, pk: int, **kwargs) -> Optional[Store]:
        cte = cls.cte(where=(cls.table.c.id == pk), limit=1)
        results = await cls.get_many(conn, cte=cte)
        return first(results.values())

    @classmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[int, Store]:
        results: Dict[int, Store] = OrderedDict()
        cte = kwargs.get('cte')
        table = cls.table if cte is None else cte

        query = (
            table
            .outerjoin(tbl.books_stores)
            .outerjoin(
                tbl.books,
                tbl.books_stores.c.book_id == tbl.books.c.id,
            )
            .join(
                tbl.authors,
                tbl.books.c.author_id == tbl.authors.c.id,
            )
            .select(use_labels=True)
        )

        books: Dict[int, Book] = {}

        async for row in conn.execute(query):
            store_id = row[table.c.id]
            store = results.get(store_id)
            if store is None:
                store = Store.from_row(row, alias=table)
                results[store_id] = store

            book_id = row[tbl.books.c.id]
            if book_id:
                if book_id not in books:
                    author = Author.from_row(row)
                    books[book_id] = book = Book.from_row(row, author=author)
                else:
                    book = books[book_id]

                if book not in store.books:
                    store.books.append(book)

        return results
