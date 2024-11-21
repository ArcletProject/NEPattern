from typing import Union

import pytest

from nepattern import *


def test_type():
    import re

    assert isinstance(re.compile(""), TPattern)  # type: ignore


def test_basic():
    from datetime import datetime

    res = STRING.execute("123")
    assert res.success
    assert res.value() == "123"
    assert STRING.execute(b"123").value() == "123"
    assert STRING.execute(123).failed

    assert BYTES.execute(b"123").success
    assert BYTES.execute("123").value() == b"123"
    assert BYTES.execute(123).failed

    assert INTEGER.execute(123).success
    assert INTEGER.execute("123").value() == 123
    assert INTEGER.execute(123.456).value() == 123
    assert INTEGER.execute("123.456").failed
    assert INTEGER.execute("-123").success

    assert FLOAT.execute(123).value() == 123.0
    assert FLOAT.execute("123").value() == 123.0
    assert FLOAT.execute(123.456).value() == 123.456
    assert FLOAT.execute("123.456").value() == 123.456
    assert FLOAT.execute("1e10").value() == 1e10
    assert FLOAT.execute("-123").value() == -123.0
    assert FLOAT.execute("-123.456").value() == -123.456
    assert FLOAT.execute("-123.456e-2").value() == -1.23456
    assert FLOAT.execute("aaa").failed
    assert FLOAT.execute([]).failed

    assert BOOLEAN.execute(True).value() is True
    assert BOOLEAN.execute(False).value() is False
    assert BOOLEAN.execute("True").value() is True
    assert BOOLEAN.execute("False").value() is False
    assert BOOLEAN.execute("true").value() is True
    assert BOOLEAN.execute("false").value() is False
    assert BOOLEAN.execute("1").failed

    assert WIDE_BOOLEAN.execute(True).value() is True
    assert WIDE_BOOLEAN.execute(False).value() is False
    assert WIDE_BOOLEAN.execute("True").value() is True
    assert WIDE_BOOLEAN.execute("False").value() is False
    assert WIDE_BOOLEAN.execute("true").value() is True
    assert WIDE_BOOLEAN.execute("false").value() is False
    assert WIDE_BOOLEAN.execute(1).value() is True
    assert WIDE_BOOLEAN.execute(0).value() is False
    assert WIDE_BOOLEAN.execute("yes").value() is True
    assert WIDE_BOOLEAN.execute("no").value() is False
    assert WIDE_BOOLEAN.execute("2").failed
    assert WIDE_BOOLEAN.execute([]).failed

    assert HEX.execute(123).failed
    assert HEX.execute("0x123").value() == 0x123
    assert HEX.execute("0o123").failed

    assert DATETIME.execute("2020-01-01").value() == datetime(2020, 1, 1)
    assert DATETIME.execute("2020-01-01-12:00:00").value() == datetime(2020, 1, 1, 12, 0, 0)
    assert DATETIME.execute("2020-01-01-12:00:00.123").value() == datetime(2020, 1, 1, 12, 0, 0, 123000)
    assert DATETIME.execute(datetime(2021, 12, 14).timestamp()).value() == datetime(2021, 12, 14, 0, 0, 0)
    assert DATETIME.execute([]).failed

    assert PATH.execute("a/b/c").value().parts == ("a", "b", "c")
    assert PATH.execute(Path("a/b/c")).value() == Path("a/b/c")
    assert PATH.execute([]).failed

    assert DelimiterInt.execute("1,000").value() == 1000
    assert DelimiterInt.execute("1,000,000").value() == 1000000
    assert DelimiterInt.execute("1,000,000.0").failed


def test_result():
    res = NUMBER.execute(123)
    assert res.success
    assert not res.failed
    assert not res.error()
    assert NUMBER.execute(123).value() == 123
    assert NUMBER.execute("123").value() == 123
    assert NUMBER.execute(123.456).value() == 123.456
    assert NUMBER.execute("123.456").value() == 123.456
    assert NUMBER.execute("aaa").failed
    res2 = NUMBER.execute([])
    assert res2.error()
    assert not res2.success
    with pytest.raises(RuntimeError):
        res2.value()


def test_pattern_of():
    """测试 Pattern 的快速创建方法之一, 对类有效"""
    pat = Pattern(int)
    assert pat.origin == int
    assert pat.execute(123).value() == 123
    assert pat.execute("abc").failed
    print(pat)
    print(pat.execute(123).error())
    print(pat.execute("abc").error())


