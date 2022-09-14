# NEPattern

[![Licence](https://img.shields.io/github/license/ArcletProject/NEPattern)](https://github.com/ArcletProject/NEPattern/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/nepattern)](https://pypi.org/project/nepattern)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nepattern)](https://www.python.org/)

`NEPattern` (`Not-Enough-Pattern`) 是一个高效的负责类型验证与类型转换的库，独立自 [Alconna](https://github.com/ArcletProject/Alconna)

## 简单实例

```python
from nepattern import BasePattern


pat = BasePattern.of(int)
assert pat.validate(13).success
assert not pat(13.0) | bool
```

## 特点

- 高效的类型转化功能
- 多种预置的实例
- 良好的 typing 支持