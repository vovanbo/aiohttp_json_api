"""Simple JSON API application with in-memory storage."""

import asyncio
import logging
from collections import defaultdict, OrderedDict

import time
from aiohttp import web

from aiohttp_json_api import setup_jsonapi
from aiohttp_json_api.const import JSONAPI


def setup_fixtures(app):
    from examples.simple.models import Article, People, Comment

    registry = app[JSONAPI]['registry']

    people = tuple(sorted(People.populate(), key=lambda p: p.id))
    comments = tuple(sorted(Comment.populate(people), key=lambda c: c.id))
    articles = tuple(sorted(Article.populate(comments, people),
                            key=lambda a: a.id))

    for entities in (people, comments, articles):
        for entity in entities:
            # ResourceID for entity
            resource_id = registry.ensure_identifier(entity)
            app['storage'][entity.__class__][resource_id] = entity

    return app


async def init() -> web.Application:
    from examples.simple.schemas import (
        ArticleSchema, CommentSchema, PeopleSchema
    )

    app = web.Application(debug=True)
    app['storage'] = defaultdict(OrderedDict)

    setup_jsonapi(app, (ArticleSchema, CommentSchema, PeopleSchema),
                  meta={'example': {'version': '0.0.1'}})
    # After JSON API application setup fixtures able to use Registry if needed.
    # In setup_fixtures function, Registry will be used to setup IDs
    # of saved entities.
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
    web.run_app(app,
                access_log_format='%a (%{X-Real-IP}i) %t "%r" %s %b %Tf '
                                  '"%{Referrer}i" "%{User-Agent}i"')


if __name__ == '__main__':
    main()
