"""Useful typing."""

# pylint: disable=C0103
from typing import Any, Awaitable, Callable, Coroutine, Dict, MutableMapping, Optional, Set, Tuple, Union

from aiohttp import web
from aiohttp_json_api.common import FilterRule, ResourceID, SortDirection
from multidict import MutableMultiMapping

#: Type for Request filters
RequestFilters = MutableMultiMapping[FilterRule]

#: Type for Request fields
RequestFields = MutableMapping[str, Tuple[str, ...]]

#: Type for Request includes (compound documents)
RequestIncludes = Tuple[Tuple[str, ...], ...]

#: Type for Request sorting parameters
RequestSorting = MutableMapping[Tuple[str, ...], SortDirection]

#: Type for callable or co-routine
Callee = Union[Callable, Coroutine]

MimeTypeComponents = Tuple[str, str, Dict[str, str]]
QualityAndFitness = Tuple[float, int]
QFParsed = Tuple[QualityAndFitness, Optional[MimeTypeComponents]]

CallableHandler = Callable[[web.Request], Awaitable[web.StreamResponse]]
Middleware = Callable[[web.Request, CallableHandler], Awaitable[web.StreamResponse]]

CompoundDocumentsMapping = Dict[ResourceID, Any]

RelationshipsMapping = Dict[str, Set[Tuple[str, ...]]]
