import json
from pathlib import Path

import sys
import sqlalchemy as sa
from invoke import task

FANTASY_DATA_FOLDER = Path(__file__).parent / 'fantasy-database'


@task
def populate_db(ctx, data_folder=FANTASY_DATA_FOLDER, dsn=None):
    from examples.fantasy import tables

    data_file = data_folder / 'data.json'
    if not Path(data_file).exists():
        sys.exit('Invalid data file: {}'.format(data_file))

    with data_file.open() as f:
        data = json.load(f)

    create_sql = (data_folder / 'schema.sql').read_text()

    if dsn is None:
        dsn = 'postgresql://example:somepassword@localhost/example'

    engine = sa.create_engine(dsn, echo=True)
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
