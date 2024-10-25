from __future__ import annotations

from functools import reduce
from typing import Any, Callable, Protocol, TypeVar, overload

from .core import Pattern

T = TypeVar("T")
T1 = TypeVar("T1")


def Index(
    pat: Pattern[list[T]],
    index: int,
) -> Pattern[T]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return _match(input_)[index]

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}[{index}]"
    
    return _new  # type: ignore


def Slice(
    pat: Pattern[list[T]],
    start: int | None = None,
    end: int | None = None,
    step: int = 1,
) -> Pattern[list[T]]:
    if start is None and end is None:
        return pat
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return _match(input_)[start:end:step]

    _new.match = match.__get__(_new)
    if start is not None and end is not None:
        _slice = f"{start}:{end}"
    elif start is not None:
        _slice = f"{start}:"
    else:
        _slice = f":{end}"
    if step != 1:
        _slice += f":{step}"
    _new.alias = f"{_new}[{_slice}]"
    
    return _new


def Map(
    pat: Pattern[list[T]],
    func: Callable[[T], T1],
    funcname: str | None = None,
) -> Pattern[list[T1]]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return list(map(func, _match(input_)))

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.map({funcname or func.__name__})"
    
    return _new  # type: ignore


def Filter(
    pat: Pattern[list[T]],
    func: Callable[[T], bool],
    funcname: str | None = None,
) -> Pattern[list[T]]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return list(filter(func, _match(input_)))

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.filter({funcname or func.__name__})"
    
    return _new


_T_contra = TypeVar("_T_contra", contravariant=True)
_T_co = TypeVar("_T_co", covariant=True)


class SupportsAdd(Protocol[_T_contra, _T_co]):
    def __add__(self, x: _T_contra, /) -> _T_co: ...


class SupportsRAdd(Protocol[_T_contra, _T_co]):
    def __radd__(self, x: _T_contra, /) -> _T_co: ...


class _SupportsSumWithNoDefaultGiven(SupportsAdd[Any, Any], SupportsRAdd[int, Any], Protocol): ...


_SupportsSumNoDefaultT = TypeVar("_SupportsSumNoDefaultT", bound=_SupportsSumWithNoDefaultGiven)


def Sum(
    pat: Pattern[list[_SupportsSumNoDefaultT]]
) -> Pattern[_SupportsSumNoDefaultT]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return sum(_match(input_))

    _new.match = match.__get__(_new)
    _new.alias = f"sum({_new})"
    
    return _new  # type: ignore


@overload
def Reduce(
    pat: Pattern[list[T]],
    func: Callable[[T, T], T],
    initializer: None = ...,
    funcname: str | None = ...,
) -> Pattern[T]: ...


@overload
def Reduce(
    pat: Pattern[list[T]],
    func: Callable[[T1, T], T1],
    initializer: T1,
    funcname: str | None = ...,
) -> Pattern[T1]: ...


def Reduce(
    pat: Pattern[list[T]],
    func: Callable[[T, T], T] | Callable[[T1, T], T1],
    initializer: T1 | None = None,
    funcname: str | None = None,
) -> Pattern:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return reduce(func, _match(input_), initializer) if initializer is not None else reduce(func, _match(input_))  # type: ignore

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.reduce({funcname or func.__name__})"
    
    return _new  # type: ignore


def Join(
    pat: Pattern[list[str]],
    sep: str,
) -> Pattern[str]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return sep.join(_match(input_))

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.join({sep!r})"
    
    return _new  # type: ignore


def Upper(
    pat: Pattern[str],
) -> Pattern[str]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return _match(input_).upper()

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.upper()"
    
    return _new  # type: ignore


def Lower(
    pat: Pattern[str],
) -> Pattern[str]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return _match(input_).lower()

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.lower()"
    
    return _new  # type: ignore


def Dot(
    pat: Pattern[Any],
    origin: type[T],
    key: str,
    default: T | None = None,
) -> Pattern[T]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return getattr(_match(input_), key, default)

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.{key}"
    
    _new.origin = origin
    return _new  # type: ignore


def GetItem(
    pat: Pattern[Any],
    origin: type[T],
    key: str,
    default: T | None = None,
) -> Pattern[T]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_) -> T:
        try:
            return _match(input_)[key]
        except Exception as e:  # pragma: no cover
            if default is not None:
                return default
            raise e

    _new.match = match.__get__(_new)
    _new.alias = f"{_new}.{key}"
    
    _new.origin = origin
    return _new  # type: ignore


def Step(
    pat: Pattern[T],
    func: Callable[[T], T1],
    *args,
    funcname: str | None = None,
    **kwargs,
) -> Pattern[T1]:
    _new = pat.copy()
    _match = _new.match

    def match(self, input_):
        return func(_match(input_), *args, **kwargs)

    _new.match = match.__get__(_new)
    _new.alias = f"{funcname or func.__name__}({_new})"
    
    return _new  # type: ignore
