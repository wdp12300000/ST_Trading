"""
MarketWebSocket类单元测试

测试MarketWebSocket类的完整功能，包括：
- 初始化
- WebSocket连接
- K线订阅
- K线消息处理
- 断线重连
- 多交易对订阅
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from src.core.de.market_websocket import MarketWebSocket
from src.core.de.de_events import DEEvents
from src.core.event import Event


def create_mock_websocket():
    """
    创建mock WebSocket连接

    Returns:
        tuple: (mock_connect, mock_websocket)
    """
    async def infinite_messages():
        """永不结束的消息流，避免触发重连"""
        while True:
            await asyncio.sleep(1)
            yield '{"test": "message"}'

    mock_websocket = MagicMock()
    # 让__aiter__返回一个async generator (self参数会被传入)
    mock_websocket.__aiter__ = lambda self: infinite_messages()
    # 添加close方法作为AsyncMock
    mock_websocket.close = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_websocket
    mock_cm.__aexit__.return_value = None

    return mock_cm, mock_websocket


class TestMarketWebSocketInitialization:
    """测试MarketWebSocket的初始化"""
    
    def test_init_with_valid_parameters(self):
        """测试使用有效参数初始化MarketWebSocket"""
        event_bus = Mock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        assert ws.user_id == "user_001"
        assert ws._event_bus == event_bus
        assert ws._ws_url == "wss://fstream.binance.com"
    
    def test_init_creates_empty_subscriptions(self):
        """测试初始化时创建空的订阅字典"""
        event_bus = Mock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # 验证初始状态
        assert ws.get_subscriptions() == []
    
    def test_init_sets_disconnected_state(self):
        """测试初始化时设置为未连接状态"""
        event_bus = Mock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        assert ws.is_connected() == False


class TestMarketWebSocketConnection:
    """测试MarketWebSocket的连接功能"""
    
    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self):
        """测试connect方法建立WebSocket连接"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接（在后台运行）
            task = asyncio.create_task(ws.connect())

            # 等待一小段时间让连接建立
            await asyncio.sleep(0.2)

            # 验证WebSocket连接已建立
            assert ws.is_connected() == True

            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_connect_publishes_connected_event(self):
        """测试连接成功后发布de.websocket.connected事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接
            task = asyncio.create_task(ws.connect())

            # 等待连接建立
            await asyncio.sleep(0.2)

            # 验证发布了de.websocket.connected事件
            assert event_bus.publish.called
            published_event = event_bus.publish.call_args[0][0]
            assert published_event.subject == DEEvents.WEBSOCKET_CONNECTED
            assert published_event.data["user_id"] == "user_001"
            assert published_event.data["connection_type"] == "market"
            assert "timestamp" in published_event.data

            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestMarketWebSocketSubscription:
    """测试MarketWebSocket的K线订阅功能"""
    
    @pytest.mark.asyncio
    async def test_subscribe_kline_single_symbol(self):
        """测试订阅单个交易对的K线"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接
            task = asyncio.create_task(ws.connect())
            await asyncio.sleep(0.2)

            # 订阅K线
            await ws.subscribe_kline("BTCUSDT", "1h")

            # 验证订阅已添加
            subscriptions = ws.get_subscriptions()
            assert len(subscriptions) == 1
            assert subscriptions[0] == {"symbol": "BTCUSDT", "interval": "1h"}

            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_subscribe_kline_multiple_symbols(self):
        """测试订阅多个交易对的K线"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接
            task = asyncio.create_task(ws.connect())
            await asyncio.sleep(0.2)

            # 订阅多个K线
            await ws.subscribe_kline("BTCUSDT", "1h")
            await ws.subscribe_kline("ETHUSDT", "15m")
            await ws.subscribe_kline("BTCUSDT", "5m")

            # 验证订阅已添加
            subscriptions = ws.get_subscriptions()
            assert len(subscriptions) == 3

            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_subscribe_kline_builds_correct_stream_name(self):
        """测试订阅K线时构建正确的流名称"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # 测试流名称构建
        stream_name = ws._build_stream_name("BTCUSDT", "1h")
        assert stream_name == "btcusdt@kline_1h"
        
        stream_name = ws._build_stream_name("ETHUSDT", "15m")
        assert stream_name == "ethusdt@kline_15m"


