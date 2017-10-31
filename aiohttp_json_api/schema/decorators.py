#!/usr/bin/env python3

"""
Schema decorators
=================

This module contains some decorators, which can be used instead of the
descriptors on the :class:`~aiohttp_json_api.schema.base_fields.BaseField`
class.

.. todo::

    Allow to define a *getter*, ..., *includer* for multiple fields::

        @includes("author", "comments")
        def include_all(self, article, **kargs):
            return (article.author, article.comments)

        @validates("a", "b")
        def validate_a_and_b(self, a, spa, b, spb, **kargs):
            if a > b:
                raise InvalidValue("a must be less than b", source_pointer=spa)
            return None

.. todo::

    Use convention over configuration::

        @gets("author")
        def get_author(self, article, **kargs):
            return article.author_id

        # Should be the same as

        def get_author(self, article, **kargs):
            return article.author_id
"""
import functools
from enum import Enum

from .common import Step, Event

__all__ = (
    'Tag',
    'gets',
    'sets',
    'updates',
    'validates',
    'adds',
    'removes',
    'includes',
    'queries'
)


class Tag(Enum):
    GET = 'get'
    SET = 'set'
    VALIDATE = 'validate'
    ADD = 'add'
    REMOVE = 'remove'
    INCLUDE = 'include'
    QUERY = 'query'


def tag_processor(tag, callee, **kwargs):
    """
    Tags decorated processor function to be picked up later.

    .. note::
        Currently ony works with functions and instance methods. Class and
        static methods are not supported.

    :return: Decorated function if supplied, else this decorator with its args
        bound.
    """
    # Allow using this as either a decorator or a decorator factory.
    if callee is None:
        return functools.partial(tag_processor, tag, **kwargs)

    try:
        processing_tags = callee.__processing_tags__
    except AttributeError:
        callee.__processing_tags__ = processing_tags = set()
    # Also save the kwargs for the tagged function on
    # __processing_kwargs__, keyed by (<tag_name>, <pass_many>)
    try:
        processing_kwargs = callee.__processing_kwargs__
    except AttributeError:
        callee.__processing_kwargs__ = processing_kwargs = {}

    field_key = kwargs.pop('field_key', None)
    processing_tags.add((tag, field_key))
    processing_kwargs[(tag, field_key)] = kwargs

    return callee


def gets(field_key):
    """
    Decorator for marking the getter of a field::

        class Article(BaseSchema):

            title = String()

            @gets("title")
            def get_title(self, article):
                return article.get_title()

    A field can have at most **one** getter.

    :arg str field_key:
        The key of the field.
    """
    return tag_processor(Tag.GET, None, field_key=field_key)


def sets(field_key):
    """
    Decorator for marking the setter of a field::

        class Article(BaseSchema):

            title = String()

            @sets("title")
            def update_title(self, article, title, sp):
                article.set_title(title)
                return None

    A field can have at most **one** updater.

    :arg str field_key:
        The key of the field.
    """
    return tag_processor(Tag.SET, None, field_key=field_key)


#: Alias for :func:`sets`.
updates = sets


def validates(field_key,
              step: Step = Step.AFTER_DESERIALIZATION,
              on: Event = Event.ALWAYS):
    """
    Decorator for adding a validator::

        class Article(BaseSchema):

            created_at = DateTime()

            @validates("created_at")
            def validate_created_at(self, data, sp, context):
                if created_at > datetime.utcnow():
                    detail = "Must be in the past."
                    raise InvalidValue(detail=detail, source_pointer=sp)

    A field can have as many validators as you want. Note, that they are not
    necessarily called in the order of their definition.

    :arg str field_key:
        The key of the field.
    :arg Step step:
        Must be any Step enumeration value (e.g. Step.BEFORE_DESERIALIZATION)
    :arg Event on:
        Validator's Event
    """
    return tag_processor(Tag.VALIDATE, None,
                         field_key=field_key, step=step, on=on)


def adds(field_key):
    """
    Decorator for marking the adder of a relationship::

        class Article(BaseSchema):

            comments = ToMany()

            @adds("comments")
            def add_comments(self, field, resource, data, sp,
                             context=None, **kwargs):
                for comment in comment:
                    comment.article_id = article.id

    A relationship can have at most **one** adder.

    :arg str field_key:
        The key of the relationship.
    """
    return tag_processor(Tag.ADD, None, field_key=field_key)


def removes(field_key):
    """
    Decorator for marking the remover of a relationship::

        class Article(BaseSchema):

            comments = ToMany()

            @removes("comments")
            def remove_comments(self, field, resource, data, sp,
                                context=None, **kwargs):
                for comment in comment:
                    comment.article_id = None

    A relationship can have at most **one** remover.

    :arg str field_key:
        The key of the relationship.
    """
    return tag_processor(Tag.REMOVE, None, field_key=field_key)


def includes(field_key):
    """
    Decorator for marking the includer of a relationship::

        class Article(BaseSchema):

            author = ToOne()

            @includes("author")
            def include_author(self, field, resources, context, **kwargs):
                return article.load_author()

    A field can have at most **one** includer.

    .. hint::

        The includer should receive list of all resources related to request.
        This able to make one request for all related includes at each step
        of recursively fetched compound documents.
        Look at :func:`~aiohttp_json_api.utils.get_compound_documents`
        for more details about how it works.

    :arg str field_key:
        The name of the relationship.
    """
    return tag_processor(Tag.INCLUDE, None, field_key=field_key)


def queries(field_key):
    """
    Decorator for marking the function used to query the resources in a
    relationship::

        class Article(BaseSchema):

            comments = ToMany()

            @queries("comments")
            def query_comments(self, article_id, **kargs):
                pass

    A field can have at most **one** query method.

    .. todo::

        Add an example.

    :arg str field_key:
        The name of the relationship.
    """
    return tag_processor(Tag.QUERY, None, field_key=field_key)
