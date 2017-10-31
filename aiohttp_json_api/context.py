"""Request context."""

import json
import re
from collections import OrderedDict, namedtuple
from enum import Enum
from typing import Optional, Tuple, MutableMapping, Any, Union

import inflection
from aiohttp import web
from multidict import MultiDict

from .const import JSONAPI
from .errors import HTTPBadRequest
from .log import logger
from .schema import BaseSchema
from .schema.common import Event

FILTER_KEY = re.compile(r"filter\[(?P<field>\w[-\w_]*)\]")
FILTER_VALUE = re.compile(r"(?P<name>[a-z]+):(?P<value>.*)")
FIELDS_RE = re.compile(r"fields\[(?P<name>\w[-\w_]*)\]")


FilterRule = namedtuple('FilterRule', ('name', 'value'))


class SortDirection(Enum):
    ASC = '+'
    DESC = '-'


RequestFilters = MutableMapping[str, FilterRule]
RequestFields = MutableMapping[str, Tuple[str, ...]]
RequestIncludes = Tuple[Tuple[str, ...], ...]
RequestSorting = MutableMapping[Tuple[str, ...], SortDirection]


class RequestContext:
    inflect = inflection.underscore

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

        logger.debug('Request context info:\n'
                     'Filters: %s\n'
                     'Fields: %s\n'
                     'Includes: %s\n'
                     'Sorting: %s\n'
                     'Event: %s',
                     self.filters, self.fields, self.include, self.sorting,
                     self.event)

    @property
    def schema(self) -> Optional[BaseSchema]:
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

    @classmethod
    def convert_field_name(cls, field_name):
        return cls.inflect(field_name) \
            if cls.inflect is not None \
            else field_name

    @classmethod
    def parse_request_filters(cls, request: web.Request) -> RequestFilters:
        """
        .. hint::

            Please note, that the *filter* strategy is not defined by the
            JSON API specification and depends on the implementation.
            If you want to use another filter strategy,
            feel free to **override** this method.

        Returns a MultiDict with field names as keys and rules as values.
        Rule value is JSON deserialized from query string.

        Filters can be applied using the query string.

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=endswith:"Simpson"')
            >>> RequestContext.parse_request_filters(request)
            <MultiDict('name': FilterRule(name='endswith', value='Simpson'))>

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=endswith:"Simpson"&filter[name]=in:["Some","Names"]')
            >>> RequestContext.parse_request_filters(request)
            <MultiDict('name': FilterRule(name='endswith', value='Simpson'), 'name': FilterRule(name='in', value=['Some', 'Names']))>

            >>> request = make_mocked_request('GET', '/api/User/?filter[name]=in:["Homer Simpson", "Darth Vader"]')
            >>> RequestContext.parse_request_filters(request)
            <MultiDict('name': FilterRule(name='in', value=['Homer Simpson', 'Darth Vader']))>

            >>> request = make_mocked_request('GET', '/api/User/?filter[some-field]=startswith:"lisa"&filter[another-field]=lt:20')
            >>> RequestContext.parse_request_filters(request)
            <MultiDict('some_field': FilterRule(name='startswith', value='lisa'), 'another_field': FilterRule(name='lt', value=20))>

        The general syntax is::

            "?filter[field]=name:rule"

        where *rule* is a JSON value.

        :raises HTTPBadRequest:
            If the rule of a filter is not a JSON object.
        :raises HTTPBadRequest:
            If a filter name contains invalid characters.
        """
        filters = MultiDict()

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
                value = value_match.group('value')
                try:
                    value = json.loads(value)
                except Exception as err:
                    logger.debug(err, exc_info=False)
                    raise HTTPBadRequest(
                        detail="The value '{}' "
                               "is not JSON serializable".format(value),
                        source_parameter=key
                    )
                filters.add(cls.convert_field_name(field),
                            FilterRule(name=name, value=value))

        return filters

    @classmethod
    def parse_request_fields(cls, request: web.Request) -> RequestFields:
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
                fields[typename] = tuple(
                    cls.convert_field_name(item.strip())
                    for item in value.split(',')
                    if item.strip()
                )

        return fields

    @classmethod
    def parse_request_includes(cls, request: web.Request) -> RequestIncludes:
        """
        Returns the names of the relationships, which should be included into
        the response.

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request
            >>> request = make_mocked_request('GET', '/api/Post?include=author,comments.author,some-field.nested')
            >>> RequestContext.parse_request_includes(request)
            (('author',), ('comments', 'author'), ('some_field', 'nested'))

        :seealso: http://jsonapi.org/format/#fetching-includes
        """
        return tuple(
            tuple(cls.convert_field_name(p) for p in path.split('.'))
            for path in request.query.get('include', '').split(',') if path
        )

    @classmethod
    def parse_request_sorting(cls, request: web.Request) -> RequestSorting:
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
        sort = OrderedDict()

        if 'sort' not in request.query:
            return sort

        direction = SortDirection.ASC

        for field in request.query.get('sort').split(','):
            if field.startswith(('+', '-')):
                direction = SortDirection(field[0])
                field = field[1:]

            field = tuple(cls.convert_field_name(e.strip())
                          for e in field.split('.'))
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
