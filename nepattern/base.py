from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import sys
from typing import TYPE_CHECKING, Any, Dict, ForwardRef, Iterable, Literal, Match, TypeVar, Union, cast, overload

from tarina import DateParser, Empty, lang

from .core import BasePattern, MatchMode, ResultFlag, ValidateResult
from .exception import MatchFailed
from .util import TPattern

TOrigin = TypeVar("TOrigin")
TDefault = TypeVar("TDefault")
_T = TypeVar("_T")


class DirectPattern(BasePattern[TOrigin, TOrigin]):
    """直接判断"""

    def __init__(self, target: TOrigin, alias: str | None = None):
        self.target = target
        super().__init__(mode=MatchMode.TYPE_CONVERT, origin=type(target), alias=alias or str(target))

    def prefixed(self):
        if isinstance(self.target, str):
            return BasePattern(self.target, MatchMode.REGEX_MATCH, alias=self.alias).prefixed()
        return self

    def suffixed(self):
        if isinstance(self.target, str):
            return BasePattern(self.target, MatchMode.REGEX_MATCH, alias=self.alias).suffixed()
        return self

    def match(self, input_: Any):
        if input_ != self.target:
            raise MatchFailed(
                lang.require("nepattern", "content_error").format(target=input_, expected=self.target)
            )
        return input_
    
    @overload
    def validate(self, input_: TOrigin) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]:
        ...

    @overload
    def validate(self, input_: _T) -> ValidateResult[_T, Literal[ResultFlag.ERROR]]:
        ...

    @overload
    def validate(self, input_: TOrigin, default: Any) -> ValidateResult[TOrigin, Literal[ResultFlag.VALID]]:
        ...

    @overload
    def validate(self, input_: Any, default: TDefault) -> ValidateResult[TDefault, Literal[ResultFlag.DEFAULT]]:
        ...

    def validate(self, input_: Any, default: Union[TDefault, Empty] = Empty) -> ValidateResult[TOrigin | TDefault, ResultFlag]:  # type: ignore
        if input_ == self.target:
            return ValidateResult(input_, flag=ResultFlag.VALID)
        e = MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.target)
        )
        if default is Empty:
            return ValidateResult(error=e, flag=ResultFlag.ERROR)
        return ValidateResult(default, flag=ResultFlag.DEFAULT)  # type: ignore


class RegexPattern(BasePattern[Match[str], str]):
    """针对正则的特化匹配，支持正则组"""

    def __init__(self, pattern: str | TPattern, alias: str | None = None):
        super().__init__("", origin=Match[str], alias=alias or "regex[:group]")  # type: ignore
        self.regex_pattern = re.compile(pattern)
        self.pattern = self.regex_pattern.pattern

    def match(self, input_: Any) -> Match[str]:
        if not isinstance(input_, str):
            raise MatchFailed(
                lang.require("nepattern", "type_error").format(
                    type=input_.__class__, target=input_, expected="str"
                )
            )
        if mat := self.regex_pattern.match(input_):
            return mat
        raise MatchFailed(
            lang.require("nepattern", "content_error").format(target=input_, expected=self.pattern)
        )


class UnionPattern(BasePattern[Any, _T]):
    """多类型参数的匹配"""

    optional: bool
    for_validate: list[BasePattern]
    for_equal: list[str | object]

    def __init__(self, base: Iterable[_T | BasePattern[Any, _T]]):
        self.base = list(base)
        self.optional = False
        self.for_validate = []
        self.for_equal = []

        for arg in self.base:
            if arg == NONE:
                self.optional = True
                self.for_equal.append(None)
            elif isinstance(arg, BasePattern):
                self.for_validate.append(arg)
            else:
                self.for_equal.append(arg)
        alias_content = "|".join([repr(a) for a in self.for_validate] + [repr(a) for a in self.for_equal])
        super().__init__(mode=MatchMode.KEEP, origin=str, alias=alias_content)

    def match(self, text: Any):
        if not text:
            text = None
        if text not in self.for_equal:
            for pat in self.for_validate:
                if (res := pat.validate(text)).success:
                    return res.value()
            raise MatchFailed(
                lang.require("nepattern", "content_error").format(target=text, expected=self.alias)
            )
        return text

    def __calc_repr__(self):
        return "|".join(repr(a) for a in (*self.for_validate, *self.for_equal))

    def prefixed(self) -> UnionPattern:
        from .main import parser

        return UnionPattern(
            [pat.prefixed() for pat in self.for_validate]
            + [parser(eq).prefixed() if isinstance(eq, str) else eq for eq in self.for_equal],  # type: ignore
        )

    def suffixed(self) -> UnionPattern:
        from .main import parser

        return UnionPattern(
            [pat.suffixed() for pat in self.for_validate]
            + [parser(eq).suffixed() if isinstance(eq, str) else eq for eq in self.for_equal],  # type: ignore
        )


