"""JSON encoder extension."""

import functools
import json

from .jsonpointer import JSONPointer


class JSONEncoder(json.JSONEncoder):
    """Overloaded JSON encoder with JSONPointer support."""

    def default(self, o):
        """Add JSONPointer serializing support to default json.dumps."""
        if isinstance(o, JSONPointer):
            return o.path

        return super(JSONEncoder, self).default(o)


# pylint: disable=C0103
json_dumps = functools.partial(json.dumps, cls=JSONEncoder)
