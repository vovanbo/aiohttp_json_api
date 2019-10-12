"""Useful typing."""

# pylint: disable=C0103
from typing import Callable, Coroutine, Dict, MutableMapping, Tuple, Union, Optional, Awaitable

from aiohttp import web
from multidict import MutableMultiMapping

from aiohttp_json_api.common import FilterRule, ResourceID, SortDirection

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

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
Middleware = Callable[[web.Request, Handler], Awaitable[web.StreamResponse]]