TSeq = TypeVar("TSeq", list, tuple, set)


class SequencePattern(BasePattern[TSeq, Union[str, TSeq]]):
    """匹配列表或者元组或者集合"""

    base: BasePattern
    _mode: Literal["pre", "suf", "all"]

    def __init__(self, form: type[TSeq], base: BasePattern):
        self.base = base
        self._mode = "all"
        if form is list:
            super().__init__(r"\[(.+?)\]", MatchMode.REGEX_CONVERT, form, alias=f"list[{base}]")
        elif form is tuple:
            super().__init__(r"\((.+?)\)", MatchMode.REGEX_CONVERT, form, alias=f"tuple[{base}]")
        elif form is set:
            super().__init__(r"\{(.+?)\}", MatchMode.REGEX_CONVERT, form, alias=f"set[{base}]")
        else:
            raise ValueError(lang.require("nepattern", "sequence_form_error").format(target=str(form)))

    def match(self, text: Any):
        _res = self._MATCHES[MatchMode.REGEX_CONVERT](self, text)  # type: ignore
        _max = 0
        success: list[tuple[int, Any]] = []
        fail: list[tuple[int, MatchFailed]] = []
        for _max, s in enumerate(re.split(r"\s*,\s*", _res) if isinstance(_res, str) else _res):
            try:
                success.append((_max, self.base.match(s)))
            except MatchFailed:
                fail.append((_max, MatchFailed(f"{s} is not matched with {self.base}")))

        if (
            (self._mode == "all" and fail)
            or (self._mode == "pre" and fail and fail[0][0] == 0)
            or (self._mode == "suf" and fail and fail[-1][0] == _max)
        ):
            raise fail[0][1]
        if self._mode == "pre" and fail:
            return self.origin(i[1] for i in success if i[0] < fail[0][0])
        if self._mode == "suf" and fail:
            return self.origin(i[1] for i in success if i[0] > fail[-1][0])
        return self.origin(i[1] for i in success)

    def __calc_repr__(self):
        return f"{self.origin.__name__}[{self.base}]"

    def prefixed(self) -> SequencePattern:
        self._mode = "pre"
        return super(SequencePattern, self).prefixed()

    def suffixed(self) -> SequencePattern:
        self._mode = "suf"
        return super(SequencePattern, self).suffixed()


TKey = TypeVar("TKey")
TVal = TypeVar("TVal")


class MappingPattern(BasePattern[Dict[TKey, TVal], Union[str, Dict[TKey, TVal]]]):
    """匹配字典或者映射表"""

    key: BasePattern[TKey, Any]
    value: BasePattern[TVal, Any]
    _mode: Literal["pre", "suf", "all"]

    def __init__(self, arg_key: BasePattern[TKey, Any], arg_value: BasePattern[TVal, Any]):
        self.key = arg_key
        self.value = arg_value
        self._mode = "all"
        super().__init__(
            r"\{(.+?)\}",
            MatchMode.REGEX_CONVERT,
            dict,
            alias=f"dict[{self.key}, {self.value}]",
        )
        self.converter = lambda _, x: x[1]

    def match(self, text: Any):
        _res = self._MATCHES[MatchMode.REGEX_CONVERT](self, text)  # type: ignore
        success: list[tuple[int, Any, Any]] = []
        fail: list[tuple[int, MatchFailed]] = []
        _max = 0

        def _generator_items(res: str | dict):
            if isinstance(res, dict):
                yield from res.items()
                return
            for m in re.split(r"\s*,\s*", res):
                yield re.split(r"\s*[:=]\s*", m)

        for _max, item in enumerate(_generator_items(_res)):
            k, v = item
            try:
                success.append((_max, self.key.match(k), self.value.match(v)))
            except MatchFailed:
                fail.append(
                    (
                        _max,
                        MatchFailed(f"{k}: {v} is not matched with {self.key}: {self.value}"),
                    )
                )
        if (
            (self._mode == "all" and fail)
            or (self._mode == "pre" and fail and fail[0][0] == 0)
            or (self._mode == "suf" and fail and fail[-1][0] == _max)
        ):
            raise fail[0][1]
        if self._mode == "pre" and fail:
            return {i[1]: i[2] for i in success if i[0] < fail[0][0]}
        if self._mode == "suf" and fail:
            return {i[1]: i[2] for i in success if i[0] > fail[-1][0]}
        return {i[1]: i[2] for i in success}

    def __calc_repr__(self):
        return f"dict[{self.key.origin.__name__}, {self.value}]"

    def prefixed(self) -> MappingPattern:
        self._mode = "pre"
        return super(MappingPattern, self).prefixed()

    def suffixed(self) -> MappingPattern:
        self._mode = "suf"
        return super(MappingPattern, self).suffixed()


