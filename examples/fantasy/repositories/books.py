from typing import Optional

import trafaret as t
from trafaret.contrib.rfc_3339 import Date, DateTime

import examples.fantasy.tables as tbl
from examples.fantasy.entities import Author, Book


def _get_book_from_row(row, author: Author, alias: Optional[str] = None, **kwargs):
    table = tbl.books if alias is None else alias
    return Book(
        id=t.Int().check(row[table.c.id]),
        title=t.String().check(row[table.c.title]),
        date_published=Date().check(row[table.c.date_published]),
        author=t.Type(Author).check(author),
        photos=kwargs.get('photos', []),
        chapters=kwargs.get('chapters', []),
        series=kwargs.get('series'),
        created_at=DateTime().check(row[table.c.created_at]),
        updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
    )
