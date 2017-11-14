"""
Base fields
===========

This module contains the definition for all basic fields. A field describes
how data should be serialized to JSON and deserialized again
and allows to define special methods for the different CRUD operations
defined by the http://jsonapi.org specification.

You should only work with the following fields directly:

*   :class:`Link`

    For JSON API link objects (usually included in a JSON API links object).

    :seealso: http://jsonapi.org/format/#document-links

*   :class:`Attribute`

    Represent information about a resource object (but not a relationship or a
    link).

    :seealso: http://jsonapi.org/format/#document-resource-object-attributes

*   :class:`ToOne`, :class:`ToMany`

    Represent relationships on a resource object.

    :seealso: http://jsonapi.org/format/#document-resource-object-relationships

.. todo::

    Add support for nested fields (aka embedded documents).

"""

from collections import Mapping
from typing import Sequence, Optional
import urllib.parse

from ..jsonpointer import JSONPointer
from ..const import ALLOWED_MEMBER_NAME_REGEX
from .abc.field import FieldABC
from .common import Event
from ..errors import InvalidType, InvalidValue

__all__ = (
    'BaseField',
    'Attribute',
    'Link',
    'Relationship',
)


class BaseField(FieldABC):
    """
    This class describes the base for all fields defined on a schema and
    knows how to serialize, deserialize and validate the field.
    A field is usually directly mapped to a property (*mapped_key*)
    on the resource object, but this mapping can be customized
    by implementing custom *getters* and *setters*
    (via :mod:`~aiohttp_json_api.schema.decorators`).

    .. hint::

        The inheritance of fields is currently implemented using the
        :func:`~copy.deepcopy` function from the standard library. This means,
        that in some rare cases, it is necessarily that you implement a
        custom :meth:`__deepcopy__` method when you subclass :class:`BaseField`.

    :arg str name:
        The name of the field in the JSON API document. If not explicitly
        given, it's the same as :attr:`key`.
    :arg str mapped_key:
        The name of the associated property on the resource class. If not
        explicitly given, it's the same as :attr:`key`.
    :arg bool allow_none:
        Allow to receive 'null' value
    :arg Event writable:
        Can be any :class:`~aiohttp_json_api.schema.common.Event`
        enumeration value and describes in which CRUD context the field
        is writable.
    :arg Event required:
        Can be any :class:`~aiohttp_json_api.schema.common.Event`
        enumeration value and describes in which CRUD context the field
        is required as input.
    """

    def __init__(self, *, name: str = None, mapped_key: str = None,
                 allow_none: bool = False,
                 writable: Event = Event.ALWAYS,
                 required: Event = Event.NEVER):
        #: The name of this field on the
        # :class:`~aiohttp_json_api.schema.BaseSchema`
        #: it has been defined on. Please note, that not each field has a *key*
        #: (like some links or meta attributes).
        self._key = None

        #: A :class:`aiohttp_json_api.jsonpointer.JSONPointer`
        #: to this field in a JSON API resource object. The source pointer is
        #: set from the BaseSchema class during initialisation.
        self._sp = None

        self._name = name
        self._mapped_key = mapped_key
        self.allow_none = allow_none

        assert isinstance(writable, Event)
        self.writable = writable

        assert isinstance(required, Event)
        self.required = required

    @property
    def key(self) -> str:
        return self._key

    @property
    def sp(self) -> JSONPointer:
        return self._sp

    @property
    def name(self) -> Optional[str]:
        return self._name

    @name.setter
    def name(self, value: Optional[str]):
        if not ALLOWED_MEMBER_NAME_REGEX.fullmatch(value):
            raise ValueError(
                'Field name "{}" is not allowed.'.format(value)
            )
        self._name = value

    @property
    def mapped_key(self) -> Optional[str]:
        return self._mapped_key

    @mapped_key.setter
    def mapped_key(self, value: Optional[str]):
        self._mapped_key = value

    def serialize(self, schema, data, **kwargs):
        return data

    def deserialize(self, schema, data, sp, **kwargs):
        return data

    def pre_validate(self, schema, data, sp, context):
        pass

    def post_validate(self, schema, data, sp, context):
        pass


class Attribute(BaseField):
    """
    .. seealso::

        http://jsonapi.org/format/#document-resource-object-attributes

    An attribute is always part of the resource's JSON API attributes object,
    unless *meta* is set, in which case the attribute appears in the resource's
    meta object.

    Per default, an attribute is mapped to a property on the resource object.
    You can customize this behaviour by implementing your own *getter* and
    *setter*:

    .. code-block:: python3

        class Article(BaseSchema):

            title = Attribute()

    Does the same as:

    .. code-block:: python3

        class Article(BaseSchema):

            title = Attribute()

            @gets('title')
            def title(self, article):
                return article.title

            @sets('title')
            def title(self, article, new_title):
                article.title = new_title
                return None

    :arg bool meta:
        If true, the attribute is part of the resource's *meta* object.
    :arg bool load_only:
        If `True` skip this field during serialization, otherwise
        its value will be present in the serialized data.
    :arg \*\*kwargs:
        The init arguments for the :class:`BaseField`.
    """

    def __init__(self, *, meta: bool = False, load_only=False, **kwargs):
        super(Attribute, self).__init__(**kwargs)
        self.meta = bool(meta)
        self.load_only = load_only
        self._trafaret = None


