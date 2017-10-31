import abc
from typing import Sequence

from aiohttp_json_api.helpers import ensure_collection


class BaseModel(abc.ABC):
    def __init__(self, id: int):
        self._id = id

    def __hash__(self):
        return hash((self.__class__.__name__, self._id))

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = int(value)


class Comment(BaseModel):
    def __init__(self, id: int, body: str, author: 'People'):
        super().__init__(id)
        self.body = body
        self.author = author


class People(BaseModel):
    def __init__(self, id: int, first_name: str, last_name: str,
                 twitter: str = None):
        super().__init__(id)
        self.first_name = first_name
        self.last_name = last_name
        self.twitter = twitter


class Article(BaseModel):
    def __init__(self, id: int, title: str, author: 'People',
                 comments: Sequence['Comment']):
        super().__init__(id)
        self.title = title
        self.author = author
        self.comments = list(ensure_collection(comments))
