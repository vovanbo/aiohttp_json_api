import functools
import json

from .jsonpointer import JSONPointer


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, JSONPointer):
            return o.path

        return super(JSONEncoder, self).default(o)


json_dumps = functools.partial(json.dumps, cls=JSONEncoder)
