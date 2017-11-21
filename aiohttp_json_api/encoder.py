"""
JSON encoder extension
======================
"""

import functools
import json

from .jsonpointer import JSONPointer


class JSONEncoder(json.JSONEncoder):
    """
    Overloaded JSON encoder with JSONPointer support.
    """
    def default(self, o):
        """Default dumps behaviour overriding."""
        if isinstance(o, JSONPointer):
            return o.path

        return super(JSONEncoder, self).default(o)


# pylint: disable=C0103
json_dumps = functools.partial(json.dumps, cls=JSONEncoder)
