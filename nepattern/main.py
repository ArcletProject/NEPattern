from __future__ import annotations

from collections.abc import Mapping as ABCMap
from collections.abc import MutableMapping as ABCMuMap
from collections.abc import MutableSequence as ABCMuSeq
from collections.abc import MutableSet as ABCMuSet
from collections.abc import Sequence as ABCSeq
from collections.abc import Set as ABCSet
from contextlib import suppress
from copy import deepcopy
from functools import lru_cache
import inspect
from types import FunctionType, LambdaType, MethodType
from typing import Any, ForwardRef, Literal, TypeVar, Union, runtime_checkable
from typing_extensions import Annotated, get_args, get_origin

from tarina.lang import lang

from .base import (
    ANY,
    NONE,
    DirectPattern,
    ForwardRefPattern,
    MappingPattern,
    RegexPattern,
    SequencePattern,
    SwitchPattern,
    UnionPattern,
)
from .context import all_patterns
from .core import BasePattern, MatchMode
from .util import CGenericAlias, CUnionType, GenericAlias, RawStr, TPattern

_Contents = (Union, CUnionType, Literal)


def _generic_parser(item: GenericAlias, extra: str) -> BasePattern:  # type: ignore
    origin = get_origin(item)
    if origin is Annotated:
        org, *meta = get_args(item)
        if not isinstance(_o := parser(org, extra), BasePattern):  # type: ignore  # pragma: no cover
            raise TypeError(_o)
        _arg = deepcopy(_o)
        _arg.alias = al[-1] if (al := [i for i in meta if isinstance(i, str)]) else _arg.alias
        _arg.validators.extend(i for i in meta if callable(i))
        return _arg
    if origin in _Contents:
        _args = {parser(t, extra) for t in get_args(item)}
        return (_args.pop() if len(_args) == 1 else UnionPattern(_args)) if _args else ANY
    if origin in (dict, ABCMap, ABCMuMap):
        if args := get_args(item):
            return MappingPattern(
                arg_key=parser(args[0], "ignore"),
                arg_value=parser(args[1], "allow"),
            )
        return MappingPattern(ANY, ANY)  # pragma: no cover
    _args = parser(args[0], "allow") if (args := get_args(item)) else ANY
    if origin in (ABCMuSeq, list):
        return SequencePattern(list, _args)
    if origin in (ABCSeq, tuple):
        return SequencePattern(tuple, _args)
    if origin in (ABCMuSet, ABCSet, set):
        return SequencePattern(set, _args)
    return BasePattern(mode=MatchMode.KEEP, origin=origin, alias=f"{repr(item).split('.')[-1]}", accepts=[origin])  # type: ignore


def _typevar_parser(item: TypeVar):
    return BasePattern(mode=MatchMode.KEEP, origin=Any, alias=f"{item}"[1:], accepts=[item])  # type: ignore


def _protocol_parser(item: type):
    if not getattr(item, "_is_runtime_protocol", True):  # pragma: no cover
        item = runtime_checkable(deepcopy(item))  # type: ignore
    return BasePattern(mode=MatchMode.KEEP, origin=Any, alias=f"{item}", accepts=[item])


def parser(item: Any, extra: str = "allow") -> BasePattern:
    """对数类型的检查， 将一般数据类型转为 BasePattern 或者特殊类型"""
    if isinstance(item, BasePattern):
        return item
    with suppress(TypeError):
        if item and (pat := all_patterns().get(item, None)):
            return pat
    with suppress(TypeError):
        if not inspect.isclass(item) and isinstance(item, (GenericAlias, CGenericAlias, CUnionType)):
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
            accepts=[] if anno == inspect.Signature.empty else list(_) if (_ := get_args(anno)) else [anno],
            origin=(Any if sig.return_annotation == inspect.Signature.empty else sig.return_annotation),
            converter=item if len(sig.parameters) == 2 else lambda _, x: item(x),
            mode=MatchMode.TYPE_CONVERT,
        )
    if isinstance(item, TPattern):  # type: ignore
        return RegexPattern(item.pattern, alias=f"'{item.pattern}'")
    if isinstance(item, str):
        if item.startswith("re:"):
            pat = item[3:]
            return BasePattern(pat, MatchMode.REGEX_MATCH, alias=f"'{pat}'")
        if item.startswith("rep:"):
            pat = item[4:]
            return RegexPattern(pat, alias=f"'{pat}'")
        if "|" in item:
            names = item.split("|")
            return UnionPattern(all_patterns().get(i, i) for i in names if i)
        return DirectPattern(item)
    if isinstance(item, RawStr):
        return DirectPattern(item.value, alias=f"'{item.value}'")
    if isinstance(item, (list, tuple, set, ABCSeq, ABCMuSeq, ABCSet, ABCMuSet)):  # Args[foo, [123, int]]
        return UnionPattern(map(lambda x: parser(x) if inspect.isclass(x) else x, item))
    if isinstance(item, (dict, ABCMap, ABCMuMap)):
        return SwitchPattern(dict(item))
    if isinstance(item, ForwardRef):
        return ForwardRefPattern(item)
    if item is None or type(None) == item:
        return NONE
    if extra == "ignore":
        return ANY
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
            raise TypeError("Bind[...] should be used with only two arguments (a type and an annotation).")
        if not (
            pattern := params[0] if isinstance(params[0], BasePattern) else all_patterns().get(params[0])
        ):
            raise ValueError("Bind[...] first argument should be a BasePattern.")
        if not all(callable(i) or isinstance(i, str) for i in params[1:]):
            raise TypeError("Bind[...] second argument should be a callable or str.")
        pattern = deepcopy(pattern)
        pattern.alias = al[0] if (al := [i for i in params[1:] if isinstance(i, str)]) else pattern.alias
        pattern._repr = pattern.__calc_repr__()
        pattern._hash = hash(pattern._repr)
        pattern.validators.extend(filter(callable, params[1:]))
        return pattern


__all__ = ["Bind", "parser"]