def test_pattern_on():
    """测试 Pattern 的快速创建方法之一, 对对象有效"""
    pat1 = Pattern.on(123)
    assert pat1.origin == int
    assert pat1.execute(123).value() == 123
    assert pat1.execute(124).failed
    print(pat1)


def test_pattern_keep():
    """测试 Pattern 的保持模式, 不会进行匹配或者类型转换"""
    pat2 = Pattern()
    assert pat2.execute(123).value() == 123
    assert pat2.execute("abc").value() == "abc"
    print(pat2)


def test_pattern_regex():
    """测试 Pattern 的正则匹配模式, 仅正则匹配"""
    import re

    pat3 = Pattern.regex_match("abc[A-Z]+123")
    assert pat3.execute("abcABC123").value() == "abcABC123"
    assert pat3.execute("abcAbc123").failed
    print(pat3)

    with pytest.raises(ValueError):
        Pattern.regex_match("^abc[A-Z]+123")

    pat3_1 = Pattern.regex_match(re.compile(r"abc[A-Z]+123"))
    assert pat3_1.execute("abcABC123").value() == "abcABC123"

    pat3_2 = Pattern.regex_match("abc").prefixed()
    assert pat3_2.execute("abc123").value() == "abc"
    assert pat3_2.execute("123abc").failed

    pat3_3 = Pattern.regex_match("abc").suffixed()
    assert pat3_3.execute("123abc").value() == "abc"
    assert pat3_3.execute("abc123").failed


def test_pattern_regex_convert():
    """测试 Pattern 的正则转换模式, 正则匹配成功后再进行类型转换"""
    pat4 = Pattern.regex_convert(
        r"\[at:(\d+)\]", int, lambda m: res if (res := int(m[1])) < 1000000 else None, allow_origin=True
    )
    assert pat4.execute("[at:123456]").value() == 123456
    assert pat4.execute("[at:abcdef]").failed
    assert pat4.execute(123456).value() == 123456
    assert pat4.execute("[at:1234567]").failed
    print(pat4)

    pat4_1 = Pattern.regex_convert(r"\[at:(\d+)\]", int, lambda m: int(m[1]), allow_origin=False)
    assert pat4_1.execute("[at:123456]").value() == 123456
    assert pat4_1.execute("[at:abcdef]").failed
    assert pat4_1.execute(123456).failed
    print(pat4_1)


def test_pattern_type_convert():
    """测试 Pattern 的类型转换模式, 仅将传入对象变为另一类型的新对象"""
    pat5 = Pattern(origin=str).accept(...).convert(lambda _, x: str(x))
    assert pat5.execute(123).value() == "123"
    assert pat5.execute([4, 5, 6]).value() == "[4, 5, 6]"
    pat5_1 = Pattern(origin=int).accept(...).convert(lambda _, x: int(x))
    assert pat5_1.execute("123").value() == 123
    assert pat5_1.execute("123.0").failed
    print(pat5)

    def convert(_, content):
        if isinstance(content, str) and content.startswith("123"):
            return 123

    pat5_3 = Pattern(origin=int).accept(str).convert(convert)
    assert pat5_3.execute("1234abcd").value() == 123
    assert pat5_3.execute("abc").failed
    prev = Pattern(origin=str).convert(lambda _, x: f"123{x}")
    pat5_4 = Pattern(int).accept(str).convert(lambda _, x: convert(_, prev.match(x)))
    assert pat5_4.execute("abc").value() == 123


def test_pattern_accepts():
    """测试 Pattern 的输入类型筛选, 不在范围内的类型视为非法"""

    pat6 = Pattern(str).accept(bytes).convert(lambda _, x: x.decode())
    assert pat6.execute(b"123").value() == "123"
    assert pat6.execute(123).failed
    pat6_1 = Pattern().accept(Union[int, float])
    assert pat6_1.execute(123).value() == 123
    assert pat6_1.execute("123").failed
    print(pat6, pat6_1)


def test_pattern_pre_validator():
    """测试 Pattern 的匹配前验证器, 会在匹配前对输入进行验证"""
    pat7 = Pattern(float).pre_validate(lambda x: x != 0).convert(lambda _, x: 1 / x)
    assert pat7.execute(123).value() == 1 / 123
    assert pat7.execute(0).failed
    print(pat7)


