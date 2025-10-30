"""
MarketWebSocket - 币安市场数据WebSocket客户端

负责订阅和接收币安市场数据流，包括：
- 建立WebSocket连接
- 订阅K线数据流
- 接收并解析K线消息
- 直接发布事件（不缓存数据）
- 断线自动重连
- 恢复订阅配置

使用方式：
    from src.core.de.market_websocket import MarketWebSocket
    from src.core.event_bus import EventBus

    bus = EventBus.get_instance()
    ws = MarketWebSocket(user_id="user_001", event_bus=bus)

    # 启动连接（后台运行）
    asyncio.create_task(ws.connect())

    # 订阅K线
    await ws.subscribe_kline("BTCUSDT", "1h")

    # 断开连接
    await ws.disconnect()
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set
import websockets
from src.core.event import Event, EventBus
from src.core.de.de_events import DEEvents
from src.utils.logger import logger


class MarketWebSocket:
    """
    币安市场数据WebSocket客户端类

    每个交易账户对应一个MarketWebSocket实例。
    负责订阅K线数据流并实时发布事件。

    属性：
        user_id: 用户ID
        _event_bus: 事件总线
        _binance_client: BinanceClient实例（用于获取历史K线）
        _ws_url: WebSocket基础URL
        _websocket: WebSocket连接对象
        _subscriptions: 订阅配置列表
        _connected: 连接状态
        _should_reconnect: 是否应该自动重连
    """

    # 币安正式网WebSocket端点
    WS_URL = "wss://fstream.binance.com"

    def __init__(self, user_id: str, event_bus: EventBus, binance_client=None):
        """
        初始化MarketWebSocket实例

        Args:
            user_id: 用户ID
            event_bus: 事件总线实例
            binance_client: BinanceClient实例（可选，用于获取历史K线）

        实现细节：
            - 初始化订阅列表
            - 设置为未连接状态
            - 启用自动重连
        """
        self.user_id = user_id
        self._event_bus = event_bus
        self._binance_client = binance_client
        self._ws_url = self.WS_URL
        self._websocket = None
        self._subscriptions: List[Dict[str, str]] = []
        self._connected = False
        self._should_reconnect = True
        self._stream_names: Set[str] = set()

        logger.info(f"MarketWebSocket初始化: user_id={user_id}")

    def is_connected(self) -> bool:
        """
        检查WebSocket是否已连接

        Returns:
            如果已连接返回True，否则返回False
        """
        return self._connected

    def get_subscriptions(self) -> List[Dict[str, str]]:
        """
        获取当前所有订阅配置

        Returns:
            订阅配置列表，每个元素包含symbol和interval
        """
        return self._subscriptions.copy()

    def _build_stream_name(self, symbol: str, interval: str) -> str:
        """
        构建币安WebSocket流名称

        Args:
            symbol: 交易对（如BTCUSDT）
            interval: K线间隔（如1h, 15m）

        Returns:
            流名称（如btcusdt@kline_1h）

        实现细节：
            - 交易对转换为小写
            - 格式：<symbol>@kline_<interval>
        """
        return f"{symbol.lower()}@kline_{interval}"

    def _build_ws_url(self) -> str:
        """
        构建WebSocket连接URL

        Returns:
            WebSocket URL

        实现细节：
            - 如果有订阅，使用组合流格式
            - 如果没有订阅，使用基础URL
        """
        if not self._stream_names:
            # 没有订阅时使用基础URL
            return f"{self._ws_url}/ws"

        # 组合多个流
        streams = "/".join(self._stream_names)
        return f"{self._ws_url}/stream?streams={streams}"

    async def connect(self) -> None:
        """
        建立WebSocket连接并保持连接

        实现细节：
            1. 建立WebSocket连接
            2. 发布de.websocket.connected事件
            3. 持续接收消息
            4. 如果断开且_should_reconnect=True，自动重连
        """
        while self._should_reconnect:
            try:
                url = self._build_ws_url()
                logger.info(f"MarketWebSocket连接中: user_id={self.user_id}, url={url}")

                async with websockets.connect(url) as websocket:
                    self._websocket = websocket
                    self._connected = True

                    # 发布连接成功事件
                    await self._publish_connected()

                    logger.info(f"MarketWebSocket连接成功: user_id={self.user_id}")

                    # 持续接收消息
                    async for message in websocket:
                        await self._handle_message(message)

            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"MarketWebSocket连接关闭: user_id={self.user_id}, reason={e}")
                self._connected = False
                await self._publish_disconnected("connection_closed")

                if self._should_reconnect:
                    logger.info(f"MarketWebSocket将在3秒后重连: user_id={self.user_id}")
                    await asyncio.sleep(3)
                else:
                    break

            except Exception as e:
                logger.error(f"MarketWebSocket连接错误: user_id={self.user_id}, error={e}")
                self._connected = False
                await self._publish_disconnected(f"error: {str(e)}")

                if self._should_reconnect:
                    logger.info(f"MarketWebSocket将在3秒后重连: user_id={self.user_id}")
                    await asyncio.sleep(3)
                else:
                    break

    async def disconnect(self) -> None:
        """
        断开WebSocket连接

        实现细节：
            1. 设置_should_reconnect=False停止自动重连
            2. 关闭WebSocket连接
            3. 发布de.websocket.disconnected事件
        """
        logger.info(f"MarketWebSocket断开连接: user_id={self.user_id}")

        self._should_reconnect = False
        self._connected = False

        if self._websocket:
            await self._websocket.close()
            self._websocket = None

        await self._publish_disconnected("manual_disconnect")

        logger.info(f"MarketWebSocket已断开: user_id={self.user_id}")

    async def subscribe_kline(self, symbol: str, interval: str) -> None:
        """
        订阅K线数据流

        Args:
            symbol: 交易对（如BTCUSDT）
            interval: K线间隔（如1h, 15m）

        实现细节：
            1. 添加到订阅列表
            2. 构建流名称
            3. 如果已连接，需要重新连接以应用新订阅
        """
        # 添加到订阅列表
        subscription = {"symbol": symbol, "interval": interval}
        if subscription not in self._subscriptions:
            self._subscriptions.append(subscription)

            # 添加流名称
            stream_name = self._build_stream_name(symbol, interval)
            self._stream_names.add(stream_name)

            logger.info(f"添加K线订阅: user_id={self.user_id}, symbol={symbol}, interval={interval}")

            # 如果已连接，需要重新连接以应用新订阅
            # 币安WebSocket不支持动态添加订阅，需要重新建立连接
            if self._connected:
                logger.info(f"重新连接以应用新订阅: user_id={self.user_id}")
                # 这里不需要手动重连，因为关闭连接后会自动重连
                if self._websocket:
                    await self._websocket.close()

    async def _handle_message(self, message: str) -> None:
        """
        处理WebSocket消息

        Args:
            message: WebSocket消息（JSON字符串）

        实现细节：
            1. 解析JSON消息
            2. 根据消息类型分发处理
            3. K线消息调用_handle_kline_message
        """
        try:
            data = json.loads(message)

            # 组合流格式的消息
            if "stream" in data and "data" in data:
                stream_data = data["data"]
                if stream_data.get("e") == "kline":
                    await self._handle_kline_message(stream_data)
            # 单流格式的消息
            elif data.get("e") == "kline":
                await self._handle_kline_message(data)
            else:
                logger.debug(f"收到未知消息类型: user_id={self.user_id}, message={message[:100]}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: user_id={self.user_id}, error={e}, message={message[:100]}")
        except Exception as e:
            logger.error(f"消息处理失败: user_id={self.user_id}, error={e}")

    async def _handle_kline_message(self, data: Dict) -> None:
        """
        处理K线消息并发布事件

        设计原则：
            - 只在K线关闭时发布事件（is_closed=True）
            - 发布完整的历史K线列表（包含最新的）
            - 符合"无缓存"设计原则

        Args:
            data: K线消息数据

        实现细节：
            1. 提取K线数据
            2. 检查is_closed标志
            3. 如果K线已关闭，调用BinanceClient获取最新的历史K线
            4. 转换K线格式（币安格式 → 标准格式）
            5. 发布de.kline.update事件（包含完整历史K线列表）
        """
        try:
            kline_data = data["k"]
            is_closed = kline_data["x"]
            symbol = kline_data["s"]
            interval = kline_data["i"]

            # 只处理已关闭的K线
            if not is_closed:
                logger.debug(f"K线未关闭，跳过: user_id={self.user_id}, symbol={symbol}, interval={interval}")
                return

            logger.info(f"K线关闭: user_id={self.user_id}, symbol={symbol}, interval={interval}")

            # 检查是否有BinanceClient实例
            if not self._binance_client:
                logger.warning(f"未设置BinanceClient，无法获取历史K线: user_id={self.user_id}")
                return

            # 获取最新的历史K线数据（默认200根）
            try:
                raw_klines = await self._binance_client.get_historical_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=200
                )

                # 转换K线格式（币安格式 → 标准格式）
                klines = []
                for k in raw_klines:
                    klines.append({
                        "open": k[1],
                        "high": k[2],
                        "low": k[3],
                        "close": k[4],
                        "volume": k[5],
                        "timestamp": k[0],
                        "is_closed": True  # 历史K线都是已关闭的
                    })

                # 发布de.kline.update事件（包含完整历史K线列表）
                event = Event(
                    subject=DEEvents.KLINE_UPDATE,
                    data={
                        "user_id": self.user_id,
                        "symbol": symbol,
                        "interval": interval,
                        "klines": klines  # 完整的历史K线列表
                    },
                    source="DE"
                )

                await self._event_bus.publish(event)

                logger.info(f"K线更新事件已发布: user_id={self.user_id}, symbol={symbol}, "
                           f"interval={interval}, klines_count={len(klines)}")

            except Exception as e:
                logger.error(f"获取历史K线失败: user_id={self.user_id}, symbol={symbol}, "
                           f"interval={interval}, error={e}")

        except KeyError as e:
            logger.error(f"K线数据格式错误: user_id={self.user_id}, missing_key={e}")
        except Exception as e:
            logger.error(f"K线消息处理失败: user_id={self.user_id}, error={e}")

    async def _publish_connected(self) -> None:
        """
        发布de.websocket.connected事件

        实现细节：
            - 创建de.websocket.connected事件
            - 包含user_id、connection_type和timestamp
            - 异步发布到事件总线
        """
        event = Event(
            subject=DEEvents.WEBSOCKET_CONNECTED,
            data={
                "user_id": self.user_id,
                "connection_type": "market",
                "timestamp": int(time.time() * 1000)
            },
            source="DE"
        )

        await self._event_bus.publish(event)
        logger.debug(f"发布de.websocket.connected事件: user_id={self.user_id}")

    async def _publish_disconnected(self, reason: str) -> None:
        """
        发布de.websocket.disconnected事件

        Args:
            reason: 断开原因

        实现细节：
            - 创建de.websocket.disconnected事件
            - 包含user_id、connection_type和reason
            - 异步发布到事件总线
        """
        event = Event(
            subject=DEEvents.WEBSOCKET_DISCONNECTED,
            data={
                "user_id": self.user_id,
                "connection_type": "market",
                "reason": reason
            },
            source="DE"
        )

        await self._event_bus.publish(event)
        logger.debug(f"发布de.websocket.disconnected事件: user_id={self.user_id}, reason={reason}")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"MarketWebSocket(user_id={self.user_id}, connected={self._connected}, subscriptions={len(self._subscriptions)})"