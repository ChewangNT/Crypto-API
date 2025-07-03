#!usr/bin/env python3
# -*- encoding: utf-8 -*-

from __future__ import annotations

from typing import Union


class BaseError(Exception):
    """ 所有错误类继承自该类 """
    def __init__(self, msg: Union[str, bytes], code: int) -> None:
        super().__init__('错误代码: %d\n%s' % (code, msg))


class EmptyContentError(BaseError):
    """ 当消息 (content) 为空时，抛出该异常 """
    def __init__(self, msg: str, code: int):
        super().__init__(msg, code)


class ContentTypeError(BaseError):
    """ 当消息 (content) 类型有误时，抛出该异常 """
    def __init__(self, msg: str, code: int):
        super().__init__(msg, code)


class UrlError(BaseError):
    """ 当文件链接格式有误时，抛出该异常 """
    def __init__(self, msg: str, code: int):
        super().__init__(msg, code)


class IncompatibilityError(BaseError):
    """ 当消息对象不支持某一方法时，抛出该异常 """
    def __init__(self, msg: str, code: int):
        super().__init__(msg, code)


class BindCommandError(BaseError):
    """ 当绑定指令参数获取失败时，抛出该异常 """
    def __init__(self, msg: str, code: int):
        super().__init__(msg, code)
