"""
Request context
===============
"""

import json
import re
from collections import OrderedDict
from enum import Enum
from typing import Optional, Tuple, MutableMapping, Any, Union

from aiohttp import web

from .const import JSONAPI
from .errors import HTTPBadRequest
from .log import logger
from .schema import Schema
from .schema.common import Event

FILTER_KEY = re.compile(r"filter\[(?P<field>\w[-\w_]*)\]")
FILTER_VALUE = re.compile(r"(?P<name>[a-z]+):(?P<rule>.*)")
FIELDS_RE = re.compile(r"fields\[(?P<name>\w[-\w_]*)\]")


class SortDirection(Enum):
    ASC = '+'
    DESC = '-'


class RequestContext:
    def __init__(self, request: web.Request, resource_type: str = None):
        self._pagination = None
        self._resource_type = resource_type
        self.request = request
        self.filters = self.parse_request_filters(request)
        self.fields = self.parse_request_fields(request)
        self.include = self.parse_request_includes(request)
        self.sorting = self.parse_request_sorting(request)
        if self.request.method in Event.__members__:
            self.event = Event[self.request.method]
        else:
            self.event = None

    @property
    def schema(self) -> Optional[Schema]:
        registry = self.request.app[JSONAPI]['registry']
        return registry.get(self._resource_type, None)

    @property
    def pagination(self):
        if self._pagination is not None:
            return self._pagination

        if self.schema is not None:
            pagination_type = self.schema.opts.get('pagination')
            if pagination_type:
                self._pagination = pagination_type(self.request)
                return self._pagination

        return None

    @staticmethod
    def parse_request_filters(
        request: web.Request) -> MutableMapping[Tuple[str, str], Any]:
        """
        .. hint::

            Please note, that the *filter* strategy is not defined by the
            JSON API specification and depends on the implementation.
            If you want to use another filter strategy,
            feel free to **override** this method.

        Returns a OrderedDict with tuples (field, name) as keys
        and rule as values. Rule value is JSON deserialized from query string.

        Filters can be applied using the query string.

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=endswith:"Simpson"')
            >>> RequestContext.parse_request_filters(request)
            OrderedDict([(('name', 'endswith'), 'Simpson')])

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=endswith:"Simpson"&filter[name]=in:["Some","Names"]')
            >>> RequestContext.parse_request_filters(request)
            OrderedDict([(('name', 'endswith'), 'Simpson'), (('name', 'in'), ['Some', 'Names'])])

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=in:["Homer Simpson", "Darth Vader"]')
            >>> RequestContext.parse_request_filters(request)
            OrderedDict([(('name', 'in'), ['Homer Simpson', 'Darth Vader'])])

            >>> request = make_mocked_request('GET', '/api/User/?filter[email]=startswith:"lisa"&filter[age]=lt:20')
            >>> RequestContext.parse_request_filters(request)
            OrderedDict([(('email', 'startswith'), 'lisa'), (('age', 'lt'), 20)])

        The general syntax is::

            "?filter[field]=name:rule"

        where *rule* is a JSON value.

        :raises HTTPBadRequest:
            If the rule of a filter is not a JSON object.
        :raises HTTPBadRequest:
            If a filtername contains other characters than *[a-z]*.
        """
        filters = OrderedDict()
        for key, value in request.query.items():
            key_match = re.fullmatch(FILTER_KEY, key)
            value_match = re.fullmatch(FILTER_VALUE, value)

            # If the key indicates a filter, but the value is not correct
            # formatted.
            if key_match and not value_match:
                field = key_match.group('field')
                raise HTTPBadRequest(
                    detail="The filter '{}' "
                           "is not correct applied.".format(field),
                    source_parameter=key
                )

            # The key indicates a filter and the filter name exists.
            elif key_match and value_match:
                field = key_match.group('field')
                name = value_match.group('name')
                rule = value_match.group('rule')
                try:
                    rule = json.loads(rule)
                except Exception as err:
                    logger.debug(err, exc_info=False)
                    raise HTTPBadRequest(
                        detail="The rule '{}' "
                               "is not JSON serializable".format(rule),
                        source_parameter=key
                    )
                filters[(field, name)] = rule
        return filters

    @staticmethod
    def parse_request_fields(
        request: web.Request) -> MutableMapping[str, Tuple[str, ...]]:
        """
        The fields, which should be included in the response (sparse fieldset).

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request
            >>> request = make_mocked_request('GET', '/api/User?fields[User]=email,name&fields[Post]=comments')
            >>> RequestContext.parse_request_fields(request)
            OrderedDict([('User', ('email', 'name')), ('Post', ('comments',))])

        :seealso: http://jsonapi.org/format/#fetching-sparse-fieldsets
        """
        fields = OrderedDict()
        for key, value in request.query.items():
            match = re.fullmatch(FIELDS_RE, key)
            if match:
                typename = match.group('name')
                type_fields = tuple(item.strip()
                                    for item in value.split(',')
                                    if item.strip())

                fields[typename] = type_fields
        return fields

    @staticmethod
    def parse_request_includes(request: web.Request) -> Tuple[Tuple[str], ...]:
        """
        Returns the names of the relationships, which should be included into
        the response.

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request
            >>> request = make_mocked_request('GET', '/api/Post?include=author,comments.author')
            >>> RequestContext.parse_request_includes(request)
            (('author',), ('comments', 'author'))

        :seealso: http://jsonapi.org/format/#fetching-includes
        """
        include = request.query.get('include', '')
        return tuple(
            tuple(path.split('.')) for path in include.split(',') if path
        )

    @staticmethod
    def parse_request_sorting(
        request: web.Request) -> MutableMapping[Tuple[str, ...], SortDirection]:
        """
        Returns a mapping with tuples as keys, and values with SortDirection,
        describing how the output should be sorted.

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request
            >>> request = make_mocked_request('GET', '/api/Post?sort=name,-age,+comments.count')
            >>> RequestContext.parse_request_sorting(request)
            OrderedDict([(('name',), <SortDirection.ASC: '+'>), (('age',), <SortDirection.DESC: '-'>), (('comments', 'count'), <SortDirection.ASC: '+'>)])

        :seealso: http://jsonapi.org/format/#fetching-sorting
        """
        sort_in_query = request.query.get('sort')
        sort_in_query = sort_in_query.split(',') if sort_in_query else list()

        sort = OrderedDict()

        for field in sort_in_query:
            if field[0] == '+' or field[0] == '-':
                direction = SortDirection(field[0])
                field = field[1:]
            else:
                direction = SortDirection.ASC

            field = tuple(e.strip() for e in field.split('.'))
            sort[field] = direction

        return sort

    def has_filter(self, field: str, name: str) -> bool:
        """
        Returns true, if the filter *name* has been applied at least once
        on the *field*.

        :arg str field:
            Name of field
        :arg str name:
            Name of filter
        """
        return (field, name) in self.filters

    def get_filter(self, field: str, name: str, default: Any = None) -> Any:
        """
        If the filter *name* has been applied on the *field*, the
        *filter* is returned and *default* otherwise.

        :arg str field:
            Name of field
        :arg str name:
            Name of filter
        :arg Any default:
            A fallback rule value for the filter.
        """
        return self.filters.get((field, name), default)

    def get_order(self, field: Union[str, Tuple[str, ...]],
                  default: SortDirection = SortDirection.ASC) -> SortDirection:
        """
        Checks if a sort criterion (``+`` or ``-``) for the *field* exists
        and returns it.

        :arg Union[str, Tuple[str, ...]] field:
        :arg SortDirection default:
            Returned, if no criterion is set by the request.
        """
        field = tuple(field.split('.')) if isinstance(field, str) else field
        return self.sorting.get(field, default)
