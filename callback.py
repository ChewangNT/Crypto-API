#!usr/bin/env python3
# -*- encoding: utf-8 -*-

"""
这是一个回调消息包，里面仅包含一个类 Callback
回调消息包封装了各种消息发送包，开箱即用
在使用 Callback 类前，请先继承 Botpy 的监听器，获取消息对象

- 可以参考 Botpy 官方文档，以了解如何继承监听器：
Github: https://github.com/tencent-connect/botpy/
"""

from __future__ import annotations

import re
import asyncio
from random import randint
from typing import Union, List, Optional, Tuple, Dict, TypedDict, Any, Callable
from functools import wraps
from botpy.api import BotAPI
from botpy.message import C2CMessage, Message, GroupMessage
from .error import *


class Session(object):
    def __init__(self) -> None:
        """
        创建一个功能上下文对象

        Args:
            bot_appid (Union[str, int]) 可选参数，绑定的机器人appid
        """
        self._bind_function = []

    @property
    def get_bind(self) -> List[Callable]:
        """
        获取所有当前 Session 对象绑定的函数

        Return:
            一个函数列表，为当前 Session 绑定的所有绑定函数
        """
        return self._bind_function

    def fusion(
        self,
        *sessions: 'Session',
    ) -> List[Callable]:
        """
        将多个 Session 实例的绑定函数拼接成一个列表

        Args:
            *sessions (Session) 传入的所有 Session 实例

        Return:
            所有 Session 实例绑定的函数
        """
        return self.get_bind + [
            func
            for s in sessions
            if isinstance(s, Session)
            for func in s.get_bind
        ]

    def bind(
        self,
        *commands: Tuple[str],
        prefixes: Union[List[str], Tuple[str]] = ['/', ''],
        limitation: Union[List[str], Tuple[str]] = []
    ) -> Any:
        """
        绑定一个指令到异步函数上

        - 借鉴了隔壁的 Commands 装饰器，只不过接收的是一个 Callback 回调消息对象
        - 注意，绑定的异步函数中必须有一个参数 msg_obj 为回调消息对象
        - 如果不使用 msg_obj 参数，也可以将回调消息对象赋值给 callback 参数
        - 在绑定的函数内，必须使用 params 参数接收分割的参数，否则将会报错

        示例：

        session = Session()

        @session.bind("echo", prefixes=['/'])
        async def echo(msg_obj: Callback, params=None)

        限制消息对象可以让你在使用指令遍历时更轻松

        - 指定 limitation 参数，可以限制无法使用该指令的回调消息类型
        - 可传入的参数 (字符串，需使用元组或列表包围)：

        - 'channel'     限制频道
        - 'group'       限制群聊
        - 'c2c'         限制私聊

        Args:
            *commands (tuple) 绑定的指令，可以是多个
            prefixes (Union[List[str], Tuple[str]]) 可选的指令前缀列表，默认为 / 和无前缀
            limitation (Union[List[str], Tuple[str]]) 限制的消息对象类型，默认为无限制
        """
        def decoration(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                callback: Optional['Callback'] = (
                    kwargs.get('msg_obj') or
                    kwargs.get('callback')
                )
                if callback is None:
                    raise BindCommandError(
                        '未找到msg_obj参数',
                        100
                    ) from None
                if not isinstance(callback, Callback):
                    raise BindCommandError(
                        'msg_obj参数类型错误',
                        100
                    ) from None

                for limit in limitation:
                    if limit == callback.msg_type:
                        return False

                for prefix in prefixes:
                    for command in commands:
                        cmd = callback.command(prefix + command)
                        if isinstance(cmd, list):
                            kwargs['params'] = cmd or ''
                            return await func(*args, **kwargs)
                return False

            self._bind_function.append(wrapper)
            return wrapper
        return decoration


class Callback(object):
    def __init__(
        self,
        msg_obj: Union[GroupMessage, Message, C2CMessage],
        database: Optional[Database] = None,
        *,
        bot_appid: Optional[Union[str, int]] = None
    ) -> None:
        """
        基于 Botpy 的回调消息类，封装了各种功能

        - 在初始化完毕后，请勿擅自修改msg_obj，可能会导致 500 报错

        Args:
            msg_obj (Union[GroupMessage, Message, C2CMessage]) 一个消息对象
            database (Database) 绑定的 Database 数据库，若不绑定默认为 None
            bot_appid (Union[str, int]) 可填参数，绑定的机器人appid，默认为 None

        Return:
            初始化后，可以正常使用回调类
        """
        if not isinstance(msg_obj, (GroupMessage, Message, C2CMessage)):
            raise ContentTypeError('错误的消息类型', 400)
        TYPE = {
            'Message': 'channel',
            'GroupMessage': 'group',
            'C2CMessage': 'c2c'
        }
        self.msg_type = TYPE[type(msg_obj).__name__]
        self.msg_obj = msg_obj
        self.api = msg_obj._api
        self._database = database
        self.bot_appid = bot_appid

    @property
    def database(self) -> Optional[Database]:
        """
        获取绑定的 Database 数据库

        - 若初始化该类时，没有传入 database 参数，则返回 None

        Return:
            绑定的 Database 数据库
        """
        return self._database

    @property
    def timestamp(self) -> Optional[str]:
        """
        获取消息发送具体时间 (字符串)

        - 当 msg_obj 被更改，可能会导致该方法返回None

        Return:
            一个字符串，为消息的具体发送时间
        """
        if hasattr(self.msg_obj, 'timestamp'):
            return self.msg_obj.timestamp
        return None

    @property
    def user_openid(self) -> str:
        """
        获取发送对象成员开放id

        - 注意，频道开放id与群聊、私聊会不相同

        Return:
            一个哈希值字符串，表示用户的的开放id
        """
        if isinstance(self.msg_obj, Message):
            return self.msg_obj.author.id
        elif isinstance(self.msg_obj, GroupMessage):
            return self.msg_obj.author.member_openid
        elif isinstance(self.msg_obj, C2CMessage):
            return self.msg_obj.author.user_openid

    @property
    def usage(self) -> Optional[Usage]:
        """
        一个很奇妙的方法，用于获取cpu使用率与内存占用

        - 该方法基于 psutil 库，若未安装会返回None (一定要记得安装！[大叫])

        Return:
            一个 Usage 对象，属性为cpu使用率与内存占用百分比 (若未安装库则返回空值)
        """
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            return self.Usage(cpu_percent, memory_percent)
        except ImportError:
            return None
        except Exception as e:
            raise RuntimeError(e) from None

    class Usage(object):
        def __init__(
            self,
            cpu: float = 0.0,
            memory: float = 0.0
        ) -> None:
            self.cpu_percent = cpu
            self.memory_percent = memory

    @property
    def date(self) -> str:
        """
        一个便捷方法，获取今天的日期

        Return:
            返回 YYYY-MM-DD 形式的日期
        """
        from datetime import date
        return date.today().strftime('%Y-%m-%d')

    @property
    def content(self) -> str:
        """
        获取消息对象成员发送的消息内容

        - 消息会随时过期，请不要长期引用

        Return:
            一个字符串，为消息内容
        """
        message = self.msg_obj.content.strip()
        return message

    def command(
        self,
        prefix: str = '/',
        sep_params: bool = True
    ) -> Union[str, List[str]]:
        """
        获取消息对象成员发送的指令以及其参数，

        - 当用户消息的开头为prefix，则视为指令，并且分割参数
        - 你也可以选择设置sep_params为False来禁用分割
        - (此方法在旧版本为content，现已分开)

        Args:
            prefix (str) 指令标识符，默认为 /
            sep_params (bool) 是否启用指令分割

        Return:
            一个列表，为群成员的指令与参数
            (当禁用分割或不为指令，返回一个完整的内容字符串)
        """
        try:
            message = self.msg_obj.content.strip()
            if message.startswith(prefix) and sep_params:
                handle_message = message[len(prefix):].strip()
                return handle_message.split()
            return message
        except Exception as e:
            raise RuntimeError(e) from None

    def head_url(
        self,
        bot_appid: Optional[Union[int, str]] = None,
        *,
        user_openid: Optional[None] = None,
        api: str = 'https://thirdqq.qlogo.cn/qqapp/{}/{}/{}',
        size: int = 640
    ) -> str:
        """
        获取发送对象成员头像接口

        Args:
            bot_appid (Union[str, bytes]) 机器人的appid (如果初始化时绑定了可以不传)
            user_openid (str) 指定的成员openid
            api (str) 选填参数，默认为官方接口
            size (int) 头像大小，默认为640 (640 x 640)

        Return:
            一个字符串，为头像url
        """
        openid = user_openid or self.user_openid
        if isinstance(self.msg_obj, Message):
            return self.msg_obj.author.avatar
        return api.format(
            str(self.bot_appid or bot_appid),
            openid,
            size
        )

    async def reduce(
        self,
        session: Union[Session, List[Callable]],
        callback: Optional['Callback'] = None
    ) -> bool:
        """
        遍历上下文对象的可执行函数

        Args:
            session (Union[Session, List[Callable]]) 上下文对象或者函数列表
            callback (Callback) 可选参数，自定义传入的回调消息对象，默认为当前实例

        Return:
            一个布尔值，为是否成功执行函数
        """
        callback = callback or self
        if isinstance(session, Session):
            func_list = session.get_bind
        elif isinstance(session, list):
            func_list = session
        else:
            raise TypeError('错误的 session 类型') from None
        for func in func_list:
            if (
                isinstance(func, Callable)
                and await func(msg_obj=callback)
            ):
                return True
        return False

    async def send(
        self,
        content: Union[str, bytes],
        /,
        seq: int = randint(0, 1000000)
    ) -> Optional[Tuple[int, str]]:
        """
        向指定对象发送消息

        Args:
            content (Union[str, bytes]) 消息内容
            seq (int) 消息序号，默认抽取一个随机值

        Return:
            一个元组，包含返回代码和发送消息
        """
        if len(content) == 0:
            raise EmptyContentError('消息不能为空', 200)
        try:
            if isinstance(self.msg_obj, Message):
                await self.api.post_message(
                    channel_id=self.msg_obj.channel_id,
                    content=str(content),
                    msg_id=self.msg_obj.id
                )
            elif isinstance(self.msg_obj, GroupMessage):
                await self.api.post_group_message(
                    group_openid=self.msg_obj.group_openid,
                    msg_type=0,
                    content=str(content),
                    msg_id=self.msg_obj.id,
                    msg_seq=seq
                )
            elif isinstance(self.msg_obj, C2CMessage):
                await self.api.post_c2c_message(
                    openid=self.msg_obj.author.user_openid,
                    msg_type=0,
                    content=str(content),
                    msg_id=self.msg_obj.id,
                    msg_seq=seq
                )
            else:
                raise ContentTypeError('错误的消息类型', 500)
            return 200, '发送成功'
        except ContentTypeError:
            raise
        except Exception as e:
            raise RuntimeError(e) from None

    async def _send_media(
        self,
        media_url: Union[str, bytes],
        media_type: int,
        content: Union[str, bytes] = '',
        /,
        seq: int = randint(1, 1000000)
    ) -> Optional[Tuple[int, str]]:
        """
        私有方法，上传一个富媒体资源

        - 注意，频道消息对象 (Message) 不可发送视频、语音

        Args:
            media_url (Union[str, bytes]) 资源网络路径
            media_type (int) 资源类型 1为图片 2为视频 3为语音
            content (Union[str, bytes]) 富媒体附属消息
            seq (int) 消息序号，默认抽取一个随机值

        Return:
            一个元组，包含返回代码和发送消息
        """
        try:
            if isinstance(self.msg_obj, Message):
                if media_type in [2, 3]:
                    raise IncompatibilityError(
                        '发送失败，该对象不可发送此类文件',
                        500
                    )
                await self.api.post_message(
                    channel_id=self.msg_obj.channel_id,
                    content=str(content),
                    image=url,
                    msg_id=self.msg_obj.id
                )
            elif isinstance(self.msg_obj, GroupMessage):
                media = await self.api.post_group_file(
                    group_openid=self.msg_obj.group_openid,
                    file_type=media_type,
                    url=media_url
                )
                await self.api.post_group_message(
                    group_openid=self.msg_obj.group_openid,
                    msg_type=7,
                    content=str(content),
                    msg_id=self.msg_obj.id,
                    msg_seq=seq,
                    media=media
                )
            elif isinstance(self.msg_obj, C2CMessage):
                media = await self.api.post_c2c_file(
                    openid=self.msg_obj.author.user_openid,
                    file_type=media_type,
                    url=media_url
                )
                await self.api.post_c2c_message(
                    openid=self.msg_obj.author.user_openid,
                    msg_type=7,
                    content=str(content),
                    msg_id=self.msg_obj.id,
                    msg_seq=seq,
                    media=media
                )
            else:
                raise ContentTypeError('错误的消息类型', 500)
        except (
            ContentTypeError,
            IncompatibilityError
        ):
            raise
        except Exception as e:
            raise RuntimeError(e) from None

    async def send_image(
        self,
        image_url: Union[str, bytes],
        content: Union[str, bytes] = '',
        /,
        seq: int = randint(1, 1000000)
    ) -> Optional[Tuple[int, str]]:
        """
        向指定对象发送图片 / 图文

        - 其中，image_url为网络链接，不是本地链接

        Args:
            image_url (Union[str, bytes]) 图片网络路径
            content (Union[str, bytes]) 图文消息
            seq (int) 消息序号，默认抽取一个随机值

        Return:
            一个元组，包含返回代码和发送消息
        """
        if len(content) == 0:
            raise EmptyContentError('消息不能为空', 500)
        await self._send_media(
            image_url,
            1,
            str(content),
            seq=seq
        )

    async def send_silk(
        self,
        silk_url: Union[str, bytes],
        seq: int = randint(1, 1000000),
        /
    ) -> Optional[Tuple[int, str]]:
        """
        向指定对象发送 silk 语音

        - 其中，silk_url为网络链接，不是本地链接
        - 频道对象无法发送silk语音，Message消息对象将会失效

        Args:
            silk_url (Union[str, bytes]) 语音网络路径
            seq (int) 消息序号，默认抽取一个随机值

        Return:
            一个元组，包含返回代码和发送消息
        """
        await self._send_media(
            silk_url,
            3,
            seq=seq
        )

    async def send_video(
        self,
        video_url: Union[str, bytes],
        seq: int = randint(1, 1000000),
        /
    ) -> Optional[Tuple[int, str]]:
        """
        向指定对象发送 mp4 视频

        - 其中，video_url为网络链接，不是本地链接
        - 频道无法发送mp4视频，Message消息对象将会失效

        Args:
            video_url (Union[str, bytes]) 视频网络路径
            seq (int) 消息序号，默认抽取一个随机值

        Return:
            一个元组，包含返回代码和发送消息
        """
        await self._send_media(
            video_url,
            2,
            seq=seq
        )


__all__ = [
    'Session',
    'Callback'
]