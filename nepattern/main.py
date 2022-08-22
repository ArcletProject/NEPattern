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
from typing import Optional, Any, Union, Dict, Literal, Iterable

try:
    from typing import Annotated, get_args, get_origin  # type: ignore
except ImportError:
    from typing_extensions import Annotated, get_args, get_origin

from .config import lang
from .core import BasePattern, PatternModel
from .base import UnionArg, MappingArg, SequenceArg
from .util import AllParam, Empty, GenericAlias

AnyOne = BasePattern(r".+", PatternModel.KEEP, Any, alias="any")
_String = BasePattern(r"(.+?)", PatternModel.KEEP, str, alias="str", accepts=[str])
_Email = BasePattern(r"(?:[\w\.+-]+)@(?:[\w\.-]+)\.(?:[\w\.-]+)", alias="email")
_IP = BasePattern(
    r"(?:(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5])\.){3}(?:[01]{0,1}\d{0,1}\d|2[0-4]\d|25[0-5]):?(?:\d+)?",
    alias="ip",
)
_Url = BasePattern(r"[\w]+://[^/\s?#]+[^\s?#]+(?:\?[^\s#]*)?(?:#[^\s]*)?", alias="url")
_HexLike = BasePattern(
    r"((?:0x)?[0-9a-fA-F]+)",
    PatternModel.REGEX_CONVERT,
    int,
    lambda x: int(x, 16),
    "hex",
)
_HexColor = BasePattern(
    r"(#[0-9a-fA-F]{6})", PatternModel.REGEX_CONVERT, str, lambda x: x[1:], "color"
)
_Datetime = BasePattern(
    model=PatternModel.TYPE_CONVERT,
    origin=datetime,
    alias="datetime",
    accepts=[str, int],
    converter=lambda x: datetime.fromtimestamp(x)
    if isinstance(x, int)
    else datetime.fromisoformat(x),
)


pattern_map = {
    Any: AnyOne,
    Ellipsis: AnyOne,
    object: AnyOne,
    "email": _Email,
    "color": _HexColor,
    "hex": _HexLike,
    "ip": _IP,
    "url": _Url,
    "...": AnyOne,
    "*": AllParam,
    "": Empty,
    "datetime": _Datetime,
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
    converter=lambda x: x.read_bytes() if x.exists() and x.is_file() else None,  # type: ignore
)

_Digit = BasePattern(
    r"(\-?\d+)", PatternModel.REGEX_CONVERT, int, lambda x: int(x), "int"
)
_Float = BasePattern(
    r"(\-?\d+\.?\d*)", PatternModel.REGEX_CONVERT, float, lambda x: float(x), "float"
)
_Bool = BasePattern(
    r"(?i:True|False)",
    PatternModel.REGEX_CONVERT,
    bool,
    lambda x: x.lower() == "true",
    "bool",
)
_List = BasePattern(r"(\[.+?\])", PatternModel.REGEX_CONVERT, list, alias="list")
_Tuple = BasePattern(r"(\(.+?\))", PatternModel.REGEX_CONVERT, tuple, alias="tuple")
_Set = BasePattern(r"(\{.+?\})", PatternModel.REGEX_CONVERT, set, alias="set")
_Dict = BasePattern(r"(\{.+?\})", PatternModel.REGEX_CONVERT, dict, alias="dict")
set_converters([PathFile, _String, _Digit, _Float, _Bool, _List, _Tuple, _Set, _Dict])


def _generic_parser(item: GenericAlias, extra: str):
    origin = get_origin(item)
    if origin is Annotated:
        org, meta = get_args(item)
        if not isinstance(_o := type_parser(org, extra), BasePattern):  # type: ignore  # pragma: no cover
            return _o
        _arg = deepcopy(_o)
        _arg.validators.extend(meta if isinstance(meta, tuple) else [meta])  # type: ignore
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


def type_parser(item: Any, extra: str = "allow"):
    """对数类型的检查， 将一般数据类型转为 BasePattern 或者特殊类型"""
    if isinstance(item, BasePattern) or item is AllParam:
        return item
    with suppress(TypeError):
        if pat := pattern_map.get(item, None):
            return pat
    if not inspect.isclass(item) and isinstance(item, GenericAlias):
        return _generic_parser(item, extra)
    if isinstance(item, (FunctionType, MethodType, LambdaType)):
        if len((sig := inspect.signature(item)).parameters) != 1:  # pragma: no cover
            raise TypeError(f"{item} can only accept 1 argument")
        anno = list(sig.parameters.values())[0].annotation
        return BasePattern(
            accepts=[]
            if anno == Empty
            else list(_)
            if (_ := get_args(anno))
            else [anno],
            converter=item,
            origin=Any if sig.return_annotation == Empty else sig.return_annotation,
            model=PatternModel.TYPE_CONVERT,
        )
    if isinstance(item, str):
        if "|" in item:
            names = item.split("|")
            return UnionArg(type_parser(i) for i in names if i)
        return BasePattern(item, alias=f"'{item}'")
    if isinstance(
        item, (list, tuple, set, ABCSeq, ABCMuSeq, ABCSet, ABCMuSet)
    ):  # Args[foo, [123, int]]
        return UnionArg(map(type_parser, item))
    if isinstance(item, (dict, ABCMap, ABCMuMap)):
        return BasePattern(
            "",
            PatternModel.TYPE_CONVERT,
            Any,
            lambda x: item.get(x, None),
            "|".join(item.keys()),
        )
    if item is None or type(None) == item:
        return Empty
    if extra == "ignore":
        return AnyOne
    elif extra == "reject":
        raise TypeError(lang.validate_reject.format(target=item))
    if inspect.isclass(item):
        return BasePattern.of(item)
    return BasePattern.on(item)


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
        if not all(callable(i) for i in params[1:]):
            raise TypeError("Bind[...] second argument should be a callable.")
        pattern = deepcopy(pattern)
        pattern.validators.extend(params[1:])
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
]
