from __future__ import annotations

from copy import deepcopy
from enum import Enum, IntEnum
import re
from typing import Any, Callable, Generic, Literal, TypeVar, overload
from typing_extensions import Annotated, Self, get_args, get_origin, NoReturn

from tarina import Empty, generic_isinstance
from tarina.lang import lang

from .exception import MatchFailed
from .util import TPattern


class MatchMode(IntEnum):
    """参数表达式匹配模式"""

    VALUE_OPERATE = 4
    """传入值进行操作"""
    REGEX_CONVERT = 3
    """正则匹配并转换"""
    TYPE_CONVERT = 2
    """传入值直接转换"""
    REGEX_MATCH = 1
    """正则匹配"""
    KEEP = 0
    """保持传入值"""


class ResultFlag(str, Enum):
    """参数表达式验证结果标识符"""

    VALID = "valid"
    "验证通过"
    ERROR = "error"
    "验证失败"
    DEFAULT = "default"
    "默认值"


T = TypeVar("T")
TInput = TypeVar("TInput")
TInput1 = TypeVar("TInput1")
TOrigin = TypeVar("TOrigin")
TVOrigin = TypeVar("TVOrigin")
TDefault = TypeVar("TDefault")
TVRF = TypeVar("TVRF", bound=ResultFlag)


class ValidateResult(Generic[TVOrigin, TVRF]):
    """参数表达式验证结果"""

    def __init__(
        self,
        value: TVOrigin | type[Empty] = Empty,
        error: Exception | type[Empty] = Empty,
        flag: TVRF = ResultFlag.VALID,
    ):
        self._value = value
        self._error = error
        self.flag = flag

    __slots__ = ("_value", "_error", "flag")

    @overload
    def value(self: ValidateResult[TVOrigin, Literal[ResultFlag.VALID]]) -> TVOrigin:
        ...

    @overload
    def value(self: ValidateResult[Any, Literal[ResultFlag.ERROR]]) -> NoReturn:
        ...

    @overload
    def value(self: ValidateResult[TVOrigin, Literal[ResultFlag.DEFAULT]]) -> TVOrigin:
        ...

    def value(self) -> TVOrigin:
        if self.flag == ResultFlag.ERROR or self._value == Empty:
            raise RuntimeError("cannot access value")
        return self._value  # type: ignore

    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.VALID]]) -> None:
        ...

    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.ERROR]]) -> Exception:
        ...

    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.DEFAULT]]) -> None:
        ...

    def error(self) -> Exception | None:
        if self.flag == ResultFlag.ERROR and self._error != Empty:
            assert isinstance(self._error, Exception)
            return self._error

    @property
    def success(self) -> bool:
        return self.flag == ResultFlag.VALID

    @property
    def failed(self) -> bool:
        return self.flag == ResultFlag.ERROR

    @property
    def or_default(self) -> bool:
        return self.flag == ResultFlag.DEFAULT

    @overload
    def step(self, other: BasePattern[T, TVOrigin]) -> ValidateResult[T, TVRF]:
        ...

    @overload
    def step(self, other: type[T]) -> T:
        ...

    @overload
    def step(self, other: Callable[[TVOrigin], T]) -> T:
        ...

    @overload
    def step(self, other: Any) -> Self:
        ...

    def step(
        self, other: type[T] | Callable[[TVOrigin], T] | Any | BasePattern[T, TVOrigin]
    ) -> T | Self | ValidateResult[T, TVRF]:
        if other is bool:
            return self.success  # type: ignore
        if callable(other) and self.success:
            return other(self.value())  # type: ignore
        return other.validate(self.value()) if isinstance(other, BasePattern) else self  # type: ignore

    @overload
    def __rshift__(self, other: BasePattern[T, TVOrigin]) -> ValidateResult[T, TVRF]:
        ...

    @overload
    def __rshift__(self, other: type[T]) -> T:
        ...

    @overload
    def __rshift__(self, other: Callable[[TVOrigin], T]) -> T:
        ...

    @overload
    def __rshift__(self, other: Any) -> Self:
        ...

    def __rshift__(self, other: type[T] | Callable[[TVOrigin], T] | Any) -> T | Self | ValidateResult[T, TVRF]:
        return self.step(other)  # type: ignore

    @overload
    def __bool__(self: ValidateResult[Any, Literal[ResultFlag.VALID]]) -> Literal[True]:
        ...

    @overload
    def __bool__(self: ValidateResult[Any, Literal[ResultFlag.ERROR]]) -> Literal[False]:
        ...

    @overload
    def __bool__(self: ValidateResult[Any, Literal[ResultFlag.DEFAULT]]) -> Literal[True]:
        ...

    def __bool__(self):
        return self.success

    def __repr__(self):
        if self.flag == ResultFlag.VALID:
            return f"ValidateResult(value={self._value!r})"
        if self.flag == ResultFlag.ERROR:
            return f"ValidateResult(error={self._error!r})"
        return f"ValidateResult(default={self._value!r})"


