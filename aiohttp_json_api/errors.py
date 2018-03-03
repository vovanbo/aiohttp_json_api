"""Errors."""

from http import HTTPStatus

from .encoder import json_dumps

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
    Base class for all exceptions thrown by the API.

    All subclasses of this exception are catches and converted into a response.
    All other exceptions will be replaced by an HTTPInternalServerError
    exception.

    :seealso: http://jsonapi.org/format/#errors
    """

    status = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, *, id_=None, about='',
                 code=None, title=None, detail='', source_parameter=None,
                 source_pointer=None, meta=None):
        """
        Error instance initializer.

        :param id_:
            A unique identifier for this particular occurrence of the problem.
        :param about:
            A link that leeds to further details about this particular
            occurrence of the problem.
        :param code:
            An application specific error code, expressed as a string value.
        :param title:
            A short, human-readable summay of the problem that
            SHOULD not change from occurrence to occurrence of the problem,
            except for purposes of localization.
            The default value is the class name.
        :param detail:
            A human-readable explanation specific to this occurrence
            of the problem.
        :param source_parameter:
            A string indicating which URI query parameter caused the error.
        :param source_pointer:
            A JSON Pointer [RFC6901] to the associated entity in the request
            document [e.g. `"/data"` for a primary data object, or
            `"/data/attributes/title"` for a specific attribute].
        :param meta:
            A meta object containing non-standard meta-information
            about the error.
        """
        super(Error, self).__init__()
        self.id = id_
        self.about = about
        self.code = code
        self.title = title if title is not None else self.status.phrase
        self.detail = detail if detail else self.status.description
        self.source_pointer = source_pointer
        self.source_parameter = source_parameter
        self.meta = meta if meta is not None else dict()

    def __str__(self):
        """Return the :attr:`detail` attribute per default."""
        return json_dumps(self.as_dict, indent=4, sort_keys=True)

    @property
    def as_dict(self):
        """Represent instance of Error as dictionary."""
        result = {}
        if self.id is not None:
            result['id'] = str(self.id)
        result['status'] = str(self.status.value)
        result['title'] = self.title
        if self.about:
            result['links'] = dict()
            result['links']['about'] = self.about
        if self.code:
            result['code'] = self.code
        if self.detail:
            result['detail'] = self.detail
        if self.source_pointer or self.source_parameter:
            result['source'] = dict()
            if self.source_pointer:
                result['source']['pointer'] = self.source_pointer
            if self.source_parameter:
                result['source']['parameter'] = self.source_parameter
        if self.meta:
            result['meta'] = self.meta
        return result


class ErrorList(Exception):
    """
    Exception contains list of errors.

    Can be used to store a list of exceptions, which occur during the
    execution of a request.

    :seealso: http://jsonapi.org/format/#error-objects
    :seealso: http://jsonapi.org/examples/#error-objects-multiple-errors
    """

    def __init__(self, errors=None):
        """Error list initializer."""
        self.errors = list()
        if errors:
            self.extend(errors)

    def __bool__(self):
        """Return True if errors are exists."""
        return bool(self.errors)

    def __len__(self):
        """Return count of errors."""
        return len(self.errors)

    def __str__(self):
        """Return string representation of errors list."""
        return json_dumps(self.json, indent=4, sort_keys=True)

    @property
    def status(self):
        """
        Return the most specific HTTP status code for all errors.

        For single error in list returns its status.
        For many errors returns maximal status code.
        """
        if not self.errors:
            return None
        elif len(self.errors) == 1:
            return self.errors[0].status
        elif any(400 <= err.status < 500 for err in self.errors):
            return max(e.status for e in self.errors)

        return HTTPStatus.INTERNAL_SERVER_ERROR

    def append(self, error):
        """
        Append the :class:`Error` error to the error list.

        :arg Error error: JSON API Error instance
        """
        if not isinstance(error, Error):
            raise TypeError('*error* must be of type Error')
        self.errors.append(error)

    def extend(self, errors):
        """
        Append errors to the list.

        :arg errors: :class:`ErrorList` or a sequence of :class:`Error`.
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
        Create the JSON API error object.

        :seealso: http://jsonapi.org/format/#error-objects
        """
        return [error.as_dict for error in self.errors]


# Common HTTP errors
# ------------------

# 4xx errors
# ~~~~~~~~~~

class HTTPBadRequest(Error):
    """
    HTTP 400 Bad Request.

    The request could not be fulfilled due to the incorrect syntax
    of the request.
    """

    status = HTTPStatus.BAD_REQUEST


class HTTPUnauthorized(Error):
    """
    HTTP 401 Unauthorized.

    The requester is not authorized to access the resource.
    This is similar to 403 but is used in cases where authentication
    is expected but has failed or has not been provided.
    """

    status = HTTPStatus.UNAUTHORIZED


class HTTPForbidden(Error):
    """
    HTTP 403 Forbidden.

    The request was formatted correctly but the server is refusing to supply
    the requested resource. Unlike 401, authenticating will not make
    a difference in the server's response.
    """

    status = HTTPStatus.FORBIDDEN


class HTTPNotFound(Error):
    """
    HTTP 404 Not found.

    The resource could not be found. This is often used as a catch-all
    for all invalid URIs requested of the server.
    """

    status = HTTPStatus.NOT_FOUND


class HTTPMethodNotAllowed(Error):
    """
    HTTP 405 Method not allowed.

    The resource was requested using a method that is not allowed.
    For example, requesting a resource via a POST method when the resource
    only supports the GET method.
    """

    status = HTTPStatus.METHOD_NOT_ALLOWED


class HTTPNotAcceptable(Error):
    """
    HTTP 406 Not acceptable.

    The resource is valid, but cannot be provided in a format specified
    in the Accept headers in the request.
    """

    status = HTTPStatus.NOT_ACCEPTABLE


class HTTPConflict(Error):
    """
    HTTP 409 Conflict.

    The request cannot be completed due to a conflict in the request
    parameters.
    """

    status = HTTPStatus.CONFLICT


class HTTPGone(Error):
    """
    HTTP 410 Gone.

    The resource is no longer available at the requested URI and
    no redirection will be given.
    """

    status = HTTPStatus.GONE


class HTTPPreConditionFailed(Error):
    """
    HTTP 412 Precondition failed.

    The server does not meet one of the preconditions specified by the client.
    """

    status = HTTPStatus.PRECONDITION_FAILED


class HTTPUnsupportedMediaType(Error):
    """
    HTTP 415 Unsupported media type.

    The client provided data with a media type that the server
    does not support.
    """

    status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE


class HTTPUnprocessableEntity(Error):
    """
    HTTP 422 Unprocessable entity.

    The request was formatted correctly but cannot be processed in its current
    form. Often used when the specified parameters fail validation errors.

    WebDAV - `RFC 4918 <https://tools.ietf.org/html/rfc4918>`_
    """

    status = HTTPStatus.UNPROCESSABLE_ENTITY


class HTTPLocked(Error):
    """
    HTTP 423 Locked.

    The requested resource was found but has been locked and will
    not be returned.

    WebDAV - `RFC 4918 <https://tools.ietf.org/html/rfc4918>`_
    """

    status = HTTPStatus.LOCKED


class HTTPFailedDependency(Error):
    """
    HTTP 424 Failed dependency.

    The request failed due to a failure of a previous request.

    WebDAV - `RFC 4918 <https://tools.ietf.org/html/rfc4918>`_
    """

    status = HTTPStatus.FAILED_DEPENDENCY


class HTTPTooManyRequests(Error):
    """
    HTTP 429 Too many requests.

    The user has sent too many requests in a given amount of time
    ("rate limiting").

    Additional HTTP Status Codes -
    `RFC 6585 <https://tools.ietf.org/html/rfc6585#section-4>`_
    """

    status = HTTPStatus.TOO_MANY_REQUESTS


# 5xx errors
# ~~~~~~~~~~

class HTTPInternalServerError(Error):
    """
    HTTP 500 Internal server error.

    A generic status for an error in the server itself.
    """

    status = HTTPStatus.INTERNAL_SERVER_ERROR


class HTTPNotImplemented(Error):
    """
    HTTP 501 Not implemented.

    The server cannot respond to the request. This usually implies that
    the server could possibly support the request in the future —
    otherwise a 4xx status may be more appropriate.
    """

    status = HTTPStatus.NOT_IMPLEMENTED


class HTTPBadGateway(Error):
    """
    HTTP 502 Bad gateway.

    The server is acting as a proxy and did not receive an acceptable response
    from the upstream server.
    """

    status = HTTPStatus.BAD_GATEWAY


class HTTPServiceUnavailable(Error):
    """
    HTTP 503 Service unavailable.

    The server is down and is not accepting requests.
    """

    status = HTTPStatus.SERVICE_UNAVAILABLE


class HTTPGatewayTimeout(Error):
    """
    HTTP 504 Gateway timeout.

    The server is acting as a proxy and did not receive a response from
    the upstream server.
    """

    status = HTTPStatus.GATEWAY_TIMEOUT


class HTTPVariantAlsoNegotiates(Error):
    """
    HTTP 506 Variant also negotiates.

    Transparent content negotiation for the request results in a circular
    reference.
    """

    status = HTTPStatus.VARIANT_ALSO_NEGOTIATES


class HTTPInsufficientStorage(Error):
    """
    HTTP 507 Insufficient storage.

    The user or server does not have sufficient storage quota to fulfill
    the request.

    WebDAV - `RFC 4918 <https://tools.ietf.org/html/rfc4918>`_
    """

    status = HTTPStatus.INSUFFICIENT_STORAGE


class HTTPNotExtended(Error):
    """
    HTTP 510 Not extended.

    Further extensions to the request are necessary for it to be fulfilled.
    """

    status = HTTPStatus.NOT_EXTENDED


# special JSONAPI errors
# ----------------------

class ValidationError(HTTPBadRequest):
    """
    JSON API validation error. HTTP 400 Bad request.

    Raised, if the structure of a json document in a request body is invalid.

    Please note, that this does not include semantic errors, like an unknown
    typename.

    This type of exception is used often in the :mod:`jsonapi.validator`
    and :mod:`jsonapi.validation` modules.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class InvalidValue(ValidationError):
    """
    JSON API invalid value error. HTTP 400 Bad request.

    Raised if an input value (part of a JSON API document) has an invalid
    value.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class InvalidType(ValidationError):
    """
    JSON API invalid type error. HTTP 400 Bad request.

    Raised if an input value (part of a JSON API document) has the wrong type.

    This type of exception is often raised during decoding.

    :seealso: http://jsonapi.org/format/#document-structure
    """


class MissingField(ValidationError):
    """
    JSON API missing field error. HTTP 400 Bad request.

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
    JSON API unresolvable include path error. HTTP 400 Bad request.

    Raised if an include path does not exist. The include path is part
    of the ``include`` query argument. (An include path is invalid, if a
    relationship mentioned in it is not defined on a resource).

    :seealso: http://jsonapi.org/format/#fetching-includes
    """

    def __init__(self, path, **kwargs):
        """
        Error initializer.

        :param path: Unresolvable include path
        :param kwargs: Additional arguments to base error
        """
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
    JSON API unsortable field. HTTP 400 Bad request.

    If a field is used as sort key, but sorting is not supported on this field.

    :seealso: http://jsonapi.org/format/#fetching-sorting
    """

    def __init__(self, type, field, **kwargs):
        """
        Unsortable field error initializer.

        :param type: Type of resource
        :param field: Field of resource
        :param kwargs: Additional arguments to base error
        """
        kwargs.setdefault(
            'detail',
            f"The field '{type}.{field}' can not be used for sorting."
        )
        kwargs.setdefault('source_parameter', 'sort')
        super(UnsortableField, self).__init__(**kwargs)


