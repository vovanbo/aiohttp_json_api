import datetime
from dataclasses import dataclass
from typing import Optional, List, Union


@dataclass(frozen=True)
class Chapter:
    id: int
    title: str
    ordering: int
    book: 'Book'
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    date_published: datetime.datetime
    author: 'Author'
    series: Optional['Series']
    photos: List['Photo']
    chapters: List['Chapter']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]


@dataclass(frozen=True)
class Author:
    id: int
    name: str
    date_of_birth: datetime.datetime
    date_of_death: Optional[datetime.datetime]
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]
    books: List['Book']
    photos: List['Photo']


@dataclass(frozen=True)
class Series:
    id: int
    title: str
    books: List['Book']
    photos: List['Photo']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]


@dataclass(frozen=True)
class Store:
    id: int
    name: str
    books: List['Book']
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]


ImageableType = Union[Author, Book, Series]


@dataclass(frozen=True)
class Photo:
    id: int
    title: str
    uri: str
    imageable: ImageableType
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime]


