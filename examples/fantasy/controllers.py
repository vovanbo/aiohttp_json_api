from aiohttp_json_api.controller import DefaultController
from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.fields.decorators import includes

import examples.fantasy.tables as tbl
from examples.fantasy.models import Author


class CommonController(DefaultController):
    async def fetch_resource(self, resource_id, **kwargs):
        model = self.ctx.schema.opts.resource_cls
        async with self.ctx.app['db'].acquire() as connection:
            result = await model.fetch_one(connection, resource_id)

        if result is None:
            raise ResourceNotFound(type=self.ctx.resource_type, id=resource_id)

        return result

    async def query_collection(self, **kwargs):
        model = self.ctx.schema.opts.resource_cls
        async with self.ctx.app['db'].acquire() as connection:
            results = await model.fetch_many(connection)

        return results.values()

    async def query_resource(self, resource_id, **kwargs):
        return await self.fetch_resource(resource_id, **kwargs)

    async def delete_resource(self, resource_id, **kwargs):
        pass


class BooksController(CommonController):
    @includes('author')
    async def include_authors(self, field, resources, **kwargs):
        authors_ids = set(r.author.id for r in resources)

        if not authors_ids:
            return ()

        cte = Author.cte(where=(tbl.authors.c.id.in_(authors_ids)))

        async with self.ctx.app['db'].acquire() as connection:
            results = await Author.fetch_many(connection, cte)

        return results.values()
