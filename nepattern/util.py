from __future__ import annotations

import contextlib
import inspect
import sre_compile
import sys
import types
from typing import Any, List, Pattern, TypeVar, Literal, Union, get_args, get_origin, TYPE_CHECKING

from typing_extensions import Annotated

Empty = inspect.Signature.empty
if TYPE_CHECKING:
    from types import GenericAlias  # noqa
else:
    GenericAlias: type = type(List[int])
TPattern: type[Pattern] = type(sre_compile.compile("", 0))
AnnotatedType: type = type(Annotated[int, lambda x: x > 0])
Unions = (Union, types.UnionType) if sys.version_info >= (3, 10) else (Union,)  # pragma: no cover


class _All:
    """泛匹配"""

    def __repr__(self):
        return "AllParam"


AllParam = _All()


def generic_isinstance(obj: Any, par: type | Any | tuple[type, ...]) -> bool:
    """
    检查 obj 是否是 par 中的一个类型, 支持泛型, Any, Union, GenericAlias
    """
    if par is Any:
        return True
    with contextlib.suppress(TypeError):
        if isinstance(par, AnnotatedType):
            return generic_isinstance(obj, get_args(par)[0])
        if isinstance(par, type):
            return isinstance(obj, par)
        if get_origin(par) is Literal:
            return obj in get_args(par)
        if get_origin(par) in Unions:  # pragma: no cover
            return any(generic_isinstance(obj, p) for p in get_args(par))
        if isinstance(par, TypeVar):  # pragma: no cover
            if par.__constraints__:
                return any(generic_isinstance(obj, p) for p in par.__constraints__)
            return generic_isinstance(obj, par.__bound__) if par.__bound__ else True
        if isinstance(par, tuple):
            return any(generic_isinstance(obj, p) for p in par)
        if isinstance(obj, get_origin(par)):  # type: ignore
            return True
    return False
