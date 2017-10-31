"""
Field abstract base class
=========================
"""

import abc
from typing import Optional

from ...jsonpointer import JSONPointer


class FieldABC(abc.ABC):
    @property
    @abc.abstractmethod
    def key(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def sp(self) -> JSONPointer:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> Optional[str]:
        raise NotImplementedError

    @name.setter
    @abc.abstractmethod
    def name(self, value: Optional[str]):
        pass

    @property
    @abc.abstractmethod
    def mapped_key(self) -> Optional[str]:
        raise NotImplementedError

    @mapped_key.setter
    @abc.abstractmethod
    def mapped_key(self, value: Optional[str]):
        pass

    @abc.abstractmethod
    def serialize(self, schema, data, **kwargs):
        """
        Serialize the passed *data*.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def deserialize(self, schema, data, sp, **kwargs):
        """
        Deserialize the raw *data* from the JSON API input document
        and returns it.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def pre_validate(self, schema, data, sp, context):
        """
        Validates the raw JSON API input for this field. This method is
        called before :meth:`deserialize`.

        :arg ~aiohttp_json_api.schema.BaseSchema schema:
            The schema this field has been defined on.
        :arg data:
            The raw input data
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            A JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            A JSON API request context instance
        """
        raise NotImplementedError

    @abc.abstractmethod
    def post_validate(self, schema, data, sp, context):
        """
        Validates the decoded input *data* for this field. This method is
        called after :meth:`deserialize`.

        :arg ~aiohttp_json_api.schema.BaseSchema schema:
            The schema this field has been defined on.
        :arg data:
            The decoded input data
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            A JSON pointer to the source of *data*.
        :arg ~aiohttp_json_api.context.RequestContext context:
            A JSON API request context instance
        """
        raise NotImplementedError
