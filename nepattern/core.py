from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Callable, Generic, TypeVar, Union, overload
from typing_extensions import Self

from tarina import Empty, generic_isinstance
from tarina.lang import lang

from .exception import MatchFailed

T = TypeVar("T")


class ValidateResult(Generic[T]):
    """参数表达式验证结果"""

    def __init__(
        self,
        value: T | type[Empty] = Empty,
        error: Exception | type[Empty] = Empty,
    ):
        self._value = value
        self._error = error

    __slots__ = ("_value", "_error")

    def value(self) -> T:
        if self._value is Empty:
            raise RuntimeError("cannot access value")
        return self._value  # type: ignore

    def error(self) -> Exception | None:
        if self._error is not Empty:
            assert isinstance(self._error, Exception)
            return self._error

    @property
    def success(self) -> bool:
        return self._value is not Empty

    @property
    def failed(self) -> bool:
        return self._value is Empty

    def __bool__(self):
        return self._value != Empty

    def __repr__(self):
        return (
            f"ValidateResult(value={self._value!r})"
            if self._value is not Empty
            else f"ValidateResult(error={self._error!r})"
        )


class Pattern(Generic[T]):
    @staticmethod
    def regex_match(pattern: str, alias: str | None = None):
        pat = Pattern(str, alias)

        @pat.convert
        def _(self, x: str):
            mat = re.match(pattern, x)
            if not mat:
                raise MatchFailed(
                    lang.require("nepattern", "error.content").format(target=x, expected=pattern)
                )
            return x

        return pat

    @staticmethod
    def regex_convert(
        pattern: str,
        origin: type[T],
        fn: Callable[[re.Match], T],
        alias: str | None = None,
        allow_origin: bool = False,
    ):
        pat = Pattern(origin, alias)
        if allow_origin:
            pat.accept(Union[str, origin])

            @pat.convert
            def _(self, x):
                if isinstance(x, origin):
                    return x
                mat = re.match(pattern, x)
                if not mat:
                    raise MatchFailed(
                        lang.require("nepattern", "error.content").format(target=x, expected=pattern)
                    )
                return fn(mat)

        else:
            pat.accept(str)

            @pat.convert
            def _(self, x: str):
                mat = re.match(pattern, x)
                if not mat:
                    raise MatchFailed(
                        lang.require("nepattern", "error.content").format(target=x, expected=pattern)
                    )
                return fn(mat)

        return pat

    @staticmethod
    def on(obj: T):
        """提供 DataUnit 类型的构造方法"""
        from .base import DirectPattern

        return DirectPattern(obj)

    @overload
    def __init__(self, origin: type[T], alias: str | None = None): ...

    @overload
    def __init__(self: Pattern[Any], *, alias: str | None = None): ...

    def __init__(self, origin: type[T] | None = None, alias: str | None = None):
        self.origin: type[T] = origin or Any  # type: ignore
        self.alias = alias

        self._accepts = Any
        self._post_validator = lambda x: generic_isinstance(x, self.origin)
        self._pre_validator = None
        self._converter = None

    def __init_subclass__(cls, **kwargs):
        cls.__hash__ = Pattern.__hash__

    def accept(self, input_type: Any):
        self._accepts = input_type
        return self

    def pre_validate(self, func: Callable[[Any], bool]):
        self._pre_validator = func
        return self

    def post_validate(self, func: Callable[[T], bool]):
        self._post_validator = func
        return self

    def convert(self, func: Callable[[Self, Any], T]):
        self._converter = func
        return self

    def match(self, input_: Any) -> T:
        if not generic_isinstance(input_, self._accepts):
            raise MatchFailed(
                lang.require("nepattern", "error.type").format(target=input_, expected=self._accepts)
            )
        if self._pre_validator and not self._pre_validator(input_):
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected=self.origin)
            )
        if self._converter:
            input_ = self._converter(self, input_)
        if self._post_validator and not self._post_validator(input_):
            raise MatchFailed(
                lang.require("nepattern", "error.content").format(target=input_, expected=self.origin)
            )
        return input_

    def execute(self, input_: Any) -> ValidateResult[T]:
        try:
            return ValidateResult(self.match(input_))
        except Exception as e:
            return ValidateResult(error=e)

    def __str__(self):
        if self.alias:
            return self.alias
        if self._accepts is self.origin:
            return f"{self.origin.__name__}"
        return f"{self._accepts.__name__} -> {self.origin.__name__}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.origin.__name__}, {self.alias})"

    def copy(self) -> Self:
        return deepcopy(self)

    def __rrshift__(self, other):
        return self.execute(other)

    def __rmatmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self

    def __matmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self

    def __hash__(self):
        return id((self.origin, self.alias, self._accepts, self._converter))

    def __eq__(self, other):
        return isinstance(other, Pattern) and self.__hash__() == other.__hash__()
