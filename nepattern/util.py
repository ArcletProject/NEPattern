import inspect
import contextlib
import sre_compile
from typing import Any, Union, Tuple, get_origin, get_args, List, Type, Pattern

Empty = inspect.Signature.empty
GenericAlias = type(List[int])
TPattern: Type[Pattern] = type(sre_compile.compile("", 0))


class _All:
    """泛匹配"""

    def __repr__(self):
        return "AllParam"


AllParam = _All()


def generic_isinstance(obj: Any, par: Union[type, Any, Tuple[type, ...]]) -> bool:
    """
    检查 obj 是否是 par 中的一个类型, 支持泛型, Any, Union, GenericAlias
    """
    if par is Any:
        return True
    with contextlib.suppress(TypeError):
        if isinstance(par, (type, tuple)):
            return isinstance(obj, par)
        if get_origin(par) is Union:
            return any(generic_isinstance(obj, p) for p in get_args(par))
        if isinstance(obj, get_origin(par)):  # type: ignore
            return True
    return False


__all__ = ["GenericAlias", "TPattern", "generic_isinstance", "Empty", "AllParam"]
