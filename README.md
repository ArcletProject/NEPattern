# NEPattern

[![Licence](https://img.shields.io/github/license/ArcletProject/NEPattern)](https://github.com/ArcletProject/NEPattern/blob/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/nepattern)](https://pypi.org/project/nepattern)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/nepattern)](https://www.python.org/)

`NEPattern` 是一个高效的负责类型验证与类型转换的库，独立自[Alconna](https://github.com/ArcletProject/Alconna)

## 实例

```python
from nepattern import BasePattern


pat = BasePattern.of(int)
assert pat.validate(123)[1] == 'V'
assert pat.validate(12.23)[1] == 'E'
```