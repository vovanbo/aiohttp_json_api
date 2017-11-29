"""Request context."""

import json
import re
from collections import OrderedDict
from typing import Any, Optional, Tuple, Union

import inflection
from aiohttp import web
from multidict import MultiDict

from .common import Event, FilterRule, JSONAPI, logger, SortDirection
from .errors import HTTPBadRequest
from .schema import BaseSchema
from .typings import (
    RequestFields, RequestFilters, RequestIncludes, RequestSorting
)


class RequestContext:
    """JSON API request context."""

    FILTER_KEY = re.compile(r"filter\[(?P<field>\w[-\w_]*)\]")
    FILTER_VALUE = re.compile(r"(?P<name>[a-z]+):(?P<value>.*)")
    FIELDS_RE = re.compile(r"fields\[(?P<name>\w[-\w_]*)\]")

    inflect = inflection.underscore

    def __init__(self, request: web.Request,
                 resource_type: str = None) -> None:
        """
        Initialize request context.

        :param request: Request instance
        :param resource_type: Resource type for current request
        """
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
        Parse filters from request query string.

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
        filters = MultiDict()  # type: MultiDict

        for key, value in request.query.items():
            key_match = re.fullmatch(cls.FILTER_KEY, key)
            value_match = re.fullmatch(cls.FILTER_VALUE, value)

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
                    logger.debug(str(err), exc_info=False)
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
        Parse sparse fields from request query string.

        Used for determine fields, which should be included in the response
        (sparse fieldset).

        .. code-block:: python3

            >>> from aiohttp_json_api.context import RequestContext
            >>> from aiohttp.test_utils import make_mocked_request
            >>> request = make_mocked_request('GET', '/api/User?fields[User]=email,name&fields[Post]=comments')
            >>> RequestContext.parse_request_fields(request)
            OrderedDict([('User', ('email', 'name')), ('Post', ('comments',))])

        :seealso: http://jsonapi.org/format/#fetching-sparse-fieldsets
        """
        fields = OrderedDict()  # type: OrderedDict

        for key, value in request.query.items():
            match = re.fullmatch(cls.FIELDS_RE, key)
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
        Parse compound documents parameters from request query string.

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
        Parse sorting parameters of fields from request query string.

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
        sort = OrderedDict()  # type: RequestSorting

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
        Check current context for existing filters of field.

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
        Get filter from request context by name and field.

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
        Get sorting order of field from request context.

        Checks if a sort criterion (``+`` or ``-``) for the *field* exists
        and returns it.

        :arg Union[str, Tuple[str, ...]] field:
        :arg SortDirection default:
            Returned, if no criterion is set by the request.
        """
        field = tuple(field.split('.')) if isinstance(field, str) else field
        return self.sorting.get(field, default)
