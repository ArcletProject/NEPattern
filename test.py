from nepattern import (
    BasePattern,
    PatternModel,
    type_parser,
    UnionArg,
    SequenceArg,
    generic_isinstance,
    set_unit,
    pattern_map,
    set_converter,
    set_converters,
    remove_converter,
    AllParam,
    AnyOne,
    Bind
)


def test_pattern_of():
    """测试 BasePattern 的快速创建方法之一, 对类有效"""
    pat = BasePattern.of(int)
    assert pat.origin == int
    assert pat.validate(123)[0] == 123
    assert pat.validate("abc")[1] == "E"
    print(pat)


def test_pattern_on():
    """测试 BasePattern 的快速创建方法之一, 对对象有效"""
    pat1 = BasePattern.on(123)
    assert pat1.origin == int
    assert pat1.validate(123)[0] == 123
    assert pat1.validate(124)[1] == "E"
    print(pat1)


def test_pattern_keep():
    """测试 BasePattern 的保持模式, 不会进行匹配或者类型转换"""
    pat2 = BasePattern(model=PatternModel.KEEP)
    assert pat2.validate(123)[0] == 123
    assert pat2.validate("abc")[0] == "abc"
    print(pat2)


def test_pattern_regex():
    """测试 BasePattern 的正则匹配模式, 仅正则匹配"""
    pat3 = BasePattern("abc[A-Z]+123", PatternModel.REGEX_MATCH)
    assert pat3.validate("abcABC123")[0] == "abcABC123"
    assert pat3.validate("abcAbc123")[1] == "E"
    print(pat3)


def test_pattern_regex_convert():
    """测试 BasePattern 的正则转换模式, 正则匹配成功后再进行类型转换"""
    pat4 = BasePattern(r"\[at:(\d+)\]", PatternModel.REGEX_CONVERT, int)
    assert pat4.validate("[at:123456]")[0] == 123456
    assert pat4.validate("[at:abcdef]")[1] == "E"
    assert pat4.validate(123456)[0] == 123456
    print(pat4)


def test_pattern_type_convert():
    """测试 BasePattern 的类型转换模式, 仅将传入对象变为另一类型的新对象"""
    pat5 = BasePattern(model=PatternModel.TYPE_CONVERT, origin=str)
    assert pat5.validate(123)[0] == "123"
    assert pat5.validate([4, 5, 6])[0] == "[4, 5, 6]"
    pat5_1 = BasePattern(
        model=PatternModel.TYPE_CONVERT, origin=int, converter=lambda x: eval(x)
    )
    assert pat5_1.validate("123")[0] == 123
    assert pat5_1.validate("123.0")[1] == "E"
    print(pat5)


def test_pattern_accepts():
    """测试 BasePattern 的输入类型筛选, 不在范围内的类型视为非法"""
    pat6 = BasePattern(
        model=PatternModel.TYPE_CONVERT,
        origin=str,
        converter=lambda x: x.decode(),
        accepts=[bytes],
    )
    assert pat6.validate(b"123")[0] == "123"
    assert pat6.validate(123)[1] == "E"
    pat6_1 = BasePattern(model=PatternModel.KEEP, accepts=[int, float])
    assert pat6_1.validate(123)[0] == 123
    assert pat6_1.validate("123")[1] == "E"
    print(pat6, pat6_1)


def test_pattern_previous():
    """测试 BasePattern 的前置表达式, 在传入的对象类型不正确时会尝试用前置表达式进行预处理"""

    class A:
        def __repr__(self):
            return "123"

    pat7 = BasePattern(
        model=PatternModel.TYPE_CONVERT, origin=str, converter=lambda x: f"abc[{x}]"
    )
    pat7_1 = BasePattern(
        r"abc\[(\d+)\]",
        model=PatternModel.REGEX_CONVERT,
        origin=int,
        converter=lambda x: int(x),
        previous=pat7,
    )
    assert pat7_1.validate("abc[123]")[0] == 123
    assert pat7_1.validate(A())[0] == 123
    pat7_2 = BasePattern(model=PatternModel.TYPE_CONVERT, origin=str)
    pat7_3 = BasePattern(
        model=PatternModel.TYPE_CONVERT,
        origin=int,
        accepts=[int, float],
        previous=pat7_2,
    )
    assert pat7_3.validate("123")[1] == "E"
    print(pat7, pat7_1)


def test_pattern_anti():
    """测试 BasePattern 的反向验证功能"""
    pat8 = BasePattern.of(int)
    assert pat8.validate(123)[1] == "V"
    assert pat8.invalidate(123)[1] == "E"
    assert pat8.validate("123")[1] == "E"
    assert pat8.invalidate("123")[1] == "V"
    print(pat8)
    print(pat8.reverse())


def test_pattern_validator():
    """测试 BasePattern 的匹配后验证器, 会对匹配结果进行验证"""
    pat9 = BasePattern(
        model=PatternModel.KEEP, origin=int, validators=[lambda x: x > 0]
    )
    assert pat9.validate(23)[0] == 23
    assert pat9.validate(-23)[1] == "E"
    assert pat9.invalidate(-23)[1] == "V"
    pat9_1 = BasePattern.to(set_unit(int, lambda x: x != 0))
    assert pat9_1.invalidate("123")
    print(pat9)


def test_pattern_default():
    pat10 = BasePattern.of(int)
    assert pat10.validate("123", 123)[1] == "D"
    assert pat10.invalidate("123", 123)[1] == "V"
    assert pat10.invalidate(123, "123")[0] == "123"


