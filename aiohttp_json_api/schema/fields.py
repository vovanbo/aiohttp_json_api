"""
Fields
======

.. note::

    Always remember that you can model the JSON API completly with the fields in
    :mod:`~aiohttp_json_api.schema.base_fields`.

.. sidebar:: Index

    *   :class:`String`
    *   :class:`Integer`
    *   :class:`Float`
    *   :class:`Complex`
    *   :class:`Decimal`
    *   :class:`Fraction`
    *   :class:`DateTime`
    *   :class:`TimeDelta`
    *   :class:`UUID`
    *   :class:`Boolean`
    *   :class:`URI`
    *   :class:`Email`
    *   :class:`Dict`
    *   :class:`List`
    *   :class:`Number`
    *   :class:`Str`
    *   :class:`Bool`

This module contains fields for several standard Python types and classes
from the standard library.
"""
import collections
import datetime
import decimal
import fractions
import typing
import uuid
from enum import Enum

import dateutil.parser
import trafaret as t
from trafaret.contrib import rfc_3339
from yarl import URL

from .trafarets import DecimalTrafaret
from .base_fields import Attribute
from ..errors import InvalidType, InvalidValue

__all__ = [
    "String",
    "Integer",
    "Float",
    "Complex",
    "Decimal",
    "Fraction",
    "DateTime",
    "TimeDelta",
    "UUID",
    "Boolean",
    "URI",
    "Email",
    "Dict",
    "List",

    "Number",
    "Str",
    "Bool"
]


class String(Attribute):
    def __init__(self, *, allow_blank: bool = False,
                 regex: typing.Union[str, bytes, typing.re] = None,
                 choices:
                    typing.Optional[typing.Union[
                        typing.Iterable[str], typing.Type[Enum]
                    ]] = None,
                 min_length: typing.Optional[int] = None,
                 max_length: typing.Optional[int] = None,
                 **kwargs):
        super(String, self).__init__(**kwargs)
        self._trafaret = t.String(allow_blank=allow_blank, regex=regex,
                                  min_length=min_length, max_length=max_length)
        if choices:
            choices = tuple(choices.__members__.keys()) \
                if isinstance(choices, type(Enum)) \
                else choices
            self._trafaret = self._trafaret | t.Enum(*choices)

        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidValue(detail=error.as_dict(), source_pointer=sp)
        return super(String, self).validate_pre_decode(schema, data, sp,
                                                       context)

    def encode(self, schema, data, **kwargs):
        result = self._trafaret.converter(data)
        if isinstance(result, Enum):
            result = result.name
        return result


