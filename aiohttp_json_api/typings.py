"""
Useful typing
=============
"""

# pylint: disable=C0103
import typing
from typing import MutableMapping, Tuple, Union, Dict

from .common import FilterRule, ResourceID, SortDirection

RequestFilters = MutableMapping[str, FilterRule]
RequestFields = MutableMapping[str, Tuple[str, ...]]
RequestIncludes = Tuple[Tuple[str, ...], ...]
RequestSorting = MutableMapping[Tuple[str, ...], SortDirection]
ResourceIdentifier = Union[ResourceID, Dict[str, str]]
Callee = typing.Union[typing.Callable, typing.Coroutine]