_TCase = TypeVar("_TCase")
_TSwtich = TypeVar("_TSwtich")


class SwitchPattern(BasePattern[_TCase, _TSwtich]):
    switch: dict[_TSwtich | ellipsis, _TCase]

    def __init__(self, data: dict[_TSwtich | ellipsis, _TCase]):
        self.switch = data
        super().__init__(mode=MatchMode.TYPE_CONVERT, origin=type(list(data.values())[0]))

    def __calc_repr__(self):
        return "|".join(f"{k}" for k in self.switch if k != Ellipsis)

    def match(self, input_: Any) -> _TCase:
        try:
            return self.switch[input_]
        except KeyError as e:
            if Ellipsis in self.switch:
                return self.switch[...]
            raise MatchFailed(
                lang.require("nepattern", "content_error").format(target=input_, expected=self._repr)
            ) from e


class ForwardRefPattern(BasePattern[Any, Any]):
    def __init__(self, ref: ForwardRef):
        self.ref = ref
        super().__init__(mode=MatchMode.TYPE_CONVERT, origin=Any, alias=ref.__forward_arg__)

    def match(self, input_: Any):
        if isinstance(input_, str) and input_ == self.ref.__forward_arg__:
            return input_
        _main = sys.modules["__main__"]
        if sys.version_info < (3, 9):  # pragma: no cover
            origin = self.ref._evaluate(_main.__dict__, _main.__dict__)
        else:  # pragma: no cover
            origin = self.ref._evaluate(_main.__dict__, _main.__dict__, frozenset())  # type: ignore
        if not isinstance(input_, origin):  # type: ignore
            raise MatchFailed(
                lang.require("nepattern", "type_error").format(
                    type=input_.__class__, target=input_, expected=self.ref.__forward_arg__
                )
            )
        return input_

class AntiPattern(BasePattern[TOrigin, Any]):
    def __init__(self, pattern: BasePattern[TOrigin, Any]):
        self.base: BasePattern[TOrigin, Any] = pattern
        super().__init__(mode=MatchMode.TYPE_CONVERT, origin=pattern.origin, alias=f"!{pattern}")

    @overload
    def validate(self, input_: TOrigin) -> ValidateResult[Any, Literal[ResultFlag.ERROR]]:
        ...

    @overload
    def validate(self, input_: _T) -> ValidateResult[_T, Literal[ResultFlag.VALID]]:
        ...

    @overload
    def validate(self, input_: TOrigin, default: TDefault) -> ValidateResult[TDefault, Literal[ResultFlag.DEFAULT]]:
        ...

    @overload
    def validate(self, input_: _T, default: Any) -> ValidateResult[_T, Literal[ResultFlag.VALID]]:
        ...

    def validate(self, input_: _T, default: Union[TDefault, Empty] = Empty) -> ValidateResult[_T | TDefault, ResultFlag]:  # type: ignore
        """
        对传入的值进行反向验证，返回可能的匹配与转化结果。

        若传入默认值，验证失败会返回默认值
        """
        try:
            res = self.base.match(input_)
        except MatchFailed:
            return ValidateResult(value=input_, flag=ResultFlag.VALID)
        else:  # pragma: no cover
            for i in self.base.validators + self.validators:
                if not i(res):
                    return ValidateResult(value=input_, flag=ResultFlag.VALID)
            if default is Empty:
                return ValidateResult(
                    error=MatchFailed(
                        lang.require("nepattern", "content_error").format(target=input_, expected=self._repr)
                    ),
                    flag=ResultFlag.ERROR,
                )
            if TYPE_CHECKING:
                default = cast(TDefault, default)
            return ValidateResult(default, flag=ResultFlag.DEFAULT)


