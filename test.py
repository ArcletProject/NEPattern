from typing import Union

from nepattern import *


def test_type():
    import re

    assert isinstance(re.compile(""), TPattern)  # type: ignore


def test_basic():
    from datetime import datetime

    res = STRING.validate("123")
    if res:
        assert res.success
        assert res.value() == "123"
    assert STRING.validate(b"123").value() == "123"
    assert STRING.validate(123).failed

    assert BYTES.validate(b"123").success
    assert BYTES.validate("123").value() == b"123"
    assert BYTES.validate(123).failed

    assert INTEGER.validate(123).success
    assert INTEGER.validate("123").value() == 123
    assert INTEGER.validate(123.456).value() == 123
    assert INTEGER.validate("123.456").failed
    assert INTEGER.validate("-123").success

    assert FLOAT.validate(123).value() == 123.0
    assert FLOAT.validate("123").value() == 123.0
    assert FLOAT.validate(123.456).value() == 123.456
    assert FLOAT.validate("123.456").value() == 123.456
    assert FLOAT.validate("1e10").value() == 1e10
    assert FLOAT.validate("-123").value() == -123.0
    assert FLOAT.validate("-123.456").value() == -123.456
    assert FLOAT.validate("-123.456e-2").value() == -1.23456
    assert FLOAT.validate("aaa").failed
    assert FLOAT.validate([]).failed

    assert BOOLEAN.validate(True).value() is True
    assert BOOLEAN.validate(False).value() is False
    assert BOOLEAN.validate("True").value() is True
    assert BOOLEAN.validate("False").value() is False
    assert BOOLEAN.validate("true").value() is True
    assert BOOLEAN.validate("false").value() is False
    assert BOOLEAN.validate("1").failed

    assert WIDE_BOOLEAN.validate(True).value() is True
    assert WIDE_BOOLEAN.validate(False).value() is False
    assert WIDE_BOOLEAN.validate("True").value() is True
    assert WIDE_BOOLEAN.validate("False").value() is False
    assert WIDE_BOOLEAN.validate("true").value() is True
    assert WIDE_BOOLEAN.validate("false").value() is False
    assert WIDE_BOOLEAN.validate(1).value() is True
    assert WIDE_BOOLEAN.validate(0).value() is False
    assert WIDE_BOOLEAN.validate("yes").value() is True
    assert WIDE_BOOLEAN.validate("no").value() is False
    assert WIDE_BOOLEAN.validate("2").failed
    assert WIDE_BOOLEAN.validate([]).failed

    assert HEX.validate(123).failed
    assert HEX.validate("0x123").value() == 0x123
    assert HEX.validate("0o123").failed

    assert DATETIME.validate("2020-01-01").value() == datetime(2020, 1, 1)
    assert DATETIME.validate("2020-01-01-12:00:00").value() == datetime(2020, 1, 1, 12, 0, 0)
    assert DATETIME.validate("2020-01-01-12:00:00.123").value() == datetime(2020, 1, 1, 12, 0, 0, 123000)
    assert DATETIME.validate(datetime(2021, 12, 14).timestamp()).value() == datetime(2021, 12, 14, 0, 0, 0)
    assert DATETIME.validate([]).failed

    assert PATH.validate("a/b/c").value().parts == ("a", "b", "c")
    assert PATH.validate(Path("a/b/c")).value() == Path("a/b/c")
    assert PATH.validate([]).failed


def test_result():
    res = NUMBER.validate(123)
    assert res.success
    assert not res.failed
    assert not res.or_default
    assert not res.error()
    assert NUMBER.validate(123).value() == 123
    assert NUMBER.validate("123").value() == 123
    assert NUMBER.validate(123.456).value() == 123.456
    assert NUMBER.validate("123.456").value() == 123.456
    assert NUMBER.validate("aaa").failed
    res1 = NUMBER.validate([], -1)
    assert res1.or_default
    assert not res1.failed
    assert not res1.success
    assert not res.error()
    res2 = NUMBER.validate([])
    assert res2.error()
    assert not res2.or_default
    assert not res2.success
    assert res2.error()
    try:
        res2.value()
    except RuntimeError as e:
        print(e)


def test_pattern_of():
    """测试 BasePattern 的快速创建方法之一, 对类有效"""
    pat = BasePattern.of(int)
    assert pat.origin == int
    assert pat.validate(123).value() == 123
    assert pat.validate("abc").failed
    print(pat)
    print(pat.validate(123).error())
    print(pat.validate("abc").error())