def _keep(self: BasePattern[Any, Any], input_: Any) -> Any:
    if not self.accept(input_) and (
        not self.previous or not self.accept(input_ := self.previous.match(input_))
    ):  # pragma: no cover
        raise MatchFailed(
            lang.require("nepattern", "type_error").format(
                type=input_.__class__, target=input_, expected=self.alias
            )
        )
    return input_


def _regex_match(self: BasePattern[str, str], input_: Any) -> str:
    if not isinstance(input_, str) and (
        not self.previous or not isinstance(input_ := self.previous.match(input_), str)
    ):  # pragma: no cover
        raise MatchFailed(
            lang.require("nepattern", "type_error").format(
                type=input_.__class__, target=input_, expected=self.alias
            )
        )
    if mat := (self.regex_pattern.match(input_) or self.regex_pattern.search(input_)):
        return mat[0]
    raise MatchFailed(lang.require("nepattern", "content_error").format(target=input_, expected=self.alias))


def _regex_convert(self: BasePattern[TOrigin, str | TOrigin], input_: Any) -> TOrigin:
    if self.origin not in (str, Any) and generic_isinstance(input_, self.origin):
        return input_  # type: ignore
    if not isinstance(input_, str) and (
        not self.previous or not isinstance(input_ := self.previous.match(input_), str)
    ):  # pragma: no cover
        raise MatchFailed(
            lang.require("nepattern", "type_error").format(
                type=input_.__class__, target=input_, expected=self.alias
            )
        )
    if mat := (self.regex_pattern.match(input_) or self.regex_pattern.search(input_)):
        if (res := self.converter(self, mat)) is not None:
            return res
    raise MatchFailed(lang.require("nepattern", "content_error").format(target=input_, expected=self.alias))


def _type_convert(self: BasePattern[TOrigin, Any], input_: Any) -> TOrigin:
    if self.origin is not Any and generic_isinstance(input_, self.origin):
        return input_
    if not self.accept(input_) and (
        not self.previous or not self.accept(input_ := self.previous.match(input_))
    ):  # pragma: no cover
        raise MatchFailed(
            lang.require("nepattern", "type_error").format(
                type=input_.__class__, target=input_, expected=self.alias
            )
        )
    res = self.converter(self, input_)
    if res is None and self.origin is Any:
        raise MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.alias)
        )
    if not generic_isinstance(res, self.origin) and (
        not self.previous
        or not generic_isinstance(res := self.converter(self, self.previous.match(input_)), self.origin)
    ):
        raise MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.alias)
        )
    return res  # type: ignore


def _value_operate(self: BasePattern[TOrigin, TOrigin], input_: Any) -> TOrigin:
    if not generic_isinstance(input_, self.origin) and (
        not self.previous or not generic_isinstance(input_ := self.previous.match(input_), self.origin)
    ):  # pragma: no cover
        raise MatchFailed(
            lang.require("nepattern", "type_error").format(
                type=input_.__class__, target=input_, expected=self.alias
            )
        )
    res = self.converter(self, input_)
    if res is None and self.origin is Any:
        raise MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.alias)
        )
    if not generic_isinstance(res, self.origin) and (
        not self.previous
        or not generic_isinstance(res := self.converter(self, self.previous.match(input_)), self.origin)
    ):
        raise MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.alias)
        )
    return res  # type: ignore


