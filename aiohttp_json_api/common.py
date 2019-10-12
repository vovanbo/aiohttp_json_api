"""Common constants, enumerations and structures."""

import collections
import logging
import re
from enum import Enum, Flag, auto
from typing import Tuple, Dict, Any, Pattern

from mimeparse import parse_media_range

#: Logger instance
logger = logging.getLogger('aiohttp-json-api')

#: Key of JSON API stuff in aiohttp.web.Application
JSONAPI: str = 'jsonapi'

#: JSON API Content-Type by specification
JSONAPI_CONTENT_TYPE: str = 'application/vnd.api+json'
JSONAPI_CONTENT_TYPE_PARSED: Tuple[str, str, Dict[str, Any]] = parse_media_range(JSONAPI_CONTENT_TYPE)

#: Regular expression rule for check allowed fields and types names
ALLOWED_MEMBER_NAME_RULE: str = r'[a-zA-Z0-9]([a-zA-Z0-9\-_]+[a-zA-Z0-9]|[a-zA-Z0-9]?)'

#: Compiled regexp of rule
ALLOWED_MEMBER_NAME_REGEX: Pattern = re.compile('^' + ALLOWED_MEMBER_NAME_RULE + '$')

#: Filter rule
FilterRule = collections.namedtuple('FilterRule', ('name', 'value'))

#: JSON API resource identifier
ResourceID = collections.namedtuple('ResourceID', ['type', 'id'])


class SortDirection(Enum):
    """Sorting direction."""
    ASC = '+'
    DESC = '-'


class Step(Enum):
    """Marshalling step."""
    BEFORE_DESERIALIZATION = auto()
    AFTER_DESERIALIZATION = auto()
    BEFORE_SERIALIZATION = auto()
    AFTER_SERIALIZATION = auto()


class Event(Flag):
    """Request event."""
    GET = auto()
    POST = auto()
    PATCH = auto()
    DELETE = auto()
    NEVER = auto()
    ALWAYS = GET | POST | PATCH | DELETE
    CREATE = POST
    UPDATE = PATCH


class Relation(Enum):
    """Types of relations."""
    TO_ONE = auto()
    TO_MANY = auto()
