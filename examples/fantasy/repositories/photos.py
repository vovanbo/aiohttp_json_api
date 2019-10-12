from typing import Optional

import trafaret as t
from trafaret.contrib.rfc_3339 import DateTime

import examples.fantasy.tables as tbl
from examples.fantasy.entities import ImageableType, Author, Book, Series, Photo


def _get_photo_from_row(row, imageable: ImageableType, alias: Optional[str] = None) -> Photo:
    table = tbl.photos if alias is None else alias
    return Photo(
        id=t.Int().check(row[table.c.id]),
        title=t.String().check(row[table.c.title]),
        uri=str(t.URL.check(row[table.c.uri])),
        imageable=t.Or(t.Type(Author), t.Type(Book), t.Type(Series)).check(imageable),
        created_at=DateTime().check(row[table.c.created_at]),
        updated_at=t.Or(DateTime, t.Null).check(row[table.c.updated_at]),
    )
