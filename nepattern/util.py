from __future__ import annotations

import dataclasses
import sre_compile
from typing import TYPE_CHECKING, List, Pattern

if TYPE_CHECKING:
    from types import GenericAlias  # noqa
else:
    GenericAlias: type = type(List[int])
TPattern: type[Pattern] = type(sre_compile.compile("", 0))


class _All:
    """泛匹配"""

    def __repr__(self):
        return "AllParam"


AllParam = _All()


@dataclasses.dataclass
class RawStr:
    value: str
