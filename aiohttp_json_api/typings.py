"""Useful typing."""

# pylint: disable=C0103
from typing import (
    Callable, Coroutine, Dict, MutableMapping, Tuple, Union, Optional
)

from .common import FilterRule, ResourceID, SortDirection

#: Type for Request filters
RequestFilters = MutableMapping[str, FilterRule]

#: Type for Request fields
RequestFields = MutableMapping[str, Tuple[str, ...]]

#: Type for Request includes (compound documents)
RequestIncludes = Tuple[Tuple[str, ...], ...]

#: Type for Request sorting parameters
RequestSorting = MutableMapping[Tuple[str, ...], SortDirection]

#: Type for Resource identifier
ResourceIdentifier = Union[ResourceID, Dict[str, str]]

#: Type for callable or co-routine
Callee = Union[Callable, Coroutine]

MimeTypeComponents = Tuple[str, str, Dict[str, str]]
QualityAndFitness = Tuple[float, int]
QFParsed = Tuple[QualityAndFitness, Optional[MimeTypeComponents]]