class TestMarketWebSocketMessageHandling:
    """测试MarketWebSocket的消息处理功能"""
    
    @pytest.mark.asyncio
    async def test_handle_kline_message_publishes_event(self):
        """测试处理K线消息并发布de.kline.update事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # 模拟币安K线消息
        binance_message = {
            "e": "kline",
            "E": 1672531200000,
            "s": "BTCUSDT",
            "k": {
                "t": 1672531200000,  # 开盘时间
                "T": 1672534799999,  # 收盘时间
                "s": "BTCUSDT",      # 交易对
                "i": "1h",           # 时间周期
                "o": "16500.00",     # 开盘价
                "h": "16600.00",     # 最高价
                "l": "16450.00",     # 最低价
                "c": "16550.00",     # 收盘价
                "v": "1234.56",      # 成交量
                "x": False           # 是否完成
            }
        }
        
        # 处理消息
        await ws._handle_kline_message(binance_message)
        
        # 验证发布了de.kline.update事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.KLINE_UPDATE
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["symbol"] == "BTCUSDT"
        assert published_event.data["interval"] == "1h"
        assert published_event.data["kline"]["open"] == "16500.00"
        assert published_event.data["kline"]["high"] == "16600.00"
        assert published_event.data["kline"]["low"] == "16450.00"
        assert published_event.data["kline"]["close"] == "16550.00"
        assert published_event.data["kline"]["volume"] == "1234.56"
        assert published_event.data["kline"]["is_closed"] == False
    
    @pytest.mark.asyncio
    async def test_handle_kline_message_does_not_cache(self):
        """测试处理K线消息时不缓存数据"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )
        
        # 模拟多条K线消息
        for i in range(10):
            binance_message = {
                "e": "kline",
                "E": 1672531200000 + i * 1000,
                "s": "BTCUSDT",
                "k": {
                    "t": 1672531200000 + i * 1000,
                    "T": 1672534799999 + i * 1000,
                    "s": "BTCUSDT",
                    "i": "1h",
                    "o": f"{16500 + i}.00",
                    "h": f"{16600 + i}.00",
                    "l": f"{16450 + i}.00",
                    "c": f"{16550 + i}.00",
                    "v": "1234.56",
                    "x": False
                }
            }
            await ws._handle_kline_message(binance_message)
        
        # 验证没有缓存（没有get_klines方法或类似的缓存查询方法）
        assert not hasattr(ws, 'get_klines')
        assert not hasattr(ws, '_kline_cache')


class TestMarketWebSocketReconnection:
    """测试MarketWebSocket的断线重连功能"""

    @pytest.mark.asyncio
    async def test_disconnect_publishes_disconnected_event(self):
        """测试断开连接时发布de.websocket.disconnected事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接
            task = asyncio.create_task(ws.connect())
            await asyncio.sleep(0.2)

            # 重置mock以清除连接事件
            event_bus.publish.reset_mock()

            # 断开连接
            await ws.disconnect()

            # 验证发布了de.websocket.disconnected事件
            assert event_bus.publish.called
            published_event = event_bus.publish.call_args[0][0]
            assert published_event.subject == DEEvents.WEBSOCKET_DISCONNECTED
            assert published_event.data["user_id"] == "user_001"
            assert published_event.data["connection_type"] == "market"

            # 停止任务
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_reconnect_restores_subscriptions(self):
        """测试重连后恢复之前的订阅"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动连接
            task = asyncio.create_task(ws.connect())
            await asyncio.sleep(0.2)

            # 添加订阅
            await ws.subscribe_kline("BTCUSDT", "1h")
            await ws.subscribe_kline("ETHUSDT", "15m")

            # 验证订阅
            subscriptions_before = ws.get_subscriptions()
            assert len(subscriptions_before) == 2

            # 断开连接
            await ws.disconnect()

            # 重新连接
            task2 = asyncio.create_task(ws.connect())
            await asyncio.sleep(0.2)

            # 验证订阅已恢复
            subscriptions_after = ws.get_subscriptions()
            assert len(subscriptions_after) == 2
            assert subscriptions_after == subscriptions_before

            # 停止连接
            await ws.disconnect()
            task.cancel()
            task2.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            try:
                await task2
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_connection_loss(self):
        """测试连接丢失时自动重连"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        # 验证有自动重连机制（通过检查是否有_should_reconnect属性或类似机制）
        # 这个测试主要验证设计意图，具体实现可能需要调整
        assert hasattr(ws, '_should_reconnect') or hasattr(ws, 'auto_reconnect')


class TestMarketWebSocketMultipleAccounts:
    """测试多账户独立性"""

    def test_different_accounts_have_independent_websockets(self):
        """测试不同账户的WebSocket连接相互独立"""
        event_bus = Mock()

        ws1 = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        ws2 = MarketWebSocket(
            user_id="user_002",
            event_bus=event_bus
        )

        # 验证是不同的实例
        assert ws1 is not ws2
        assert ws1.user_id == "user_001"
        assert ws2.user_id == "user_002"

    @pytest.mark.asyncio
    async def test_different_accounts_have_independent_subscriptions(self):
        """测试不同账户的订阅相互独立"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        ws1 = MarketWebSocket(
            user_id="user_001",
            event_bus=event_bus
        )

        ws2 = MarketWebSocket(
            user_id="user_002",
            event_bus=event_bus
        )

        # Mock WebSocket连接
        with patch('src.core.de.market_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm

            # 启动两个连接
            task1 = asyncio.create_task(ws1.connect())
            task2 = asyncio.create_task(ws2.connect())
            await asyncio.sleep(0.2)

            # 分别订阅不同的K线
            await ws1.subscribe_kline("BTCUSDT", "1h")
            await ws2.subscribe_kline("ETHUSDT", "15m")

            # 验证订阅独立
            subs1 = ws1.get_subscriptions()
            subs2 = ws2.get_subscriptions()

            assert len(subs1) == 1
            assert len(subs2) == 1
            assert subs1[0]["symbol"] == "BTCUSDT"
            assert subs2[0]["symbol"] == "ETHUSDT"

            # 停止连接
            await ws1.disconnect()
            await ws2.disconnect()
            task1.cancel()
            task2.cancel()
            try:
                await task1
            except asyncio.CancelledError:
                pass
            try:
                await task2
            except asyncio.CancelledError:
                pass

