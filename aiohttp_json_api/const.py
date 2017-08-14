"""Common constants."""

import re

JSONAPI = 'jsonapi'
JSONAPI_CONTENT_TYPE = 'application/vnd.api+json'
ALLOWED_MEMBER_NAME_RULE = \
    r'[a-zA-Z0-9]([a-zA-Z0-9\-_]+[a-zA-Z0-9]|[a-zA-Z0-9]?)'
ALLOWED_MEMBER_NAME_REGEX = re.compile('^' + ALLOWED_MEMBER_NAME_RULE + '$')