def test_pattern_anti():
    """测试 Pattern 的反向验证功能"""
    pat8 = Pattern(int)
    pat8_1 = AntiPattern(pat8)
    assert pat8.execute(123).value() == 123
    assert pat8.execute("123").failed
    assert pat8_1.execute(123).failed
    assert pat8_1.execute("123").value() == "123"


def test_pattern_validator():
    """测试 Pattern 的匹配后验证器, 会对匹配结果进行验证"""
    pat9 = Pattern(int).pre_validate(lambda x: x > 0).accept(int)
    assert pat9.execute(23).value() == 23
    assert pat9.execute(-23).failed
    print(pat9)


def test_pattern_post_validator():
    """测试 Pattern 的匹配后验证器, 会对转换后的结果进行验证"""
    pat10 = Pattern(int).convert(lambda _, x: x + 1).post_validate(lambda x: x % 2 == 0)
    assert pat10.execute(123).value() == 124
    assert pat10.execute(122).failed
    print(pat10)


def test_parser():
    from typing import Literal, Protocol, Type, TypeVar, Sequence
    from typing_extensions import Annotated

    pat11 = parser(int)
    assert pat11.execute(-321).success
    pat11_1 = parser(123)
    print(pat11, pat11_1)
    pat11_2 = parser(int)
    assert pat11_2 == pat11
    assert isinstance(parser(Literal["a", "b"]), UnionPattern)
    assert parser(Type[int]).origin == type[int]
    assert parser(complex) != Pattern(complex)
    assert isinstance(parser("a|b|c"), UnionPattern)
    assert isinstance(parser("re:a|b|c"), Pattern)
    assert parser([1, 2, 3]).execute(1).success
    assert parser({"a": 1, "b": 2}).execute("a").value() == 1

    def _func(x: int):
        return x + 1

    assert parser(_func).execute(1).value() == 2

    def my_func(x: int) -> str:
        return str(x)

    pat11_3 = parser(my_func)
    assert pat11_3.origin == str
    assert pat11_3._accepts == int

    assert parser(complex, extra="ignore") == ANY

    with pytest.raises(TypeError):
        parser(complex, extra="reject")

    pat11_4 = parser(Annotated[int, lambda x: x < 10])
    assert pat11_4.execute(11).failed
    pat11_5 = parser(Annotated[int, lambda x: x >= 0, "normal number"])
    assert pat11_5.alias == "normal number"

    class TestP(Protocol):
        def __setitem__(self): ...

    pat11_6 = parser(TestP)
    assert pat11_6.execute([1, 2, 3]).success
    assert pat11_6.execute((1, 2, 3)).failed

    TestT = TypeVar("TestT", str, int)
    pat11_7 = parser(TestT)
    assert pat11_7.execute("abc").success
    assert pat11_7.execute([]).failed

    pat11_8 = parser(Sequence[int])
    assert pat11_8.execute([1, 2, 3]).success
    assert pat11_8.execute((1, 2, 3)).success


def test_union_pattern():
    from typing import List, Optional, Union, Annotated

    pat12 = parser(Union[int, bool])
    assert pat12.execute(123).success
    assert pat12.execute("123").success
    assert pat12.execute("123").value() == 123
    assert pat12.execute(123.0).value() == 123
    pat12_1 = parser(Optional[str])
    assert pat12_1.execute("123").success
    assert pat12_1.execute(None).success
    pat12_2 = UnionPattern("abc", "efg")
    assert pat12_2.execute("abc").success
    assert pat12_2.execute("bca").failed
    print(pat12, pat12_1, pat12_2)
    pat12_3 = UnionPattern.of(List[bool], int)
    print(pat12_3)
    pat12_4 = UnionPattern.with_(INTEGER, WIDE_BOOLEAN)
    assert pat12_4.execute(123).success
    assert pat12_4.execute("123").success
    assert pat12_4.execute("123").value() == 123
    assert pat12_4.execute("true").success
    assert pat12_4.execute("true").value() is True
    assert pat12_4.execute("false").success
    assert pat12_4.execute("false").value() is False
    assert pat12_4.execute("yes").success
    assert pat12_4.execute("yes").value() is True


