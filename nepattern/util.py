from __future__ import annotations

import dataclasses
from pathlib import Path
import sre_compile
import sys
from typing import TYPE_CHECKING, List, Pattern, Union

from tarina.lang import lang

if sys.version_info >= (3, 10):  # pragma: no cover
    from types import GenericAlias as CGenericAlias  # noqa
    from types import UnionType as CUnionType  # noqa
else:
    CGenericAlias: type = type(List[int])  # noqa
    CUnionType: type = type(Union[int, str])  # noqa

if TYPE_CHECKING:
    TPattern = Pattern[str]
else:
    TPattern: type[Pattern[str]] = type(sre_compile.compile("", 0))
GenericAlias: type = type(List[int])
UnionType: type = type(Union[int, str])


@dataclasses.dataclass
class RawStr:
    value: str


lang.load(Path(__file__).parent / "i18n")