class Integer(Attribute):
    def __init__(self, *,
                 gte: typing.Optional[int] = None,
                 lte: typing.Optional[int] = None,
                 gt: typing.Optional[int] = None,
                 lt: typing.Optional[int] = None,
                 **kwargs):
        super(Integer, self).__init__(**kwargs)
        self._trafaret = t.Int(gte=gte, lte=lte, gt=gt, lt=lt)
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidValue(detail=error.as_dict(), source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return int(data)

    def encode(self, schema, data, **kwargs):
        return self._trafaret.check(data)


class Float(Attribute):
    def __init__(self, *,
                 gte: typing.Optional[int] = None,
                 lte: typing.Optional[int] = None,
                 gt: typing.Optional[int] = None,
                 lt: typing.Optional[int] = None,
                 **kwargs):
        super(Float, self).__init__(**kwargs)
        self._trafaret = t.Float(gte=gte, lte=lte, gt=gt, lt=lt)
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidValue(detail=error.as_dict(), source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return float(data)

    def encode(self, schema, data, **kwargs):
        return self._trafaret.check(data)


class Complex(Attribute):
    """
    Encodes a :class:`complex` number as JSON object with a *real* and *imag*
    member::

        {"real": 1.2, "imag": 42}
    """

    def validate_pre_decode(self, schema, data, sp, context):
        detail = "Must be an object with a 'real' and 'imag' member.'"

        if not isinstance(data, collections.Mapping):
            raise InvalidType(detail=detail, source_pointer=sp)
        if not "real" in data:
            detail = "Does not have a 'real' member."
            raise InvalidValue(detail=detail, source_pointer=sp)
        if not "imag" in data:
            detail = "Does not have an 'imag' member."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if not isinstance(data["real"], (int, float)):
            detail = "The real part must be a number."
            raise InvalidValue(detail=detail, source_pointer=sp / "real")
        if not isinstance(data["imag"], (int, float)):
            detail = "The imaginar part must be a number."
            raise InvalidValue(detail=detail, source_pointer=sp / "imag")
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return complex(data["real"], data["imag"])

    def encode(self, schema, data, **kwargs):
        data = complex(data)
        return {"real": data.real, "imag": data.imag}


class Decimal(Attribute):
    """Encodes and decodes a :class:`decimal.Decimal` as a string."""
    def __init__(self, *,
                 gte: typing.Optional[int] = None,
                 lte: typing.Optional[int] = None,
                 gt: typing.Optional[int] = None,
                 lt: typing.Optional[int] = None,
                 **kwargs):
        super(Decimal, self).__init__(**kwargs)
        self._trafaret = DecimalTrafaret(gte=gte, lte=lte, gt=gt, lt=lt) >> str
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidValue(detail=error.as_dict(), source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return decimal.Decimal(data)

    def encode(self, schema, data, **kwargs):
        return self._trafaret.check(data)


class Fraction(Attribute):
    """Stores a :class:`fractions.Fraction` in an object with a *numerator*
    and *denominator* member::

        # 1.5
        {"numerator": 2, "denominator": 3}

    :arg float min:
        The fraction must be greater or equal than this value.
    :arg float max:
        The fraction must be less or equal than this value.
    """

    def __init__(self, *, min=None, max=None, **kwargs):
        super(Fraction, self).__init__(**kwargs)

        # min must be <= max
        assert min is None or max is None or min <= max

        self.min = min
        self.max = max

    def validate_pre_decode(self, schema, data, sp, context):
        if not isinstance(data, dict):
            detail = "Must be an object with a 'numerator' and 'denominator' " \
                     "member."
            raise InvalidType(detail=detail, source_pointer=sp)
        if not "numerator" in data:
            detail = "Does not have a 'numerator' member."
            raise InvalidValue(detail=detail, source_pointer=sp)
        if not "denominator" in data:
            detail = "Does not have a 'denominator' member."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if not isinstance(data["numerator"], int):
            detail = "The numerator must be an integer."
            raise InvalidValue(detail=detail, source_pointer=sp / "numerator")
        if not isinstance(data["denominator"], int):
            detail = "The denominator must be an integer."
            raise InvalidValue(detail=detail, source_pointer=sp / "denominator")
        if data["denominator"] == 0:
            detail = "The denominator must be not equal to zero."
            raise InvalidValue(detail=detail, source_pointer=sp / "denominator")

        val = data["numerator"] / data["denominator"]
        if self.min is not None and self.min > val:
            detail = "Must be >= {}.".format(self.min)
            raise InvalidValue(detail=detail, source_pointer=sp)
        if self.max is not None and self.max < val:
            detail = "Must be <= {}.".format(self.max)
            raise InvalidValue(detail=detail, source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return fractions.Fraction(int(data[0]), int(data[1]))

    def encode(self, schema, data, **kwargs):
        return {"numerator": data.numerator, "denominator": data.denominator}


class DateTime(Attribute):
    """
    Stores a :class:`datetime.datetime` in ISO-8601 as recommeded in
    http://jsonapi.org/recommendations/#date-and-time-fields.
    """
    def __init__(self, *, allow_blank: bool = False, **kwargs):
        super(DateTime, self).__init__(**kwargs)
        self._trafaret = rfc_3339.DateTime(allow_blank=allow_blank)
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidValue(detail=error.as_dict(), source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return dateutil.parser.parse(data)

    def encode(self, schema, data, **kwargs):
        value = self._trafaret.check(data)
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        else:
            return value


class TimeDelta(Attribute):
    """Stores a :class:`datetime.timedelta` as total number of seconds.

    :arg datetime.timedelta min:
        The timedelta must be greater or equal than this value.
    :arg datetime.timedelta max:
        The timedelta must be less or equal than this value.
    """

    def __init__(self, *, min=None, max=None, **kwargs):
        super(TimeDelta, self).__init__(**kwargs)

        # min must be <= max
        assert min is None or max is None or min <= max

        self.min = min
        self.max = max

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            data = float(data)
        except TypeError:
            detail = "Must be a number."
            raise InvalidType(detail=detail, source_pointer=sp)

        data = datetime.timedelta(seconds=data)

        if self.min is not None and self.min > data:
            detail = "The timedelta must be >= {}.".format(self.min)
            raise InvalidValue(detail=detail, source_pointer=sp)
        if self.max is not None and self.max < data:
            detail = "The timedelta must be <= {}.".format(self.max)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return datetime.timedelta(seconds=float(data))

    def encode(self, schema, data, **kwargs):
        return data.total_seconds()


class UUID(Attribute):
    """Encodes and decodes a :class:`uuid.UUID`.

    :arg int version:
        The required version of the UUID.
    """

    def __init__(self, *, version: int = None, **kwargs):
        super(UUID, self).__init__(**kwargs)
        self.version = version

    def validate_pre_decode(self, schema, data, sp, context):
        if not isinstance(data, str):
            detail = "The UUID must be a hexadecimal string."
            raise InvalidType(detail=detail, source_pointer=sp)

        try:
            data = uuid.UUID(hex=data)
        except ValueError:
            detail = "The UUID is badly formed (the representation as " \
                     "hexadecimal string is needed)."
            raise InvalidValue(detail=detail, source_pointer=sp)

        if self.version is not None and self.version != data.version:
            detail = f"Not a UUID{self.version}."
            raise InvalidValue(detail=detail, source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return uuid.UUID(hex=data)

    def encode(self, schema, data, **kwargs):
        if self.allow_none and data is None:
            return None
        return data.hex


class Boolean(Attribute):
    """Ensures that the input is a :class:`bool`."""
    def __init__(self, **kwargs):
        super(Boolean, self).__init__(**kwargs)
        self._trafaret = t.Bool()
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError as error:
            raise InvalidType(detail=error.as_dict(), source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def encode(self, schema, data, **kwargs):
        return self._trafaret.check(data)


class URI(Attribute):
    """Parses the URI with :func:`rfc3986.urlparse` and returns the result."""

    def validate_pre_decode(self, schema, data, sp, context):
        if not isinstance(data, str):
            detail = "Must be a string."
            raise InvalidType(detail=detail, source_pointer=sp)
        try:
            URL(data)
        except ValueError:
            detail = "Not a valid URI."
            raise InvalidValue(detail=detail, source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def decode(self, schema, data, sp, **kwargs):
        return URL(data)

    def encode(self, schema, data, **kwargs):
        return str(data)


class Email(Attribute):
    """Checks if a string is syntactically correct Email address."""
    def __init__(self, **kwargs):
        super(Email, self).__init__(**kwargs)
        self._trafaret = t.Email()
        if self.allow_none:
            self._trafaret = self._trafaret | t.Null()

    def validate_pre_decode(self, schema, data, sp, context):
        try:
            self._trafaret.check(data)
        except t.DataError:
            if not isinstance(data, str):
                detail = "Must be a string."
                raise InvalidType(detail=detail, source_pointer=sp)
            else:
                detail = "Not a valid Email address."
                raise InvalidValue(detail=detail, source_pointer=sp)
        return super().validate_pre_decode(schema, data, sp, context)

    def encode(self, schema, data, **kwargs):
        return self._trafaret.check(data)


class Dict(Attribute):
    """
    Realises a dictionary which has only values of a special field::

        todo = Dict(String(regex=".*[A-z0-9].*"))

    .. note::

        If you deal with dictionaries with values of different types, you can
        still use the more general
        :class:`~aiohttp_json_api.schema.base_fields.Attribute`
        field to model this data.

        *You are not forced to use a* :class:`Dict` *field*! It is only a
        helper.

    :arg Attribute field:
        All values of the dictionary are encoded and decoded using this
        field.
    """

    def __init__(self, field, **kwargs):
        super(Dict, self).__init__(**kwargs)
        self.field = field

    def decode(self, schema, data, sp, **kwargs):
        return {
            key: self.field.decode(schema, value, sp / key)
            for key, value in data.items()
        }

    def encode(self, schema, data, **kwargs):
        return {
            key: self.field.encode(schema, value)
            for key, value in data.items()
        }


class List(Attribute):
    """
    Realises a list which has only values of a special type::

        todo = List(String(regex=".*[A-z0-9].*"))

    .. note::

        If your list has items of different types, you can still use the more
        general :class:`~aiohttp_json_api.schema.base_fields.Attribute`
        field to model this data.

        *You are not forced to use a* :class:`List` *field*! It is only a
        helper.

    :arg Attribute field:
        All values of the list are encoded and decoded using this field.
    """

    def __init__(self, field, **kwargs):
        super(List, self).__init__(**kwargs)
        self.field = field

    def decode(self, schema, data, sp, **kwargs):
        return [
            self.field.decode(schema, item, sp / i) for item, i in
            enumerate(data)
        ]

    def encode(self, schema, data, **kwargs):
        return [self.field.encode(schema, item) for item in data] \
            if data \
            else []


# Some aliases.
Number = Float
Str = String
Bool = Boolean
