"""
DEManager类单元测试

测试DEManager类的完整功能，包括：
- 单例模式
- 初始化和事件订阅
- 响应pm.account.loaded事件
- BinanceClient实例创建和管理
- 多账户管理
- 查询接口
- 系统关闭
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call, MagicMock
from src.core.de.de_manager import DEManager
from src.core.de.binance_client import BinanceClient
from src.core.de.de_events import DEEvents
from src.core.pm.pm_events import PMEvents
from src.core.event import Event


class TestDEManagerSingleton:
    """测试DEManager的单例模式"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()
    
    def test_get_instance_creates_singleton(self):
        """测试get_instance创建单例"""
        event_bus = Mock()
        
        manager1 = DEManager.get_instance(event_bus=event_bus)
        manager2 = DEManager.get_instance()
        
        assert manager1 is manager2
    
    def test_get_instance_requires_event_bus_on_first_call(self):
        """测试首次调用必须提供event_bus"""
        with pytest.raises(ValueError, match="首次调用必须提供event_bus"):
            DEManager.get_instance()
    
    def test_reset_instance(self):
        """测试重置单例"""
        event_bus = Mock()
        
        manager1 = DEManager.get_instance(event_bus=event_bus)
        DEManager.reset_instance()
        manager2 = DEManager.get_instance(event_bus=event_bus)
        
        assert manager1 is not manager2


class TestDEManagerInitialization:
    """测试DEManager的初始化"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()
    
    def test_init_subscribes_to_pm_account_loaded(self):
        """测试初始化时订阅pm.account.loaded事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 验证订阅了pm.account.loaded事件
        # 现在DEManager订阅了4个事件：pm.account.loaded, trading.order.create, trading.order.cancel, trading.get_account_balance
        assert event_bus.subscribe.call_count == 4

        # 验证第一个订阅是pm.account.loaded
        first_call_args = event_bus.subscribe.call_args_list[0]
        assert first_call_args[0][0] == PMEvents.ACCOUNT_LOADED
        assert callable(first_call_args[0][1])  # 第二个参数是回调函数
    
    def test_init_creates_empty_client_dict(self):
        """测试初始化时创建空的客户端字典"""
        event_bus = Mock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 验证初始状态
        assert manager.get_all_user_ids() == []


class TestDEManagerAccountLoaded:
    """测试DEManager响应pm.account.loaded事件"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_on_account_loaded_creates_binance_client(self):
        """测试接收pm.account.loaded事件后创建BinanceClient"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 模拟pm.account.loaded事件
        event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "strategy": "test_strategy",
                "testnet": False
            },
            source="PM"
        )
        
        # 调用事件处理器
        await manager._on_account_loaded(event)
        
        # 验证创建了BinanceClient
        assert "user_001" in manager.get_all_user_ids()
        client = manager.get_client("user_001")
        assert client is not None
        assert isinstance(client, BinanceClient)
        assert client.user_id == "user_001"
        assert client.api_key == "test_api_key"
        assert client.api_secret == "test_api_secret"
    
    @pytest.mark.asyncio
    async def test_on_account_loaded_publishes_client_connected(self):
        """测试创建BinanceClient成功后发布de.client.connected事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 模拟pm.account.loaded事件
        event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "strategy": "test_strategy",
                "testnet": False
            },
            source="PM"
        )
        
        # 调用事件处理器
        await manager._on_account_loaded(event)
        
        # 验证发布了de.client.connected事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.CLIENT_CONNECTED
        assert published_event.data["user_id"] == "user_001"
        assert "timestamp" in published_event.data
    
    @pytest.mark.asyncio
    async def test_on_account_loaded_handles_missing_fields(self):
        """测试处理缺少必需字段的事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 模拟缺少api_key的事件
        event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_secret": "test_api_secret",
                "strategy": "test_strategy"
            },
            source="PM"
        )
        
        # 调用事件处理器（应该不抛出异常）
        await manager._on_account_loaded(event)
        
        # 验证发布了de.client.connection_failed事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.CLIENT_CONNECTION_FAILED
        assert published_event.data["user_id"] == "user_001"
        assert "error_message" in published_event.data


