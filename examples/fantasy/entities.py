import abc
import datetime
from typing import Optional, List, Union, Any

import sqlalchemy as sa
from aiopg.sa.result import RowProxy
from pydantic import BaseModel

import examples.fantasy.tables as tbl


ImageableType = Union['Author', 'Book', 'Series']


class FantasyModel(BaseModel):
    id: int
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    def __eq__(self, other: Any) -> bool:
        # Compare only IDs of entities to avoid infinite recursion of BaseModels
        if isinstance(other, BaseModel):
            return self.dict(include={'id'}) == other.dict(include={'id'})
        else:
            return self.dict() == other

    @property
    @abc.abstractmethod
    def _db_table(self) -> sa.Table:
        pass

    @classmethod
    @abc.abstractmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'FantasyModel':
        pass


class Photo(FantasyModel):
    title: str
    uri: str
    imageable: ImageableType

    _db_table = tbl.photos

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Photo':
        table = cls._db_table if alias is None else alias
        imageable = kwargs['imageable']
        return Photo(
            id=row[table.c.id],
            title=row[table.c.title],
            uri=row[table.c.uri],
            imageable=imageable,
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


class Book(FantasyModel):
    title: str
    date_published: datetime.date
    author: 'Author'
    series: Optional['Series']
    photos: List[Photo]
    chapters: List['Chapter']

    _db_table = tbl.books

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Book':
        table = cls._db_table if alias is None else alias
        author = kwargs['author']
        return cls(
            id=row[table.c.id],
            title=row[table.c.title],
            date_published=row[table.c.date_published],
            author=author,
            photos=kwargs.get('photos', []),
            chapters=kwargs.get('chapters', []),
            series=kwargs.get('series'),
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


class Chapter(FantasyModel):
    title: str
    ordering: int
    book: Book

    _db_table = tbl.chapters

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Chapter':
        table = cls._db_table if alias is None else alias
        book = kwargs['book']
        return cls(
            id=row[table.c.id],
            title=row[table.c.title],
            ordering=row[table.c.ordering],
            book=book,
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


class Author(FantasyModel):
    name: str
    date_of_birth: datetime.date
    date_of_death: Optional[datetime.date]
    books: List[Book]
    photos: List[Photo]

    _db_table = tbl.authors

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Author':
        table = cls._db_table if alias is None else alias
        return cls(
            id=row[table.c.id],
            name=row[table.c.name],
            date_of_birth=row[table.c.date_of_birth],
            date_of_death=row[table.c.date_of_death],
            books=[],
            photos=[],
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


class Series(FantasyModel):
    title: str
    books: List[Book]
    photos: List[Photo]

    _db_table = tbl.series

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Series':
        table = cls._db_table if alias is None else alias
        return cls(
            id=row[table.c.id],
            title=row[table.c.title],
            books=[],
            photos=[],
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


class Store(FantasyModel):
    name: str
    books: List[Book]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]

    _db_table = tbl.stores

    @classmethod
    def from_row(cls, row: RowProxy, alias: Optional[sa.Table] = None, **kwargs) -> 'Store':
        table = cls._db_table if alias is None else alias
        books = kwargs.get('books', [])
        return cls(
            id=row[table.c.id],
            name=row[table.c.name],
            books=books,
            created_at=row[table.c.created_at],
            updated_at=row[table.c.updated_at],
        )


Book.update_forward_refs()
Photo.update_forward_refs()
