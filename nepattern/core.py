from __future__ import annotations

import re
from enum import IntEnum, Enum
from copy import deepcopy
from typing import (
    TypeVar,
    Callable,
    Any,
    Generic,
    overload,
)
from dataclasses import dataclass

try:
    from typing import Annotated, Self, get_origin  # type: ignore
except ImportError:
    from typing_extensions import Annotated, Self, get_origin

from .exception import MatchFailed
from .config import lang
from .util import generic_isinstance, TPattern, Empty


def _accept(
    input_: Any,
    patterns: list[BasePattern] | None = None,
    types: list[type] | None = None,
):
    res_p = any(map(lambda x: x(input_).success, patterns)) if patterns else False
    res_t = generic_isinstance(input_, tuple(types)) if types else False
    return res_t or res_p


class PatternModel(IntEnum):
    """参数表达式匹配模式"""

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
TOrigin = TypeVar("TOrigin")
TVOrigin = TypeVar("TVOrigin")
TDefault = TypeVar("TDefault")


@dataclass
class ValidateResult(Generic[TVOrigin]):
    value: TVOrigin
    flag: ResultFlag

    @property
    def error(self) -> Exception | None:
        if self.flag == ResultFlag.ERROR:
            assert isinstance(self.value, Exception)
            return self.value

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
    def step(self, other: type[T] | T) -> T:
        ...

    @overload
    def step(
        self, other: Callable[[TVOrigin], T]
    ) -> T | Self:
        ...

    @overload
    def step(self, other: BasePattern[T]) -> ValidateResult[T | Exception]:
        ...

    def step(
        self, other: type[T] | Callable[[TVOrigin], T] | Any | BasePattern[T]
    ) -> T | Self | ValidateResult[T | Exception]:
        if other is bool:
            return self.success  # type: ignore
        if callable(other) and self.success:
            return other(self.value)
        if self.success and hasattr(self.value, "__rshift__"):
            return self.value | other  # type: ignore
        return self

    @overload
    def __rshift__(self, other: type[T]| T) -> T:
        ...

    @overload
    def __rshift__(
        self, other: Callable[[TVOrigin], T]
    ) -> T | Self:
        ...

    @overload
    def __rshift__(self, other: BasePattern[T]) -> ValidateResult[T | Exception]:
        ...

    def __rshift__(
        self, other: type[T] | Callable[[TVOrigin], T] | Any
    ) -> T | Self | ValidateResult[T | Exception]:
        return self.step(other)

    def __bool__(self):
        return self.success


