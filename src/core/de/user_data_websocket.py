"""
UserDataWebSocket - 币安用户数据流WebSocket客户端

负责订阅和接收币安用户数据流，包括：
- 创建和管理ListenKey
- 建立WebSocket连接
- 接收并解析订单更新消息
- 接收并解析账户更新消息
- 接收并解析持仓更新消息
- 断线自动重连
- 30分钟keepalive循环

使用方式：
    from src.core.de.user_data_websocket import UserDataWebSocket
    from src.core.event_bus import EventBus
    from src.core.de.binance_client import BinanceClient

    bus = EventBus.get_instance()
    client = BinanceClient(user_id="user_001", api_key="...", api_secret="...")
    ws = UserDataWebSocket(user_id="user_001", event_bus=bus, binance_client=client)

    # 启动连接（后台运行）
    asyncio.create_task(ws.connect())

    # 断开连接
    await ws.disconnect()
"""

import asyncio
import json
import time
from typing import Dict, Optional
import websockets
from src.core.event import Event, EventBus
from src.core.de.de_events import DEEvents
from src.utils.logger import logger


class UserDataWebSocket:
    """
    币安用户数据流WebSocket客户端类

    每个交易账户对应一个UserDataWebSocket实例。
    负责接收订单更新、账户更新、持仓更新并实时发布事件。

    属性：
        user_id: 用户ID
        _event_bus: 事件总线
        _binance_client: BinanceClient实例
        _ws_url: WebSocket基础URL
        _websocket: WebSocket连接对象
        _listen_key: 用户数据流密钥
        _connected: 连接状态
        _should_reconnect: 是否应该自动重连
        _keepalive_task: keepalive任务
    """

    # 币安正式网WebSocket端点
    WS_URL = "wss://fstream.binance.com"

    # ListenKey keepalive间隔（30分钟 = 1800秒）
    KEEPALIVE_INTERVAL = 1800

    def __init__(self, user_id: str, event_bus: EventBus, binance_client):
        """
        初始化UserDataWebSocket实例

        Args:
            user_id: 用户ID
            event_bus: 事件总线实例
            binance_client: BinanceClient实例

        实现细节：
            - 保存BinanceClient引用用于ListenKey管理
            - 设置为未连接状态
            - 启用自动重连
        """
        self.user_id = user_id
        self._event_bus = event_bus
        self._binance_client = binance_client
        self._ws_url = self.WS_URL
        self._websocket = None
        self._listen_key: Optional[str] = None
        self._connected = False
        self._should_reconnect = True
        self._keepalive_task: Optional[asyncio.Task] = None

        logger.info(f"UserDataWebSocket初始化: user_id={user_id}")

    def is_connected(self) -> bool:
        """
        检查WebSocket是否已连接

        Returns:
            如果已连接返回True，否则返回False
        """
        return self._connected

    def get_listen_key(self) -> Optional[str]:
        """
        获取当前的ListenKey

        Returns:
            ListenKey字符串，如果未创建则返回None
        """
        return self._listen_key

    async def _create_listen_key(self) -> str:
        """
        创建用户数据流ListenKey

        Returns:
            ListenKey字符串

        Raises:
            Exception: 创建失败

        实现细节：
            - 调用BinanceClient的create_listen_key方法
            - 存储ListenKey供后续使用
        """
        logger.debug(f"创建ListenKey: user_id={self.user_id}")

        try:
            listen_key = await self._binance_client.create_listen_key()
            self._listen_key = listen_key
            logger.info(f"ListenKey创建成功: user_id={self.user_id}")
            return listen_key
        except Exception as e:
            logger.error(f"ListenKey创建失败: user_id={self.user_id}, error={e}")
            raise

    async def _keepalive_listen_key(self) -> None:
        """
        延长ListenKey有效期

        实现细节：
            - 调用BinanceClient的keepalive_listen_key方法
            - 建议每30分钟调用一次
        """
        if not self._listen_key:
            logger.warning(f"无法keepalive: ListenKey不存在, user_id={self.user_id}")
            return

        logger.debug(f"Keepalive ListenKey: user_id={self.user_id}")

        try:
            await self._binance_client.keepalive_listen_key(self._listen_key)
            logger.info(f"ListenKey keepalive成功: user_id={self.user_id}")
        except Exception as e:
            logger.error(f"ListenKey keepalive失败: user_id={self.user_id}, error={e}")

    async def _keepalive_loop(self) -> None:
        """
        ListenKey keepalive循环

        实现细节：
            - 每30分钟调用一次keepalive_listen_key
            - 在_should_reconnect为False时停止
        """
        logger.info(f"启动ListenKey keepalive循环: user_id={self.user_id}")

        while self._should_reconnect:
            await asyncio.sleep(self.KEEPALIVE_INTERVAL)

            if self._should_reconnect:
                await self._keepalive_listen_key()

    async def connect(self) -> None:
        """
        建立WebSocket连接并维持

        实现细节：
            1. 创建ListenKey
            2. 构建WebSocket URL
            3. 建立连接
            4. 启动keepalive循环
            5. 持续接收消息
            6. 断线后自动重连（如果_should_reconnect为True）
        """
        while self._should_reconnect:
            try:
                # 创建ListenKey
                if not self._listen_key:
                    await self._create_listen_key()

                # 构建WebSocket URL
                url = f"{self._ws_url}/ws/{self._listen_key}"
                logger.info(f"UserDataWebSocket连接中: user_id={self.user_id}, url={url}")

                # 建立WebSocket连接
                async with websockets.connect(url) as websocket:
                    self._websocket = websocket
                    self._connected = True

                    # 发布连接成功事件
                    await self._publish_user_stream_started()
                    logger.info(f"UserDataWebSocket连接成功: user_id={self.user_id}")

                    # 启动keepalive循环
                    if not self._keepalive_task or self._keepalive_task.done():
                        self._keepalive_task = asyncio.create_task(self._keepalive_loop())

                    # 持续接收消息
                    async for message in websocket:
                        await self._handle_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                self._connected = False
                logger.warning(f"UserDataWebSocket连接关闭: user_id={self.user_id}, code={e.code}, reason={e.reason}")
                await self._publish_disconnected("connection_closed")

                if self._should_reconnect:
                    logger.info(f"UserDataWebSocket将在3秒后重连: user_id={self.user_id}")
                    await asyncio.sleep(3)

            except Exception as e:
                self._connected = False
                logger.error(f"UserDataWebSocket连接错误: user_id={self.user_id}, error={e}")
                await self._publish_disconnected(f"error: {e}")

                if self._should_reconnect:
                    logger.info(f"UserDataWebSocket将在3秒后重连: user_id={self.user_id}")
                    await asyncio.sleep(3)

    async def disconnect(self) -> None:
        """
        断开WebSocket连接

        实现细节：
            1. 设置_should_reconnect=False停止自动重连
            2. 停止keepalive循环
            3. 关闭WebSocket连接
            4. 发布de.websocket.disconnected事件
        """
        logger.info(f"UserDataWebSocket断开连接: user_id={self.user_id}")

        self._should_reconnect = False
        self._connected = False

        # 停止keepalive循环
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                pass

        # 关闭WebSocket连接
        if self._websocket:
            await self._websocket.close()

        await self._publish_disconnected("manual_disconnect")

    async def _handle_message(self, message: str) -> None:
        """
        处理WebSocket消息

        Args:
            message: WebSocket消息（JSON字符串）

        实现细节：
            - 解析JSON消息
            - 根据事件类型分发到不同的处理方法
        """
        try:
            data = json.loads(message)
            event_type = data.get("e")

            if event_type == "ORDER_TRADE_UPDATE":
                await self._handle_order_update(data.get("o", {}))
            elif event_type == "ACCOUNT_UPDATE":
                await self._handle_account_update(data.get("a", {}))
            else:
                logger.debug(f"收到未处理的消息类型: user_id={self.user_id}, event_type={event_type}")

        except json.JSONDecodeError as e:
            logger.error(f"消息JSON解析失败: user_id={self.user_id}, error={e}, message={message}")
        except Exception as e:
            logger.error(f"消息处理失败: user_id={self.user_id}, error={e}")

    async def _handle_order_update(self, order_data: Dict) -> None:
        """
        处理订单更新消息

        Args:
            order_data: 订单数据字典

        实现细节：
            - 发布de.order.update事件
            - 如果订单状态为FILLED，额外发布de.order.filled事件
        """
        try:
            order_id = order_data.get("i")
            symbol = order_data.get("s")
            status = order_data.get("X")
            filled_quantity = order_data.get("z")

            logger.debug(f"处理订单更新: user_id={self.user_id}, order_id={order_id}, symbol={symbol}, status={status}")

            # 发布de.order.update事件
            await self._publish_order_update(order_data)

            # 如果订单完全成交，发布de.order.filled事件
            if status == "FILLED":
                await self._publish_order_filled(order_data)

        except Exception as e:
            logger.error(f"订单更新处理失败: user_id={self.user_id}, error={e}")

    async def _handle_account_update(self, account_data: Dict) -> None:
        """
        处理账户更新消息

        Args:
            account_data: 账户数据字典

        实现细节：
            - 发布de.account.update事件
            - 处理持仓更新（如果有）
        """
        try:
            logger.debug(f"处理账户更新: user_id={self.user_id}")

            # 发布de.account.update事件
            await self._publish_account_update(account_data)

            # 处理持仓更新
            positions = account_data.get("P", [])
            for position_data in positions:
                await self._handle_position_update(position_data)

        except Exception as e:
            logger.error(f"账户更新处理失败: user_id={self.user_id}, error={e}")

    async def _handle_position_update(self, position_data: Dict) -> None:
        """
        处理持仓更新消息

        Args:
            position_data: 持仓数据字典

        实现细节：
            - 发布de.position.update事件
        """
        try:
            symbol = position_data.get("s")
            position_amount = position_data.get("pa")

            logger.debug(f"处理持仓更新: user_id={self.user_id}, symbol={symbol}, amount={position_amount}")

            # 发布de.position.update事件
            await self._publish_position_update(position_data)

        except Exception as e:
            logger.error(f"持仓更新处理失败: user_id={self.user_id}, error={e}")

    async def _publish_user_stream_started(self) -> None:
        """
        发布de.user_stream.started事件

        实现细节：
            - 包含user_id和listen_key
        """
        event = Event(
            subject=DEEvents.USER_STREAM_STARTED,
            data={
                "user_id": self.user_id,
                "listen_key": self._listen_key,
                "timestamp": time.time()
            }
        )

        logger.debug(f"发布de.user_stream.started事件: user_id={self.user_id}")
        await self._event_bus.publish(event)

    async def _publish_disconnected(self, reason: str) -> None:
        """
        发布de.websocket.disconnected事件

        Args:
            reason: 断开原因

        实现细节：
            - 包含user_id、connection_type和reason
        """
        event = Event(
            subject=DEEvents.WEBSOCKET_DISCONNECTED,
            data={
                "user_id": self.user_id,
                "connection_type": "user_data",
                "reason": reason,
                "timestamp": time.time()
            }
        )

        logger.debug(f"发布de.websocket.disconnected事件: user_id={self.user_id}, reason={reason}")
        await self._event_bus.publish(event)

    async def _publish_order_update(self, order_data: Dict) -> None:
        """
        发布de.order.update事件

        Args:
            order_data: 订单数据字典

        实现细节：
            - 提取订单关键信息并发布事件
        """
        event = Event(
            subject=DEEvents.ORDER_UPDATE,
            data={
                "user_id": self.user_id,
                "order_id": order_data.get("i"),
                "symbol": order_data.get("s"),
                "status": order_data.get("X"),
                "filled_quantity": order_data.get("z"),
                "remaining_quantity": float(order_data.get("q", 0)) - float(order_data.get("z", 0)),
                "timestamp": time.time()
            }
        )

        logger.debug(f"发布de.order.update事件: user_id={self.user_id}, order_id={order_data.get('i')}")
        await self._event_bus.publish(event)

    async def _publish_order_filled(self, order_data: Dict) -> None:
        """
        发布de.order.filled事件

        Args:
            order_data: 订单数据字典

        实现细节：
            - 提取订单成交信息并发布事件
        """
        event = Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": self.user_id,
                "order_id": order_data.get("i"),
                "symbol": order_data.get("s"),
                "price": order_data.get("p"),
                "quantity": order_data.get("z"),
                "timestamp": order_data.get("T", time.time() * 1000) / 1000
            }
        )

        logger.debug(f"发布de.order.filled事件: user_id={self.user_id}, order_id={order_data.get('i')}")
        await self._event_bus.publish(event)

    async def _publish_account_update(self, account_data: Dict) -> None:
        """
        发布de.account.update事件

        Args:
            account_data: 账户数据字典

        实现细节：
            - 提取账户余额信息并发布事件
        """
        # 提取USDT余额信息
        balances = account_data.get("B", [])
        usdt_balance = next((b for b in balances if b.get("a") == "USDT"), {})

        event = Event(
            subject=DEEvents.ACCOUNT_UPDATE,
            data={
                "user_id": self.user_id,
                "total_equity": usdt_balance.get("wb", "0"),
                "available_balance": usdt_balance.get("cw", "0"),
                "margin_used": float(usdt_balance.get("wb", 0)) - float(usdt_balance.get("cw", 0)),
                "timestamp": time.time()
            }
        )

        logger.debug(f"发布de.account.update事件: user_id={self.user_id}")
        await self._event_bus.publish(event)

    async def _publish_position_update(self, position_data: Dict) -> None:
        """
        发布de.position.update事件

        Args:
            position_data: 持仓数据字典

        实现细节：
            - 提取持仓信息并发布事件
        """
        event = Event(
            subject=DEEvents.POSITION_UPDATE,
            data={
                "user_id": self.user_id,
                "symbol": position_data.get("s"),
                "side": "LONG" if float(position_data.get("pa", 0)) > 0 else "SHORT",
                "quantity": abs(float(position_data.get("pa", 0))),
                "unrealized_pnl": position_data.get("up"),
                "entry_price": position_data.get("ep"),
                "timestamp": time.time()
            }
        )

        logger.debug(f"发布de.position.update事件: user_id={self.user_id}, symbol={position_data.get('s')}")
        await self._event_bus.publish(event)
