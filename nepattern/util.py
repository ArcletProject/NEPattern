from __future__ import annotations

import dataclasses
import sre_compile
from typing import TYPE_CHECKING, List, Pattern
from pathlib import Path
from tarina.lang import lang

try:
    from types import GenericAlias as CGenericAlias  # noqa
except ImportError:
    CGenericAlias = type(List[int])

if TYPE_CHECKING:
    TPattern = Pattern[str]
else:
    TPattern: type[Pattern[str]] = type(sre_compile.compile("", 0))
GenericAlias: type = type(List[int])


class _All:
    """泛匹配"""

    def __repr__(self):
        return "AllParam"


AllParam = _All()


@dataclasses.dataclass
class RawStr:
    value: str


lang.load(Path(__file__).parent / "i18n")
