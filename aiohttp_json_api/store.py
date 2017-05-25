from collections import OrderedDict, defaultdict
from functools import partial

import attr


@attr.s
class Store:
    resources = attr.ib(default=attr.Factory(OrderedDict))
    compound_documents = attr.ib(default=attr.Factory(OrderedDict))
    relationships = attr.ib(
        default=attr.Factory(partial(defaultdict, set))
    )