from collections import OrderedDict
from typing import NamedTuple

import datetime

import trafaret as t
from aiopg.sa import SAConnection
from trafaret.contrib.rfc_3339 import DateTime
import examples.fantasy.tables as tbl

NON_POPULATED = object()


class Store(NamedTuple):
    id: int
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    is_populated: bool = False

    @classmethod
    def from_row(cls, row):
        return cls(
            id=t.Int().check(row[tbl.stores.c.id]),
            name=t.String().check(row[tbl.stores.c.name]),
            created_at=DateTime().check(row[tbl.stores.c.created_at]),
            updated_at=t.Or(DateTime, t.Null).check(
                row[tbl.stores.c.updated_at]
            ),
            is_populated=True
        )

    @classmethod
    def not_populated(cls, id):
        return cls(id=id,
                   name=NON_POPULATED,
                   created_at=NON_POPULATED,
                   updated_at=NON_POPULATED)

    @classmethod
    async def fetch_stores(cls, conn: SAConnection):
        results = OrderedDict()
        query = tbl.stores.select()

        async for row in conn.execute(query):
            store_id = row[tbl.stores.c.id]
            store = results.get(store_id)
            if store is None:
                store = Store.from_row(row)
                results[store_id] = store

        return results