def test_pattern_on():
    """测试 BasePattern 的快速创建方法之一, 对对象有效"""
    pat1 = BasePattern.on(123)
    assert pat1.origin == int
    assert pat1.validate(123).value() == 123
    assert pat1.validate(124).failed
    print(pat1)


def test_pattern_keep():
    """测试 BasePattern 的保持模式, 不会进行匹配或者类型转换"""
    pat2 = BasePattern(mode=MatchMode.KEEP)
    assert pat2.validate(123).value() == 123
    assert pat2.validate("abc").value() == "abc"
    print(pat2)


def test_pattern_regex():
    """测试 BasePattern 的正则匹配模式, 仅正则匹配"""
    pat3 = BasePattern("abc[A-Z]+123", mode=MatchMode.REGEX_MATCH)
    assert pat3.validate("abcABC123").value() == "abcABC123"
    assert pat3.validate("abcAbc123").failed
    print(pat3)

    try:
        BasePattern("^abc$", MatchMode.REGEX_MATCH)
    except ValueError as e:
        print(e)


def test_pattern_regex_convert():
    """测试 BasePattern 的正则转换模式, 正则匹配成功后再进行类型转换"""
    pat4 = BasePattern(
        r"\[at:(\d+)\]",
        MatchMode.REGEX_CONVERT,
        int,
        lambda _, x: res if (res := int(x[1])) < 1000000 else None,
    )
    assert pat4.validate("[at:123456]").value() == 123456
    assert pat4.validate("[at:abcdef]").failed
    assert pat4.validate(123456).value() == 123456
    assert pat4.validate("[at:1234567]").failed
    print(pat4)


def test_pattern_type_convert():
    """测试 BasePattern 的类型转换模式, 仅将传入对象变为另一类型的新对象"""
    pat5 = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=str)
    assert pat5.validate(123).value() == "123"
    assert pat5.validate([4, 5, 6]).value() == "[4, 5, 6]"
    pat5_1 = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=int, converter=lambda self, x: self.origin(x))
    assert pat5_1.validate("123").value() == 123
    assert pat5_1.validate("123.0").failed
    print(pat5)

    def convert(self, content):
        if isinstance(content, str) and content.startswith("123"):
            return 123

    pat5_3 = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=int, converter=convert)
    assert pat5_3.validate("1234abcd").value() == 123
    assert pat5_3.validate("abc").failed
    prev = BasePattern(mode=MatchMode.VALUE_OPERATE, origin=str, converter=lambda _, x: f"123{x}")
    pat5_4 = BasePattern(
        mode=MatchMode.TYPE_CONVERT,
        origin=int,
        accepts=str,
        converter=convert,
        previous=prev,
    )
    assert pat5_4.validate("abc").value() == 123


def test_pattern_accepts():
    """测试 BasePattern 的输入类型筛选, 不在范围内的类型视为非法"""
    pat6 = BasePattern(
        mode=MatchMode.TYPE_CONVERT,
        origin=str,
        converter=lambda _, x: x.decode(),
        accepts=bytes,
    )
    assert pat6.validate(b"123").value() == "123"
    assert pat6.validate(123).failed
    pat6_1 = BasePattern(mode=MatchMode.KEEP, accepts=Union[int, float])
    assert pat6_1.validate(123).value() == 123
    assert pat6_1.validate("123").failed
    print(pat6, pat6_1)
    pat6_2 = BasePattern(mode=MatchMode.KEEP, accepts=bytes, addition_accepts=NUMBER)
    assert pat6_2.validate(123).value() == 123
    assert pat6_2.validate(123.123).value() == 123.123
    assert pat6_2.validate(b"123").value() == b"123"
    print(pat6_2)
    pat6_3 = BasePattern(mode=MatchMode.KEEP, addition_accepts=INTEGER | BOOLEAN)
    assert pat6_3.validate(123).value() == 123
    assert pat6_3.validate(True).value() is True
    assert pat6_3.validate(b"123").value() == b"123"
    assert pat6_3.validate([]).failed


