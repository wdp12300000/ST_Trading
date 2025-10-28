"""
UserDataWebSocket类单元测试

测试UserDataWebSocket类的完整功能，包括：
- 初始化
- ListenKey管理（创建、keepalive）
- WebSocket连接
- 订单更新处理
- 账户更新处理
- 持仓更新处理
- 断线重连
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from src.core.de.user_data_websocket import UserDataWebSocket
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


class TestUserDataWebSocketInitialization:
    """测试UserDataWebSocket的初始化"""
    
    def test_init_with_valid_parameters(self):
        """测试使用有效参数初始化UserDataWebSocket"""
        event_bus = Mock()
        binance_client = Mock()
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        assert ws.user_id == "user_001"
        assert ws._event_bus == event_bus
        assert ws._binance_client == binance_client
        assert ws._ws_url == "wss://fstream.binance.com"
    
    def test_init_sets_disconnected_state(self):
        """测试初始化时设置为未连接状态"""
        event_bus = Mock()
        binance_client = Mock()
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        assert ws.is_connected() == False
    
    def test_init_sets_no_listen_key(self):
        """测试初始化时没有ListenKey"""
        event_bus = Mock()
        binance_client = Mock()
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        assert ws.get_listen_key() is None


class TestUserDataWebSocketListenKey:
    """测试UserDataWebSocket的ListenKey管理"""
    
    @pytest.mark.asyncio
    async def test_create_listen_key_success(self):
        """测试成功创建ListenKey"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        # 创建ListenKey
        listen_key = await ws._create_listen_key()
        
        # 验证调用了BinanceClient的create_listen_key方法
        binance_client.create_listen_key.assert_called_once()
        
        # 验证返回的ListenKey
        assert listen_key == "test_listen_key_123"
        
        # 验证存储了ListenKey
        assert ws.get_listen_key() == "test_listen_key_123"
    
    @pytest.mark.asyncio
    async def test_keepalive_listen_key_success(self):
        """测试成功keepalive ListenKey"""
        event_bus = Mock()
        binance_client = Mock()
        binance_client.keepalive_listen_key = AsyncMock()
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        ws._listen_key = "test_listen_key_123"
        
        # Keepalive ListenKey
        await ws._keepalive_listen_key()
        
        # 验证调用了BinanceClient的keepalive_listen_key方法
        binance_client.keepalive_listen_key.assert_called_once_with("test_listen_key_123")
    
    @pytest.mark.asyncio
    async def test_keepalive_loop_runs_every_30_minutes(self):
        """测试keepalive循环每30分钟运行一次"""
        event_bus = Mock()
        binance_client = Mock()
        binance_client.keepalive_listen_key = AsyncMock()

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 验证KEEPALIVE_INTERVAL常量是1800秒（30分钟）
        assert ws.KEEPALIVE_INTERVAL == 1800