class Link(BaseField):
    """
    .. seealso::

        http://jsonapi.org/format/#document-links

    .. code-block:: python3

        class Article(BaseSchema):

            self = Link(route="some_route_name")

            author = ToOne()
            author_related = Link(
                route="another_route_name", link_of="author"
            )

    In the http://jsonapi.org specification, a link is always part of a
    JSON API links object and is either a simple string or an object with
    the members *href* and *meta*.

    A link is only readable and *not* mapped to a property on the resource
    object (You can however define a *getter*).

    :arg str route:
        A route name for the link
    :arg str link_of:
        If given, the link is part of the links object of the field with the
        key *link_of* and appears otherwise in the resource object's links
        objects. E.g.: ``link_of = "author"``.
    :arg bool normalize:
        If true, the *serialize* method normalizes the link so that it is always
        an object.
    """

    def __init__(self, route: str, link_of: str, *, name: str = None,
                 normalize: bool = True, absolute: bool = True):
        super(Link, self).__init__(name=name, writable=Event.NEVER)

        self.normalize = bool(normalize)
        self.absolute = absolute
        self.route = route
        self.link_of = link_of

    def serialize(self, schema, data, context=None, **kwargs):
        """Normalizes the links object if wished."""
        rid = schema.registry.ensure_identifier(data)
        route = schema.app.router[self.route]
        route_url = route._formatter.format_map({'type': rid.type,
                                                 'id': rid.id,
                                                 'relation': self.link_of})
        if context is not None and self.absolute:
            result = urllib.parse.urlunsplit(
                (context.request.scheme, context.request.host, route_url,
                 None, None)
            )
        else:
            result = route_url

        if not self.normalize:
            return result
        elif isinstance(result, str):
            return {'href': result}

        return result


class Relationship(BaseField):
    """
    .. seealso::

        http://jsonapi.org/format/#document-resource-object-relationships

    Additionally to attributes and basic fields, we must know how to *include*
    the related resources in the case of relationships. This class defines
    the common interface of *to-one* and *to-many* relationships (links object,
    meta object, *self* link, *related* link, validation, ...).

    Relationships are always part of the resource's JSON API relationships
    object.

    .. seealso::

        * :class:`~aiohttp_json_api.schema.relationships.ToOne`
        * :class:`~aiohttp_json_api.schema.relationships.ToMany`

    :arg Event require_data:
        If true, the JSON API relationship object must contain the *data*
        member. Must be a :class:`~aiohttp_json_api.schema.common.Event`
        instance.
    :arg bool dereference:
        If true, the relationship linkage is dereferenced automatic when
        decoded. (Implicitly sets *require_data* to Event.ALWAYS)
    :arg Sequence[str] foreign_types:
        A set with all foreign types. If given, this list is used to validate
        the input data. Leave it empty to allow all types.
    """
    relation = None

    def __init__(self, *, dereference: bool = True,
                 require_data: Event = Event.ALWAYS,
                 foreign_types: Sequence[str] = None,
                 links: Sequence[Link] = None,
                 id_field: Attribute = None,
                 **kwargs):
        BaseField.__init__(self, **kwargs)
        self.links = {link.name: link for link in links} if links else {}

        # NOTE: The related resources are loaded by the schema class for
        #       performance reasons (one big query vs many small ones).
        self.dereference = dereference

        self.foreign_types = frozenset(foreign_types or [])

        assert isinstance(require_data, Event)
        self.require_data = require_data
        self.id_field = id_field

    def add_link(self, link: Link):
        """
        Adds a new link to the links object.
        """
        self.links[link.name] = link
        return self

    def validate_resource_identifier(self, schema, data, sp):
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-identifier-objects

        Asserts that *data* is a JSON API resource identifier with the correct
        *type* value.
        """
        if not isinstance(data, Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        if not ('type' in data and 'id' in data):
            detail = 'Must contain a "type" and an "id" member.'
            raise InvalidValue(detail=detail, source_pointer=sp)

        if self.foreign_types and not data['type'] in self.foreign_types:
            detail = 'Unexpected type: "{}".'.format(data["type"])
            raise InvalidValue(detail=detail, source_pointer=sp / 'type')

        if self.id_field is not None:
            self.id_field.pre_validate(self, data['id'], sp / 'id', None)

    def validate_relationship_object(self, schema, data, sp):
        """
        Asserts that *data* is a JSON API relationship object.

        *   *data* is a dictionary
        *   *data* must be not empty
        *   *data* may only have the members *data*, *links* or *meta*.
        *   *data* must contain a *data* member, if :attr:`dereference` or
            :attr:`require_data` is true.
        """
        if not isinstance(data, Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        if not data:
            detail = 'Must contain at least a "data", "links" or "meta" member.'
            raise InvalidValue(detail=detail, source_pointer=sp)

        if not (data.keys() <= {'links', 'data', 'meta'}):
            unexpected = (data.keys() - {'links', 'data', 'meta'}).pop()
            detail = "Unexpected member: '{}'.".format(unexpected)
            raise InvalidValue(detail=detail, source_pointer=sp)

        if (self.dereference or self.require_data) and 'data' not in data:
            detail = 'The "data" member is required.'
            raise InvalidValue(detail=detail, source_pointer=sp)

    def pre_validate(self, schema, data, sp, context):
        self.validate_relationship_object(schema, data, sp)
        super(Relationship, self).pre_validate(schema, data, sp, context)
