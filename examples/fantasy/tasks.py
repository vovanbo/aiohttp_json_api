import json
from pathlib import Path

import sys
import sqlalchemy as sa
from invoke import task

FANTASY_DB_SQL = Path.cwd() / 'fantasy-database' / 'schema.sql'
FANTASY_DB_DATA = Path.cwd() / 'fantasy-database' / 'data.json'


@task
def populate_db(ctx, data_file=FANTASY_DB_DATA):
    from examples.fantasy import tables

    if not Path(data_file).exists():
        sys.exit(f'Invalid data file: {data_file}')

    with data_file.open() as f:
        data = json.load(f)

    create_sql = FANTASY_DB_SQL.read_text()

    engine = \
        sa.create_engine('postgresql://example:somepassword@localhost/example',
                         echo=True)
    conn = engine.connect()
    trans = conn.begin()

    conn.execute(sa.text(create_sql))

    tables_in_order = ('photos', 'stores', 'authors', 'series', 'books',
                       'chapters', 'books_stores')

    try:
        for table_name in tables_in_order:
            table = getattr(tables, table_name)
            values = data[table_name]
            for value in values:
                query = table.insert().values(value)
                conn.execute(query)
        trans.commit()
    except Exception as exc:
        trans.rollback()
        raise

    print('\nDatabase is successfully populated!')