NONE = BasePattern(mode=MatchMode.KEEP, origin=None, alias="none")  # type: ignore

ANY = BasePattern(mode=MatchMode.KEEP, origin=Any, alias="any")
"""匹配任意内容的表达式"""

AnyString = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=str, alias="any_str")
"""匹配任意内容并转为字符串的表达式"""

STRING = BasePattern(mode=MatchMode.KEEP, origin=str, alias="str", accepts=str)

INTEGER = BasePattern(r"(\-?\d+)", MatchMode.REGEX_CONVERT, int, lambda _, x: int(x[1]), "int")
"""整形数表达式，只能接受整数样式的量"""

FLOAT = BasePattern(r"(\-?\d+\.?\d*)", MatchMode.REGEX_CONVERT, float, lambda _, x: float(x[1]), "float")
"""浮点数表达式"""

NUMBER = BasePattern(
    r"(\-?\d+(?P<float>\.\d*)?)",
    MatchMode.REGEX_CONVERT,
    Union[int, float],
    lambda _, x: float(x[1]) if x["float"] else int(x[1]),
    "number",
)
"""一般数表达式，既可以浮点数也可以整数"""

BOOLEAN = BasePattern(
    r"(?i:True|False)",
    MatchMode.REGEX_CONVERT,
    bool,
    lambda _, x: x[0].lower() == "true",
    "bool",
)
LIST = BasePattern(r"(\[.+?\])", MatchMode.REGEX_CONVERT, list, alias="list")
TUPLE = BasePattern(r"(\(.+?\))", MatchMode.REGEX_CONVERT, tuple, alias="tuple")
SET = BasePattern(r"(\{.+?\})", MatchMode.REGEX_CONVERT, set, alias="set")
DICT = BasePattern(r"(\{.+?\})", MatchMode.REGEX_CONVERT, dict, alias="dict")

EMAIL = BasePattern(r"(?:[\w\.+-]+)@(?:[\w\.-]+)\.(?:[\w\.-]+)", MatchMode.REGEX_MATCH, alias="email")
"""匹配邮箱地址的表达式"""

IP = BasePattern(
    r"(?:(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])\.){3}(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5]):?(?:\d+)?",
    MatchMode.REGEX_MATCH,
    alias="ip",
)
"""匹配Ip地址的表达式"""

URL = BasePattern(
    r"(?:\w+://)?[a-zA-Z0-9][-a-zA-Z0-9]{0,62}(?:\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(?::[0-9]{1,5})?[-a-zA-Z0-9()@:%_\\\+\.~#?&//=]*",
    MatchMode.REGEX_MATCH,
    alias="url",
)
"""匹配网页链接的表达式"""

HEX = BasePattern(
    r"((?:0x)?[0-9a-fA-F]+)",
    MatchMode.REGEX_CONVERT,
    int,
    lambda _, x: int(x[1], 16),
    "hex",
)
"""匹配16进制数的表达式"""

HEX_COLOR = BasePattern(r"(#[0-9a-fA-F]{6})", MatchMode.REGEX_CONVERT, str, lambda _, x: x[1][1:], "color")
"""匹配16进制颜色代码的表达式"""


DATETIME = BasePattern(
    mode=MatchMode.TYPE_CONVERT,
    origin=datetime,
    alias="datetime",
    accepts=Union[str, int, float],
    converter=lambda _, x: datetime.fromtimestamp(x) if isinstance(x, (int, float)) else DateParser.parse(x),
)
"""匹配时间的表达式"""


StrPath = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=Path, alias="path", accepts=str)

PathFile = BasePattern(
    mode=MatchMode.TYPE_CONVERT,
    origin=bytes,
    alias="file",
    accepts=Path,
    previous=StrPath,
    converter=lambda _, x: x.read_bytes() if x.exists() and x.is_file() else None,
)
