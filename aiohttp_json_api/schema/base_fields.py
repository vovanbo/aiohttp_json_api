#!/usr/bin/env python3

"""
Base fields
===========

This module contains the definition for all basic fields. A field describes
how data should be encoded to JSON and decoded again and allows to define
special methods for the different CRUD operations defined by the
http://jsonapi.org specification.

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

.. todo::

    Fields are currently not bound to schema instances. It may be helpful
    to do something like this in the future::

        class BaseField(object):

            #....

            def __get__(self, obj, cls=None):
                if obj is None:
                    return self

                class BoundField(object):
                    def get(*args, **kwargs): return self.get(obj, *args, **kwargs)
                    def set(*args, **kwargs): return self.set(obj, *args, **kwargs)
                    def add(*args, **kwargs): return self.add(obj, *args, **kwargs)
                    #...
                    __call__ = get
                return BoundField
"""

import collections
import typing

from .common import Event, Step
from ..errors import InvalidType, InvalidValue

__all__ = (
    'BaseField',
    'Attribute',
    'Link',
    'LinksObjectMixin',
    'Relationship',
)


class BaseField(object):
    """
    This class describes the base for all fields defined on a schema and
    knows how to encode, decode and update the field. A field is usually
    directly mapped to a property (*mapped_key*) on the resource object, but
    this mapping can be customized by implementing custom *getters* and
    *setters*.

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
    :arg str writable:
        Can be either *never*, *always*, *creation* or *update* and
        describes in which CRUD context the field is writable.
    :arg str required:
        Can be either *never*, *always*, *creation* or *update* and
        describes in which CRUD context the field is required as input.
    :arg callable fget:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which returns the current value of the resource's attribute:
        ``fget(self, resource, **kwargs)``.
    :arg fset:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which updates the current value of the resource's attribute:
        ``fget(self, resource, data, sp, **kwargs)``.
    """

    def __init__(self, *, name='', mapped_key='',
                 writable: Event = Event.ALWAYS,
                 required: Event = Event.NEVER,
                 fget=None, fset=None):
        #: The name of this field on the
        # :class:`~aiohttp_json_api.schema.Schema`
        #: it has been defined on. Please note, that not each field has a *key*
        #: (like some links or meta attributes).
        self.key = None

        #: A :class:`aiohttp_json_api.jsonpointer.JSONPointer`
        #: to this field in a JSON API resource object. The source pointer is
        #: set from the Schema class during initialisation.
        self.sp = None

        self.name = name
        self.mapped_key = mapped_key

        assert isinstance(writable, Event)
        self.writable = writable

        assert isinstance(required, Event)
        self.required = required

        self.fget = fget
        self.fset = fset
        self.fvalidators = list()

    def __call__(self, f):
        """The same as :meth:`getter`."""
        return self.getter(f)

    def getter(self, f):
        """
        Descriptor to change the getter.

        :seealso: :func:`aiohttp_json_api.schema.decorators.gets`
        """
        self.fget = f
        self.name = self.name or f.__name__
        return self

    def setter(self, f):
        """
        Descriptor to change the setter.

        :seealso: :func:`aiohttp_json_api.schema.decorators.sets`
        """
        self.fset = f
        return self

    def validator(self, f: typing.Callable,
                  step: Step = Step.POST_DECODE,
                  on: Event = Event.ALWAYS):
        """
        Descriptor to add a validator.

        :seealso: :func:`aiohttp_json_api.schema.decorators.validates`

        :arg Step step:
            Must be either *pre-decode* or *post-decode*.
        :arg Event on:
            The CRUD context in which the validator is invoked. Must
            be *never*, *always*, *creation* or *update*.
        """
        self.fvalidators.append({
            'validator': f, 'step': step, 'on': on
        })
        return self

    async def default_get(self, schema, resource, **kwargs):
        """Used if no *getter* has been defined. Can be overridden."""
        if self.mapped_key:
            return getattr(resource, self.mapped_key)
        return None

    async def default_set(self, schema, resource, data, sp, **kwargs):
        """Used if no *setter* has been defined. Can be overridden."""
        if self.mapped_key:
            setattr(resource, self.mapped_key, data)
        return None

    async def get(self, schema, resource, **kwargs):
        """
        Returns the value of the field on the resource.

        :arg ~aiohttp_json_api.schema.Schema schema:
            The schema this field has been defined on.
        """
        f = self.fget or self.default_get
        return await f(schema, resource, **kwargs)

    async def set(self, schema, resource, data, sp, **kwargs):
        """
        Changes the value of the field on the resource.

        :arg ~aiohttp_json_api.schema.Schema schema:
            The schema this field has been defined on.
        :arg data:
            The (decoded and validated) new value of the field
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            A JSON pointer to the source of the original input data.
        """
        assert self.writable not in Event.NEVER
        f = self.fset or self.default_set
        return await f(schema, resource, data, sp, **kwargs)

    def encode(self, schema, data, **kwargs):
        """
        Encodes the *data* returned from :meth:`get` so that it can be
        serialized with :func:`json.dumps`. Can be overridden.
        """
        return data

    def decode(self, schema, data, sp, **kwargs):
        """
        Decodes the raw *data* from the JSON API input document and returns it.
        Can be overridden.
        """
        return data

    def validate_pre_decode(self, schema, data, sp, context):
        """
        Validates the raw JSON API input for this field. This method is
        called before :meth:`decode`.

        :arg ~aiohttp_json_api.schema.Schema schema:
            The schema this field has been defined on.
        :arg data:
            The raw input data
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            A JSON pointer to the source of *data*.
        """
        for validator in self.fvalidators:
            if validator['step'] is not Step.PRE_DECODE:
                continue
            if validator['on'] not in (Event.ALWAYS, context.event):
                continue

            f = validator['validator']
            f(schema, data, sp)

    def validate_post_decode(self, schema, data, sp, context):
        """
        Validates the decoded input *data* for this field. This method is
        called after :meth:`decode`.

        :arg ~aiohttp_json_api.schema.Schema schema:
            The schema this field has been defined on.
        :arg data:
            The decoded input data
        :arg ~aiohttp_json_api.jsonpointer.JSONPointer sp:
            A JSON pointer to the source of *data*.
        """
        for validator in self.fvalidators:
            if validator['step'] is not Step.POST_DECODE:
                continue
            if validator['on'] not in (Event.ALWAYS, context.event):
                continue

            f = validator['validator']
            f(schema, data, sp)


