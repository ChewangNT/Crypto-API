#!usr/bin/env python3
# -*- encoding: utf-8 -*-

from __future__ import annotations

import asyncio
import mysql.connector
from time import time
from typing import Union, Optional, List, Tuple
from botpy.message import Message, GroupMessage, C2CMessage
from .callback import Callback
from .error import ContentTypeError


INTERFACE = {
    'channel': ', channel_id VARCHAR(70)',
    'group': ', group_id VARCHAR(70)',
    'c2c': ''
}


def _init_database(db_type: str, **kwargs) -> float:
    """
    数据库初始化方法

    Args:
        db_type (str) 数据库类型
        kwargs (dict) 更多参数

    Return:
        执行时间差，精确至ms
    """
    start = time()
    try:
        # 尝试连接 mysql 数据库
        connection = mysql.connector.connect(**kwargs)
        cursor = connection.cursor(
            dictionary=True,
            prepared=True,
        )
        # 建表，此处使用默认的表
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS {}_table (
                userid INT PRIMARY KEY AUTO_INCREMENT,
                openid VARCHAR(70) UNIQUE,
                message_number INT
                {}
            )
            '''.format(db_type, INTERFACE[db_type])
        )
        connection.commit()
        cursor.close()
        connection.close()
        return time() - start
    except Exception as e:
        raise RuntimeError(e) from None


class BaseUser(object):
    __slots__ = [
        'userid',
        'openid',
        'message_number',
        'channel_id',
        'group_id'
    ]

    def __init__(
        self,
        userid: int = 0,
        openid: str = '',
        message_number: int = 0,
        channel_id: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> None:
        self.userid = userid
        self.openid = openid
        self.message_number = message_number
        self.channel_id = channel_id
        self.group_id = group_id


class Database(object):
    def __init__(
        self,
        user: str,
        password: str,
        *,
        host: str = 'localhost'
    ) -> None:
        """
        一个用于消息对象的数据库服务，用于管理所有用户数据

        - 注意，该服务基于MySQL数据库，在使用前请先安装MySQL (版本 >= 5.0)

        Args:
            user (str) MySQL的登录用户名称
            password (str) MySQL的登录密码
            host (str) MySQL的本地回环

        Return:
            初始化后，可以正常使用该服务
        """
        try:
            self.user = user
            self.password = password
            self.host = host
            self._db()
            self.connection = mysql.connector.connect(
                user=self.user,
                password=self.password,
                host=self.host,
                database='qq_bot_database'
            )
            self.cursor = self.connection.cursor(
                dictionary=True,
                prepared=True,
            )
        except Exception as e:
            raise RuntimeError(e) from None

    def _db(self) -> None:
        with mysql.connector.connect(
            user=self.user,
            password=self.password,
            host=self.host
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    '''
                    CREATE DATABASE 
                    IF NOT EXISTS qq_bot_database
                    '''
                )

    def clear_table(self) -> None:
        """
        清空所有表 (包含频道、群聊、私聊) 的数据

        - 该方法仅限特殊情况下使用，正常情况下请勿使用该方法，后果自负！
        """
        try:
            for coc_type in ['channel', 'group', 'c2c']:
                self.cursor.execute(
                    'TRUNCATE TABLE {}_table'.format(coc_type)
                )
            self.connection.commit()
        except Exception as e:
            raise RuntimeError(e) from None

    def init_channel_database(self) -> float:
        """
        用于初始化频道相关的数据库

        Return:
            执行时间差，精确至ms
        """
        return _init_database(
            'channel',
            user=self.user,
            password=self.password,
            host=self.host,
            database='qq_bot_database'
        )

    def init_group_database(self) -> float:
        """
        用于初始化群聊相关的数据库

        Return:
            执行时间差，精确至ms
        """
        return _init_database(
            'group',
            user=self.user,
            password=self.password,
            host=self.host,
            database='qq_bot_database'
        )

    def init_c2c_database(self) -> float:
        """
        用于初始化私聊相关的数据库

        Return:
            执行时间差，精确至ms
        """
        return _init_database(
            'c2c',
            user=self.user,
            password=self.password,
            host=self.host,
            database='qq_bot_database'
        )

    def insert_userinfo(
        self,
        callback: Callback
    ) -> BaseUser:
        """
        通过回调对象插入用户数据

        - 注意，请先初始化频道、群聊、私聊数据库，否则会报错
        - 当用户数据已经存在时，将直接返回用户对象，不会插入

        Args:
            callback (Callback) 回调消息对象

        Return:
            插入成功后，将返回一个BaseUser对象，为该用户信息
            (注：返回对象没有userid)
        """
        query_user = self.get_userinfo(callback)
        if query_user:
            return query_user
        try:
            DB_TYPE = {
                'Message': ('channel', lambda obj: obj.channel_id),
                'GroupMessage': ('group', lambda obj: obj.group_openid),
                'C2CMessage': ('c2c', 'None')
            }
            msg_type = type(callback.msg_obj).__name__
            coc_type, coc_func = DB_TYPE[msg_type]
            coc_value = coc_func(callback.msg_obj)

            base_column = ['openid', 'message_number']
            base_values = [callback.user_openid, '1']
            if coc_value:
                base_column.append(coc_type + '_id')
                base_values.append(coc_value)
            self.cursor.execute(
                'INSERT INTO {}_table ({}) VALUES ({})'
                .format(
                    coc_type,
                    ', '.join(base_column),
                    ', '.join(['%s'] * len(base_values))
                ),
                base_values
            )
            self.connection.commit()
            return BaseUser(**{
                'openid': callback.user_openid,
                'message_number': 1,
                'channel_id': coc_value if coc_type == 'channel' else None,
                'group_id': coc_value if coc_type == 'group' else None
            })
        except Exception as e:
            raise RuntimeError(e) from None

    def get_userinfo(
        self,
        callback: Callback
    ) -> Optional[BaseUser]:
        """
        通过开放id获取用户的相关信息

        - 注意，请先初始化频道、群聊、私聊数据库，否则会报错

        Args:
            callback (Callback) 回调消息对象

        Return:
            在数据库中获取的用户的群聊信息，若无查询结果则返回None
        """
        try:
            self.cursor.execute(
                'SELECT * from {}_table WHERE openid = %s'
                .format(callback.msg_type),
                (callback.user_openid, )
            )
            query = self.cursor.fetchone()
            if query:
                return BaseUser(**query)
            else:
                return None
        except Exception as e:
            raise RuntimeError(e) from None

    def get_group_use_user(
        self,
        callback: Callback
    ) -> List[BaseUser]:
        """
        获取某群使用过的人员列表

        - 注意，请先初始化群聊数据库，否则会报错

        Args:
            callback (Callback) 回调消息对象

        Return:
            获取回调消息对象群组的使用人员列表，若没有使用人物则返回空列表
        """
        if isinstance(callback.msg_obj, GroupMessage):
            group_id = callback.msg_obj.group_openid
        else:
            return []
        self.cursor.execute(
            'SELECT * FROM group_table WHERE group_id = %s',
            (group_id,)
        )
        return [
            BaseUser(**user)
            for user in self.cursor.fetchall()
        ]
