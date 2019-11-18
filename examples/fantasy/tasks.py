from invoke import task

from examples.fantasy import db


@task
def populate_db(ctx, data_folder=None, dsn=None):
    db.populate_db(data_folder, dsn)
    print('\nDatabase is successfully populated!')
