from __future__ import annotations

from enum import Enum, IntEnum
import re
from typing import Any, Callable, Generic, Literal, TypeVar, overload
from typing_extensions import NoReturn, Self

from tarina import Empty

from .base import DirectPattern, DirectTypePattern
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
T1 = TypeVar("T1")
TInput = TypeVar("TInput")
TInput1 = TypeVar("TInput1")
TInput2 = TypeVar("TInput2")
TInput3 = TypeVar("TInput3")
TOrigin = TypeVar("TOrigin")
TOrigin1 = TypeVar("TOrigin1")
TVOrigin = TypeVar("TVOrigin")
TDefault = TypeVar("TDefault")
TVRF = TypeVar("TVRF", bound=ResultFlag)
TMM = TypeVar("TMM", bound=MatchMode)

class ValidateResult(Generic[TVOrigin, TVRF]):
    """参数表达式验证结果"""

    flag: TVRF
    _value: TVOrigin | type[Empty]
    _error: Exception | type[Empty]

    def __init__(
        self,
        value: TVOrigin | type[Empty] = Empty,
        error: Exception | type[Empty] = Empty,
        flag: TVRF = ResultFlag.VALID,
    ): ...
    @overload
    def value(self: ValidateResult[Any, Literal[ResultFlag.ERROR]]) -> NoReturn: ...
    @overload
    def value(self: ValidateResult[TVOrigin, TVRF]) -> TVOrigin: ...
    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.VALID]]) -> None: ...
    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.ERROR]]) -> Exception: ...
    @overload
    def error(self: ValidateResult[Any, Literal[ResultFlag.DEFAULT]]) -> None: ...
    @overload
    def error(self: ValidateResult[TVOrigin, TVRF]) -> Exception | None: ...
    @property
    def success(self) -> bool: ...
    @property
    def failed(self) -> bool: ...
    @property
    def or_default(self) -> bool: ...
    @overload
    def step(self, other: type[T]) -> T: ...
    @overload
    def step(self, other: BasePattern[T, TVOrigin, MatchMode]) -> ValidateResult[T, TVRF]: ...
    @overload
    def step(self, other: Callable[[TVOrigin], T]) -> T: ...
    @overload
    def step(self, other: Any) -> Self: ...
    @overload
    def __rshift__(self, other: BasePattern[T, TVOrigin, MatchMode]) -> ValidateResult[T, TVRF]: ...
    @overload
    def __rshift__(self, other: type[T]) -> T: ...
    @overload
    def __rshift__(self, other: Callable[[TVOrigin], T]) -> T: ...
    @overload
    def __rshift__(self, other: Any) -> Self: ...
    @overload
    def __bool__(self: ValidateResult[TVOrigin, Literal[ResultFlag.VALID]] | ValidateResult[TVOrigin, Literal[ResultFlag.DEFAULT]]) -> Literal[True]: ...
    @overload
    def __bool__(self: ValidateResult[TVOrigin, Literal[ResultFlag.ERROR]]) -> Literal[False]: ...
    def __repr__(self): ...


_MATCHES: dict[MatchMode, Callable[[Any], Callable[[Any, Any], Any]]] = {}

