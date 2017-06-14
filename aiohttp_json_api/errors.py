"""
Errors
======
"""
import json
from http import HTTPStatus

import inflection

__all__ = (
    'Error',
    'ErrorList',
    # 4xx errors
    'HTTPBadRequest',
    'HTTPUnauthorized',
    'HTTPForbidden',
    'HTTPNotFound',
    'HTTPMethodNotAllowed',
    'HTTPNotAcceptable',
    'HTTPConflict',
    'HTTPGone',
    'HTTPPreConditionFailed',
    'HTTPUnsupportedMediaType',
    'HTTPUnprocessableEntity',
    'HTTPLocked',
    'HTTPFailedDependency',
    'HTTPTooManyRequests',

    # 5xx errors
    'HTTPInternalServerError',
    'HTTPNotImplemented',
    'HTTPBadGateway',
    'HTTPServiceUnavailable',
    'HTTPGatewayTimeout',
    'HTTPVariantAlsoNegotiates',
    'HTTPInsufficientStorage',
    'HTTPNotExtended',

    # JSONAPI errors
    'ValidationError',
    'InvalidType',
    'InvalidValue',
    'UnresolvableIncludePath',
    'UnsortableField',
    'UnsortableField',
    'ResourceNotFound',
)


class Error(Exception):
    """
    :seealso: http://jsonapi.org/format/#errors

    This is the base class for all exceptions thrown by the API. All subclasses
    of this exception are catched and converted into a response.
    All other exceptions will be replaced by an HTTPInternalServerError
    exception.

    :arg int http_status:
        The HTTP status code applicable to this problem.
    :arg str id:
        A unique identifier for this particular occurrence of the problem.
    :arg str about:
        A link that leeds to further details about this particular occurrence
        of the problem.
    :arg str code:
        An application specific error code, expressed as a string value.
    :arg str title:
        A short, human-readable summay of the problem that SHOULD not change
        from occurrence to occurrence of the problem, except for purposes
        of localization. The default value is the class name.
    :arg str detail:
        A human-readable explanation specific to this occurrence
        of the problem.
    :arg source_pointer:
        A JSON Pointer [RFC6901] to the associated entity in the request
        document [e.g. `"/data"` for a primary data object, or
        `"/data/attributes/title"` for a specific attribute].
    :arg str source_parameter:
        A string indicating which URI query parameter caused the error.
    :arg dict meta:
        A meta object containing non-standard meta-information about the error.
    """
    status = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, *, id_=None, about='',
                 code=None, title=None, detail='', source_parameter=None,
                 source_pointer=None, meta=None):
        self.id = id_
        self.about = about
        self.code = code
        self.title = title if title is not None else self.status.phrase
        self.detail = detail if detail else self.status.description
        self.source_pointer = source_pointer
        self.source_parameter = source_parameter
        self.meta = meta if meta is not None else dict()

    def __str__(self):
        """
        Returns the :attr:`detail` attribute per default.
        """
        return json.dumps(self.json, indent=4, sort_keys=True)

    @property
    def json(self):
        """
        The serialized version of this error.
        """
        d = dict()
        if self.id is not None:
            d['id'] = str(self.id)
        d['status'] = self.status.value
        d['title'] = self.title
        if self.about:
            d['links'] = dict()
            d['links']['about'] = self.about
        if self.code:
            d['code'] = self.code
        if self.detail:
            d['detail'] = self.detail
        if self.source_pointer or self.source_parameter:
            d['source'] = dict()
            if self.source_pointer:
                d['source']['pointer'] = \
                    inflection.dasherize(self.source_pointer.path)
            if self.source_parameter:
                d['source']['parameter'] = self.source_parameter
        if self.meta:
            d['meta'] = self.meta
        return d


class ErrorList(Exception):
    """
    Can be used to store a list of exceptions, which occur during the
    execution of a request.

    :seealso: http://jsonapi.org/format/#error-objects
    :seealso: http://jsonapi.org/examples/#error-objects-multiple-errors
    """

    def __init__(self, errors=None):
        self.errors = list()
        if errors:
            self.extend(errors)

    def __bool__(self):
        return bool(self.errors)

    def __len__(self):
        return len(self.errors)

    def __str__(self):
        return json.dumps(self.json, indent=4, sort_keys=True)

    @property
    def status_code(self):
        """
        The most specific http status code, which matches all exceptions.
        """
        if not self.errors:
            return None
        elif len(self.errors) == 1:
            return self.errors[0].status_code
        elif any(400 <= err.status_code.value < 500 for err in self.errors):
            return HTTPStatus.BAD_REQUEST
        else:
            return HTTPStatus.INTERNAL_SERVER_ERROR

    def append(self, error):
        """
        Appends the :class:`Error` error to the error list.

        :arg Error error:
        """
        if not isinstance(error, Error):
            raise TypeError('*error* must be of type Error')
        self.errors.append(error)

    def extend(self, errors):
        """
        Appends all errors in *errors* to the list. *errors* must be an
        :class:`ErrorList` or a sequence of :class:`Error`.

        :arg errors:
        """
        if isinstance(errors, ErrorList):
            self.errors.extend(errors.errors)
        elif all(isinstance(err, Error) for err in errors):
            self.errors.extend(errors)
        else:
            raise TypeError(
                '*errors* must be of type ErrorList or a sequence of Error.'
            )

    @property
    def json(self):
        """
        Creates the JSONapi error object.

        :seealso: http://jsonapi.org/format/#error-objects
        """
        return [error.json for error in self.errors]


