"""JSON encoder extension."""

import functools
import json
from typing import Any

from aiohttp_json_api.jsonpointer import JSONPointer


class JSONEncoder(json.JSONEncoder):
    """Overloaded JSON encoder with JSONPointer support."""

    def default(self, o: Any) -> Any:
        """Add JSONPointer serializing support to default json.dumps."""
        if isinstance(o, JSONPointer):
            return o.path

        return super(JSONEncoder, self).default(o)


# pylint: disable=C0103
json_dumps = functools.partial(json.dumps, cls=JSONEncoder)
