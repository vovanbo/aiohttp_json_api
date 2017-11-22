# coding: utf-8
from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, MetaData,
    Table, Text, text
)

metadata = MetaData()

authors = Table(
    'authors', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Text, nullable=False),
    Column('date_of_birth', Date, nullable=False),
    Column('date_of_death', Date),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("name <> ''::text")
)

books = Table(
    'books', metadata,
    Column('id', Integer, primary_key=True),
    Column('author_id', ForeignKey('authors.id'), nullable=False),
    Column('series_id', ForeignKey('series.id')),
    Column('date_published', Date, nullable=False),
    Column('title', Text, nullable=False),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("title <> ''::text")
)

books_stores = Table(
    'books_stores', metadata,
    Column('book_id', ForeignKey('books.id'), nullable=False),
    Column('store_id', ForeignKey('stores.id'), nullable=False)
)

chapters = Table(
    'chapters', metadata,
    Column('id', Integer, primary_key=True),
    Column('book_id', ForeignKey('books.id'), nullable=False),
    Column('title', Text, nullable=False),
    Column('ordering', Integer, nullable=False),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("title <> ''::text")
)

photos = Table(
    'photos', metadata,
    Column('id', Integer, primary_key=True),
    Column('title', Text, nullable=False),
    Column('uri', Text, nullable=False),
    Column('imageable_id', Integer, nullable=False),
    Column('imageable_type', Text, nullable=False),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("imageable_type <> ''::text"),
    CheckConstraint("title <> ''::text"),
    CheckConstraint("uri <> ''::text")
)

series = Table(
    'series', metadata,
    Column('id', Integer, primary_key=True),
    Column('title', Text, nullable=False),
    Column('photo_id', ForeignKey('photos.id'), nullable=False),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("title <> ''::text")
)

stores = Table(
    'stores', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', Text, nullable=False),
    Column('created_at', DateTime, nullable=False,
           server_default=text("CURRENT_TIMESTAMP")),
    Column('updated_at', DateTime),
    CheckConstraint("name <> ''::text")
)
