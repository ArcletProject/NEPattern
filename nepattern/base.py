import re
from typing import List, Union, Iterable, Any, Dict

from .config import lang
from .core import BasePattern, PatternModel
from .exception import MatchFailed
from .util import Empty


class UnionArg(BasePattern):
    """多类型参数的匹配"""

    optional: bool
    arg_value: List[Union[BasePattern, object, str]]
    for_validate: List[BasePattern]
    for_equal: List[Union[str, object]]

    def __init__(
        self, base: Iterable[Union[BasePattern, object, str]], anti: bool = False
    ):
        self.arg_value = list(base)
        self.optional = False
        self.for_validate = []
        self.for_equal = []

        for arg in self.arg_value:
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
            r"(.+?)", PatternModel.KEEP, str, alias=alias_content, anti=anti
        )

    def match(self, text: Union[str, Any]):
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


class SequenceArg(BasePattern):
    """匹配列表或者元组或者集合"""

    form: str
    arg_value: BasePattern

    def __init__(self, base: BasePattern, form: str = "list"):
        self.form = form
        self.arg_value = base
        if form == "list":
            super().__init__(
                r"\[(.+?)\]", PatternModel.REGEX_MATCH, list, alias=f"list[{base}]"
            )
        elif form == "tuple":
            super().__init__(
                r"\((.+?)\)", PatternModel.REGEX_MATCH, tuple, alias=f"tuple[{base}]"
            )
        elif form == "set":
            super().__init__(
                r"\{(.+?)\}", PatternModel.REGEX_MATCH, set, alias=f"set[{base}]"
            )
        else:
            raise ValueError(lang.sequence_form_error.format(target=form))

    def match(self, text: Union[str, Any]):
        _res = super().match(text)
        result = []
        for s in re.split(r"\s*,\s*", _res) if isinstance(_res, str) else _res:
            try:
                result.append(self.arg_value.match(s))
            except MatchFailed as e:
                raise MatchFailed(f"{s} is not matched with {self.arg_value}") from e
        return self.origin(result)

    def __repr__(self):
        return f"{self.form}[{self.arg_value}]"


class MappingArg(BasePattern):
    """匹配字典或者映射表"""

    arg_key: BasePattern
    arg_value: BasePattern

    def __init__(self, arg_key: BasePattern, arg_value: BasePattern):
        self.arg_key = arg_key
        self.arg_value = arg_value
        super().__init__(
            r"\{(.+?)\}",
            PatternModel.REGEX_MATCH,
            dict,
            alias=f"dict[{self.arg_key}, {self.arg_value}]",
        )

    def match(self, text: Union[str, Any]):
        _res = super().match(text)
        result = {}

        def _generator_items(res: Union[str, Dict]):
            if isinstance(res, dict):
                yield from res.items()
                return
            for m in re.split(r"\s*,\s*", res):
                yield re.split(r"\s*[:=]\s*", m)

        for k, v in _generator_items(_res):
            try:
                real_key = self.arg_key.match(k)
            except MatchFailed as e:
                raise MatchFailed(f"{k} is not matched with {self.arg_key}") from e
            try:
                arg_find = self.arg_value.match(v)
            except MatchFailed as e:
                raise MatchFailed(f"{v} is not matched with {self.arg_value}") from e
            result[real_key] = arg_find

        return result

    def __repr__(self):
        return f"dict[{self.arg_key.origin.__name__}, {self.arg_value}]"


__all__ = ["UnionArg", "SequenceArg", "MappingArg"]
