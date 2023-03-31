from __future__ import annotations

import re
from typing import Iterable, Any, Literal, TypeVar, Dict, Union
from tarina import Empty

from .config import lang
from .core import BasePattern, MatchMode
from .exception import MatchFailed


class RegexPattern(BasePattern[Union[dict, tuple]]):
    """针对正则的特化匹配，支持正则组"""

    def __init__(self, pattern: str, alias: str | None = None):
        super().__init__(pattern, origin=Union[dict, tuple], alias=alias or 'regex[:group]')  # type: ignore

    def match(self, input_: str | Any):
        if not isinstance(input_, str):
            raise MatchFailed(lang.type_error.format(target=input_))
        if mat := self.regex_pattern.match(input_):
            return mat.groupdict() or mat.groups()
        raise MatchFailed(lang.content_error.format(target=input_))


class UnionPattern(BasePattern):
    """多类型参数的匹配"""

    optional: bool
    base: list[BasePattern | object | str]
    for_validate: list[BasePattern]
    for_equal: list[str | object]

    def __init__(self, base: Iterable[BasePattern | object | str], anti: bool = False):
        self.base = list(base)
        self.optional = False
        self.for_validate = []
        self.for_equal = []

        for arg in self.base:
            if arg == Empty:
                self.optional = True
                self.for_equal.append(None)
            elif isinstance(arg, BasePattern):
                self.for_validate.append(arg)
            else:
                self.for_equal.append(arg)
        alias_content = "|".join(
            [repr(a) for a in self.for_validate] + [repr(a) for a in self.for_equal]
        )
        super().__init__(
            r"(.+?)", MatchMode.KEEP, str, alias=alias_content, anti=anti
        )

    def match(self, text: str | Any):
        if not text:
            text = None
        if text not in self.for_equal:
            for pat in self.for_validate:
                if (res := pat.validate(text)).success:
                    return res.value
            raise MatchFailed(lang.content_error.format(target=text))
        return text

    def __repr__(self):
        return ("!" if self.anti else "") + (
            "|".join(repr(a) for a in (*self.for_validate, *self.for_equal))
        )

    def prefixed(self) -> UnionPattern:
        from .main import type_parser

        return UnionPattern(
            [pat.prefixed() for pat in self.for_validate]
            + [
                type_parser(eq).prefixed() if isinstance(eq, str) else eq  # type: ignore
                for eq in self.for_equal
            ],
            self.anti,
        )

    def suffixed(self) -> UnionPattern:
        from .main import type_parser

        return UnionPattern(
            [pat.suffixed() for pat in self.for_validate]
            + [
                type_parser(eq).suffixed() if isinstance(eq, str) else eq  # type: ignore
                for eq in self.for_equal
            ],
            self.anti,
        )


TSeq = TypeVar("TSeq", list, tuple, set)


class SequencePattern(BasePattern[TSeq]):
    """匹配列表或者元组或者集合"""

    base: BasePattern
    _mode: Literal["pre", "suf", "all"]

    def __init__(self, form: type[TSeq], base: BasePattern):
        self.base = base
        self._mode = "all"
        if form is list:
            super().__init__(
                r"\[(.+?)\]", MatchMode.REGEX_MATCH, form, alias=f"list[{base}]"
            )
        elif form is tuple:
            super().__init__(
                r"\((.+?)\)", MatchMode.REGEX_MATCH, form, alias=f"tuple[{base}]"
            )
        elif form is set:
            super().__init__(
                r"\{(.+?)\}", MatchMode.REGEX_MATCH, form, alias=f"set[{base}]"
            )
        else:
            raise ValueError(lang.sequence_form_error.format(target=str(form)))

    def match(self, text: str | Any):
        _res = super().match(text)
        _max = 0
        success: list[tuple[int, Any]] = []
        fail: list[tuple[int, MatchFailed]] = []
        for _max, s in enumerate(
                re.split(r"\s*,\s*", _res) if isinstance(_res, str) else _res
        ):
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

    def __repr__(self):
        return f"{self.origin.__name__}[{self.base}]"

    def prefixed(self) -> SequencePattern:
        self._mode = "pre"
        return super(SequencePattern, self).prefixed()

    def suffixed(self) -> SequencePattern:
        self._mode = "suf"
        return super(SequencePattern, self).suffixed()


TKey = TypeVar("TKey")
TVal = TypeVar("TVal")


class MappingPattern(BasePattern[Dict[TKey, TVal]]):
    """匹配字典或者映射表"""

    key: BasePattern[TKey]
    value: BasePattern[TVal]
    _mode: Literal["pre", "suf", "all"]

    def __init__(self, arg_key: BasePattern[TKey], arg_value: BasePattern[TVal]):
        self.key = arg_key
        self.value = arg_value
        self._mode = "all"
        super().__init__(
            r"\{(.+?)\}",
            MatchMode.REGEX_MATCH,
            dict,
            alias=f"dict[{self.key}, {self.value}]",
        )

    def match(self, text: str | Any):
        _res = super().match(text)
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
                        MatchFailed(
                            f"{k}: {v} is not matched with {self.key}: {self.value}"
                        ),
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

    def __repr__(self):
        return f"dict[{self.key.origin.__name__}, {self.value}]"

    def prefixed(self) -> MappingPattern:
        self._mode = "pre"
        return super(MappingPattern, self).prefixed()

    def suffixed(self) -> MappingPattern:
        self._mode = "suf"
        return super(MappingPattern, self).suffixed()


_TCase = TypeVar("_TCase")


class SwitchPattern(BasePattern[_TCase]):
    switch: dict[Any, _TCase]

    def __init__(self, data: dict[Any | ellipsis, _TCase]):
        self.switch = data
        super().__init__("", MatchMode.TYPE_CONVERT, type(list(data.values())[0]))

    def __repr__(self):
        return "|".join(f"{k}" for k in self.switch if k != Ellipsis)

    def match(self, input_: Any) -> _TCase:
        try:
            return self.switch[input_]
        except KeyError as e:
            if Ellipsis in self.switch:
                return self.switch[...]
            raise MatchFailed(lang.content_error.format(target=input_)) from e


__all__ = ["RegexPattern", "UnionPattern", "SequencePattern", "MappingPattern", "SwitchPattern"]