def test_converters():
    pattern_map = all_patterns()
    print(pattern_map)
    assert pattern_map["any_str"].execute(123456).value() == "123456"
    assert pattern_map["email"].execute("example@outlook.com").success
    assert pattern_map["ip"].execute("192.168.0.1").success
    assert pattern_map["url"].execute("www.example.com").success
    assert pattern_map["url"].execute("https://www.example.com").value() == "https://www.example.com"
    assert pattern_map["url"].execute("wwwexamplecom").failed
    assert pattern_map["hex"].execute("0xff").value() == 255
    assert pattern_map["color"].execute("#ffffff").value() == "ffffff"
    assert pattern_map["datetime"].execute("2011-11-04").value().day == 4
    assert pattern_map["file"].execute("test.py").value()[:4] == b"from"
    assert pattern_map["number"].execute("123").value() == 123
    assert pattern_map["int"].execute("123").value() == 123
    assert pattern_map["float"].execute("12.34").value() == 12.34
    assert pattern_map["bool"].execute("false").value() is False
    assert pattern_map[list].execute("[1,2,3]").value() == [1, 2, 3]
    assert pattern_map[tuple].execute("(1,2,3)").value() == (1, 2, 3)
    assert pattern_map[set].execute("{1,2,3}").value() == {1, 2, 3}
    assert pattern_map[dict].execute('{"a":1,"b":2,"c":3}').value() == {
        "a": 1,
        "b": 2,
        "c": 3,
    }


def test_converter_method():
    temp = create_local_patterns("test", set_current=False)
    temp.set(Pattern(complex, "complex"))
    assert temp["complex"]
    temp.set(Pattern(complex), alias="abc")
    assert temp["abc"]
    temp.set(Pattern(int), alias="abc", cover=False)
    assert isinstance(temp["abc"], UnionPattern)
    temp.merge({"b": Pattern(bool), "c": Pattern(str)})
    assert temp["b"]
    assert temp["c"]
    temp.remove(complex, alias="complex")
    assert not temp.get("complex")
    temp.set(Pattern(alias="a"))
    temp.set(Pattern(alias="b").accept(int), alias="a", cover=False)
    temp.remove(int, alias="a")
    assert temp["a"]
    temp.remove(int)
    temp.remove(bool)
    temp.remove(type(None))
    assert not temp.get(int)


def test_regex_pattern():
    from re import Match, compile

    pat18 = RegexPattern(r"((https?://)?github\.com/)?(?P<owner>[^/]+)/(?P<repo>[^/]+)", "ghrepo")
    res = pat18.execute("https://github.com/ArcletProject/NEPattern").value()
    assert isinstance(res, Match)
    assert res.groupdict() == {"owner": "ArcletProject", "repo": "NEPattern"}
    assert pat18.execute(123).failed
    assert pat18.execute("www.bilibili.com").failed
    pat18_1 = parser(r"re:(\d+)")  # str starts with "re:" will convert to Pattern instead of RegexPattern
    assert pat18_1.execute("1234").value() == "1234"
    pat18_2 = parser(r"rep:(\d+)")  # str starts with "rep:" will convert to RegexPattern
    assert pat18_2.execute("1234").value().groups() == ("1234",)  # type: ignore
    pat18_3 = parser(compile(r"(\d+)"))  # re.Pattern will convert to RegexPattern
    assert pat18_3.execute("1234").value().groups() == ("1234",)


def test_switch_pattern():
    from typing import Annotated

    pat19 = SwitchPattern({"foo": 1, "bar": 2})
    assert pat19.execute("foo").value() == 1
    assert pat19.execute("baz").failed
    pat19_1 = SwitchPattern({"foo": 1, "bar": 2, ...: 3})
    assert pat19_1.execute("foo").value() == 1
    assert pat19_1.execute("baz").value() == 3
    pat19_2 = parser(Annotated[int, {"foo": 1, "bar": 2}])
    assert pat19_2.execute("foo").value() == 1
    assert pat19_2.execute("baz").failed


def test_patterns():
    temp = create_local_patterns("temp", {"a": Pattern.on("A")})
    assert temp["a"]
    assert local_patterns() == temp
    assert all_patterns()["a"]
    temp1 = create_local_patterns("temp1", {"b": Pattern.on("B")}, set_current=False)
    assert temp1["b"]
    assert not local_patterns().get("b")
    switch_local_patterns("temp1")
    assert local_patterns()["b"]
    assert not local_patterns().get("a")
    switch_local_patterns("temp")
    assert local_patterns()["a"]
    assert not local_patterns().get("b")
    reset_local_patterns()

    with pytest.raises(ValueError):
        create_local_patterns("$temp")

    with pytest.raises(ValueError):
        switch_local_patterns("$temp")

    with pytest.raises(KeyError):
        switch_local_patterns("temp2")


def test_rawstr():
    assert parser("url") == URL
    assert parser(RawStr("url")) == DirectPattern("url", "'url'")