def test_pattern_previous():
    """测试 BasePattern 的前置表达式, 在传入的对象类型不正确时会尝试用前置表达式进行预处理"""

    class A:
        def __repr__(self):
            return "123"

    pat7 = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=str, converter=lambda _, x: f"abc[{x}]", accepts=A)
    pat7_1 = BasePattern(
        r"abc\[(\d+)\]",
        mode=MatchMode.REGEX_CONVERT,
        origin=int,
        converter=lambda self, x: self.origin(x[1]),
        previous=pat7,
    )
    assert pat7_1.validate("abc[123]").value() == 123
    assert pat7_1.validate(A()).value() == 123
    pat7_2 = BasePattern(mode=MatchMode.TYPE_CONVERT, origin=str)
    pat7_3 = BasePattern(
        mode=MatchMode.TYPE_CONVERT,
        origin=int,
        accepts=Union[int, float],  # type: ignore
        previous=pat7_2,  # type: ignore
    )
    assert pat7_3.validate("123").failed
    print(pat7, pat7_1)


def test_pattern_anti():
    """测试 BasePattern 的反向验证功能"""
    pat8 = BasePattern.of(int)
    pat8_1 = AntiPattern(pat8)
    assert pat8.validate(123).value() == 123
    assert pat8.validate("123").failed
    assert pat8_1.validate(123).failed
    assert pat8_1.validate("123").value() == "123"


def test_pattern_validator():
    """测试 BasePattern 的匹配后验证器, 会对匹配结果进行验证"""
    pat9 = BasePattern(mode=MatchMode.KEEP, accepts=int, validators=[lambda x: x > 0])
    assert pat9.validate(23).value() == 23
    assert pat9.validate(-23).failed
    print(pat9)


def test_pattern_default():
    pat10 = BasePattern.of(int)
    assert pat10.validate("123", 123).or_default
    assert pat10.validate("123", 123).value() == 123
    assert AntiPattern(pat10).validate(123, "123").value() == "123"


def test_parser():
    from typing import Literal, Protocol, Type, TypeVar
    from typing_extensions import Annotated

    pat11 = parser(int)
    assert pat11.validate(-321).success
    pat11_1 = parser(123)
    print(pat11, pat11_1)
    pat11_2 = BasePattern.to(int)
    assert pat11_2 == pat11
    assert isinstance(parser(Literal["a", "b"]), UnionPattern)
    assert parser(Type[int]).origin is type
    assert parser(complex) == BasePattern.of(complex)
    assert isinstance(parser("a|b|c"), UnionPattern)
    assert isinstance(parser("re:a|b|c"), BasePattern)
    assert parser([1, 2, 3]).validate(1).success
    assert parser({"a": 1, "b": 2}).validate("a").value() == 1

    def _func(x: int):
        return x + 1

    assert parser(_func).validate(1).value() == 2

    def my_func(x: int) -> str:
        return str(x)

    pat11_3 = parser(my_func)
    assert pat11_3.origin == str
    assert pat11_3._accepts == (int,)

    assert parser(complex, extra="ignore") == ANY

    try:
        parser(complex, extra="reject")
    except TypeError as e:
        print(e)

    pat11_4 = parser(Annotated[int, lambda x: x < 10])
    assert pat11_4.validate(11).failed
    pat11_5 = parser(Annotated[int, lambda x: x >= 0, "normal number"])
    assert pat11_5.alias == "normal number"

    class TestP(Protocol):
        def __setitem__(self): ...

    pat11_6 = parser(TestP)
    assert pat11_6.validate([1, 2, 3]).success
    assert pat11_6.validate((1, 2, 3)).failed

    TestT = TypeVar("TestT", str, int)
    pat11_7 = parser(TestT)
    assert pat11_7.validate("abc").success
    assert pat11_7.validate([]).failed


def test_union_pattern():
    from typing import List, Optional, Union

    pat12 = parser(Union[int, bool])
    assert pat12.validate(123).success
    assert pat12.validate("123").success
    assert pat12.validate("123").value() == 123
    assert pat12.validate(123.0).value() == 123
    pat12_1 = parser(Optional[str])
    assert pat12_1.validate("123").success
    assert pat12_1.validate(None).success
    pat12_2 = UnionPattern(["abc", "efg"])
    assert pat12_2.validate("abc").success
    assert pat12_2.validate("bca").failed
    print(pat12, pat12_1, pat12_2)
    pat12_3 = UnionPattern._(List[bool], int)
    pat12_4 = pat12_2 | pat12_3
    print(pat12_3, pat12_4)


