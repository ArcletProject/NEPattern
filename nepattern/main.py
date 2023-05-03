from __future__ import annotations

import inspect
import sys
import types
from datetime import datetime
from copy import deepcopy
from collections.abc import (
    Sequence as ABCSeq,
    Set as ABCSet,
    MutableSet as ABCMuSet,
    MutableSequence as ABCMuSeq,
    MutableMapping as ABCMuMap,
    Mapping as ABCMap,
)
from contextlib import suppress
from functools import lru_cache
from pathlib import Path
from types import FunctionType, LambdaType, MethodType
from typing import Any, Union, Literal, TypeVar, runtime_checkable
from tarina import Empty
from tarina.lang import lang

try:
    from typing import Annotated, get_args, get_origin  # type: ignore
except ImportError:
    from typing_extensions import Annotated, get_args, get_origin


from .context import global_patterns, all_patterns
from .core import BasePattern, MatchMode
from .base import UnionPattern, MappingPattern, SequencePattern, RegexPattern, SwitchPattern
from .util import AllParam, GenericAlias, RawStr, CGenericAlias

_Contents = (Union, types.UnionType, Literal) if sys.version_info >= (3, 10) else (Union, Literal)  # pragma: no cover


AnyOne = BasePattern(r".+", MatchMode.KEEP, Any, alias="any")
"""匹配任意内容的表达式"""

AnyString = BasePattern(r".+", MatchMode.TYPE_CONVERT, str, alias="any_str")
"""匹配任意内容并转为字符串的表达式"""

_String = BasePattern(r".+", MatchMode.KEEP, str, alias="str", accepts=[str])

EMAIL = BasePattern(r"(?:[\w\.+-]+)@(?:[\w\.-]+)\.(?:[\w\.-]+)", alias="email")
"""匹配邮箱地址的表达式"""

IP = BasePattern(
    r"(?:(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])\.){3}(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5]):?(?:\d+)?",
    alias="ip",
)
"""匹配Ip地址的表达式"""

URL = BasePattern(
    r"(?:[\w]+://)?[^/\s?#]+[^\s?#]+(?:\?[^\s#]*)?(?:#[^\s]*)?", alias="url"
)
"""匹配网页链接的表达式"""

HEX = BasePattern(
    r"((?:0x)?[0-9a-fA-F]+)",
    MatchMode.REGEX_CONVERT,
    int,
    lambda _, x: int(x, 16),
    "hex",
)
"""匹配16进制数的表达式"""

HEX_COLOR = BasePattern(
    r"(#[0-9a-fA-F]{6})", MatchMode.REGEX_CONVERT, str, lambda _, x: x[1:], "color"
)
"""匹配16进制颜色代码的表达式"""

DATETIME = BasePattern(
    model=MatchMode.TYPE_CONVERT,
    origin=datetime,
    alias="datetime",
    accepts=[str, int],
    converter=lambda _, x: datetime.fromtimestamp(x)
    if isinstance(x, int)
    else datetime.fromisoformat(x),
)
"""匹配时间的表达式"""

global_patterns().update(
    {
        Any: AnyOne,
        Ellipsis: AnyOne,
        object: AnyOne,
        "any": AnyOne,
        "any_str": AnyString,
        "email": EMAIL,
        "color": HEX_COLOR,
        "hex": HEX,
        "ip": IP,
        "url": URL,
        "...": AnyOne,
        "datetime": DATETIME,
    }
)

StrPath = BasePattern(
    model=MatchMode.TYPE_CONVERT, origin=Path, alias="path", accepts=[str]
)
PathFile = BasePattern(
    model=MatchMode.TYPE_CONVERT,
    origin=bytes,
    alias="file",
    accepts=[Path],
    previous=StrPath,
    converter=lambda _, x: x.read_bytes() if x.exists() and x.is_file() else None,  # type: ignore
)

INTEGER = BasePattern(
    r"(\-?\d+)", MatchMode.REGEX_CONVERT, int, lambda _, x: int(x), "int"
)
"""整形数表达式，只能接受整数样式的量"""

FLOAT = BasePattern(
    r"(\-?\d+\.?\d*)", MatchMode.REGEX_CONVERT, float, lambda _, x: float(x), "float"
)
"""浮点数表达式"""

NUMBER = BasePattern(
    r"(\-?\d+\.?\d*)",
    MatchMode.TYPE_CONVERT,
    int,
    lambda _, x: int(float(x)),
    "number",
    accepts=[FLOAT, int],
)
"""一般数表达式，既可以浮点数也可以整数"""

_Bool = BasePattern(
    r"(?i:True|False)",
    MatchMode.REGEX_CONVERT,
    bool,
    lambda _, x: x.lower() == "true",
    "bool",
)
_List = BasePattern(r"(\[.+?\])", MatchMode.REGEX_CONVERT, list, alias="list")
_Tuple = BasePattern(r"(\(.+?\))", MatchMode.REGEX_CONVERT, tuple, alias="tuple")
_Set = BasePattern(r"(\{.+?\})", MatchMode.REGEX_CONVERT, set, alias="set")
_Dict = BasePattern(r"(\{.+?\})", MatchMode.REGEX_CONVERT, dict, alias="dict")

global_patterns().sets([PathFile, _String, INTEGER, FLOAT, _Bool, _List, _Tuple, _Set, _Dict])
global_patterns()["number"] = NUMBER


