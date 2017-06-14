"""
Pagination
==========

This module contains helper for the pagination feature:
http://jsonapi.org/format/#fetching-pagination

We have built-in support for:

*   *limit*, *offset* based pagination (:class:`LimitOffset`),
*   *number*, *size* based pagination (:class:`NumberSize`),
*   and *cursor* based pagination (:class:`Cursor`).

All helpers have a similar interface. Here is an example for the
:class:`NumberSize` pagination:

.. code-block:: python3

    >>> p = NumberSize(
    ...     request,
    ...     number=2,
    ...     size=25,
    ...     total_resources=106
    )
    >>> p.links()
    {
    'first': 'http://example.org/api/Article/?page%5Bsize%5D=25&sort=date_added&page%5Bnumber%5D=0',
    'last': 'http://example.org/api/Article/?page%5Bsize%5D=25&sort=date_added&page%5Bnumber%5D=4',
    'next': 'http://example.org/api/Article/?page%5Bsize%5D=25&sort=date_added&page%5Bnumber%5D=3',
    'prev': 'http://example.org/api/Article/?page%5Bsize%5D=25&sort=date_added&page%5Bnumber%5D=1',
    'self': 'http://example.org/api/Article/?page%5Bsize%5D=25&sort=date_added&page%5Bnumber%5D=2'
    }
    >>> p.meta()
    {
    'page-number': 2,
    'page-size': 25,
    'total-pages': 4,
    'total-resources': 106
    }
"""

import re
import typing

import yarl
from aiohttp import web
from boltons.typeutils import make_sentinel

from .errors import HTTPBadRequest
from .log import logger

__all__ = (
    'DEFAULT_LIMIT',
    'BasePagination',
    'LimitOffset',
    'NumberSize',
    'Cursor'
)

#: The default number of resources on a page.
DEFAULT_LIMIT = 25


class BasePagination:
    def __init__(self, request: web.Request):
        self.request = request

    @classmethod
    def from_request(cls, request: web.Request, **kwargs) -> 'BasePagination':
        """
        Checks if the needed pagination parameters are present in the request
        and if so, a new pagination instance with these parameters is returned
        and *None* otherwise.
        """
        raise NotImplementedError()

    @property
    def url(self) -> yarl.URL:
        return self.request.url

    def meta(self) -> typing.MutableMapping:
        """
        **Must be overridden.**

        A dictionary, which must be included in the top-level *meta object*.
        """
        return dict()

    def links(self) -> typing.MutableMapping:
        """
        **Must be overridden.**

        A dictionary, which must be included in the top-level *links object*. It
        contains these keys:

        *   *self*
            The link to the current page

        *   *first*
            The link to the first page

        *   *last*
            The link to the last page

        *   *prev*
            The link to the previous page (only set, if a previous page exists)

        *   *next*
            The link to the next page (only set, if a next page exists)
        """
        raise NotImplementedError()

    def page_link(self, **kwargs) -> str:
        """
        Uses the :attr:`uri` and replaces the *page* query parameters with the
        values in *pagination*.

        .. code-block:: python3

            pager.page_link({"offset": 10, "limit": 5})
            pager.page_link({"number": 10, "size": 5})
            pager.page_link({"cursor": 1, "limit": 5})
            # ...

        :arg dict pagination:
            Query parameters for the pagination.
        :rtype: str
        :returns:
            The url to the page
        """
        query = self.request.query.copy()
        query.update({
            f'page[{key}]': str(value)
            for key, value in kwargs.items()
        })

        return str(self.request.url.update_query(query))


