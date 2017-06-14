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

__all__ = [
    "gets",
    "sets",
    "updates",
    "validates",
    "adds",
    "removes",
    "includes",
    "queries"
]

from .common import Step, Event


def gets(field):
    """
    Decorator for marking the getter of a field::

        class Article(Schema):

            title = String()

            @gets("title")
            def get_title(self, article):
                return article.get_title()

    A field can have at most **one** getter.

    :arg str field:
        The key of the field.
    """
    def decorator(f):
        f.japi_getter = {"field": field}
        return f
    return decorator


def sets(field):
    """
    Decorator for marking the setter of a field::

        class Article(Schema):

            title = String()

            @sets("title")
            def update_title(self, article, title, sp):
                article.set_title(title)
                return None

    A field can have at most **one** updater.

    :arg str field:
        The key of the field.
    """
    def decorator(f):
        f.japi_setter = {"field": field}
        return f
    return decorator


#: Alias for :func:`sets`.
updates = sets


def validates(field, step: Step = Step.POST_DECODE, on: Event = Event.ALWAYS):
    """
    Decorator for adding a validator::

        class Article(Schema):

            created_at = DateTime()

            @validates("created_at")
            def validate_created_at(self, created_at, sp):
                if created_at > datetime.utcnow():
                    detail = "Must be in the past."
                    raise InvalidValue(detail=detail, source_pointer=sp)
                return None

    A field can have as many validators as you want. Note, that they are not
    necessarily called in the order of their definition.

    :arg str field:
        The key of the field.
    :arg Step step:
        Must be either *pre-decode* or *post-decode*.
    :arg str context:
        Must be either *always*, *never*, *on_create* or *on_update*.
    """
    def decorator(f):
        f.japi_validator = {"field": field, "step": step, "on": on}
        return f
    return decorator


def adds(field):
    """
    Decorator for marking the adder of a relationship::

        class Article(Schema):

            comments = ToMany()

            @adds("comments")
            def add_comments(self, article, comments, sp):
                for comment in comment:
                    comment.article_id = article.id
                return None

    A relationship can have at most **one** adder.

    :arg str field:
        The key of the relationship.
    """
    def decorator(f):
        f.japi_adder = {"field": field}
        return f
    return decorator


def removes(field):
    """
    Decorator for marking the remover of a relationship::

        class Article(Schema):

            comments = ToMany()

            @removes("comments")
            def remove_comments(self, article, comments, sp=):
                for comment in comment:
                    comment.article_id = None
                return None

    A relationship can have at most **one** remover.

    :arg str field:
        The key of the relationship.
    """
    def decorator(f):
        f.japi_remover = {"field": field}
        return f
    return decorator


def includes(field):
    """
    Decorator for marking the includer of a relationship::

        class Article(Schema):

            author = ToOne()

            @includes("author")
            def include_author(self, article):
                return article.load_author()

    A field can have at most **one** includer.

    .. hint::

        The includer should not make any database requests for a
        better performance. The included relationships should be
        loaded in the same request as the resource.

    :arg str field:
        The name of the relationship.
    """
    def decorator(f):
        f.japi_includer = {"field": field}
        return f
    return decorator


def queries(field):
    """
    Decorator for marking the function used to query the resources in a
    relationship::

        class Article(Schema):

            comments = ToMany()

            @queries("comments")
            def query_comments(self, article_id, **kargs):
                pass

    A field can have at most **one** query method.

    .. todo::

        Add an example.

    :arg str field:
        The name of the relationship.
    """
    def decorator(f):
        f.japi_query = {"field": field}
        return f
    return decorator