class BasePattern(Generic[TOrigin, TInput]):
    """对参数类型值的包装"""

    regex_pattern: TPattern  # type: ignore
    pattern: str
    mode: MatchMode
    converter: Callable[[BasePattern[TOrigin, TInput], Any], TOrigin | None]
    validators: list[Callable[[TOrigin], bool]]

    origin: type[TOrigin]
    alias: str | None
    previous: BasePattern | None
    match: Callable[[TInput], TOrigin]

    _MATCHES = {
        MatchMode.KEEP: _keep,
        MatchMode.REGEX_MATCH: _regex_match,
        MatchMode.REGEX_CONVERT: _regex_convert,
        MatchMode.TYPE_CONVERT: _type_convert,
        MatchMode.VALUE_OPERATE: _value_operate,
    }

    __slots__ = (
        "regex_pattern",
        "pattern",
        "mode",
        "converter",
        "origin",
        "pattern_accepts",
        "type_accepts",
        "alias",
        "previous",
        "validators",
        "match",
        "accept",
        "_hash",
        "_repr",
    )

    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput],
        *,
        mode: Literal[MatchMode.KEEP],
        origin: type[TOrigin] = Any,
        alias: str | None = None,
        previous: None = None,
        accepts: type[TInput] = Any,
        addition_accepts: list[BasePattern] | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    @overload
    def __init__(
        self: BasePattern[str, str],
        pattern: str,
        mode: Literal[MatchMode.REGEX_MATCH],
        origin: type[TOrigin] = str,
        converter: Callable[[BasePattern[str, str], str], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: BasePattern[str, Any] | None = None,
        accepts: type[TInput] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, str | TOrigin],
        pattern: str,
        mode: Literal[MatchMode.REGEX_CONVERT],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, str | TOrigin], re.Match[str]], TOrigin | None]
        | None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: type[TInput] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, str | TOrigin | TInput1],
        pattern: str,
        mode: Literal[MatchMode.REGEX_CONVERT],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, str | TOrigin], re.Match[str]], TOrigin | None]
        | None = None,
        alias: str | None = None,
        previous: BasePattern[str, TInput1] | None = None,
        accepts: type[TInput] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, TInput], Any], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: BasePattern[TInput, Any] | None = None,
        accepts: type[TInput] = Any,
        addition_accepts: list[BasePattern] | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, TOrigin],
        *,
        mode: Literal[MatchMode.VALUE_OPERATE],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, TOrigin], TOrigin], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: BasePattern[TOrigin, Any] | None = None,
        accepts: type[TInput] = Any,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        ...

    def __init__(
        self,
        pattern: str = ".+",
        mode: MatchMode = MatchMode.REGEX_MATCH,
        origin: type[TOrigin] = str,
        converter: Callable[[BasePattern, Any], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: BasePattern | None = None,
        accepts: type[TInput] = Any,
        addition_accepts: list[BasePattern] | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ):
        """
        初始化参数匹配表达式
        """
        if pattern.startswith("^") or pattern.endswith("$"):
            raise ValueError(lang.require("nepattern", "pattern_head_or_tail_error").format(target=pattern))
        self.pattern = pattern
        self.regex_pattern = re.compile(f"^{pattern}$")
        self.mode = MatchMode(mode)
        self.origin = origin
        self.alias = alias
        self.previous = previous
        self.converter = converter or (
            lambda _, x: (get_origin(origin) or origin)(x) if mode == MatchMode.TYPE_CONVERT else eval(x[0])
        )
        self.validators = validators or []
        self.type_accepts = () if accepts is Any else (get_args(accepts) or (accepts,))
        self.pattern_accepts = tuple(addition_accepts) if addition_accepts else ()
        self._repr = self.__calc_repr__()
        self._hash = hash(self._repr)
        if not addition_accepts:
            self.accept = lambda _: True if accepts is Any else generic_isinstance(_, accepts)
        elif accepts is Any:
            self.accept = lambda _: any(map(lambda x: x.validate(_).flag == "valid", addition_accepts))
        else:
            self.accept = lambda _: (
                generic_isinstance(_, accepts)
                or any(map(lambda x: x.validate(_).flag == "valid", addition_accepts))
            )
        if not hasattr(self, "match"):
            self.match = self._MATCHES[self.mode].__get__(self)  # type: ignore

    def refresh(self):  # pragma: no cover
        self._repr = self.__calc_repr__()
        self._hash = hash(self._repr)

    def __calc_repr__(self):
        if self.mode == MatchMode.KEEP:
            if self.alias:
                return self.alias
            return (
                "Any"
                if not self.type_accepts and not self.pattern_accepts
                else "|".join(
                    [x.__name__ for x in self.type_accepts] + [x.__repr__() for x in self.pattern_accepts]
                )
            )

        if not self.alias:
            name = getattr(self.origin, "__name__", str(self.origin))
            if self.mode == MatchMode.REGEX_MATCH:
                text = self.pattern
            elif self.mode == MatchMode.REGEX_CONVERT or (not self.type_accepts and not self.pattern_accepts):
                text = name
            else:
                text = (
                    "|".join(
                        [x.__name__ for x in self.type_accepts] + [x.__repr__() for x in self.pattern_accepts]
                    )
                    + f" -> {name}"
                )
        else:
            text = self.alias
        return (
            f"{f'{self.previous.__repr__()} -> ' if self.previous and id(self.previous) != id(self) else ''}"
            f"{text}"
        )

    def __repr__(self):
        return self._repr

    def __str__(self):
        return self._repr

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, BasePattern) and self._repr == other._repr

    @staticmethod
    def of(unit: type[TOrigin]) -> BasePattern[TOrigin, TOrigin]:
        """提供 Type[DataUnit] 类型的构造方法"""
        return BasePattern(mode=MatchMode.KEEP, origin=unit, alias=unit.__name__, accepts=unit)

    @staticmethod
    def on(obj: TOrigin) -> BasePattern[TOrigin, TOrigin]:
        """提供 DataUnit 类型的构造方法"""
        from .base import DirectPattern

        return DirectPattern(obj)

    @staticmethod
    def to(content: Any) -> BasePattern:
        """便捷的使用 type_parser 的方法"""
        from .main import parser

        res = parser(content, "allow")
        return res if isinstance(res, BasePattern) else parser(Any)

    def prefixed(self):
        """让表达式能在某些场景下实现前缀匹配; 返回自身的拷贝"""
        cp_self = deepcopy(self)
        if self.mode in (MatchMode.REGEX_MATCH, MatchMode.REGEX_CONVERT):
            cp_self.regex_pattern = re.compile(f"^{self.pattern}")
        return cp_self

    def suffixed(self):
        """让表达式能在某些场景下实现后缀匹配; 返回自身的拷贝"""
        cp_self = deepcopy(self)
        if self.mode in (MatchMode.REGEX_MATCH, MatchMode.REGEX_CONVERT):
            cp_self.regex_pattern = re.compile(f"{self.pattern}$")
        return cp_self

    @overload
    def validate(self, input_: TInput) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]:
        ...

    @overload
    def validate(self, input_: Any) -> ValidateResult[TOrigin, Literal[ResultFlag.ERROR]]:
        ...

    @overload
    def validate(self, input_: TInput, default: TDefault) -> ValidateResult[TOrigin | TDefault, Literal[ResultFlag.VALID]]:
        ...

    @overload
    def validate(self, input_: Any, default: TDefault) -> ValidateResult[TOrigin | TDefault, Literal[ResultFlag.DEFAULT]]:
        ...

    def validate(self, input_: Any, default: TDefault | Empty = Empty) -> ValidateResult[TOrigin | TDefault, ResultFlag]:  # type: ignore
        """
        对传入的值进行正向验证，返回可能的匹配与转化结果。

        若传入默认值，验证失败会返回默认值
        """
        try:
            res = self.match(input_)
            if self.validators and not all(i(res) for i in self.validators):
                raise MatchFailed(lang.require("nepattern", "validate_error").format(target=input_))
            return ValidateResult(value=res, flag=ResultFlag.VALID)
        except Exception as e:
            if default is Empty:
                return ValidateResult(error=e, flag=ResultFlag.ERROR)
            return ValidateResult(default, flag=ResultFlag.DEFAULT)  # type: ignore

    def __rrshift__(self, other):
        return self.validate(other)

    def __rmatmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self

    def __matmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self


def set_unit(target: type[TOrigin], predicate: Callable[..., bool]) -> Annotated[TOrigin, ...]:
    """通过predicate区分同一个类的不同情况"""
    return Annotated[target, predicate]  # type: ignore


__all__ = ["MatchMode", "BasePattern", "set_unit", "ValidateResult", "TOrigin", "ResultFlag"]