class UnfilterableField(HTTPBadRequest):
    """
    JSON API unfilterable field. HTTP 400 Bad request.

    If a filter should be used on a field, which does not support the
    filter.

    :seealso: http://jsonapi.org/format/#fetching-filtering
    """

    def __init__(self, type, field, filtername, **kwargs):
        """
        Unfilterable field error initializer.

        :param type: Type of resource
        :param field: Field of resource
        :param filtername: Name of filter
        :param kwargs: Additional arguments to base error
        """
        kwargs.setdefault(
            "detail",
            f"The field '{type}.{field}' does not support "
            f"the '{filtername}' filter."
        )
        kwargs.setdefault('source_parameter', f'filter[{field}]')
        super(UnfilterableField, self).__init__(**kwargs)


class ResourceNotFound(HTTPNotFound):
    """
    JSON API resource not found error. HTTP 404 Not found.

    Raised, if a resource does not exist.
    """

    def __init__(self, type, id, **kwargs):
        """
        Resource not found error initializer.

        :param type: Type of resource
        :param id: Resource identifier
        :param kwargs: Additional arguments to base error
        """
        kwargs.setdefault(
            "detail",
            f"The resource (type='{type}', id='{id}') does not exist."
        )
        super(ResourceNotFound, self).__init__(**kwargs)
