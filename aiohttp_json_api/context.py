"""
Request context
===============
"""

import json
import re

from aiohttp import web
from boltons.cacheutils import cachedproperty

from .const import JSONAPI
from .errors import HTTPBadRequest
from .log import logger
from .schema.common import Event


class RequestContext(object):
    FILTER_KEY = re.compile(r"filter\[(?P<field>[A-z0-9-]+)\]")
    FILTER_VALUE = re.compile(r"(?P<filtername>[a-z]+):(?P<rule>.*)")
    FIELDS_RE = re.compile(r"fields\[([A-z0-9-]+)\]")

    def __init__(self, request: web.Request):
        self._pagination = None
        self.request = request

    @property
    def event(self):
        return Event[self.request.method]

    @property
    def pagination(self):
        if self._pagination is not None:
            return self._pagination

        if self.schema is not None:
            pagination_type = self.schema.opts.get('pagination')
            if pagination_type:
                self._pagination = pagination_type.from_request(self.request)
                return self._pagination

        return None

    @property
    def schema(self):
        registry = self.request.app[JSONAPI]['registry']
        try:
            return registry.get_schema(self.request.match_info.get('type'))
        except KeyError:
            return None

    @cachedproperty
    def filters(self):
        """
        .. hint::

            Please note, that the *filter* strategy is not defined by the
            jsonapi specification and depends on the implementation.
            If you want to use another filter strategy,
            feel free to **override** this property.

        Returns a list, which contains 3-tuples::

            (fieldname, filtername, rule)

        This tuples describes on which field a filter is applied. For example::

            ("name", "startswith", "Homer")
            ("age", "gt", 25)
            ("name", "in", ["Homer", "Marge"])

        Filters can be applied using the query string::

            >>> # /api/User/?filter[name]=endswith:'Simpson'
            >>> context.filters
            [("name", "endswith", "Simpson")]

            >>> # /api/User/?filter[name]=in:['Homer Simpson', 'Darth Vader']
            >>> context.filters
            [("name", "in", ["Homer Simpson", "Darth Vader"])]

            >>> # /api/User/?filter[email]=startswith:'lisa'&filter[age]=lt:20
            >>> context.filters
            [("email", "startswith", "lisa"), ("age", "lt", 20)]

        The general syntax is::

            "?filter[fieldname]=filtername:rule"

        where *rule* is a JSON value.

        :raises BadRequest:
            If the rule of a filter is not a JSON object.
        :raises BadRequest:
            If a filtername contains other characters than *[a-z]*.
        """
        filters = []
        for key, values in self.request.query.items():
            key_match = re.fullmatch(self.FILTER_KEY, key)
            value_match = re.fullmatch(self.FILTER_VALUE, values[0])

            # If the key indicates a filter, but the value is not correct
            # formatted.
            if key_match and not value_match:
                field = key_match.group('field')
                raise HTTPBadRequest(
                    detail=f"The filter '{field}' is not correct applied.",
                    source_parameter=key
                )

            # The key indicates a filter and the filternames exists.
            elif key_match and value_match:
                field = key_match.group(1)
                filtername = value_match.group('filtername')
                rule = value_match.group('rule')
                try:
                    rule = json.loads(rule)
                except Exception as err:
                    logger.debug(err, exc_info=False)
                    raise HTTPBadRequest(
                        detail=f"The rule '{rule}' is not JSON serializable",
                        source_parameter=key
                    )
                filters.append((field, filtername, rule))
        return filters

    @cachedproperty
    def fields(self):
        """
        The fields, which should be included in the response (sparse fieldset).

        .. code-block:: python3

            >>> # /api/User?fields[User]=email,name&fields[Post]=comments
            >>> context.fields
            {"User": ["email", "name"], "Post": ["comments"]}

        :seealso: http://jsonapi.org/format/#fetching-sparse-fieldsets
        """
        fields = dict()
        for key, value in self.request.query.items():
            match = re.fullmatch(self.FIELDS_RE, key)
            if match:
                typename = match.group(1)
                type_fields = value[0].split(',')
                type_fields = [
                    item.strip() for item in type_fields if item.strip()
                ]

                fields[typename] = type_fields
        return fields

    @cachedproperty
    def include(self):
        """
        Returns the names of the relationships, which should be included into
        the response.

        .. code-block:: python3

            >>> # /api/Post?include=author,comments.author
            >>> context.include
            [["author"], ["comments", "author"]]

        :seealso: http://jsonapi.org/format/#fetching-includes
        """
        include = self.request.query.get('include', '')
        return [path.split('.') for path in include.split(',') if path]

    @cachedproperty
    def sort(self):
        """
        Returns a list with two tuples, describing how the output should be
        sorted:

        .. code-block:: python3

            >>> # /api/Post?sort=name,-age,+comments.count
            [("+", ["name"]), ("-", ["age"]), ("+", ["comments", "count"])]]

        :seealso: http://jsonapi.org/format/#fetching-sorting
        """
        sort_in_query = self.request.query.get('sort')
        sort_in_query = sort_in_query.split(',') if sort_in_query else list()

        sort = list()
        for field in sort_in_query:
            if field[0] == '+' or field[0] == '-':
                direction = field[0]
                field = field[1:]
            else:
                direction = '+'

            field = field.split('.')
            field = [e.strip() for e in field]

            sort.append((direction, field))
        return sort

    def has_filter(self, field, filtername):
        """
        Returns true, if the filter *filtername* has been applied at least once
        on the *field*.

        :arg str field:
        :arg str filtername:
        """
        return any(
            field == item[0] and filtername == item[1]
            for item in self.filters
        )

    def get_filter(self, field, filtername, default=None):
        """
        If the filter *filtername* has been applied on the *field*, the
        *filterrule* is returned and *default* otherwise.

        :arg str field:
        :arg str filtername:
        :arg default:
            A fallback value for the filter.
        """
        for item in self.filters:
            if item[0] == field and item[1] == filtername:
                return item[2]
        return default

    def get_order(self, field, default='+'):
        """
        Checks if a sort criterion (``+`` or ``-``) for the *field* exists
        and returns it.

        :arg str field:
        :arg default:
            Returned, if no criterion is set by the request.
        """
        if isinstance(field, str):
            field = field.split('.')

        for direction, field_ in self.sort:
            print(field_, field)
            if field_ == field:
                return direction
        return default
