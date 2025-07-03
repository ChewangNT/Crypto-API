# botpy回调消息类
请将python提升至`3.7`版本以上，否则将无法使用该包

项目目录：
```text
__init__.py     初始化api包
callback.py     回调消息包
database.py     数据库相关功能包
error.py        异常类
```

在使用该包时，推荐使用`from`引用：
```python
from api import Callback
```

- 回调消息对象`Callback`是一个基于`botpy`的回调消息类，使用回调
消息对象时需要传入通过`botpy.Client`继承类获得的`BaseMessage`对象，
一般分为`Message`，`GroupMessage`与`C2CMessage`：

```python
import botpy
from botpy.message import GroupMessage
from api import Callback


class App(botpy.Client):
    async def on_group_at_message_create(self, msg: GroupMessage):
        # 初始化回调对象，传入接收到的 BaseMessage 对象
        new_callback = Callback(msg)
        # 现在便可以使用 Callback 类轻松发送消息
        await new_callback.send('Hello, world!')
```

- 在最后，还需要传入`appid`与`secret`以启动机器人：

```python
intents = botpy.Intents(public_messages=True)
app = App(intents)
# 此处填写自己 bot 的 appid 与 secret
app.run(appid='appid', secret='secret')
```

在使用机器人时，有时需要开发指令功能，这时可以引入`callback`包中的`Session`类，
用于创建一个功能上下文管理器：

```python
from api import Callback, Session

# 初始化 Session 对象
session = Session()
```

- 在初始化完毕后，你可以使用`Session.bind`装饰器绑定异步函数，装饰器参数如下：

```python
def bind(
    self,
    *commands: str,
    prefixes: list[str] | tuple[str] = ['/', ''],
    limitation: list[str] | tuple[str] = []
) -> Any: ...
```
- `*commands`：接收任意数量的绑定指令名称
- `prefixes`：可选参数，指令触发前缀（默认为`/`与无前缀）
- `limitation`：限制的发送对象（只可传入三种参数，`channel`代表频道
`group`代表群聊，`c2c`代表私聊）

>注意，绑定的函数必须传入一个 msg_obj 参数作为回调消息对象，与一个params参数接收指令参数，否则将会报错

```python
@session.bind('echo')
async def echo(msg_obj: Callback, params=None):
    msg_obj.send(' '.join(params))
```