class BasePattern(Generic[TOrigin, TInput, TMM]):
    """对参数类型值的包装"""

    regex_pattern: TPattern  # type: ignore
    pattern: str
    mode: MatchMode
    converter: Callable[[BasePattern[TOrigin, TInput, TMM], Any], TOrigin | None]
    validators: list[Callable[[TOrigin], bool]]

    origin: type[TOrigin]
    alias: str | None
    previous: BasePattern | None
    _repr: str
    _hash: int
    _accepts: type[Any] | tuple[type[Any], ...]
    _pattern_accepts: BasePattern | None

    @overload
    def __init__(
        self: BasePattern[Any, Any, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        origin: Any = None,
        alias: str | None = None,
        previous: None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[T], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput, TInput, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        accepts: type[TInput],
        origin: None = None,
        alias: str | None = None,
        previous: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TInput], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput1, TInput1, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        addition_accepts: BasePattern[Any, TInput1, Any],
        origin: None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: None = None,
        validators: list[Callable[[TInput1], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput1 | TInput2, TInput1 | TInput2, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        accepts: type[TInput1],
        addition_accepts: BasePattern[Any, TInput2, Any],
        origin: None = None,
        alias: str | None = None,
        previous: None = None,
        validators: list[Callable[[TInput1 | TInput2], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput1, TInput1, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        accepts: type[TInput1],
        previous: BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        origin: None = None,
        alias: str | None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TInput1], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput1, TInput1, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        previous: BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        addition_accepts: BasePattern[Any, TInput1, Any],
        origin: None = None,
        alias: str | None = None,
        accepts: None = None,
        validators: list[Callable[[TInput1], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TInput1 | TInput2, TInput1 | TInput2, Literal[MatchMode.KEEP]],
        *,
        mode: Literal[MatchMode.KEEP],
        accepts: type[TInput1],
        previous: BasePattern[TInput1 | TInput2, TInput1 | TInput2, Literal[MatchMode.VALUE_OPERATE]],
        addition_accepts: BasePattern[Any, TInput2, Any],
        origin: None = None,
        alias: str | None = None,
        validators: list[Callable[[TInput1 | TInput2], bool]] | None = None,
    ): ...

    @overload
    def __init__(
        self: BasePattern[str, str, Literal[MatchMode.REGEX_MATCH]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_MATCH],
        origin: type[str] = str,
        converter: None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[str], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[str, str, Literal[MatchMode.REGEX_MATCH]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_MATCH],
        previous: BasePattern[str, str, Literal[MatchMode.VALUE_OPERATE]],
        origin: type[str] = str,
        converter: None = None,
        alias: str | None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[str], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[str, str | TInput1, Literal[MatchMode.REGEX_MATCH]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_MATCH],
        previous: BasePattern[str, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        origin: type[str] = str,
        converter: None = None,
        alias: str | None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[str], bool]] | None = None,
    ): ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, str | TOrigin, Literal[MatchMode.REGEX_CONVERT]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_CONVERT],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, str | TOrigin, Literal[MatchMode.REGEX_CONVERT]], re.Match[str]], TOrigin | None]
        | None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, str | TOrigin | TInput1, Literal[MatchMode.REGEX_CONVERT]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_CONVERT],
        origin: type[TOrigin],
        previous: BasePattern[str | TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]] | BasePattern[str, TInput1, Literal[MatchMode.TYPE_CONVERT]] | BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        converter: Callable[[BasePattern[TOrigin, str | TOrigin | TInput1, Literal[MatchMode.REGEX_CONVERT]], re.Match[str]], TOrigin | None]
        | None = None,
        alias: str | None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, str | TOrigin, Literal[MatchMode.REGEX_CONVERT]],
        pattern: str,
        mode: Literal[MatchMode.REGEX_CONVERT],
        origin: type[TOrigin],
        previous: BasePattern[str | TOrigin, str | TOrigin, Literal[MatchMode.VALUE_OPERATE]] | BasePattern[str, str, Literal[MatchMode.VALUE_OPERATE]] | BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]],
        converter: Callable[[BasePattern[TOrigin, str | TOrigin, Literal[MatchMode.REGEX_CONVERT]], re.Match[str]], TOrigin | None]
        | None = None,
        alias: str | None = None,
        accepts: type[str] = str,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...

    @overload
    def __init__(
        self: BasePattern[TOrigin, Any, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, Any, Literal[MatchMode.TYPE_CONVERT]], Any], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | Any, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        previous: BasePattern[Any, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        converter: Callable[[BasePattern[TOrigin, TInput1 | Any, Literal[MatchMode.TYPE_CONVERT]], Any], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | Any, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        previous: BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        converter: Callable[[BasePattern[TOrigin, TInput1 | Any, Literal[MatchMode.TYPE_CONVERT]], TInput1 | Any], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput],
        converter: Callable[[BasePattern[TOrigin, TInput, Literal[MatchMode.REGEX_CONVERT]], TInput], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        addition_accepts: BasePattern[Any, TInput1, Any],
        converter: Callable[[BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]], TInput1], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput1],
        addition_accepts: BasePattern[Any, TInput2, Any],
        converter: Callable[[BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]], TInput1 | TInput2], TOrigin | None]
        | None = None,
        alias: str | None = None,
        previous: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput1],
        previous: BasePattern[TInput1, TInput2, Literal[MatchMode.TYPE_CONVERT]],
        converter: Callable[[BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]], TInput1], TOrigin | None] | None = None,
        alias: str | None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput1],
        previous: BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        converter: Callable[[BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]], TInput1], TOrigin | None] | None = None,
        alias: str | None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        addition_accepts: BasePattern[Any, TInput1, Any],
        previous: BasePattern[TInput1, TInput2, Literal[MatchMode.TYPE_CONVERT]],
        converter: Callable[[BasePattern[TOrigin, TInput1 | TInput2, Literal[MatchMode.TYPE_CONVERT]], TInput1], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        addition_accepts: BasePattern[Any, TInput1, Any],
        previous: BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        converter: Callable[[BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]], TInput1], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | TInput2 | TInput3, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput1],
        previous: BasePattern[TInput1 | TInput3, TInput2, Literal[MatchMode.TYPE_CONVERT]] | BasePattern[TInput1, TInput2, Literal[MatchMode.TYPE_CONVERT]] | BasePattern[TInput3, TInput2, Literal[MatchMode.TYPE_CONVERT]],
        addition_accepts: BasePattern[Any, TInput3, Any],
        converter: Callable[[BasePattern[TOrigin, TInput1 | TInput2 | TInput3, Literal[MatchMode.TYPE_CONVERT]], TInput1 | TInput3], TOrigin | None]
        | None = None,
        alias: str | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TInput1 | TInput3, Literal[MatchMode.TYPE_CONVERT]],
        *,
        mode: Literal[MatchMode.TYPE_CONVERT],
        origin: type[TOrigin],
        accepts: type[TInput1],
        previous: BasePattern[TInput1 | TInput3, TInput1 | TInput3, Literal[MatchMode.VALUE_OPERATE]] | BasePattern[TInput3, TInput3, Literal[MatchMode.VALUE_OPERATE]] | BasePattern[TInput1, TInput1, Literal[MatchMode.VALUE_OPERATE]],
        addition_accepts: BasePattern[Any, TInput3, Any],
        converter: Callable[[BasePattern[TOrigin, TInput1 | TInput3, Literal[MatchMode.TYPE_CONVERT]], TInput1 | TInput3], TOrigin | None]
        | None = None,
        alias: str | None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]],
        *,
        mode: Literal[MatchMode.VALUE_OPERATE],
        origin: type[TOrigin],
        converter: Callable[[BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]], TOrigin], TOrigin | None] | None = None,
        alias: str | None = None,
        previous: None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TOrigin | TInput1, Literal[MatchMode.VALUE_OPERATE]],
        *,
        mode: Literal[MatchMode.VALUE_OPERATE],
        origin: type[TOrigin],
        previous: BasePattern[TOrigin, TInput1, Literal[MatchMode.TYPE_CONVERT]],
        converter: Callable[[BasePattern[TOrigin, TOrigin | TInput1, Literal[MatchMode.VALUE_OPERATE]], TOrigin], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    @overload
    def __init__(
        self: BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]],
        *,
        mode: Literal[MatchMode.VALUE_OPERATE],
        origin: type[TOrigin],
        previous: BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]],
        converter: Callable[[BasePattern[TOrigin, TOrigin, Literal[MatchMode.VALUE_OPERATE]], TOrigin], TOrigin | None] | None = None,
        alias: str | None = None,
        accepts: None = None,
        addition_accepts: None = None,
        validators: list[Callable[[TOrigin], bool]] | None = None,
    ): ...
    def refresh(self): ...
    def __calc_hash__(self): ...
    def __calc_repr__(self): ...
    def __calc_eq__(self, other): ...
    def __repr__(self): ...
    def __str__(self): ...
    def __hash__(self): ...
    def __eq__(self, other): ...
    @staticmethod
    def of(unit: type[TOrigin]) -> DirectTypePattern[TOrigin]:
        """提供 Type[DataUnit] 类型的构造方法"""
        ...
    @staticmethod
    def on(obj: TOrigin) -> DirectPattern[TOrigin]:
        """提供 DataUnit 类型的构造方法"""
        ...
    @staticmethod
    def to(content: Any) -> BasePattern:
        """便捷的使用 type_parser 的方法"""
        ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, Literal[MatchMode.KEEP]], input_: TInput) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]: ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, Literal[MatchMode.KEEP]], input_: T) -> ValidateResult[T, Literal[ResultFlag.ERROR]]: ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, Literal[MatchMode.VALUE_OPERATE]], input_: TInput) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]: ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, Literal[MatchMode.VALUE_OPERATE]], input_: T) -> ValidateResult[T, Literal[ResultFlag.ERROR]]: ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, TMM], input_: TInput) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]] | ValidateResult[TOrigin, Literal[ResultFlag.ERROR]]: ...
    @overload
    def validate(self: BasePattern[TOrigin, TInput, TMM], input_: T) -> ValidateResult[T, Literal[ResultFlag.ERROR]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, Literal[MatchMode.KEEP]], input_: TInput, default: Any
    ) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, Literal[MatchMode.KEEP]], input_: Any, default: TDefault
    ) -> ValidateResult[TDefault, Literal[ResultFlag.DEFAULT]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, Literal[MatchMode.VALUE_OPERATE]], input_: TInput, default: Any
    ) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, Literal[MatchMode.VALUE_OPERATE]], input_: Any, default: TDefault
    ) -> ValidateResult[TDefault, Literal[ResultFlag.DEFAULT]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, TMM], input_: TInput, default: Any
    ) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]] | ValidateResult[TOrigin, Literal[ResultFlag.ERROR]]: ...
    @overload
    def validate(
        self: BasePattern[TOrigin, TInput, TMM], input_: Any, default: TDefault
    ) -> ValidateResult[TDefault, Literal[ResultFlag.DEFAULT]]: ...
    def match(self, input_: TInput) -> TOrigin: ...
    def copy(self) -> BasePattern[TOrigin, TInput, TMM]: ...
    def __rrshift__(
        self, other: T
    ) -> ValidateResult[T, Literal[ResultFlag.VALID]] | ValidateResult[T, Literal[ResultFlag.ERROR]]: ...
    def __rmatmul__(self, other) -> Self: ...
    def __matmul__(self, other) -> Self: ...
    def __or__(self, other: BasePattern[TOrigin1, TInput1, Any]) -> BasePattern[TOrigin1 | TOrigin, TInput1 | TInput, TMM]: ...