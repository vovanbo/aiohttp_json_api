from aiohttp_json_api.errors import ResourceNotFound
from aiohttp_json_api.schema import BaseSchema, fields, relationships, sets
from aiohttp_json_api.common import Event

from examples.fantasy.models import Store


class StoreSchema(BaseSchema):
    resource_class = Store
    type = 'stores'

    name = fields.String()
    created_at = fields.DateTime()
    updated_at = fields.DateTime(allow_none=True)

    async def fetch_resource(self, resource_id, context, **kwargs):
        pass

    async def delete_resource(self, resource_id, context, **kwargs):
        pass

    async def query_collection(self, context, **kwargs):
        async with self.app['db'].acquire() as connection:
            results = await Store.fetch_stores(connection)

        return results.values()

    async def query_resource(self, resource_id, context, **kwargs):
        pass