class TestDEManagerMultiAccount:
    """测试DEManager的多账户管理"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_manage_multiple_accounts(self):
        """测试同时管理多个账户"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 创建两个账户
        event1 = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "账户1",
                "api_key": "key1",
                "api_secret": "secret1",
                "strategy": "strategy1",
                "testnet": False
            },
            source="PM"
        )
        
        event2 = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_002",
                "name": "账户2",
                "api_key": "key2",
                "api_secret": "secret2",
                "strategy": "strategy2",
                "testnet": False
            },
            source="PM"
        )
        
        await manager._on_account_loaded(event1)
        await manager._on_account_loaded(event2)
        
        # 验证两个账户都创建成功
        user_ids = manager.get_all_user_ids()
        assert len(user_ids) == 2
        assert "user_001" in user_ids
        assert "user_002" in user_ids
        
        # 验证可以分别获取客户端
        client1 = manager.get_client("user_001")
        client2 = manager.get_client("user_002")
        assert client1.api_key == "key1"
        assert client2.api_key == "key2"
    
    def test_get_client_returns_none_for_nonexistent_user(self):
        """测试获取不存在的用户返回None"""
        event_bus = Mock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        client = manager.get_client("nonexistent_user")
        assert client is None


class TestDEManagerShutdown:
    """测试DEManager的系统关闭"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_shutdown_clears_all_clients(self):
        """测试关闭时清理所有客户端"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()
        
        manager = DEManager.get_instance(event_bus=event_bus)
        
        # 创建一个账户
        event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "strategy": "test_strategy",
                "testnet": False
            },
            source="PM"
        )
        
        await manager._on_account_loaded(event)
        
        # 验证账户已创建
        assert len(manager.get_all_user_ids()) == 1
        
        # 关闭管理器
        await manager.shutdown()
        
        # 验证所有客户端已清理
        assert len(manager.get_all_user_ids()) == 0


