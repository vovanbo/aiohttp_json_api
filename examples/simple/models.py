import abc
import random
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


class People(BaseModel):
    def __init__(self, id: int, first_name: str, last_name: str,
                 twitter: str = None):
        super().__init__(id)
        self.first_name = first_name
        self.last_name = last_name
        self.twitter = twitter

    @staticmethod
    def populate(count=100):
        import mimesis

        person = mimesis.Personal()

        return (
            People(id=person.cid(), first_name=person.name(),
                   last_name=person.surname(), twitter=person.username())
            for _ in range(count)
        )


class Comment(BaseModel):
    def __init__(self, id: int, body: str, author: 'People'):
        super().__init__(id)
        self.body = body
        self.author = author

    @staticmethod
    def populate(authors: Sequence['People'], count=100):
        import mimesis

        cid = mimesis.Numbers()
        comment = mimesis.Text()

        return (
            Comment(id=cid.between(1, count),
                    body=comment.sentence(),
                    author=random.choice(authors))
            for _ in range(count)
        )


class Article(BaseModel):
    def __init__(self, id: int, title: str, author: 'People',
                 comments: Sequence['Comment']):
        super().__init__(id)
        self.title = title
        self.author = author
        self.comments = list(ensure_collection(comments))

    @staticmethod
    def populate(comments: Sequence['Comment'], authors: Sequence['People'],
                 count=100):
        import mimesis

        aid = mimesis.Numbers()
        article = mimesis.Text()
        answers = list(comments)

        def get_random_answers(max):
            counter = 0
            while answers and counter < max:
                yield answers.pop(random.randint(0, len(answers) - 1))
                counter += 1

        return (
            Article(id=aid.between(1, count),
                    title=article.title(),
                    author=random.choice(authors),
                    comments=[
                        c for c in get_random_answers(random.randint(1, 10))
                    ])
            for _ in range(count)
        )