class LinksObjectMixin(object):
    """
    Mixin for JSON API documents that contain a JSON API links object.

    The :meth:`BaseField.encode` receives an additional keyword argument *link*
    with the encoded links.

    :arg list links:
        A list of (transient) :class:`links <Link>`.
    """

    def __init__(self, links=None):
        self.links = {link.name: link for link in links} if links else {}

    def add_link(self, link):
        """
        Adds a new link to the links object.
        """
        self.links[link.name] = link
        return self


class Link(BaseField):
    """
    .. seealso::

        http://jsonapi.org/format/#document-links

    .. code-block:: python3

        class Article(Schema):

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
        If true, the *encode* method normalizes the link so that it is always
        an object.
    """

    def __init__(self, route='', *,
                 link_of='<resource>', name='', fget=None, normalize=True):
        super(Link, self).__init__(name=name, writable=Event.NEVER, fget=fget)

        self.normalize = bool(normalize)
        self.route = route
        self.link_of = link_of

    async def default_get(self, schema, resource, **kwargs):
        """Returns the formatted :attr:`href`."""
        url = schema.app.router[self.route].url_for(
            **schema.registry.ensure_identifier(resource, asdict=True)
        )
        return str(url)

    def encode(self, schema, data, context=None, **kwargs):
        """Normalizes the links object if wished."""
        url = schema.app.router[self.route].url_for(
            **schema.registry.ensure_identifier(data, asdict=True),
            relation=self.link_of
        )
        if context is not None:
            url = context.request.url.join(url)

        result = str(url)
        if not self.normalize:
            return result
        elif isinstance(result, str):
            return {'href': result}
        else:
            # assert isinstance(data, collections.Mapping)
            return result


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

        class Article(Schema):

            title = Attribute()

    Does the same as:

    .. code-block:: python3

        class Article(Schema):

            title = Attribute()

            @title.getter
            def title(self, article):
                return article.title

            @title.setter
            def title(self, article, new_title):
                article.title = new_title
                return None

    :arg bool meta:
        If true, the attribute is part of the resource's *meta* object.
    :arg \*\*kwargs:
        The init arguments for the :class:`BaseField`.
    """

    def __init__(self, *, meta=False, allow_none=False, **kwargs):
        super(Attribute, self).__init__(**kwargs)
        self.meta = bool(meta)
        self.allow_none = allow_none


class Relationship(BaseField, LinksObjectMixin):
    """
    .. seealso::

        http://jsonapi.org/format/#document-resource-object-relationships

    Additionaly to attributes and basic fields, we must know how to *include*
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
    :arg set foreign_types:
        A set with all foreign types. If given, this list is used to validate
        the input data. Leave it empty to allow all types.
    :arg callable finclude:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which returns the related resources:
        ``finclude(self, resource, **kwargs)``.
    :arg callable fquery:
        A method on a :class:`~aiohttp_json_api.schema.Schema`
        which returns the queries the related resources:
        ``fquery(self, resource, **kwargs)``.
    """

    #: True, if this is to-one relationship::
    #:
    #:      field.to_one == isinstance(field, ToOne)
    to_one = None

    #: True, if this is a to-many relationship::
    #:
    #:      field.to_many == isinstance(field, ToMany)
    to_many = None

    def __init__(self, *, dereference=True, require_data=Event.ALWAYS,
                 foreign_types=None, finclude=None, fquery=None, links=None,
                 **kwargs):
        BaseField.__init__(self, **kwargs)
        LinksObjectMixin.__init__(self, links=links)

        # NOTE: The related resources are loaded by the schema class for
        #       performance reasons (one big query vs many small ones).
        self.dereference = bool(dereference)

        self.foreign_types = frozenset(foreign_types or [])
        self.finclude = finclude
        self.fquery = fquery

        assert isinstance(require_data, Event)
        self.require_data = require_data

        # Add the default links.
        self.add_link(
            Link('jsonapi.relationships', name='self', link_of=self.name)
        )
        self.add_link(
            Link('jsonapi.related', name='related', link_of=self.name)
        )

    def includer(self, f):
        """
        Descriptor to change the includer.

        :seealso: :func:`~aiohttp_json_api.schema.decorators.includes`
        """
        self.finclude = f
        return f

    async def default_include(self, schema, resources, context, **kwargs):
        """Used if no *includer* has been defined. Can be overridden."""
        if self.mapped_key:
            compound_documents = []
            for resource in resources:
                compound_document = getattr(resource, self.mapped_key)
                if compound_document:
                    compound_documents.extend(compound_document)
            return compound_documents
        raise RuntimeError('No includer and mapped_key have been defined.')

    async def include(self, schema, resources, context, **kwargs):
        """
        Returns the related resources.

        :arg ~aiohttp_json_api.schema.Schema schema:
            The schema this field has been defined on.
        """
        f = self.finclude or self.default_include
        return await f(schema, resources, context, **kwargs)

    def query_(self, f):
        """
        Descriptor to change the query function.

        :seealso: :func:`~aiohttp_json_api.schema.decorators.queries`
        """
        self.fquery = f
        return self

    async def default_query(self, schema, resource, context, **kwargs):
        """Used of no *query* function has been defined. Can be overridden."""
        if self.mapped_key:
            return getattr(resource, self.mapped_key)
        raise RuntimeError('No query method and mapped_key have been defined.')

    async def query(self, schema, resource, context, **kwargs):
        """Queries the related resources."""
        f = self.fquery or self.default_query
        return await f(schema, resource, context, **kwargs)

    def validate_resource_identifier(self, schema, data, sp):
        """
        .. seealso::

            http://jsonapi.org/format/#document-resource-identifier-objects

        Asserts that *data* is a JSON API resource identifier with the correct
        *type* value.
        """
        if not isinstance(data, collections.Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        if not ('type' in data and 'id' in data):
            detail = 'Must contain a "type" and an "id" member.'
            raise InvalidValue(detail=detail, source_pointer=sp)

        if self.foreign_types and not data['type'] in self.foreign_types:
            detail = f'Unexpected type: "{data["type"]}".'
            raise InvalidValue(detail=detail, source_pointer=sp / 'type')

    def validate_relationship_object(self, schema, data, sp):
        """
        Asserts that *data* is a JSON API relationship object.

        *   *data* is a dictionary
        *   *data* must be not empty
        *   *data* may only have the members *data*, *links* or *meta*.
        *   *data* must contain a *data* member, if :attr:`dereference` or
            :attr:`require_data` is true.
        """
        if not isinstance(data, collections.Mapping):
            detail = 'Must be an object.'
            raise InvalidType(detail=detail, source_pointer=sp)

        if not data:
            detail = 'Must contain at least a "data", "links" or "meta" member.'
            raise InvalidValue(detail=detail, source_pointer=sp)

        if not (data.keys() <= {'links', 'data', 'meta'}):
            unexpected = (data.keys() - {'links', 'data', 'meta'}).pop()
            detail = f'Unexpected member: "{unexpected}".'
            raise InvalidValue(detail=detail, source_pointer=sp)

        if (self.dereference or self.require_data) and 'data' not in data:
            detail = 'The "data" member is required.'
            raise InvalidValue(detail=detail, source_pointer=sp)

    def validate_pre_decode(self, schema, data, sp, context):
        self.validate_relationship_object(schema, data, sp)
        super(Relationship, self).validate_pre_decode(schema, data, sp, context)
