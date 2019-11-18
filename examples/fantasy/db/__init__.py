import json
from pathlib import Path
from typing import Optional

import sqlalchemy as sa

from examples.fantasy import tables


def populate_db(data_folder: Optional[Path] = None, dsn: Optional[str] = None) -> None:
    if data_folder is None:
        data_folder = Path(__file__).parent

    data_file = (data_folder / 'data.json').resolve(strict=True)

    with data_file.open() as f:
        data = json.load(f)

    create_sql = (data_folder / 'schema.sql').read_text()

    if dsn is None:
        dsn = 'postgresql://example:somepassword@localhost/example'

    engine = sa.create_engine(dsn, echo=True)
    conn = engine.connect()
    trans = conn.begin()

    conn.execute(sa.text(create_sql))

    tables_in_order = ('photos', 'stores', 'authors', 'series', 'books', 'chapters', 'books_stores')

    try:
        for table_name in tables_in_order:
            table = getattr(tables, table_name)
            values = data[table_name]
            for value in values:
                query = table.insert().values(value)
                conn.execute(query)
        trans.commit()
    except Exception:
        trans.rollback()
        raise
