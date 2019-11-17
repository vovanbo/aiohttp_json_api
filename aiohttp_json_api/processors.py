import abc
import inspect
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from aiohttp_json_api.fields.decorators import Tag


class ProcessorsMeta(abc.ABCMeta):
    def _resolve_processors(cls) -> None:
        """
        Add in the decorated processors
        By doing this after constructing the class, we let standard inheritance
        do all the hard work.

        Almost the same as https://github.com/marshmallow-code/marshmallow/blob/dev/marshmallow/schema.py#L139-L174
        """

        mro = inspect.getmro(cls)
        cls._has_processors = False
        cls.__processors__: Dict[Tuple[Tag, Optional[str]], List[str]] = defaultdict(list)
        for attr_name in dir(cls):
            # Need to look up the actual descriptor, not whatever might be
            # bound to the class. This needs to come from the __dict__ of the
            # declaring class.
            for parent in mro:
                try:
                    attr = parent.__dict__[attr_name]
                except KeyError:
                    continue
                else:
                    break
            else:
                # In case we didn't find the attribute and didn't break above.
                # We should never hit this - it's just here for completeness
                # to exclude the possibility of attr being undefined.
                continue

            try:
                processor_tags = attr.__processing_tags__
            except AttributeError:
                continue

            cls._has_processors = bool(processor_tags)
            for tag in processor_tags:
                # Use name here so we can get the bound method later, in case
                # the processor was a descriptor or something.
                cls.__processors__[tag].append(attr_name)
