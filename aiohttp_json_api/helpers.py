"""Helpers."""

import inspect
from collections import Iterable, Mapping
from typing import Optional

from aiohttp import web

from .abc.field import FieldABC
from .fields.decorators import Tag
from .typings import Callee
from .common import JSONAPI


def is_generator(obj):
    """Return True if ``obj`` is a generator."""
    return inspect.isgeneratorfunction(obj) or inspect.isgenerator(obj)


def is_iterable_but_not_string(obj):
    """Return True if ``obj`` is an iterable object that isn't a string."""
    return (
        (isinstance(obj, Iterable) and not hasattr(obj, "strip")) or
        is_generator(obj)
    )


def is_indexable_but_not_string(obj):
    """Return True if ``obj`` is indexable but isn't a string."""
    return not hasattr(obj, "strip") and hasattr(obj, "__getitem__")


def is_collection(obj, exclude=()):
    """Return True if ``obj`` is a collection type."""
    return (not isinstance(obj, (Mapping,) + exclude) and
            is_iterable_but_not_string(obj))


def ensure_collection(value, exclude=()):
    """Ensure value is collection."""
    return value if is_collection(value, exclude=exclude) else (value,)


def first(iterable, default=None, key=None):
    """
    Return first element of *iterable*.

    Return first element of *iterable* that evaluates to ``True``, else
    return ``None`` or optional *default*.

    >>> first([0, False, None, [], (), 42])
    42
    >>> first([0, False, None, [], ()]) is None
    True
    >>> first([0, False, None, [], ()], default='ohai')
    'ohai'
    >>> import re
    >>> m = first(re.match(regex, 'abc') for regex in ['b.*', 'a(.*)'])
    >>> m.group(1)
    'bc'

    The optional *key* argument specifies a one-argument predicate function
    like that used for *filter()*.  The *key* argument, if supplied, should be
    in keyword form. For example, finding the first even number in an iterable:

    >>> first([1, 1, 3, 4, 5], key=lambda x: x % 2 == 0)
    4

    Contributed by Hynek Schlawack, author of `the original standalone module`_

    .. _the original standalone module: https://github.com/hynek/first
    """
    return next(filter(key, iterable), default)


def make_sentinel(name='_MISSING', var_name=None):
    """
    Create sentinel instance.

    Creates and returns a new **instance** of a new class, suitable for
    usage as a "sentinel", a kind of singleton often used to indicate
    a value is missing when ``None`` is a valid input.

    >>> make_sentinel(var_name='_MISSING')
    _MISSING

    The most common use cases here in project are as default values
    for optional function arguments, partly because of its
    less-confusing appearance in automatically generated
    documentation. Sentinels also function well as placeholders in queues
    and linked lists.

    .. note::

      By design, additional calls to ``make_sentinel`` with the same
      values will not produce equivalent objects.

      >>> make_sentinel('TEST') == make_sentinel('TEST')
      False
      >>> type(make_sentinel('TEST')) == type(make_sentinel('TEST'))
      False

    :arg str name:
        Name of the Sentinel
    :arg str var_name:
        Set this name to the name of the variable in its respective
        module enable pickleability.
    """
    class Sentinel(object):
        def __init__(self):
            self.name = name
            self.var_name = var_name

        def __repr__(self):
            if self.var_name:
                return self.var_name
            return '%s(%r)' % (self.__class__.__name__, self.name)

        if var_name:
            def __reduce__(self):
                return self.var_name

        def __nonzero__(self):
            return False

        __bool__ = __nonzero__

    return Sentinel()


def get_router_resource(app: web.Application, resource: str):
    """Return route of JSON API application for resource."""
    return app.router[
        '{}.{}'.format(app[JSONAPI]['routes_namespace'], resource)
    ]


def get_processors(obj, tag: Tag, field: FieldABC,
                   default: Optional[Callee] = None):
    has_processors = getattr(obj, '_has_processors', False)
    if has_processors:
        processor_tag = tag, field.key
        processors = obj.__processors__.get(processor_tag)
        if processors:
            for processor_name in processors:
                processor = getattr(obj, processor_name)
                processor_kwargs = \
                    processor.__processing_kwargs__.get(processor_tag)
                yield processor, processor_kwargs
            return

    if not callable(default):
        return

    yield default, {}


MISSING = make_sentinel()