def test_seq_pattern():
    from typing import List, Set, Tuple

    pat13 = parser(List[int])
    pat13_1 = parser(Tuple[int, int])
    pat13_2 = parser(Set[int])
    assert pat13.validate("[1,2,3]").value() == [1, 2, 3]
    assert pat13.validate([1, 2, 3]).success
    assert pat13_1.validate("(1,2,3)").value() == (1, 2, 3)
    assert pat13_2.validate("{1,2,a}").failed
    print(pat13, pat13_1, pat13_2)
    try:
        SequencePattern(dict, BasePattern.of(int))  # type: ignore
    except ValueError as e:
        print(e)
    pat13_3 = SequencePattern(list, INTEGER, IterMode.PRE)
    assert pat13_3.validate([1, 2, 3]).success
    assert pat13_3.validate("[1, 2, a]").value() == [1, 2]
    pat13_4 = SequencePattern(list, INTEGER, IterMode.SUF)
    assert pat13_4.validate([1, 2, 3]).success
    assert pat13_4.validate("[1, 2, a]").failed
    assert pat13_4.validate("[a, 2, 3]").value() == [2, 3]


def test_map_pattern():
    from typing import Dict

    pat14 = parser(Dict[str, int])
    assert pat14.validate("{a:1,b:2}").value() == {"a": 1, "b": 2}
    assert pat14.validate("{a:a, b:2}").failed
    assert pat14.validate({"a": 1, "b": 2}).success
    pat14_1 = parser(Dict[int, int])
    assert pat14_1.validate({"a": 1, "b": 2}).failed
    print(pat14)
    pat14_2 = MappingPattern(INTEGER, BOOLEAN, IterMode.PRE)
    assert pat14_2.validate({1: True, 2: False}).success
    assert pat14_2.validate({1: True, 2: None}).value() == {1: True}
    assert pat14_2.validate({0: None, 1: True, 2: False}).failed
    pat14_3 = MappingPattern(INTEGER, BOOLEAN, IterMode.SUF)
    assert pat14_3.validate({1: True, 2: False}).success
    assert pat14_3.validate({0: None, 1: False, 2: True}).value() == {1: False, 2: True}
    assert pat14_3.validate({0: False, 1: True, 2: None}).failed


def test_converters():
    pattern_map = all_patterns()
    print(pattern_map)
    assert pattern_map["any_str"].validate(123456).value() == "123456"
    assert pattern_map["email"].validate("example@outlook.com").success
    assert pattern_map["ip"].validate("192.168.0.1").success
    assert pattern_map["url"].validate("www.example.com").success
    assert pattern_map["url"].validate("https://www.example.com").value() == "https://www.example.com"
    assert pattern_map["url"].validate("wwwexamplecom").failed
    assert pattern_map["hex"].validate("0xff").value() == 255
    assert pattern_map["color"].validate("#ffffff").value() == "ffffff"
    assert pattern_map["datetime"].validate("2011-11-04").value().day == 4
    assert pattern_map["file"].validate("test.py").value()[:4] == b"from"
    assert pattern_map["number"].validate("123").value() == 123
    assert pattern_map["int"].validate("123").value() == 123
    assert pattern_map["float"].validate("12.34").value() == 12.34
    assert pattern_map["bool"].validate("false").value() is False
    assert pattern_map[list].validate("[1,2,3]").value() == [1, 2, 3]
    assert pattern_map[tuple].validate("(1,2,3)").value() == (1, 2, 3)
    assert pattern_map[set].validate("{1,2,3}").value() == {1, 2, 3}
    assert pattern_map[dict].validate('{"a":1,"b":2,"c":3}').value() == {
        "a": 1,
        "b": 2,
        "c": 3,
    }


def test_converter_method():
    temp = create_local_patterns("test", set_current=False)
    temp.set(BasePattern.of(complex))
    assert temp["complex"]
    temp.set(BasePattern.of(complex), alias="abc")
    assert temp["abc"]
    temp.set(BasePattern.of(int), alias="abc", cover=False)
    assert isinstance(temp["abc"], UnionPattern)
    temp.merge({"b": BasePattern.of(bool), "c": BasePattern.of(str)})
    assert temp["b"]
    assert temp["c"]
    temp.remove(complex, alias="complex")
    assert not temp.get("complex")
    temp.set(BasePattern(mode=MatchMode.KEEP, alias="a"))
    temp.set(BasePattern(mode=MatchMode.KEEP, accepts=int, alias="b"), alias="a", cover=False)
    temp.remove(int, alias="a")
    assert temp["a"]
    temp.remove(int)
    temp.remove(bool)
    temp.remove(type(None))
    assert not temp.get(int)


