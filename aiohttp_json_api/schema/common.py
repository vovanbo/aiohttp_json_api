"""
Schema's common stuff
"""
import sys

if sys.version_info < (3, 6):
    from aiohttp_json_api.compat.enum import Enum, Flag, auto
else:
    from enum import Enum, Flag, auto


class Step(Enum):
    BEFORE_DESERIALIZATION = auto()
    AFTER_DESERIALIZATION = auto()
    BEFORE_SERIALIZATION = auto()
    AFTER_SERIALIZATION = auto()


class Event(Flag):
    GET = auto()
    POST = auto()
    PATCH = auto()
    DELETE = auto()
    NEVER = auto()
    ALWAYS = GET | POST | PATCH | DELETE
    CREATE = POST
    UPDATE = PATCH


class Relation(Enum):
    TO_ONE = auto()
    TO_MANY = auto()