class LimitOffset(BasePagination):
    """
    Implements a pagination based on *limit* and *offset* values.

    .. code-block:: text

        /api/Article/?sort=date_added&page[limit]=5&page[offset]=10

    :arg int limit:
        The number of resources on a page.
    :arg int offset:
        The offset, which leads to the current page.
    :arg int total_resources:
        The total number of resources in the collection.
    """
    def __init__(self, request: web.Request, total_resources: int = 0,
                 offset: int = 0, limit: int = DEFAULT_LIMIT):
        super(LimitOffset, self).__init__(request)
        self.total_resources = total_resources
        self.offset = offset
        self.limit = limit

    @classmethod
    def from_request(cls, request: web.Request,
                     total_resources: int = 0,
                     default_limit: int = DEFAULT_LIMIT,
                     **kwargs) -> 'LimitOffset':
        """
        Extracts the current pagination values (*limit* and *offset*) from the
        request's query parameters.

        :arg ~aiohttp.web.Request request:
        :arg int total_resources:
            The total number of resources in the collection.
        :arg int default_limit:
            If the request's query string does not contain a limit,
            we will use this one as fallback value.
        """
        limit = request.query.get('page[limit]')
        if limit is not None and (not limit.isdigit() or int(limit) <= 0):
            raise HTTPBadRequest(
                detail='The limit must be an integer > 0.',
                source_parameter='page[limit]'
            )
        if limit is None:
            limit = default_limit

        offset = request.query.get('page[offset]')
        if offset is not None and (not offset.isdigit() or int(offset) < 0):
            raise HTTPBadRequest(
                detail='The offset must be an integer >= 0.',
                source_parameter='page[offset]'
            )
        if offset is None:
            offset = 0

        if offset % limit != 0:
            logger.warning('The offset is not dividable by the limit.')
        return cls(request=request,
                   limit=limit,
                   offset=offset,
                   total_resources=total_resources)

    def links(self) -> typing.MutableMapping:
        d = {
            'self': self.page_link(limit=self.limit, offset=self.offset),
            'first': self.page_link(limit=self.limit, offset=0),
            'last': self.page_link(
                limit=self.limit,
                offset=int((self.total_resources - 1) / self.limit) * self.limit
            )
        }
        if self.offset > 0:
            d['prev'] = self.page_link(
                limit=self.limit,
                offset=max(self.offset - self.limit, 0)
            )
        if self.offset + self.limit < self.total_resources:
            d['next'] = self.page_link(
                limit=self.limit,
                offset=self.offset + self.limit
            )
        return d

    def meta(self) -> typing.MutableMapping:
        """
        Returns a dictionary with

        *   *total-resources*
            The total number of resources in the collection
        *   *page-limit*
            The number of resources on a page
        *   *page-offset*
            The offset of the current page
        """
        return {
            'total-resources': self.total_resources,
            'page-limit': self.limit,
            'page-offset': self.offset
        }


class NumberSize(BasePagination):
    """
    Implements a pagination based on *number* and *size* values.

    .. code-block:: text

        /api/Article/?sort=date_added&page[size]=5&page[number]=10

    :arg ~aiohttp.web.Request request:
    :arg int number:
        The number of the current page.
    :arg int size:
        The number of resources on a page.
    :arg int total_resources:
        The total number of resources in the collection.
    """
    def __init__(self, request: web.Request, total_resources, number, size):
        super(NumberSize, self).__init__(request)
        self.total_resources = total_resources
        self.number = number
        self.size = size

    @classmethod
    def from_request(cls, request: web.Request,
                     total_resources: int = 0,
                     default_size: int = DEFAULT_LIMIT,
                     **kwargs) -> 'NumberSize':
        """
        Extracts the current pagination values (*size* and *number*) from the
        request's query parameters.

        :arg ~aiohttp.web.Request request:
        :arg int total_resources:
            The total number of resources in the collection.
        :arg int default_size:
            If the request's query string does not contain the page size
            parameter, we will use this one as fallback.
        """
        number = request.query.get('page[number]')
        if number is not None and (not number.isdigit() or int(number) < 0):
            raise HTTPBadRequest(
                detail='The number must an integer >= 0.',
                source_parameter='page[number]'
            )
        number = int(number) if number else 0

        size = request.query.get('page[size]')
        if size is not None and (not size.isdigit() or int(size) <= 0):
            raise HTTPBadRequest(
                detail='The size must be an integer > 0.',
                source_parameter='page[size]'
            )
        if size is None:
            size = default_size
        size = int(size) if size else 0

        return cls(request=request,
                   number=number,
                   size=size,
                   total_resources=total_resources)

    @property
    def limit(self) -> int:
        """
        The limit, based on the page :attr:`size`.
        """
        return self.size

    @property
    def offset(self) -> int:
        """
        The offset, based on the page :attr:`size` and :attr:`number`.
        """
        return self.size * self.number

    @property
    def last_page(self) -> int:
        """
        The number of the last page.
        """
        return int((self.total_resources - 1) / self.size)

    def links(self) -> typing.MutableMapping:
        d = {
            'self': self.page_link(number=self.number, size=self.size),
            'first': self.page_link(number=0, size=self.size),
            'last': self.page_link(number=self.last_page, size=self.size)
        }
        if self.number > 0:
            d['prev'] = self.page_link(number=self.number - 1, size=self.size)
        if self.number < self.last_page:
            d['next'] = self.page_link(number=self.number + 1, size=self.size)
        return d

    def meta(self) -> typing.MutableMapping:
        """
        Returns a dictionary with

        *   *total-resources*
            The total number of resources in the collection
        *   *last-page*
            The index of the last page
        *   *page-number*
            The number of the current page
        *   *page-size*
            The (maximum) number of resources on a page
        """
        return {
            'total-resources': self.total_resources,
            'last-page': self.last_page,
            'page-number': self.number,
            'page-size': self.size
        }


