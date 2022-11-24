import inspect
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
from typing import Optional, Any, Union, Dict, Literal, Iterable, TypeVar, Type

try:
    from typing import Annotated, get_args, get_origin  # type: ignore
except ImportError:
    from typing_extensions import Annotated, get_args, get_origin

from .config import lang
from .core import BasePattern, PatternModel
from .base import UnionArg, MappingArg, SequenceArg
from .util import AllParam, Empty, GenericAlias

AnyOne = BasePattern(r".+", PatternModel.KEEP, Any, alias="any")
"""匹配任意内容的表达式"""

_String = BasePattern(r"(.+?)", PatternModel.KEEP, str, alias="str", accepts=[str])

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
    PatternModel.REGEX_CONVERT,
    int,
    lambda _, x: int(x, 16),
    "hex",
)
"""匹配16进制数的表达式"""

HEX_COLOR = BasePattern(
    r"(#[0-9a-fA-F]{6})", PatternModel.REGEX_CONVERT, str, lambda _, x: x[1:], "color"
)
"""匹配16进制颜色代码的表达式"""

DATETIME = BasePattern(
    model=PatternModel.TYPE_CONVERT,
    origin=datetime,
    alias="datetime",
    accepts=[str, int],
    converter=lambda _, x: datetime.fromtimestamp(x)
    if isinstance(x, int)
    else datetime.fromisoformat(x),
)
"""匹配时间的表达式"""

pattern_map = {
    Any: AnyOne,
    Ellipsis: AnyOne,
    object: AnyOne,
    "email": EMAIL,
    "color": HEX_COLOR,
    "hex": HEX,
    "ip": IP,
    "url": URL,
    "...": AnyOne,
    "*": AllParam,
    "": Empty,
    "datetime": DATETIME,
}


def set_converter(
        target: BasePattern,
        alias: Optional[str] = None,
        cover: bool = True,
        data: Optional[dict] = None,
):
    """
    增加可使用的类型转换器

    Args:
        target: 设置的表达式
        alias: 目标类型的别名
        cover: 是否覆盖已有的转换器
        data: BasePattern的存储字典
    """
    data = pattern_map if data is None else data
    for k in {alias, target.alias, target.origin}:
        if not k:
            continue
        if k not in data or cover:
            data[k] = target
        else:
            al_pat = data[k]
            data[k] = (
                UnionArg([*al_pat.arg_value, target])
                if isinstance(al_pat, UnionArg)
                else (UnionArg([al_pat, target]))
            )


def set_converters(
        patterns: Union[Iterable[BasePattern], Dict[str, BasePattern]],
        cover: bool = True,
        data: Optional[dict] = None,
):
    for arg_pattern in patterns:
        if isinstance(patterns, Dict):
            set_converter(patterns[arg_pattern], alias=arg_pattern, cover=cover, data=data)  # type: ignore
        else:
            set_converter(arg_pattern, cover=cover, data=data)  # type: ignore


def remove_converter(
        origin_type: type, alias: Optional[str] = None, data: Optional[dict] = None
):
    data = data or pattern_map
    if alias and (al_pat := data.get(alias)):
        if isinstance(al_pat, UnionArg):
            data[alias] = UnionArg(filter(lambda x: x.alias != alias, al_pat.arg_value))  # type: ignore
            if not data[alias].arg_value:  # pragma: no cover
                del data[alias]
        else:
            del data[alias]
    elif al_pat := data.get(origin_type):
        if isinstance(al_pat, UnionArg):
            data[origin_type] = UnionArg(
                filter(lambda x: x.origin != origin_type, al_pat.for_validate)
            )
            if not data[origin_type].arg_value:  # pragma: no cover
                del data[origin_type]
        else:
            del data[origin_type]


StrPath = BasePattern(
    model=PatternModel.TYPE_CONVERT, origin=Path, alias="path", accepts=[str]
)
PathFile = BasePattern(
    model=PatternModel.TYPE_CONVERT,
    origin=bytes,
    alias="file",
    accepts=[Path],
    previous=StrPath,
    converter=lambda _, x: x.read_bytes() if x.exists() and x.is_file() else None,  # type: ignore
)

INTEGER = BasePattern(
    r"(\-?\d+)", PatternModel.REGEX_CONVERT, int, lambda _, x: int(x), "int"
)
"""整形数表达式，只能接受整数样式的量"""

FLOAT = BasePattern(
    r"(\-?\d+\.?\d*)", PatternModel.REGEX_CONVERT, float, lambda _, x: float(x), "float"
)
"""浮点数表达式"""