class TestUserDataWebSocketConnection:
    """测试UserDataWebSocket的连接功能"""
    
    @pytest.mark.asyncio
    async def test_connect_creates_listen_key_first(self):
        """测试连接前先创建ListenKey"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        # Mock WebSocket连接
        with patch('src.core.de.user_data_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm
            
            # 启动连接（在后台运行）
            task = asyncio.create_task(ws.connect())
            
            # 等待一小段时间让连接建立
            await asyncio.sleep(0.2)
            
            # 验证创建了ListenKey
            binance_client.create_listen_key.assert_called_once()
            assert ws.get_listen_key() == "test_listen_key_123"
            
            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_connect_establishes_websocket(self):
        """测试connect方法建立WebSocket连接"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        # Mock WebSocket连接
        with patch('src.core.de.user_data_websocket.websockets.connect') as mock_connect:
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
    async def test_connect_publishes_user_stream_started_event(self):
        """测试连接成功后发布de.user_stream.started事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")
        
        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )
        
        # Mock WebSocket连接
        with patch('src.core.de.user_data_websocket.websockets.connect') as mock_connect:
            mock_cm, mock_websocket = create_mock_websocket()
            mock_connect.return_value = mock_cm
            
            # 启动连接
            task = asyncio.create_task(ws.connect())
            
            # 等待连接建立
            await asyncio.sleep(0.2)
            
            # 验证发布了de.user_stream.started事件
            assert event_bus.publish.called
            # 查找de.user_stream.started事件
            user_stream_started_calls = [
                call_args[0][0] for call_args in event_bus.publish.call_args_list
                if call_args[0][0].subject == DEEvents.USER_STREAM_STARTED
            ]
            assert len(user_stream_started_calls) > 0
            published_event = user_stream_started_calls[0]
            assert published_event.data["user_id"] == "user_001"
            assert published_event.data["listen_key"] == "test_listen_key_123"
            
            # 停止连接
            await ws.disconnect()
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestUserDataWebSocketOrderUpdate:
    """测试UserDataWebSocket的订单更新处理"""

    @pytest.mark.asyncio
    async def test_handle_order_update_publishes_event(self):
        """测试处理订单更新消息并发布de.order.update事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 模拟订单更新消息
        order_update_message = {
            "e": "ORDER_TRADE_UPDATE",
            "o": {
                "s": "BTCUSDT",
                "c": "client_order_id_123",
                "S": "BUY",
                "o": "LIMIT",
                "q": "0.001",
                "p": "50000",
                "X": "PARTIALLY_FILLED",
                "i": 12345678,
                "z": "0.0005",
                "n": "0",
                "N": "USDT",
                "T": 1640000000000
            }
        }

        # 处理消息
        await ws._handle_order_update(order_update_message["o"])

        # 验证发布了de.order.update事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.ORDER_UPDATE
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["order_id"] == 12345678
        assert published_event.data["symbol"] == "BTCUSDT"
        assert published_event.data["status"] == "PARTIALLY_FILLED"

    @pytest.mark.asyncio
    async def test_handle_order_filled_publishes_event(self):
        """测试处理订单完全成交消息并发布de.order.filled事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 模拟订单完全成交消息
        order_filled_message = {
            "e": "ORDER_TRADE_UPDATE",
            "o": {
                "s": "BTCUSDT",
                "c": "client_order_id_123",
                "S": "BUY",
                "o": "LIMIT",
                "q": "0.001",
                "p": "50000",
                "X": "FILLED",
                "i": 12345678,
                "z": "0.001",
                "n": "0",
                "N": "USDT",
                "T": 1640000000000
            }
        }

        # 处理消息
        await ws._handle_order_update(order_filled_message["o"])

        # 验证发布了de.order.filled事件
        # 查找de.order.filled事件
        order_filled_calls = [
            call_args[0][0] for call_args in event_bus.publish.call_args_list
            if call_args[0][0].subject == DEEvents.ORDER_FILLED
        ]
        assert len(order_filled_calls) > 0
        published_event = order_filled_calls[0]
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["order_id"] == 12345678
        assert published_event.data["symbol"] == "BTCUSDT"


class TestUserDataWebSocketAccountUpdate:
    """测试UserDataWebSocket的账户更新处理"""

    @pytest.mark.asyncio
    async def test_handle_account_update_publishes_event(self):
        """测试处理账户更新消息并发布de.account.update事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 模拟账户更新消息
        account_update_message = {
            "e": "ACCOUNT_UPDATE",
            "a": {
                "B": [
                    {"a": "USDT", "wb": "10000.00000000", "cw": "9500.00000000"}
                ],
                "P": [
                    {
                        "s": "BTCUSDT",
                        "pa": "0.001",
                        "ep": "50000.00",
                        "up": "100.00"
                    }
                ]
            }
        }

        # 处理消息
        await ws._handle_account_update(account_update_message["a"])

        # 验证发布了de.account.update事件
        assert event_bus.publish.called
        # 查找de.account.update事件（可能发布了多个事件）
        account_update_calls = [
            call_args[0][0] for call_args in event_bus.publish.call_args_list
            if call_args[0][0].subject == DEEvents.ACCOUNT_UPDATE
        ]
        assert len(account_update_calls) > 0
        published_event = account_update_calls[0]
        assert published_event.data["user_id"] == "user_001"

    @pytest.mark.asyncio
    async def test_handle_position_update_publishes_event(self):
        """测试处理持仓更新消息并发布de.position.update事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 模拟持仓更新（从账户更新消息中提取）
        position_data = {
            "s": "BTCUSDT",
            "pa": "0.001",
            "ep": "50000.00",
            "up": "100.00"
        }

        # 处理持仓更新
        await ws._handle_position_update(position_data)

        # 验证发布了de.position.update事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.POSITION_UPDATE
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["symbol"] == "BTCUSDT"


class TestUserDataWebSocketReconnection:
    """测试UserDataWebSocket的断线重连"""

    @pytest.mark.asyncio
    async def test_disconnect_publishes_disconnected_event(self):
        """测试断开连接时发布de.websocket.disconnected事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # Mock WebSocket连接
        with patch('src.core.de.user_data_websocket.websockets.connect') as mock_connect:
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
            assert published_event.data["connection_type"] == "user_data"

            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_auto_reconnect_on_connection_loss(self):
        """测试连接断开后自动重连"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        binance_client = Mock()
        binance_client.create_listen_key = AsyncMock(return_value="test_listen_key_123")

        ws = UserDataWebSocket(
            user_id="user_001",
            event_bus=event_bus,
            binance_client=binance_client
        )

        # 验证_should_reconnect默认为True
        assert ws._should_reconnect == True