class Cursor(BasePagination):
    """
    Implements a (generic) approach for a cursor based pagination.

    .. code-block:: text

        /api/Article/?sort=date_added&page[limit]=5&page[cursor]=19395939020

    :arg ~aiohttp.web.Request request:
    :arg int limit:
        The number of resources on a page
    :arg cursor:
        The cursor to the current page
    :arg prev_cursor:
        The cursor to the previous page
    :arg next_cursor:
        The cursor to the next page
    """
    # The cursor to the first page
    FIRST = make_sentinel(var_name='jsonapi:first')
    # The cursor to the last page
    LAST = make_sentinel(var_name='jsonapi:last')

    def __init__(self, request: web.Request, cursor, prev_cursor=None,
                 next_cursor=None, limit: int = DEFAULT_LIMIT):
        super(Cursor, self).__init__(request)
        self.cursor = make_sentinel(var_name=str(cursor))
        self.prev_cursor = \
            make_sentinel(var_name=str(prev_cursor)) if prev_cursor else None
        self.next_cursor = \
            make_sentinel(var_name=str(next_cursor)) if next_cursor else None
        self.limit = limit

    @classmethod
    def from_request(cls, request: web.Request,
                     default_limit: int = DEFAULT_LIMIT,
                     cursor_re: typing.Optional[str] = None) -> 'Cursor':
        """
        Extracts the current pagination values (*limit* and *cursor*) from the
        request's query parameters.

        :arg ~aiohttp.web.Request request:
        :arg int default_limit:
             If the request’s query string does not contain a limit,
             we will use this one as fallback value.
        :arg str cursor_re:
            The cursor in the query string must match this regular expression.
            If it doesn't, an exception is raised.
        """
        cursor = request.query.get('page[cursor]', cls.FIRST)
        if cursor is not None and \
            cursor_re and not re.fullmatch(cursor_re, cursor):
            raise HTTPBadRequest(
                detail='The cursor is invalid.',
                source_parameter='page[cursor]'
            )

        limit = request.query.get('page[limit]')
        if limit is not None and ((not limit.isdigit()) or int(limit) <= 0):
            raise HTTPBadRequest(
                detail='The limit must be an integer > 0.',
                source_parameter='page[limit]'
            )
        if limit is None:
            limit = default_limit
        return cls(request, limit, cursor)

    def links(self, prev_cursor=None,
              next_cursor=None) -> typing.MutableMapping:
        """
        :arg str prev_cursor:
            The cursor to the previous page.
        :arg str next_cursor:
            The cursor to the next page.
        """
        if prev_cursor is None:
            prev_cursor = self.prev_cursor
        if next_cursor is None:
            next_cursor = self.next_cursor

        d = {
            'self': self.page_link(cursor=str(self.cursor), limit=self.limit),
            'first': self.page_link(cursor=str(self.FIRST), limit=self.limit),
            'last': self.page_link(cursor=str(self.LAST), limit=self.limit)
        }
        if next_cursor is not None:
            d['next'] = self.page_link(cursor=str(next_cursor),
                                       limit=self.limit)
        if prev_cursor is not None:
            d['prev'] = self.page_link(cursor=str(prev_cursor),
                                       limit=self.limit)
        return d

    def meta(self) -> typing.MutableMapping:
        """
        Returns a dictionary with

        *   *page-limit*
            The number of resources per page
        """
        return {'page-limit': self.limit}
