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
import typing
from abc import ABC, abstractmethod

import yarl
from aiohttp import web
import trafaret as t

from .errors import HTTPBadRequest
from .log import logger
from .helpers import make_sentinel

__all__ = (
    'DEFAULT_LIMIT',
    'PaginationABC',
    'LimitOffset',
    'NumberSize',
    'Cursor'
)

#: The default number of resources on a page.
DEFAULT_LIMIT = 25


class PaginationABC(ABC):
    def __init__(self, request: web.Request):
        self.request = request

    @property
    def url(self) -> yarl.URL:
        return self.request.url

    @abstractmethod
    def meta(self) -> typing.MutableMapping:
        """
        **Must be overridden.**

        A dictionary, which must be included in the top-level *meta object*.
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

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
            'page[{}]'.format(key): str(value)
            for key, value in kwargs.items()
        })

        return str(self.request.url.update_query(query))


class LimitOffset(PaginationABC):
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
    def __init__(self, request: web.Request, total_resources: int = 0):
        super(LimitOffset, self).__init__(request)
        self.total_resources = total_resources

        self.limit = request.query.get('page[limit]', DEFAULT_LIMIT)
        try:
            self.limit = t.Int(gt=0).check(self.limit)
        except t.DataError:
            raise HTTPBadRequest(
                detail='The limit must be an integer > 0.',
                source_parameter='page[limit]'
            )

        self.offset = request.query.get('page[offset]', 0)
        try:
            self.offset = t.Int(gte=0).check(self.offset)
        except t.DataError:
            raise HTTPBadRequest(
                detail='The offset must be an integer >= 0.',
                source_parameter='page[offset]'
            )

        if self.offset % self.limit != 0:
            logger.warning('The offset is not dividable by the limit.')

    def links(self) -> typing.MutableMapping:
        result = {
            'self': self.page_link(limit=self.limit, offset=self.offset),
            'first': self.page_link(limit=self.limit, offset=0),
            'last': self.page_link(
                limit=self.limit,
                offset=int((self.total_resources - 1) / self.limit) * self.limit
            )
        }
        if self.offset > 0:
            result['prev'] = self.page_link(
                limit=self.limit,
                offset=max(self.offset - self.limit, 0)
            )
        if self.offset + self.limit < self.total_resources:
            result['next'] = self.page_link(
                limit=self.limit,
                offset=self.offset + self.limit
            )
        return result

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


class NumberSize(PaginationABC):
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
    def __init__(self, request: web.Request, total_resources):
        super(NumberSize, self).__init__(request)
        self.total_resources = total_resources

        self.number = request.query.get('page[number]', 0)
        try:
            self.number = t.Int(gte=0).check(self.number)
        except t.DataError:
            raise HTTPBadRequest(
                detail='The number must an integer >= 0.',
                source_parameter='page[number]'
            )

        self.size = request.query.get('page[size]', DEFAULT_LIMIT)
        try:
            self.size = t.Int(gt=0).check(self.size)
        except t.DataError:
            raise HTTPBadRequest(
                detail='The size must be an integer > 0.',
                source_parameter='page[size]'
            )

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
        result = {
            'self': self.page_link(number=self.number, size=self.size),
            'first': self.page_link(number=0, size=self.size),
            'last': self.page_link(number=self.last_page, size=self.size)
        }
        if self.number > 0:
            result['prev'] = \
                self.page_link(number=self.number - 1, size=self.size)
        if self.number < self.last_page:
            result['next'] = \
                self.page_link(number=self.number + 1, size=self.size)
        return result

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


class Cursor(PaginationABC):
    """
    Implements a (generic) approach for a cursor based pagination.

    .. code-block:: text

        /api/Article/?sort=date_added&page[limit]=5&page[cursor]=19395939020

    :arg ~aiohttp.web.Request request:
    :arg prev_cursor:
        The cursor to the previous page
    :arg next_cursor:
        The cursor to the next page
    :arg str cursor_regex:
        The cursor in the query string must match this regular expression.
        If it doesn't, an exception is raised.
    """
    # The cursor to the first page
    FIRST = make_sentinel(var_name='jsonapi:first')
    # The cursor to the last page
    LAST = make_sentinel(var_name='jsonapi:last')

    def __init__(self, request: web.Request, prev_cursor=None,
                 next_cursor=None, cursor_regex: str = None):
        super(Cursor, self).__init__(request)

        self.cursor = request.query.get('page[cursor]', self.FIRST)
        if isinstance(self.cursor, str):
            if cursor_regex is not None:
                try:
                    self.cursor = t.Regexp(cursor_regex).check(self.cursor)
                except t.DataError:
                    raise HTTPBadRequest(
                        detail='The cursor is invalid.',
                        source_parameter='page[cursor]'
                    )
            self.cursor = make_sentinel(var_name=str(self.cursor))

        self.prev_cursor = \
            make_sentinel(var_name=str(prev_cursor)) if prev_cursor else None
        self.next_cursor = \
            make_sentinel(var_name=str(next_cursor)) if next_cursor else None

        self.limit = request.query.get('page[limit]', DEFAULT_LIMIT)
        try:
            self.limit = t.Int(gt=0).check(self.limit)
        except t.DataError:
            raise HTTPBadRequest(
                detail='The limit must be an integer > 0.',
                source_parameter='page[limit]'
            )

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

        result = {
            'self': self.page_link(cursor=str(self.cursor), limit=self.limit),
            'first': self.page_link(cursor=str(self.FIRST), limit=self.limit),
            'last': self.page_link(cursor=str(self.LAST), limit=self.limit)
        }
        if next_cursor is not None:
            result['next'] = self.page_link(cursor=str(next_cursor),
                                            limit=self.limit)
        if prev_cursor is not None:
            result['prev'] = self.page_link(cursor=str(prev_cursor),
                                            limit=self.limit)
        return result

    def meta(self) -> typing.MutableMapping:
        """
        Returns a dictionary with

        *   *page-limit*
            The number of resources per page
        """
        return {'page-limit': self.limit}
