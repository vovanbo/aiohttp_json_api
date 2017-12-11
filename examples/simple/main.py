#!/usr/bin/env python
"""Simple JSON API application example with in-memory storage."""

import asyncio
import logging
from collections import defaultdict, OrderedDict

import time
from aiohttp import web

from aiohttp_json_api import setup_jsonapi
from aiohttp_json_api.common import JSONAPI


def setup_fixtures(app):
    from examples.simple.models import Article, People, Comment

    registry = app[JSONAPI]['registry']

    people = tuple(sorted(People.populate(), key=lambda p: p.id))
    comments = tuple(sorted(Comment.populate(people), key=lambda c: c.id))
    articles = tuple(sorted(Article.populate(comments, people),
                            key=lambda a: a.id))

    for resources in (people, comments, articles):
        for resource in resources:
            # Registry have a helper to return a ResourceID of instances
            # of registered resource classes
            resource_id = registry.ensure_identifier(resource)
            app['storage'][resource_id.type][resource_id.id] = resource

    return app


async def init() -> web.Application:
    from examples.simple.controllers import (
        SimpleController, CommentsController
    )
    from examples.simple.schemas import (
        ArticleSchema, CommentSchema, PeopleSchema
    )

    app = web.Application(debug=True)
    app['storage'] = defaultdict(OrderedDict)

    # Note that we pass schema classes, not instances of them.
    # Schemas instances will be initialized application-wide.
    # Schema instance is stateless, therefore any request state must be passed
    # to each of Schema's method as JSONAPIContext instance.
    # JSONAPIContext instance created automatically in JSON API middleware
    # for each request. JSON API handlers use it in calls of Schema's methods.
    setup_jsonapi(
        app,
        {
            ArticleSchema: SimpleController,
            CommentSchema: CommentsController,
            PeopleSchema: SimpleController,
        },
        meta={'example': {'version': '0.0.1'}}
    )

    # After setup of JSON API application fixtures able to use Registry
    # if needed. In setup_fixtures function, Registry will be used
    # to get ResourceID as keys of resources saved to simple storage.
    setup_fixtures(app)

    return app


def main():
    loop = asyncio.get_event_loop()

    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            root.removeHandler(handler)

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)-8s [%(asctime)s.%(msecs)03d] '
               '(%(name)s): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.Formatter.converter = time.gmtime

    app = loop.run_until_complete(init())

    # More useful log format than default
    log_format = '%a (%{X-Real-IP}i) %t "%r" %s %b %Tf ' \
                 '"%{Referrer}i" "%{User-Agent}i"'
    web.run_app(app, access_log_format=log_format)


if __name__ == '__main__':
    main()
