from typing import Any

from tarina import Empty as Empty  # noqa

from .base import ANY as ANY
from .base import AnyString as AnyString
from .base import BOOLEAN as BOOLEAN
from .base import DATETIME as DATETIME
from .base import DICT as DICT
from .base import DirectPattern as DirectPattern
from .base import EMAIL as EMAIL
from .base import FLOAT as FLOAT
from .base import HEX as HEX
from .base import HEX_COLOR as HEX_COLOR
from .base import INTEGER as INTEGER
from .base import IP as IP
from .base import LIST as LIST
from .base import MappingPattern as MappingPattern
from .base import NONE as NONE
from .base import NUMBER as NUMBER
from .base import PathFile as PathFile
from .base import RegexPattern as RegexPattern
from .base import SET as SET
from .base import STRING as STRING
from .base import SequencePattern as SequencePattern
from .base import SwitchPattern as SwitchPattern
from .base import TUPLE as TUPLE
from .base import URL as URL
from .base import UnionPattern as UnionPattern
from .context import Patterns as Patterns
from .context import all_patterns as all_patterns
from .context import create_local_patterns as create_local_patterns
from .context import global_patterns
from .context import local_patterns as local_patterns
from .context import reset_local_patterns as reset_local_patterns
from .context import switch_local_patterns as switch_local_patterns
from .core import BasePattern as BasePattern
from .core import MatchMode as MatchMode
from .core import ValidateResult as ValidateResult
from .core import set_unit as set_unit
from .exception import MatchFailed as MatchFailed
from .main import Bind as Bind
from .main import parser as parser
from .util import RawStr as RawStr
from .util import TPattern as TPattern

type_parser = parser

global_patterns().update(
    {
        Any: ANY,
        Ellipsis: ANY,
        object: ANY,
        "any": ANY,
        "any_str": AnyString,
        "email": EMAIL,
        "color": HEX_COLOR,
        "hex": HEX,
        "ip": IP,
        "url": URL,
        "...": ANY,
        "datetime": DATETIME,
    }
)
global_patterns().set(PathFile)


global_patterns().sets([STRING, INTEGER, FLOAT, BOOLEAN, LIST, TUPLE, SET, DICT], no_alias=True)
global_patterns()["number"] = NUMBER