NUMBER = BasePattern(
    r"(\-?\d+\.?\d*)",
    PatternModel.TYPE_CONVERT,
    int,
    lambda _, x: int(float(x)),
    "number",
    accepts=[FLOAT, int],
)
"""一般数表达式，既可以浮点数也可以整数"""

_Bool = BasePattern(
    r"(?i:True|False)",
    PatternModel.REGEX_CONVERT,
    bool,
    lambda _, x: x.lower() == "true",
    "bool",
)
_List = BasePattern(r"(\[.+?\])", PatternModel.REGEX_CONVERT, list, alias="list")
_Tuple = BasePattern(r"(\(.+?\))", PatternModel.REGEX_CONVERT, tuple, alias="tuple")
_Set = BasePattern(r"(\{.+?\})", PatternModel.REGEX_CONVERT, set, alias="set")
_Dict = BasePattern(r"(\{.+?\})", PatternModel.REGEX_CONVERT, dict, alias="dict")
set_converters([PathFile, _String, INTEGER, FLOAT, _Bool, _List, _Tuple, _Set, _Dict])

pattern_map["number"] = NUMBER


def _generic_parser(item: GenericAlias, extra: str):
    origin = get_origin(item)
    if origin is Annotated:
        org, *meta = get_args(item)
        if not isinstance(_o := type_parser(org, extra), BasePattern):  # type: ignore  # pragma: no cover
            return _o
        _arg = deepcopy(_o)
        _arg.alias = (
            al[-1] if (al := [i for i in meta if isinstance(i, str)]) else _arg.alias
        )
        _arg.validators.extend(i for i in meta if callable(i))
        return _arg
    if origin in (Union, Literal):
        _args = {type_parser(t, extra) for t in get_args(item)}
        return (_args.pop() if len(_args) == 1 else UnionArg(_args)) if _args else item
    if origin in (dict, ABCMap, ABCMuMap):
        return MappingArg(
            arg_key=type_parser(get_args(item)[0], "ignore"),
            arg_value=type_parser(get_args(item)[1], "allow"),
        )
    args = type_parser(get_args(item)[0], "allow")
    if origin in (ABCMuSeq, list):
        return SequenceArg(args)
    if origin in (ABCSeq, tuple):
        return SequenceArg(args, form="tuple")
    if origin in (ABCMuSet, ABCSet, set):
        return SequenceArg(args, form="set")
    return BasePattern("", 0, origin, alias=f"{repr(item).split('.')[-1]}", accepts=[origin])  # type: ignore


def _typevar_parser(item: TypeVar):
    return BasePattern(model=PatternModel.KEEP, origin=Any, alias=f'{item}'[1:], accepts=[item])  # type: ignore


def _protocol_parser(item: Type):
    if getattr(item, '_is_runtime_protocol', False):
        return BasePattern(model=PatternModel.KEEP, origin=Any, alias=f'{item}', accepts=[item])
    return AnyOne # pragma: no cover


def type_parser(item: Any, extra: str = "allow"):
    """对数类型的检查， 将一般数据类型转为 BasePattern 或者特殊类型"""
    if isinstance(item, BasePattern) or item is AllParam:
        return item
    with suppress(TypeError):
        if pat := pattern_map.get(item, None):
            return pat
    if not inspect.isclass(item) and isinstance(item, GenericAlias):
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
            model=PatternModel.TYPE_CONVERT,
        )
    if isinstance(item, str):
        if item.startswith("re:"):
            return BasePattern(item[3:], alias=f"'{item}'")
        if "|" in item:
            names = item.split("|")
            return UnionArg(pattern_map.get(i, i) for i in names if i)
        return BasePattern(item, alias=f"'{item}'")
    if isinstance(
            item, (list, tuple, set, ABCSeq, ABCMuSeq, ABCSet, ABCMuSet)
    ):  # Args[foo, [123, int]]
        return UnionArg(
            map(lambda x: type_parser(x) if inspect.isclass(x) else x, item)
        )
    if isinstance(item, (dict, ABCMap, ABCMuMap)):
        return BasePattern(
            "",
            PatternModel.TYPE_CONVERT,
            Any,
            lambda _, x: item.get(x, None),
            "|".join(item.keys()),
        )
    if item is None or type(None) == item:
        return Empty
    if extra == "ignore":
        return AnyOne
    elif extra == "reject":
        raise TypeError(lang.validate_reject.format(target=item))
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
                else pattern_map.get(params[0])
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
        pattern.validators.extend(filter(callable, params[1:]))
        return pattern


__all__ = [
    "Bind",
    "pattern_map",
    "set_converter",
    "set_converters",
    "remove_converter",
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