def test_dunder():
    pat17 = BasePattern.of(float)
    assert ("test_float" @ pat17).alias == "test_float"
    assert pat17.validate(1.33).step(str) == pat17.validate(1.33) >> str == "1.33"
    assert (pat17.validate(1.33) >> 1).value() == 1.33
    assert not "1.33" >> pat17
    assert pat17.validate(1.33) >> bool
    assert BasePattern.of(int).validate(1).step(lambda x: x + 2) == 3
    pat17_1 = BasePattern(r"@(\d+)", MatchMode.REGEX_CONVERT, str, lambda _, x: x[0][1:])
    pat17_2: BasePattern[int, Any, Any] = parser(int)
    assert ("@123456" >> pat17_1 >> pat17_2).value() == 123456


def test_regex_pattern():
    from re import Match, compile

    pat18 = RegexPattern(r"((https?://)?github\.com/)?(?P<owner>[^/]+)/(?P<repo>[^/]+)", "ghrepo")
    res = pat18.validate("https://github.com/ArcletProject/NEPattern").value()
    assert isinstance(res, Match)
    assert res.groupdict() == {"owner": "ArcletProject", "repo": "NEPattern"}
    assert pat18.validate(123).failed
    assert pat18.validate("www.bilibili.com").failed
    pat18_1 = parser(r"re:(\d+)")  # str starts with "re:" will convert to BasePattern instead of RegexPattern
    assert pat18_1.validate("1234").value() == "1234"
    pat18_2 = parser(r"rep:(\d+)")  # str starts with "rep:" will convert to RegexPattern
    assert pat18_2.validate("1234").value().groups() == ("1234",)  # type: ignore
    pat18_3 = parser(compile(r"(\d+)"))  # re.Pattern will convert to RegexPattern
    assert pat18_3.validate("1234").value().groups() == ("1234",)


def test_switch_pattern():
    pat19 = SwitchPattern({"foo": 1, "bar": 2})
    assert pat19.validate("foo").value() == 1
    assert pat19.validate("baz").failed
    pat19_1 = SwitchPattern({"foo": 1, "bar": 2, ...: 3})
    assert pat19_1.validate("foo").value() == 1
    assert pat19_1.validate("baz").value() == 3


def test_patterns():
    temp = create_local_patterns("temp", {"a": BasePattern.on("A")})
    assert temp["a"]
    assert local_patterns() == temp
    assert all_patterns()["a"]
    temp1 = create_local_patterns("temp1", {"b": BasePattern.on("B")}, set_current=False)
    assert temp1["b"]
    assert not local_patterns().get("b")
    switch_local_patterns("temp1")
    assert local_patterns()["b"]
    assert not local_patterns().get("a")
    switch_local_patterns("temp")
    assert local_patterns()["a"]
    assert not local_patterns().get("b")
    reset_local_patterns()

    try:
        create_local_patterns("$temp")
    except ValueError as e:
        print(e)

    try:
        switch_local_patterns("$temp")
    except ValueError as e:
        print(e)


def test_rawstr():
    assert parser("url") == URL
    assert parser(RawStr("url")) == DirectPattern("url", "'url'")


def test_direct():
    pat20 = DirectPattern("abc")
    assert pat20.validate("abc").value() == "abc"
    assert pat20.validate("abcd").failed
    assert pat20.validate(123).failed
    assert pat20.validate("123", 123).value() == 123
    pat20_1 = DirectPattern(123)
    assert pat20_1.validate(123).value() == 123
    assert pat20_1.validate("123").failed
    assert pat20_1.validate(123, "123").value() == 123
    assert pat20_1.match(123) == 123
    try:
        pat20_1.match("123")
    except MatchFailed as e:
        print(e)
    pat21 = DirectTypePattern(int)
    assert pat21.validate(123).value() == 123
    assert pat21.validate("123").failed
    assert pat21.validate(123, "123").value() == 123
    assert pat21.match(123) == 123
    assert pat21.match(456) == 456


def test_forward_red():
    from typing import ForwardRef

    pat21 = parser(ForwardRef("int"))
    assert pat21.validate(123).value() == 123
    assert pat21.validate("int").value() == "int"
    assert pat21.validate(134.5).failed


