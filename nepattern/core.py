from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Callable, Generic, TypeVar, Union, overload
from typing_extensions import Self

from tarina import Empty, generic_isinstance
from tarina.lang import lang

from .exception import MatchFailed
from .util import TPattern

T = TypeVar("T")
_T = TypeVar("_T")


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
        """获取验证结果"""
        if self._value is Empty:
            raise RuntimeError("cannot access value")
        return self._value  # type: ignore

    def error(self) -> Exception | None:
        """获取验证错误"""
        if self._error is not Empty:
            assert isinstance(self._error, Exception)
            return self._error

    @property
    def success(self) -> bool:
        """是否验证成功"""
        return self._value is not Empty

    @property
    def failed(self) -> bool:
        """是否验证失败"""
        return self._value is Empty

    def __bool__(self):  # pragma: no cover
        return self._value != Empty

    def __repr__(self):
        return (
            f"ValidateResult(value={self._value!r})"
            if self._value is not Empty
            else f"ValidateResult(error={self._error!r})"
        )


class Pattern(Generic[T]):
    @staticmethod
    def regex_match(pattern: str | TPattern, alias: str | None = None) -> _RegexPattern[str]:
        """构建一个仅正则表达式匹配的 Pattern，不进行转换"""
        pat = _RegexPattern(pattern, str, alias or str(pattern))

        @pat.convert
        def _(self: _RegexPattern, x: str):
            mat = re.match(self.pattern, x) or re.search(self.pattern, x)
            if not mat:
                raise MatchFailed(
                    lang.require("nepattern", "error.content").format(target=x, expected=self.pattern)
                )
            return mat[0]

        return pat

    @staticmethod
    def regex_convert(
        pattern: str,
        origin: type[_T],
        fn: Callable[[re.Match[str]], _T],
        alias: str | None = None,
        allow_origin: bool = False,
    ) -> _RegexPattern[_T]:
        """构建一个正则表达式匹配的 Pattern，并提供转换函数"""
        pat = _RegexPattern(pattern, origin, alias or str(pattern))
        if allow_origin:
            pat.accept(Union[str, origin])

            @pat.convert
            def _(self: _RegexPattern, x):
                if isinstance(x, origin):
                    return x
                mat = re.match(self.pattern, x) or re.search(self.pattern, x)
                if not mat:
                    raise MatchFailed(
                        lang.require("nepattern", "error.content").format(target=x, expected=self.pattern)
                    )
                return fn(mat)

        else:
            pat.accept(str)

            @pat.convert
            def _(self: _RegexPattern, x: str):
                mat = re.match(self.pattern, x) or re.search(self.pattern, x)
                if not mat:
                    raise MatchFailed(
                        lang.require("nepattern", "error.content").format(target=x, expected=self.pattern)
                    )
                return fn(mat)

        return pat

    @staticmethod
    def on(obj: _T) -> Pattern[_T]:
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
        self._post_validator = None
        self._pre_validator = (lambda x: generic_isinstance(x, self.origin)) if origin else None
        self._converter = None
        self._pre_validate_modified = False

    def __init_subclass__(cls, **kwargs):
        cls.__hash__ = Pattern.__hash__

    def accept(self, input_type: Any):
        """设置接受的输入类型"""
        if input_type is ...:
            input_type = Any
        self._accepts = input_type
        if not self._pre_validate_modified:
            self._pre_validator = None
        return self

    def pre_validate(self, func: Callable[[Any], bool]):
        """设置预验证函数 (经过 accept 后，convert 前)"""
        self._pre_validator = func
        self._pre_validate_modified = True
        return self

    def post_validate(self, func: Callable[[T], bool]):
        """设置后验证函数 (convert 后，仅当设置了 converter 才会生效)"""
        self._post_validator = func
        return self

    def convert(self, func: Callable[[Self, Any], T | None]):
        """设置转换函数, 返回 None 时表示转换失败"""
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
            if input_ is None:
                raise MatchFailed(
                    lang.require("nepattern", "error.content").format(target=input_, expected=self.origin)
                )
            if self._post_validator and not self._post_validator(input_):
                raise MatchFailed(
                    lang.require("nepattern", "error.content").format(target=input_, expected=self.origin)
                )
        return input_

    def execute(self, input_: Any) -> ValidateResult[T]:
        """执行验证"""
        try:
            return ValidateResult(self.match(input_))
        except Exception as e:
            return ValidateResult(error=e)

    def __str__(self):
        if self.alias:
            return self.alias
        if self._accepts is self.origin or self._accepts is Any:
            return f"{getattr(self.origin, '__name__', self.origin)}"
        return f"{getattr(self._accepts, '__name__', self._accepts)} -> {getattr(self.origin, '__name__', self.origin)}"

    def __repr__(self):
        return f"{self.__class__.__name__}({self.origin}, {self.alias!r})"

    def copy(self) -> Self:
        return deepcopy(self)

    def __rrshift__(self, other):  # pragma: no cover
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
        return hash((self.origin, self.alias, self._accepts, self._converter))

    def __eq__(self, other):
        return isinstance(other, Pattern) and self.__hash__() == other.__hash__()


class _RegexPattern(Pattern[T]):
    def __init__(self, pattern: str | TPattern, origin: type[T], alias: str | None = None):
        super().__init__(origin, alias)
        _pat = pattern if isinstance(pattern, str) else pattern.pattern
        if _pat.startswith("^") or _pat.endswith("$"):
            raise ValueError(lang.require("nepattern", "error.pattern_head_or_tail").format(target=pattern))
        if isinstance(pattern, str):
            self.pattern = f"^{pattern}$"
        else:
            self.pattern = re.compile(f"^{pattern.pattern}$", pattern.flags)

    def prefixed(self):
        """转为前缀型匹配"""
        new = self.copy()
        if isinstance(self.pattern, str):
            new.pattern = self.pattern[:-1]
        else:  # pragma: no cover
            new.pattern = re.compile(self.pattern.pattern[:-1], self.pattern.flags)
        return new

    def suffixed(self):
        """转为后缀型匹配"""
        new = self.copy()
        if isinstance(self.pattern, str):
            new.pattern = self.pattern[1:]
        else:  # pragma: no cover
            new.pattern = re.compile(self.pattern.pattern[1:], self.pattern.flags)
        return new