class BasePattern(Generic[TOrigin]):
    """对参数类型值的包装"""

    regex_pattern: TPattern  # type: ignore
    pattern: str
    model: PatternModel
    converter: Callable[[BasePattern[TOrigin], str | Any], TOrigin]
    validators: list[Callable[[TOrigin], bool]]

    anti: bool
    origin: type[TOrigin]
    pattern_accepts: list[BasePattern] | None
    type_accepts: list[type] | None
    alias: str | None
    previous: BasePattern | None

    __slots__ = (
        "regex_pattern",
        "pattern",
        "model",
        "converter",
        "anti",
        "origin",
        "pattern_accepts",
        "type_accepts",
        "alias",
        "previous",
        "validators",
    )

    def __init__(
        self,
        pattern: str = "(.+?)",
        model: int | PatternModel = PatternModel.REGEX_MATCH,
        origin: type[TOrigin] = str,
        converter: Callable[[BasePattern[TOrigin], str | Any], TOrigin] | None = None,
        alias: str | None = None,
        previous: BasePattern | None = None,
        accepts: list[type | BasePattern] | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
        anti: bool = False,
    ):
        """
        初始化参数匹配表达式
        """
        if pattern.startswith("^") or pattern.endswith("$"):
            raise ValueError(lang.pattern_head_or_tail_error.format(target=pattern))
        self.pattern = pattern
        self.regex_pattern = re.compile(f"^{pattern}$")
        self.model = PatternModel(model)
        self.origin = origin
        self.alias = alias
        self.previous = previous
        accepts = accepts or []
        self.pattern_accepts = list(
            filter(lambda x: isinstance(x, BasePattern), accepts)
        )
        self.type_accepts = list(
            filter(lambda x: not isinstance(x, BasePattern), accepts)
        )
        self.converter = converter or (
            lambda _, x: (get_origin(origin) or origin)(x)
            if model == PatternModel.TYPE_CONVERT
            else eval(x)
        )
        self.validators = validators or []
        self.anti = anti

    def __repr__(self):
        if self.model == PatternModel.KEEP:
            if self.alias:
                return self.alias
            return (
                "Any" if not self.type_accepts and not self.pattern_accepts else
                "|".join([x.__name__ for x in self.type_accepts] + [x.__repr__() for x in self.pattern_accepts])
            )

        if not self.alias:
            name = getattr(self.origin, "__name__", str(self.origin))
            if self.model == PatternModel.REGEX_MATCH:
                text = self.pattern
            elif self.model == PatternModel.REGEX_CONVERT or (
                not self.type_accepts and not self.pattern_accepts
            ):
                text = name
            else:
                text = (
                    "|".join(
                        [x.__name__ for x in self.type_accepts]
                        + [x.__repr__() for x in self.pattern_accepts]
                    )
                    + " -> "
                    + name
                )
        else:
            text = self.alias
        return (
            f"{f'{self.previous.__repr__()} -> ' if self.previous and id(self.previous) != id(self) else ''}"
            f"{'!' if self.anti else ''}{text}"
        )

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return isinstance(other, BasePattern) and self.__repr__() == other.__repr__()

    @staticmethod
    def of(unit: type[TOrigin]) -> BasePattern[TOrigin]:
        """提供 Type[DataUnit] 类型的构造方法"""
        return BasePattern(
            "", PatternModel.KEEP, unit, alias=unit.__name__, accepts=[unit]
        )

    @staticmethod
    def on(obj: TOrigin) -> BasePattern[TOrigin]:
        """提供 DataUnit 类型的构造方法"""
        return BasePattern(
            "",
            PatternModel.KEEP,
            type(obj),
            alias=str(obj),
            validators=[lambda x: x == obj],
        )

    @staticmethod
    def to(content: Any) -> BasePattern | None:
        """便捷的使用 type_parser 的方法"""
        from .main import type_parser

        if isinstance(res := type_parser(content, "allow"), BasePattern):
            return res

    def reverse(self) -> Self:
        """改变 pattern 的 anti 值"""
        self.anti = not self.anti
        return self

    def prefixed(self):
        """让表达式能在某些场景下实现前缀匹配; 返回自身的拷贝"""
        if self.model in (PatternModel.REGEX_MATCH, PatternModel.REGEX_CONVERT):
            self.regex_pattern = re.compile(f"^{self.pattern}")
        return deepcopy(self)

    def suffixed(self):
        """让表达式能在某些场景下实现后缀匹配; 返回自身的拷贝"""
        if self.model in (PatternModel.REGEX_MATCH, PatternModel.REGEX_CONVERT):
            self.regex_pattern = re.compile(f"{self.pattern}$")
        return deepcopy(self)

    def match(self, input_: str | Any) -> TOrigin:
        """
        对传入的参数进行匹配, 如果匹配成功, 则返回转换后的值, 否则返回None
        """
        if (
            self.model > 0
            and self.origin not in (str, Any)
            and generic_isinstance(input_, self.origin)
        ):
            return input_  # type: ignore
        if (self.type_accepts or self.pattern_accepts) and not _accept(
            input_, self.pattern_accepts, self.type_accepts
        ):
            if not self.previous or not _accept(
                input_ := self.previous.match(input_),
                self.pattern_accepts,
                self.type_accepts,
            ):  # pragma: no cover
                raise MatchFailed(lang.type_error.format(target=input_.__class__))
        if self.model == PatternModel.KEEP:
            return input_  # type: ignore
        if self.model == PatternModel.TYPE_CONVERT:
            res = self.converter(self, input_)
            if res is None and self.origin == Any:  # pragma: no cover
                raise MatchFailed(lang.content_error.format(target=input_))
            if not generic_isinstance(res, self.origin):
                if not self.previous or not generic_isinstance(
                    res := self.converter(self, self.previous.match(input_)), self.origin
                ):
                    raise MatchFailed(lang.content_error.format(target=input_))
            return res
        if not isinstance(input_, str):
            if not self.previous or not isinstance(
                input_ := self.previous.match(input_), str
            ):
                raise MatchFailed(lang.type_error.format(target=type(input_)))
        if r := self.regex_pattern.findall(input_):
            res = r[0][0] if isinstance(r[0], tuple) else r[0]
            return (
                self.converter(self, res)
                if self.model == PatternModel.REGEX_CONVERT
                else res
            )
        raise MatchFailed(lang.content_error.format(target=input_))

    @overload
    def validate(
        self, input_: str | Any
    ) -> ValidateResult[TOrigin | Exception]:
        ...

    @overload
    def validate(
        self, input_: str | Any, default: TDefault
    ) -> ValidateResult[TOrigin | TDefault]:
        ...

    def validate(  # type: ignore
        self, input_: str | Any, default: TDefault | None = None
    ) -> ValidateResult[TOrigin | Exception | TDefault]:
        """
        对传入的值进行正向验证，返回可能的匹配与转化结果。

        若传入默认值，验证失败会返回默认值
        """
        try:
            res = self.match(input_)
            for i in self.validators:
                if not i(res):
                    raise MatchFailed(lang.content_error.format(target=input_))
            return ValidateResult(res, ResultFlag.VALID)
        except Exception as e:
            if default is None:
                return ValidateResult(e, ResultFlag.ERROR)
            return ValidateResult(
                None if default is Empty else default, ResultFlag.DEFAULT
            )

    @overload
    def invalidate(
        self, input_: str | Any
    ) -> ValidateResult[Any | Exception]:
        ...

    @overload
    def invalidate(
        self, input_: str | Any, default: TDefault
    ) -> ValidateResult[Any | TDefault]:
        ...

    def invalidate(
        self, input_: str | Any, default: TDefault | None = None
    ) -> ValidateResult[Any | Exception | TDefault]:
        """
        对传入的值进行反向验证，返回可能的匹配与转化结果。

        若传入默认值，验证失败会返回默认值
        """
        try:
            res = self.match(input_)
        except MatchFailed:
            return ValidateResult(input_, ResultFlag.VALID)
        else:
            for i in self.validators:
                if not i(res):
                    return ValidateResult(input_, ResultFlag.VALID)
            if default is None:
                return ValidateResult(
                    MatchFailed(lang.content_error.format(target=input_)),
                    ResultFlag.ERROR,
                )
            return ValidateResult(
                None if default is Empty else default, ResultFlag.DEFAULT
            )

    def __call__(self, input_: str | Any, default: TDefault | None = None):
        """
        依据 anti 值 自动选择验证方式
        """
        if self.anti:
            return self.invalidate(input_, default)
        else:
            return self.validate(input_, default)

    def __rrshift__(self, other):
        return self.__call__(other)

    def __rmatmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self

    def __matmul__(self, other) -> Self:  # pragma: no cover
        if isinstance(other, str):
            self.alias = other
        return self


def set_unit(
    target: type[TOrigin], predicate: Callable[..., bool]
) -> Annotated[TOrigin, ...]:
    """通过predicate区分同一个类的不同情况"""
    return Annotated[target, predicate]


__all__ = ["PatternModel", "BasePattern", "set_unit", "ValidateResult", "TOrigin"]