# Common HTTP errors
# ------------------

# 4xx errors
# ~~~~~~~~~~

class HTTPBadRequest(Error):
    status = HTTPStatus.BAD_REQUEST


class HTTPUnauthorized(Error):
    status = HTTPStatus.UNAUTHORIZED


class HTTPForbidden(Error):
    status = HTTPStatus.FORBIDDEN


class HTTPNotFound(Error):
    status = HTTPStatus.NOT_FOUND


class HTTPMethodNotAllowed(Error):
    status = HTTPStatus.METHOD_NOT_ALLOWED


class HTTPNotAcceptable(Error):
    status = HTTPStatus.NOT_ACCEPTABLE


class HTTPConflict(Error):
    status = HTTPStatus.CONFLICT


class HTTPGone(Error):
    status = HTTPStatus.GONE


class HTTPPreConditionFailed(Error):
    status = HTTPStatus.PRECONDITION_FAILED


class HTTPUnsupportedMediaType(Error):
    status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE


class HTTPUnprocessableEntity(Error):
    status = HTTPStatus.UNPROCESSABLE_ENTITY


class HTTPLocked(Error):
    status = HTTPStatus.LOCKED


class HTTPFailedDependency(Error):
    status = HTTPStatus.FAILED_DEPENDENCY


class HTTPTooManyRequests(Error):
    status = HTTPStatus.TOO_MANY_REQUESTS


# 5xx errors
# ~~~~~~~~~~

class HTTPInternalServerError(Error):
    status = HTTPStatus.INTERNAL_SERVER_ERROR


class HTTPNotImplemented(Error):
    status = HTTPStatus.NOT_IMPLEMENTED


class HTTPBadGateway(Error):
    status = HTTPStatus.BAD_GATEWAY


class HTTPServiceUnavailable(Error):
    status = HTTPStatus.SERVICE_UNAVAILABLE


class HTTPGatewayTimeout(Error):
    status = HTTPStatus.GATEWAY_TIMEOUT


class HTTPVariantAlsoNegotiates(Error):
    status = HTTPStatus.VARIANT_ALSO_NEGOTIATES


class HTTPInsufficientStorage(Error):
    status = HTTPStatus.INSUFFICIENT_STORAGE


class HTTPNotExtended(Error):
    status = HTTPStatus.NOT_EXTENDED


# special JSONAPI errors
# ----------------------

class ValidationError(HTTPBadRequest):
    """
    Raised, if the structure of a json document in a request body is invalid.

    Please note, that this does not include semantic errors, like an unknown
    typename.

    This type of exception is used often in the :mod:`jsonapi.validator`
    and :mod:`jsonapi.validation` modules.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class InvalidValue(ValidationError):
    """
    Raised if an input value (part of a JSON API document) has an invalid
    value.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class InvalidType(ValidationError):
    """
    Raised if an input value (part of a JSON API document) has the wrong type.

    This type of exception is often raised during decoding.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class MissingField(ValidationError):
    """
    Raised if a field is required but not part of the input data.

    :seealso: http://jsonapi.org/format/#document-structure
    """

    def __init__(self, type, field, **kwargs):
        kwargs.setdefault(
            'detail',
            f"The field '{type}.{field}' is required."
        )
        super(MissingField, self).__init__(**kwargs)


class UnresolvableIncludePath(HTTPBadRequest):
    """
    Raised if an include path does not exist. The include path is part
    of the ``include`` query argument. (An include path is invalid, if a
    relationship mentioned in it is not defined on a resource).

    :seealso: http://jsonapi.org/format/#fetching-includes
    """

    def __init__(self, path, **kwargs):
        if not isinstance(path, str):
            path = ".".join(path)

        kwargs.setdefault(
            'detail',
            f"The include path '{path}' does not exist."
        )
        kwargs.setdefault('source_parameter', 'include')
        super(UnresolvableIncludePath, self).__init__(**kwargs)


class UnsortableField(HTTPBadRequest):
    """
    If a field is used as sort key, but sorting is not supported on this field.

    :seealso: http://jsonapi.org/format/#fetching-sorting
    """

    def __init__(self, type, field, **kwargs):
        kwargs.setdefault(
            'detail',
            f"The field '{type}.{field}' can not be used for sorting."
        )
        kwargs.setdefault('source_parameter', 'sort')
        super(UnsortableField, self).__init__(**kwargs)


class UnfilterableField(HTTPBadRequest):
    """
    If a filter should be used on a field, which does not support the
    filter.

    :seealso: http://jsonapi.org/format/#fetching-filtering
    """

    def __init__(self, type, field, filtername, **kwargs):
        kwargs.setdefault(
            "detail",
            f"The field '{type}.{field}' does not support "
            f"the '{filtername}' filter."
        )
        kwargs.setdefault('source_parameter', f'filter[{field}]')
        super(UnfilterableField, self).__init__(**kwargs)


class ResourceNotFound(HTTPNotFound):
    """
    Raised, if a resource does not exist.
    """

    def __init__(self, type, id, **kwargs):
        kwargs.setdefault(
            "detail",
            f"The resource (type='{type}', id='{id}') does not exist."
        )
        super(ResourceNotFound, self).__init__(**kwargs)
