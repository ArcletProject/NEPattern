import re
from enum import IntEnum, Enum
from typing import (
    TypeVar,
    Type,
    Callable,
    Optional,
    Any,
    Union,
    List,
    Generic,
    overload,
)
from dataclasses import dataclass

try:
    from typing import Annotated  # type: ignore
except ImportError:
    from typing_extensions import Annotated

from .exception import MatchFailed
from .config import lang
from .util import generic_isinstance, TPattern, Empty


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


TOrigin = TypeVar("TOrigin")
TDefault = TypeVar("TDefault")


@dataclass
class ValidateResult(Generic[TOrigin]):
    value: TOrigin
    flag: ResultFlag

    @property
    def error(self) -> Optional[Exception]:
        if self.flag == ResultFlag.ERROR:
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


class BasePattern(Generic[TOrigin]):
    """对参数类型值的包装"""

    regex_pattern: TPattern  # type: ignore
    pattern: str
    model: PatternModel
    converter: Callable[[Union[str, Any]], TOrigin]
    validators: List[Callable[[TOrigin], bool]]

    anti: bool
    origin: Type[TOrigin]
    accepts: Optional[List[Type]]
    alias: Optional[str]
    previous: Optional["BasePattern"]

    __slots__ = (
        "regex_pattern",
        "pattern",
        "model",
        "converter",
        "anti",
        "origin",
        "accepts",
        "alias",
        "previous",
        "validators",
    )

    def __init__(
        self,
        pattern: str = "(.+?)",
        model: Union[int, PatternModel] = PatternModel.REGEX_MATCH,
        origin: Type[TOrigin] = str,
        converter: Optional[Callable[[Union[str, Any]], TOrigin]] = None,
        alias: Optional[str] = None,
        previous: Optional["BasePattern"] = None,
        accepts: Optional[List[Type]] = None,
        validators: Optional[List[Callable[[TOrigin], bool]]] = None,
        anti: bool = False,
    ):
        """
        初始化参数匹配表达式
        """
        self.pattern = pattern
        self.regex_pattern = re.compile(f"^{pattern}$")
        self.model = PatternModel(model)
        self.origin = origin
        self.alias = alias
        self.previous = previous
        self.accepts = accepts
        self.converter = converter or (
            lambda x: origin(x) if model == PatternModel.TYPE_CONVERT else eval(x)
        )
        self.validators = validators or []
        self.anti = anti

    def __repr__(self):
        if self.model == PatternModel.KEEP:
            return self.alias or (
                ("|".join(x.__name__ for x in self.accepts)) if self.accepts else "Any"
            )
        name = self.alias or getattr(self.origin, "__name__", str(self.origin))
        if self.model == PatternModel.REGEX_MATCH:
            text = self.alias or self.pattern
        elif self.model == PatternModel.REGEX_CONVERT:
            text = name
        else:
            text = (
                ("|".join(x.__name__ for x in self.accepts) + " -> ")
                if self.accepts
                else ""
            ) + name
        return f"{(f'{self.previous.__repr__()}, ' if self.previous else '')}{'!' if self.anti else ''}{text}"

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return hash(self.__repr__())

    def __eq__(self, other):
        return isinstance(other, BasePattern) and self.__repr__() == other.__repr__()

    @staticmethod
    def of(unit: Type[TOrigin]) -> "BasePattern[TOrigin]":
        """提供 Type[DataUnit] 类型的构造方法"""
        return BasePattern(
            "", PatternModel.KEEP, unit, alias=unit.__name__, accepts=[unit]
        )

    @staticmethod
    def on(obj: TOrigin) -> "BasePattern[TOrigin]":
        """提供 DataUnit 类型的构造方法"""
        return BasePattern(
            "",
            PatternModel.KEEP,
            type(obj),
            alias=str(obj),
            validators=[lambda x: x == obj],
        )

    @staticmethod
    def to(content: Any) -> Optional["BasePattern"]:
        """便捷的使用 type_parser 的方法"""
        from .main import type_parser

        if isinstance(res := type_parser(content, "allow"), BasePattern):
            return res

    def reverse(self):
        self.anti = not self.anti
        return self

    def match(self, input_: Union[str, Any]) -> TOrigin:
        """
        对传入的参数进行匹配, 如果匹配成功, 则返回转换后的值, 否则返回None
        """
        if (
            self.model > 0
            and self.origin not in (str, Any)
            and generic_isinstance(input_, self.origin)
        ):
            return input_  # type: ignore
        if self.accepts and not isinstance(input_, tuple(self.accepts)):
            if not self.previous or not isinstance(
                input_ := self.previous.match(input_), tuple(self.accepts)
            ):  # pragma: no cover
                raise MatchFailed(lang.type_error.format(target=input_.__class__))
        if self.model == PatternModel.KEEP:
            return input_  # type: ignore
        if self.model == PatternModel.TYPE_CONVERT:
            res = self.converter(input_)
            if not generic_isinstance(res, self.origin) or (
                not res and self.origin == Any
            ):
                raise MatchFailed(lang.content_error.format(target=input_))
            return res
        if not isinstance(input_, str):
            if not self.previous or not isinstance(
                input_ := self.previous.match(input_), str
            ):
                raise MatchFailed(lang.type_error.format(target=type(input_)))
        if r := self.regex_pattern.findall(input_):
            return (
                self.converter(r[0])
                if self.model == PatternModel.REGEX_CONVERT
                else r[0]
            )
        raise MatchFailed(lang.content_error.format(target=input_))

    @overload
    def validate(
        self, input_: Union[str, Any]
    ) -> ValidateResult[Union[TOrigin, Exception]]:
        ...

    @overload
    def validate(
        self, input_: Union[str, Any], default: TDefault
    ) -> ValidateResult[Union[TOrigin, TDefault]]:
        ...

    def validate(
        self, input_: Union[str, Any], default: Optional[TDefault] = None
    ) -> ValidateResult[Union[TOrigin, Exception, TDefault]]:
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
        self, input_: Union[str, Any]
    ) -> ValidateResult[Union[TOrigin, Exception]]:
        ...

    @overload
    def invalidate(
        self, input_: Union[str, Any], default: TDefault
    ) -> ValidateResult[Union[TOrigin, TDefault]]:
        ...

    def invalidate(
        self, input_: Union[str, Any], default: Optional[TDefault] = None
    ) -> ValidateResult[Union[TOrigin, Exception, TDefault]]:
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


def set_unit(
    target: Type[TOrigin], predicate: Callable[..., bool]
) -> Annotated[TOrigin, ...]:
    return Annotated[target, predicate]


__all__ = ["PatternModel", "BasePattern", "set_unit", "ValidateResult"]