def test_type_parser():
    from typing import Literal, Type

    pat11 = type_parser(int)
    assert pat11.validate(-321)[1] == "V"
    pat11_1 = type_parser(123)
    assert pat11_1 == BasePattern.on(123)
    print(pat11, pat11_1)
    pat11_2 = BasePattern.to(int)
    assert pat11_2 == pat11
    assert not BasePattern.to(None)
    assert type_parser(BasePattern.of(int)) == BasePattern.of(int)
    assert type_parser(AllParam) == AllParam
    assert isinstance(type_parser(Literal["a", "b"]), UnionArg)
    assert type_parser(Type[int]).origin is type
    assert type_parser(complex) == BasePattern.of(complex)
    assert isinstance(type_parser("a|b|c"), UnionArg)
    assert type_parser([1, 2, 3]).validate(1)[1] == 'V'
    assert type_parser({"a": 1, "b": 2}).validate('a')[0] == 1
    assert type_parser(lambda x: x + 1).validate(1)[0] == 2

    def my_func(x: int) -> str:
        return str(x)

    pat11_3 = type_parser(my_func)
    assert pat11_3.origin == str
    assert pat11_3.accepts == [int]

    assert type_parser(complex, extra='ignore') == AnyOne

    try:
        type_parser(complex, extra='reject')
    except TypeError as e:
        print(e)


def test_union_pattern():
    from typing import Union, Optional

    pat12 = type_parser(Union[int, str])
    assert pat12.validate(123)[1] == "V"
    assert pat12.validate("123")[1] == "V"
    assert pat12.validate(123.0)[1] == "E"
    pat12_1 = type_parser(Optional[str])
    assert pat12_1.validate("123")[1] == "V"
    assert pat12_1.validate(None)[1] == "V"
    pat12_2 = UnionArg(["abc", "efg"])
    assert pat12_2.validate("abc")[1] == "V"
    assert pat12_2.validate("bca")[1] == "E"
    print(pat12, pat12_1, pat12_2)


def test_seq_pattern():
    from typing import List, Tuple, Set

    pat13 = type_parser(List[int])
    pat13_1 = type_parser(Tuple[int, int])
    pat13_2 = type_parser(Set[int])
    assert pat13.validate("[1,2,3]")[0] == [1, 2, 3]
    assert pat13.validate([1, 2, 3])[1] == "V"
    assert pat13_1.validate("(1,2,3)")[0] == (1, 2, 3)
    assert pat13_2.validate("{1,2,3.0}")[1] == "E"
    print(pat13, pat13_1, pat13_2)
    try:
        SequenceArg(BasePattern.of(int), "orderlist")
    except ValueError as e:
        print(e)


def test_map_pattern():
    from typing import Dict

    pat14 = type_parser(Dict[str, int])
    assert pat14.validate("{a:1,b:2}")[0] == {"a": 1, "b": 2}
    assert pat14.validate("{a:1.0, b:2}")[1] == "E"
    assert pat14.validate({"a": 1, "b": 2})[1] == "V"
    pat14_1 = type_parser(Dict[int, int])
    assert pat14_1.validate({"a": 1, "b": 2})[1] == "E"
    print(pat14)


def test_generic_isinstance():
    from typing import Union, List

    assert generic_isinstance(1, int)
    assert generic_isinstance(1, Union[str, int])
    assert generic_isinstance([1], List[int])


def test_converters():
    print(pattern_map)
    assert pattern_map["email"].validate("example@outlook.com")[1] == "V"
    assert pattern_map["ip"].validate("192.168.0.1")[1] == "V"
    assert pattern_map["url"].validate("https://www.example.com")[1] == "V"
    assert pattern_map["hex"].validate("0xff")[0] == 255
    assert pattern_map["color"].validate("#ffffff")[0] == "ffffff"
    assert pattern_map["datetime"].validate("2011-11-04")[0].day == 4
    assert pattern_map["file"].validate("test.py")[0][:4] == b"from"
    assert pattern_map["int"].validate("123")[0] == 123
    assert pattern_map["float"].validate("12.34")[0] == 12.34
    assert pattern_map["bool"].validate("false")[0] is False
    assert pattern_map["list"].validate("[1,2,3]")[0] == [1, 2, 3]
    assert pattern_map["tuple"].validate("(1,2,3)")[0] == (1, 2, 3)
    assert pattern_map["set"].validate("{1,2,3}")[0] == {1, 2, 3}
    assert pattern_map["dict"].validate('{"a":1,"b":2,"c":3}')[0] == {
        "a": 1,
        "b": 2,
        "c": 3,
    }


def test_converter_method():
    temp = {}
    set_converter(BasePattern.of(complex), data=temp)
    assert temp['complex']
    set_converter(BasePattern.of(complex), alias='abc', data=temp)
    assert temp['abc']
    set_converter(BasePattern.of(int), alias='abc', cover=False, data=temp)
    assert isinstance(temp['abc'], UnionArg)
    set_converters({'b': BasePattern.of(bool), 'c': BasePattern.of(str)}, data=temp)
    assert temp['b']
    assert temp['c']
    remove_converter(complex, alias='complex', data=temp)
    assert not temp.get('complex')
    set_converter(BasePattern(alias='a'), data=temp)
    set_converter(BasePattern(origin=int, alias='b'), alias='a', cover=False, data=temp)
    remove_converter(int, alias='a', data=temp)
    assert temp['a']
    remove_converter(int, data=temp)
    remove_converter(bool, data=temp)
    remove_converter(type(None), data=temp)
    assert not temp.get(int)


def test_bind():
    try:
        Bind[int]
    except TypeError as e:
        print(e)

    try:
        Bind[None, lambda x: x]
    except ValueError as e:
        print(e)

    try:
        Bind[int, int]
    except TypeError as e:
        print(e)

    assert isinstance(Bind[int, lambda x: x < 10], BasePattern)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-vs"])
