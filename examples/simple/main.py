"""Simple JSON API application with in-memory storage."""

import asyncio
import logging
from collections import defaultdict, OrderedDict

import time
from aiohttp import web

from aiohttp_json_api import setup_jsonapi


def setup_fixtures(app):
    from examples.simple.models import Article, People, Comment

    peoples = (
        People(1, 'Some', 'User'),
        People(2, 'Another', 'Man'),
        People(9, 'Dan', 'Gebhardt', 'dgeb'),
    )

    comments = (
        Comment(5, 'First!', peoples[0]),
        Comment(12, 'I like XML better', peoples[2])
    )

    articles = (
        Article(1, 'JSON API paints my bikeshed!', peoples[2],
                comments),
    )

    for entities in (peoples, comments, articles):
        for entity in entities:
            app['storage'][entity.__class__.__name__][str(entity.id)] = entity

    return app


async def init() -> web.Application:
    from examples.simple.schemas import (
        ArticleSchema, CommentSchema, PeopleSchema
    )

    app = web.Application(debug=True)
    app['storage'] = defaultdict(OrderedDict)

    setup_jsonapi(
        app,
        [
            ArticleSchema, CommentSchema, PeopleSchema
        ],
        meta={'example': {'version': '0.0.1'}},
    )
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
