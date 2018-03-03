"""Common constants, enumerations and structures."""

import collections
import logging
import re
import sys
from collections import namedtuple

from mimeparse import parse_media_range

if sys.version_info < (3, 6):
    from .compat.enum import Enum, Flag, auto
else:
    from enum import Enum, Flag, auto

#: Logger instance
logger = logging.getLogger('aiohttp-json-api')

#: Key of JSON API stuff in aiohttp.web.Application
JSONAPI = 'jsonapi'

#: JSON API Content-Type by specification
JSONAPI_CONTENT_TYPE = 'application/vnd.api+json'
JSONAPI_CONTENT_TYPE_PARSED = parse_media_range(JSONAPI_CONTENT_TYPE)

#: Regular expression rule for check allowed fields and types names
ALLOWED_MEMBER_NAME_RULE = \
    r'[a-zA-Z0-9]([a-zA-Z0-9\-_]+[a-zA-Z0-9]|[a-zA-Z0-9]?)'

#: Compiled regexp of rule
ALLOWED_MEMBER_NAME_REGEX = re.compile('^' + ALLOWED_MEMBER_NAME_RULE + '$')

#: Filter rule
FilterRule = namedtuple('FilterRule', ('name', 'value'))

#: JSON API resource identifier
ResourceID = collections.namedtuple('ResourceID', ['type', 'id'])


class SortDirection(Enum):
    """Sorting direction enumeration."""

    ASC = '+'
    DESC = '-'


class Step(Enum):
    """Marshalling step enumeration."""

    BEFORE_DESERIALIZATION = auto()
    AFTER_DESERIALIZATION = auto()
    BEFORE_SERIALIZATION = auto()
    AFTER_SERIALIZATION = auto()


class Event(Flag):
    """Request event enumeration."""

    GET = auto()
    POST = auto()
    PATCH = auto()
    DELETE = auto()
    NEVER = auto()
    ALWAYS = GET | POST | PATCH | DELETE
    CREATE = POST
    UPDATE = PATCH


class Relation(Enum):
    """Types of relations enumeration."""

    TO_ONE = auto()
    TO_MANY = auto()
