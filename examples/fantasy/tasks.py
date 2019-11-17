import json
from pathlib import Path

import sys
from typing import Optional

import sqlalchemy as sa
from invoke import task, Context


@task
def populate_db(ctx: Context, data_folder: Optional[Path] = None, dsn: Optional[str] = None):
    from examples.fantasy import tables

    if data_folder is None:
        data_folder = Path(__file__).parent / 'db'

    data_file = data_folder / 'data.json'
    if not Path(data_file).exists():
        sys.exit(f'Invalid data file: {data_file}')

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

    print('\nDatabase is successfully populated!')
