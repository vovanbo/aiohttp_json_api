import sqlalchemy as sa
from sqlalchemy.sql.selectable import CTE


def cte_constructor(table: sa.Table, name=None, where=None, limit=None, offset=None) -> CTE:
    name = name or f'{table.name}_cte'
    query = table.select()
    if where is not None:
        query = query.where(where)
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)
    return query.cte(name=name)