def test_direct():
    pat20 = DirectPattern("abc")
    assert pat20.execute("abc").value() == "abc"
    assert pat20.execute("abcd").failed
    assert pat20.execute(123).failed
    pat20_1 = DirectPattern(123)
    assert pat20_1.execute(123).value() == 123
    assert pat20_1.execute("123").failed
    assert pat20_1.match(123) == 123
    with pytest.raises(MatchFailed):
        pat20_1.match("123")
    pat21 = DirectTypePattern(int)
    assert pat21.execute(123).value() == 123
    assert pat21.execute("123").failed
    assert pat21.match(123) == 123
    assert pat21.match(456) == 456


def test_forward_ref():
    from typing import ForwardRef

    pat21 = parser(ForwardRef("int"))
    assert pat21.execute(123).value() == 123
    assert pat21.execute("int").value() == "int"
    assert pat21.execute(134.5).failed


def test_value_operate():
    pat22 = Pattern(origin=int).convert(
        lambda _, x: x + 1,
    )
    assert pat22.execute(123).value() == 124
    assert pat22.execute("123").failed
    assert pat22.execute(123.0).failed


def test_eq():
    assert parser(123) == Pattern.on(123)
    assert parser(None) == NONE
    assert parser(Pattern(int)) == Pattern(int)
    assert parser(str) == STRING


def test_combine():
    pre = Pattern(origin=str).convert(lambda _, x: x.replace(",", "_"))
    pat23 = combine(INTEGER, pre)
    assert pat23.execute("123,456").value() == 123456
    assert pat23.execute("1,000,000").value() == 1_000_000

    pat23_1 = combine(INTEGER, alias="0~10", validator=lambda x: 0 <= x <= 10)
    assert pat23_1.execute(5).value() == 5
    assert pat23_1.execute(11).failed
    assert str(pat23_1) == "0~10"


def test_funcs():
    from dataclasses import dataclass
    from nepattern.func import Index, Slice, Map, Filter, Reduce, Join, Upper, Lower, Sum, Step, Dot, GetItem

    pat = Pattern(list[str], "chars").accept(str).convert(lambda _, x: list(x))
    assert pat.execute("abcde").value() == ["a", "b", "c", "d", "e"]

    pat24 = Index(pat, 2)
    assert pat24.execute("abcde").value() == "c"

    pat24_1 = Slice(pat, 1, 3)
    assert pat24_1.execute("abcde").value() == ["b", "c"]

    pat24_2 = Map(pat, lambda x: x.upper(), "str.upper")
    assert pat24_2.execute("abcde").value() == ["A", "B", "C", "D", "E"]

    pat24_3 = Filter(pat, lambda x: x in "aeiou", "vowels")
    assert pat24_3.execute("abcde").value() == ["a", "e"]

    pat24_4 = Filter(Map(pat, lambda x: x.upper(), "str.upper"), lambda x: x in "AEIOU", "vowels")
    assert pat24_4.execute("abcde").value() == ["A", "E"]

    pat24_5 = Reduce(pat24_2, lambda x, y: x + y, funcname="add")
    assert pat24_5.execute("abcde").value() == "ABCDE"

    pat24_6 = Join(pat, sep="-")
    assert pat24_6.execute("abcde").value() == "a-b-c-d-e"

    pat24_7 = Upper(pat24_6)
    assert pat24_7.execute("abcde").value() == "A-B-C-D-E"

    pat24_8 = Lower(pat24_7)
    assert pat24_8.execute("abcde").value() == "a-b-c-d-e"

    pat24_9 = Sum(Map(pat, ord))
    assert pat24_9.execute("abcde").value() == 495

    pat24_10 = Step(pat, len)
    assert pat24_10.execute("abcde").value() == 5

    pat24_11 = Step(pat, lambda x: x.count("a"), funcname="count_a")
    assert pat24_11.execute("abcde").value() == 1

    @dataclass
    class Test:
        a: int
        b: str

    pat1 = Pattern(Test)
    obj = Test(123, "abc")
    assert pat1.execute(obj).value() == obj

    pat24_12 = Dot(pat1, int, "a")
    assert pat24_12.execute(obj).value() == 123

    pat2 = Pattern.on({"a": 123, "b": "abc"})
    pat24_13 = GetItem(pat2, int, "a")
    assert pat24_13.execute({"a": 123, "b": "abc"}).value() == 123


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vs"])
