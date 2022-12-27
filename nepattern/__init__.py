from .core import BasePattern, PatternModel, set_unit, ValidateResult
from .main import (
    type_parser,
    pattern_map,
    set_converter,
    set_converters,
    remove_converter,
    AnyOne,
    Bind,
    NUMBER,
    HEX,
    HEX_COLOR,
    EMAIL,
    DATETIME,
    IP,
    URL,
    INTEGER,
    FLOAT,
)
from .base import UnionPattern, SequencePattern, MappingPattern, RegexPattern, SwitchPattern
from .util import Empty, AllParam, generic_isinstance
from .exception import MatchFailed
from .config import lang


# backport

UnionArg = UnionPattern
MappingArg = MappingPattern
SequenceArg = SequencePattern
RegexArg = RegexPattern
SwitchArg = SwitchPattern