def _generic_parser(item: GenericAlias, extra: str) -> BasePattern:
    origin = get_origin(item)
    if origin is Annotated:
        org, *meta = get_args(item)
        if not isinstance(_o := type_parser(org, extra), BasePattern):  # type: ignore  # pragma: no cover
            raise TypeError(_o)
        _arg = deepcopy(_o)
        _arg.alias = (
            al[-1] if (al := [i for i in meta if isinstance(i, str)]) else _arg.alias
        )
        _arg.validators.extend(i for i in meta if callable(i))
        return _arg
    if origin in _Contents:
        _args = {type_parser(t, extra) for t in get_args(item)}
        return (_args.pop() if len(_args) == 1 else UnionPattern(_args)) if _args else AnyOne
    if origin in (dict, ABCMap, ABCMuMap):
        if args := get_args(item):
            return MappingPattern(
                arg_key=type_parser(args[0], "ignore"),
                arg_value=type_parser(args[1], "allow"),
            )
        return MappingPattern(AnyOne, AnyOne)  # pragma: no cover
    _args = type_parser(args[0], "allow") if (args := get_args(item)) else AnyOne
    if origin in (ABCMuSeq, list):
        return SequencePattern(list, _args)
    if origin in (ABCSeq, tuple):
        return SequencePattern(tuple, _args)
    if origin in (ABCMuSet, ABCSet, set):
        return SequencePattern(set, _args)
    return BasePattern("", 0, origin, alias=f"{repr(item).split('.')[-1]}", accepts=[origin])  # type: ignore


def _typevar_parser(item: TypeVar):
    return BasePattern(model=MatchMode.KEEP, origin=Any, alias=f'{item}'[1:], accepts=[item])  # type: ignore


def _protocol_parser(item: type):
    if not getattr(item, '_is_runtime_protocol', True):  # pragma: no cover
        item = runtime_checkable(deepcopy(item))  # type: ignore
    return BasePattern(model=MatchMode.KEEP, origin=Any, alias=f'{item}', accepts=[item])


def type_parser(item: Any, extra: str = "allow") -> BasePattern:
    """对数类型的检查， 将一般数据类型转为 BasePattern 或者特殊类型"""
    if isinstance(item, BasePattern) or item is AllParam:
        return item
    with suppress(TypeError):
        if item and (pat := all_patterns().get(item, None)):
            return pat
    with suppress(TypeError):
        if not inspect.isclass(item) and isinstance(item, (GenericAlias, CGenericAlias)):
            return _generic_parser(item, extra)
    if isinstance(item, TypeVar):
        return _typevar_parser(item)
    if inspect.isclass(item) and getattr(item, "_is_protocol", False):
        return _protocol_parser(item)
    if isinstance(item, (FunctionType, MethodType, LambdaType)):
        if len((sig := inspect.signature(item)).parameters) not in (1, 2):  # pragma: no cover
            raise TypeError(f"{item} can only accept 1 or 2 argument")
        anno = list(sig.parameters.values())[-1].annotation
        return BasePattern(
            accepts=[]
            if anno == Empty
            else list(_)
            if (_ := get_args(anno))
            else [anno],
            origin=Any if sig.return_annotation == Empty else sig.return_annotation,
            converter=item if len(sig.parameters) == 2 else lambda _, x: item(x),
            model=MatchMode.TYPE_CONVERT,
        )
    if isinstance(item, str):
        if item.startswith("re:"):
            return RegexPattern(item[3:])
        if "|" in item:
            names = item.split("|")
            return UnionPattern(all_patterns().get(i, i) for i in names if i)
        return BasePattern(item, alias=f"'{item}'")
    if isinstance(item, RawStr):
        return BasePattern(item.value, alias=f"'{item.value}'")
    if isinstance(
        item, (list, tuple, set, ABCSeq, ABCMuSeq, ABCSet, ABCMuSet)
    ):  # Args[foo, [123, int]]
        return UnionPattern(
            map(lambda x: type_parser(x) if inspect.isclass(x) else x, item)
        )
    if isinstance(item, (dict, ABCMap, ABCMuMap)):
        return SwitchPattern(dict(item))
    if item is None or type(None) == item:
        return Empty  # type: ignore
    if extra == "ignore":
        return AnyOne
    elif extra == "reject":
        raise TypeError(lang.require("nepattern", "validate_reject").format(target=item))
    return BasePattern.of(item) if inspect.isclass(item) else BasePattern.on(item)


class Bind:
    __slots__ = ()

    def __new__(cls, *args, **kwargs):  # pragma: no cover
        raise TypeError("Type Bind cannot be instantiated.")

    @classmethod
    @lru_cache(maxsize=None)
    def __class_getitem__(cls, params) -> BasePattern:
        if not isinstance(params, tuple) or len(params) < 2:
            raise TypeError(
                "Bind[...] should be used with only two arguments (a type and an annotation)."
            )
        if not (
            pattern := params[0]
            if isinstance(params[0], BasePattern)
            else all_patterns().get(params[0])
        ):
            raise ValueError("Bind[...] first argument should be a BasePattern.")
        if not all(callable(i) or isinstance(i, str) for i in params[1:]):
            raise TypeError("Bind[...] second argument should be a callable or str.")
        pattern = deepcopy(pattern)
        pattern.alias = (
            al[0]
            if (al := [i for i in params[1:] if isinstance(i, str)])
            else pattern.alias
        )
        pattern._repr = pattern.__calc_repr__()
        pattern._hash = hash(pattern._repr)
        pattern.validators.extend(filter(callable, params[1:]))
        return pattern


__all__ = [
    "Bind",
    "AnyString",
    "type_parser",
    "AnyOne",
    "StrPath",
    "PathFile",
    "NUMBER",
    "HEX",
    "HEX_COLOR",
    "IP",
    "URL",
    "EMAIL",
    "DATETIME",
    "INTEGER",
    "FLOAT",
]
