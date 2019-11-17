from typing import Iterable

from aiohttp_json_api.controller import BaseController
from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.fields.decorators import includes

import examples.fantasy.tables as tbl
from examples.fantasy.entities import Author
from examples.fantasy.repositories import Repository
from examples.fantasy.repositories.authors import AuthorsRepository
from examples.fantasy.repositories.books import BooksRepository
from examples.fantasy.repositories.chapters import ChaptersRepository
from examples.fantasy.repositories.photos import PhotoRepository
from examples.fantasy.repositories.stores import StoresRepository


class CommonController(BaseController):
    repository: Repository

    async def create_resource(self, data, **kwargs):
        pass

    async def fetch_resource(self, resource_id, **kwargs):
        async with self.ctx.app['db'].acquire() as connection:
            result = await self.repository.get_one(connection, resource_id)

        if result is None:
            raise ResourceNotFound(type=self.ctx.resource_type, id=resource_id)

        return result

    async def query_collection(self, **kwargs):
        async with self.ctx.app['db'].acquire() as connection:
            results = await self.repository.get_many(connection)
        return results.values()

    async def query_resource(self, resource_id, **kwargs):
        return await self.fetch_resource(resource_id, **kwargs)

    async def delete_resource(self, resource_id, **kwargs):
        pass


class AuthorsController(CommonController):
    repository = AuthorsRepository


class BooksController(CommonController):
    repository = BooksRepository

    @includes('author')
    async def include_authors(self, field, resources, **kwargs) -> Iterable[Author]:
        authors_ids = set(r.author.id for r in resources)

        if not authors_ids:
            return ()

        cte = AuthorsRepository.cte(where=(tbl.authors.c.id.in_(authors_ids)))
        async with self.ctx.app['db'].acquire() as connection:
            results = await AuthorsRepository.get_many(connection, cte=cte)

        return results.values()


class ChaptersController(CommonController):
    repository = ChaptersRepository


class StoresController(CommonController):
    repository = StoresRepository


class PhotosController(CommonController):
    repository = PhotoRepository
