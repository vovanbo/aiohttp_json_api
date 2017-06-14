"""
Helpers
=======
"""
import inspect
from collections import Mapping, Iterable


def is_generator(obj):
    """Return True if ``obj`` is a generator
    """
    return inspect.isgeneratorfunction(obj) or inspect.isgenerator(obj)


def is_iterable_but_not_string(obj):
    """Return True if ``obj`` is an iterable object that isn't a string."""
    return (
        (isinstance(obj, Iterable) and not hasattr(obj, "strip"))
        or is_generator(obj)
    )


def is_indexable_but_not_string(obj):
    """Return True if ``obj`` is indexable but isn't a string."""
    return not hasattr(obj, "strip") and hasattr(obj, "__getitem__")


def is_collection(obj):
    """
    Return True if ``obj`` is a collection type,
    e.g list, tuple, queryset.
    """
    return is_iterable_but_not_string(obj) and not isinstance(obj, Mapping)