class TestDEManagerOrderEvents:
    """测试DEManager响应订单事件"""

    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()

    @pytest.mark.asyncio
    async def test_subscribe_to_order_create_event(self):
        """测试DEManager订阅trading.order.create事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 验证订阅了trading.order.create事件
        subscribe_calls = [call[0][0] for call in event_bus.subscribe.call_args_list]
        assert DEEvents.INPUT_ORDER_CREATE in subscribe_calls

    @pytest.mark.asyncio
    async def test_subscribe_to_order_cancel_event(self):
        """测试DEManager订阅trading.order.cancel事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 验证订阅了trading.order.cancel事件
        subscribe_calls = [call[0][0] for call in event_bus.subscribe.call_args_list]
        assert DEEvents.INPUT_ORDER_CANCEL in subscribe_calls

    @pytest.mark.asyncio
    async def test_on_order_create_success(self):
        """测试处理trading.order.create事件成功"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 模拟账户已加载
        with patch.object(BinanceClient, '__init__', return_value=None):
            with patch.object(BinanceClient, 'place_order', new_callable=AsyncMock) as mock_place_order:
                mock_place_order.return_value = {
                    "orderId": 123456789,
                    "symbol": "BTCUSDT",
                    "status": "NEW",
                    "side": "BUY",
                    "type": "MARKET",
                    "origQty": "0.001"
                }

                # 创建BinanceClient实例
                client = BinanceClient(user_id="user_001", api_key="test_key", api_secret="test_secret")
                manager._clients["user_001"] = client

                # 创建订单创建事件
                event = Event(
                    subject=DEEvents.INPUT_ORDER_CREATE,
                    data={
                        "user_id": "user_001",
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "order_type": "MARKET",
                        "quantity": 0.001
                    }
                )

                # 调用处理方法
                await manager._on_order_create(event)

                # 验证调用了place_order
                mock_place_order.assert_called_once_with(
                    symbol="BTCUSDT",
                    side="BUY",
                    order_type="MARKET",
                    quantity=0.001,
                    price=None
                )

                # 验证发布了de.order.submitted事件
                assert event_bus.publish.called
                published_event = event_bus.publish.call_args[0][0]
                assert published_event.subject == DEEvents.ORDER_SUBMITTED
                assert published_event.data["user_id"] == "user_001"
                assert published_event.data["order_id"] == 123456789

    @pytest.mark.asyncio
    async def test_on_order_create_client_not_found(self):
        """测试处理trading.order.create事件时客户端不存在"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 创建订单创建事件（user_id不存在）
        event = Event(
            subject=DEEvents.INPUT_ORDER_CREATE,
            data={
                "user_id": "user_999",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "MARKET",
                "quantity": 0.001
            }
        )

        # 调用处理方法
        await manager._on_order_create(event)

        # 验证发布了de.order.failed事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.ORDER_FAILED
        assert published_event.data["user_id"] == "user_999"
        assert "客户端不存在" in published_event.data["error"]

    @pytest.mark.asyncio
    async def test_on_order_create_api_error(self):
        """测试处理trading.order.create事件时API错误"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 模拟账户已加载
        with patch.object(BinanceClient, '__init__', return_value=None):
            with patch.object(BinanceClient, 'place_order', new_callable=AsyncMock) as mock_place_order:
                mock_place_order.side_effect = Exception("API错误: 余额不足")

                # 创建BinanceClient实例
                client = BinanceClient(user_id="user_001", api_key="test_key", api_secret="test_secret")
                manager._clients["user_001"] = client

                # 创建订单创建事件
                event = Event(
                    subject=DEEvents.INPUT_ORDER_CREATE,
                    data={
                        "user_id": "user_001",
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "order_type": "MARKET",
                        "quantity": 0.001
                    }
                )

                # 调用处理方法
                await manager._on_order_create(event)

                # 验证发布了de.order.failed事件
                assert event_bus.publish.called
                published_event = event_bus.publish.call_args[0][0]
                assert published_event.subject == DEEvents.ORDER_FAILED
                assert published_event.data["user_id"] == "user_001"
                assert "API错误" in published_event.data["error"]

    @pytest.mark.asyncio
    async def test_on_order_cancel_success(self):
        """测试处理trading.order.cancel事件成功"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 模拟账户已加载
        with patch.object(BinanceClient, '__init__', return_value=None):
            with patch.object(BinanceClient, 'cancel_order', new_callable=AsyncMock) as mock_cancel_order:
                mock_cancel_order.return_value = {
                    "orderId": 123456789,
                    "symbol": "BTCUSDT",
                    "status": "CANCELED"
                }

                # 创建BinanceClient实例
                client = BinanceClient(user_id="user_001", api_key="test_key", api_secret="test_secret")
                manager._clients["user_001"] = client

                # 创建订单取消事件
                event = Event(
                    subject=DEEvents.INPUT_ORDER_CANCEL,
                    data={
                        "user_id": "user_001",
                        "symbol": "BTCUSDT",
                        "order_id": 123456789
                    }
                )

                # 调用处理方法
                await manager._on_order_cancel(event)

                # 验证调用了cancel_order
                mock_cancel_order.assert_called_once_with(
                    symbol="BTCUSDT",
                    order_id=123456789,
                    client_order_id=None
                )

                # 验证发布了de.order.cancelled事件
                assert event_bus.publish.called
                published_event = event_bus.publish.call_args[0][0]
                assert published_event.subject == DEEvents.ORDER_CANCELLED
                assert published_event.data["user_id"] == "user_001"
                assert published_event.data["order_id"] == 123456789

    @pytest.mark.asyncio
    async def test_on_order_cancel_client_not_found(self):
        """测试处理trading.order.cancel事件时客户端不存在"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = AsyncMock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 创建订单取消事件（user_id不存在）
        event = Event(
            subject=DEEvents.INPUT_ORDER_CANCEL,
            data={
                "user_id": "user_999",
                "symbol": "BTCUSDT",
                "order_id": 123456789
            }
        )

        # 调用处理方法
        await manager._on_order_cancel(event)

        # 验证发布了de.order.failed事件
        assert event_bus.publish.called
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.subject == DEEvents.ORDER_FAILED
        assert published_event.data["user_id"] == "user_999"
        assert "客户端不存在" in published_event.data["error"]


class TestDEManagerAccountBalanceEvents:
    """测试DEManager响应账户余额查询事件"""

    def teardown_method(self):
        """每个测试后重置单例"""
        DEManager.reset_instance()

    @pytest.mark.asyncio
    async def test_subscribe_to_get_account_balance_event(self):
        """测试DEManager订阅trading.get_account_balance事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 验证订阅了trading.get_account_balance事件
        subscribe_calls = [call[0][0] for call in event_bus.subscribe.call_args_list]
        assert DEEvents.INPUT_GET_ACCOUNT_BALANCE in subscribe_calls

    @pytest.mark.asyncio
    async def test_on_get_account_balance_success(self):
        """测试处理trading.get_account_balance事件成功"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 模拟账户已加载
        with patch.object(BinanceClient, '__init__', return_value=None):
            with patch.object(BinanceClient, 'get_account_balance', new_callable=AsyncMock) as mock_get_balance:
                mock_get_balance.return_value = {
                    "asset": "USDT",
                    "balance": "10000.00000000",
                    "availableBalance": "9500.00000000"
                }

                # 创建BinanceClient实例
                client = BinanceClient(user_id="user_001", api_key="test_key", api_secret="test_secret")
                manager._clients["user_001"] = client

                # 创建余额查询事件
                event = Event(
                    subject=DEEvents.INPUT_GET_ACCOUNT_BALANCE,
                    data={
                        "user_id": "user_001",
                        "asset": "USDT"
                    }
                )

                # 调用处理方法
                await manager._on_get_account_balance(event)

                # 验证调用了get_account_balance
                mock_get_balance.assert_called_once_with(asset="USDT")

                # 验证发布了de.account.balance事件
                assert event_bus.publish.called
                published_event = event_bus.publish.call_args[0][0]
                assert published_event.subject == DEEvents.ACCOUNT_BALANCE
                assert published_event.data["user_id"] == "user_001"
                assert published_event.data["asset"] == "USDT"
                assert published_event.data["available_balance"] == "9500.00000000"

    @pytest.mark.asyncio
    async def test_on_get_account_balance_client_not_found(self):
        """测试处理trading.get_account_balance事件时客户端不存在"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 创建余额查询事件（user_id不存在）
        event = Event(
            subject=DEEvents.INPUT_GET_ACCOUNT_BALANCE,
            data={
                "user_id": "user_999",
                "asset": "USDT"
            }
        )

        # 调用处理方法
        await manager._on_get_account_balance(event)

        # 验证没有发布任何事件（或者发布错误事件）
        # 这里我们选择不发布事件，只记录日志
        # 如果需要发布错误事件，可以修改实现
        # 暂时验证没有调用publish
        assert not event_bus.publish.called

    @pytest.mark.asyncio
    async def test_on_get_account_balance_api_error(self):
        """测试处理trading.get_account_balance事件时API错误"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        event_bus.publish = Mock()

        manager = DEManager.get_instance(event_bus=event_bus)

        # 模拟账户已加载
        with patch.object(BinanceClient, '__init__', return_value=None):
            with patch.object(BinanceClient, 'get_account_balance', new_callable=AsyncMock) as mock_get_balance:
                mock_get_balance.side_effect = Exception("API错误: 网络超时")

                # 创建BinanceClient实例
                client = BinanceClient(user_id="user_001", api_key="test_key", api_secret="test_secret")
                manager._clients["user_001"] = client

                # 创建余额查询事件
                event = Event(
                    subject=DEEvents.INPUT_GET_ACCOUNT_BALANCE,
                    data={
                        "user_id": "user_001",
                        "asset": "USDT"
                    }
                )

                # 调用处理方法
                await manager._on_get_account_balance(event)

                # 验证没有发布事件（错误只记录日志）
                assert not event_bus.publish.called
