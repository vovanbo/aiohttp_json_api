"""
Schema's common stuff
"""

from enum import Enum, Flag, auto


class Step(Enum):
    PRE_DECODE = auto()
    POST_DECODE = auto()
    PRE_ENCODE = auto()
    POST_ENCODE = auto()


class Event(Flag):
    GET = auto()
    POST = auto()
    PATCH = auto()
    DELETE = auto()
    NEVER = auto()
    ALWAYS = GET | POST | PATCH | DELETE
    CREATE = POST
    UPDATE = PATCH
