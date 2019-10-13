import abc
from typing import Any, Mapping

import sqlalchemy as sa
from aiopg.sa import SAConnection
from sqlalchemy.sql.selectable import CTE


class Repository(abc.ABC):
    table: sa.Table

    @classmethod
    @abc.abstractmethod
    async def get_one(cls, conn: SAConnection, pk: Any, **kwargs) -> Any:
        pass

    @classmethod
    @abc.abstractmethod
    async def get_many(cls, conn: SAConnection, **kwargs) -> Mapping[Any, Any]:
        pass

    @classmethod
    def cte(cls, name=None, where=None, limit=None, offset=None) -> CTE:
        name = name or f'{cls.table.name}_cte'
        query = cls.table.select()
        if where is not None:
            query = query.where(where)
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.cte(name=name)
