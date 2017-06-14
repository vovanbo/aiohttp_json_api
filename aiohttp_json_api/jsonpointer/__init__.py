"""
Extended JSONPointer from python-json-pointer_
==============================================

.. _python-json-pointer: https://github.com/stefankoegl/python-json-pointer
"""

import typing

from jsonpointer import JsonPointer as BaseJsonPointer


class JSONPointer(BaseJsonPointer):
    def __init__(self, pointer):
        super(JSONPointer, self).__init__(pointer)

    def __truediv__(self,
                    path: typing.Union['JSONPointer', str]) -> 'JSONPointer':
        parts = self.parts.copy()
        if isinstance(path, str):
            if not path.startswith('/'):
                path = f'/{path}'
            new_parts = JSONPointer(path).parts.pop(0)
            parts.append(new_parts)
        else:
            new_parts = path.parts
            parts.extend(new_parts)
        return JSONPointer.from_parts(parts)