def test_value_operate():
    pat22 = BasePattern(
        mode=MatchMode.VALUE_OPERATE,
        origin=int,
        converter=lambda _, x: x + 1,
    )
    assert pat22.validate(123).value() == 124
    assert pat22.validate("123").failed
    assert pat22.validate(123.0).failed

    pat22_1p = BasePattern(
        mode=MatchMode.TYPE_CONVERT,
        origin=int,
        accepts=Union[str, float],
        converter=lambda _, x: int(x),
    )

    pat22_1 = BasePattern(
        mode=MatchMode.VALUE_OPERATE,
        origin=int,
        converter=lambda _, x: x + 1,
        previous=pat22_1p,
    )
    assert pat22_1.validate(123).value() == 124
    assert pat22_1.validate("123").value() == 124
    assert pat22_1.validate(123.0).value() == 124
    assert pat22_1.validate("123.0").failed
    assert pat22_1.validate([]).failed


def test_eq():
    assert parser(123) == BasePattern.on(123)
    assert BasePattern.to(None) == NONE
    assert parser(BasePattern.of(int)) == BasePattern.of(int)
    assert parser(str) == STRING


def test_combine():
    pre = BasePattern(mode=MatchMode.VALUE_OPERATE, origin=str, converter=lambda _, x: x.replace(",", "_"))
    pat23 = combine(INTEGER, pre)
    assert pat23.validate("123,456").value() == 123456
    assert pat23.validate("1,000,000").value() == 1_000_000

    pat23_1 = combine(INTEGER, alias="0~10", validators=[lambda x: 0 <= x <= 10])
    assert pat23_1.validate(5).value() == 5
    assert pat23_1.validate(11).failed
    assert str(pat23_1) == "0~10"


def test_funcs():
    from dataclasses import dataclass

    pat = BasePattern(
        mode=MatchMode.TYPE_CONVERT,
        accepts=str,
        origin=list[str],
        alias="chars",
        converter=lambda _, x: list(x),
    )
    assert pat.validate("abcde").value() == ["a", "b", "c", "d", "e"]

    pat24 = Index(pat, 2)
    assert pat24.validate("abcde").value() == "c"

    pat24_1 = Slice(pat, 1, 3)
    assert pat24_1.validate("abcde").value() == ["b", "c"]

    pat24_2 = Map(pat, lambda x: x.upper(), "str.upper")
    assert pat24_2.validate("abcde").value() == ["A", "B", "C", "D", "E"]

    pat24_3 = Filter(pat, lambda x: x in "aeiou", "vowels")
    assert pat24_3.validate("abcde").value() == ["a", "e"]

    pat24_4 = Filter(Map(pat, lambda x: x.upper(), "str.upper"), lambda x: x in "AEIOU", "vowels")
    assert pat24_4.validate("abcde").value() == ["A", "E"]

    pat24_5 = Reduce(pat24_2, lambda x, y: x + y, funcname="add")
    assert pat24_5.validate("abcde").value() == "ABCDE"

    pat24_6 = Join(pat, sep="-")
    assert pat24_6.validate("abcde").value() == "a-b-c-d-e"

    pat24_7 = Upper(pat24_6)
    assert pat24_7.validate("abcde").value() == "A-B-C-D-E"

    pat24_8 = Lower(pat24_7)
    assert pat24_8.validate("abcde").value() == "a-b-c-d-e"

    pat24_9 = Sum(Map(pat, ord))
    assert pat24_9.validate("abcde").value() == 495

    pat24_10 = Step(pat, len)
    assert pat24_10.validate("abcde").value() == 5

    pat24_11 = Step(pat, lambda x: x.count("a"), funcname="count_a")
    assert pat24_11.validate("abcde").value() == 1

    @dataclass
    class Test:
        a: int
        b: str

    pat1 = BasePattern.of(Test)
    obj = Test(123, "abc")
    assert pat1.validate(obj).value() == obj

    pat24_12 = Dot(pat1, int, "a")
    assert pat24_12.validate(obj).value() == 123

    pat2 = BasePattern.on({"a": 123, "b": "abc"})
    pat24_13 = GetItem(pat2, int, "a")
    assert pat24_13.validate({"a": 123, "b": "abc"}).value() == 123


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vs"])
