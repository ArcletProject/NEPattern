from __future__ import annotations

import dataclasses
import sys
from typing import TYPE_CHECKING, List, Pattern, Union
from typing_extensions import TypeAlias

from .i18n import lang as lang  # noqa: F401

from types import GenericAlias as CGenericAlias  # noqa: F401

if sys.version_info >= (3, 10):  # pragma: no cover
    from types import UnionType as CUnionType  # noqa: F401
else:  # pragma: no cover
    CUnionType: type = type(Union[int, str])  # noqa

if sys.version_info >= (3, 11):  # pragma: no cover
    from re._compiler import compile as re_compile  # noqa
else:  # pragma: no cover
    from sre_compile import compile as re_compile  # noqa

if TYPE_CHECKING:
    TPattern: TypeAlias = Pattern[str]
else:
    TPattern: type[Pattern[str]] = type(re_compile("", 0))
GenericAlias: type = type(List[int])
UnionType: type = type(Union[int, str])


@dataclasses.dataclass
class RawStr:
    value: str
