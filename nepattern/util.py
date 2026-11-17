from __future__ import annotations

import dataclasses
from types import GenericAlias as CGenericAlias  # noqa: F401
from types import UnionType as CUnionType  # noqa: F401
from typing import List, TypeVar, Generic  # noqa: UP035
from re import Pattern
from typing import TypeAlias, LiteralString

from .i18n import lang as lang  # noqa: F401


TPattern: TypeAlias = Pattern[str]
TypGenericAlias: type[CGenericAlias] = type(List[int])  # type: ignore  # noqa: UP006


_TS = TypeVar("_TS", bound=LiteralString)


@dataclasses.dataclass(frozen=True, slots=True, eq=True)
class RawStr(Generic[_TS]):
    value: _TS
