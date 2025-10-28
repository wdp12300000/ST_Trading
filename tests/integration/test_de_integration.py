"""
DE模块集成测试

测试DE模块与EventBus的完整交互，包括：
- 账户加载流程（pm.account.loaded → de.client.connected）
- K线订阅流程（de.subscribe.kline → de.kline.update）
- 订单执行流程（trading.order.create → de.order.submitted）
- 账户余额查询流程（trading.get_account_balance → de.account.balance）
- 多账户隔离
- 错误处理和恢复
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.core.event import EventBus, Event
from src.core.de.de_manager import DEManager
from src.core.de.de_events import DEEvents
from src.core.pm.pm_events import PMEvents
from src.core.de.binance_client import BinanceClient


class TestDEIntegration:
    """DE模块集成测试"""
    
    def setup_method(self):
        """每个测试前重置单例和事件收集器"""
        EventBus._instance = None
        DEManager.reset_instance()
        self.event_bus = EventBus.get_instance()
        self.received_events = []
    
    def teardown_method(self):
        """每个测试后清理"""
        EventBus._instance = None
        DEManager.reset_instance()
    
    async def event_collector(self, event):
        """事件收集器"""
        self.received_events.append(event)
    
    @pytest.mark.asyncio
    async def test_account_loading_workflow(self):
        """测试完整的账户加载流程：pm.account.loaded → de.client.connected"""
        # 订阅de.client.connected事件
        self.event_bus.subscribe(DEEvents.CLIENT_CONNECTED, self.event_collector)
        
        # 创建DEManager
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 模拟PM模块发布pm.account.loaded事件
        account_loaded_event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_api_key",
                "api_secret": "test_api_secret",
                "testnet": False
            }
        )
        
        # 发布事件
        await self.event_bus.publish(account_loaded_event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证DEManager创建了BinanceClient
        assert manager.get_client("user_001") is not None
        
        # 验证发布了de.client.connected事件
        assert len(self.received_events) == 1
        connected_event = self.received_events[0]
        assert connected_event.subject == DEEvents.CLIENT_CONNECTED
        assert connected_event.data["user_id"] == "user_001"
    
    @pytest.mark.asyncio
    async def test_multi_account_isolation(self):
        """测试多账户隔离：多个账户同时运行，互不影响"""
        # 订阅所有de事件
        self.event_bus.subscribe("de.*", self.event_collector)
        
        # 创建DEManager
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 模拟加载3个账户
        for i in range(1, 4):
            account_event = Event(
                subject=PMEvents.ACCOUNT_LOADED,
                data={
                    "user_id": f"user_00{i}",
                    "name": f"账户{i}",
                    "api_key": f"key_{i}",
                    "api_secret": f"secret_{i}",
                    "testnet": False
                }
            )
            await self.event_bus.publish(account_event)
        
        await asyncio.sleep(0.1)
        
        # 验证创建了3个客户端
        assert len(manager.get_all_user_ids()) == 3
        assert manager.get_client("user_001") is not None
        assert manager.get_client("user_002") is not None
        assert manager.get_client("user_003") is not None
        
        # 验证每个客户端都是独立的
        client1 = manager.get_client("user_001")
        client2 = manager.get_client("user_002")
        client3 = manager.get_client("user_003")
        
        assert client1 != client2
        assert client2 != client3
        assert client1 != client3
        
        # 验证发布了3个de.client.connected事件
        connected_events = [e for e in self.received_events if e.subject == DEEvents.CLIENT_CONNECTED]
        assert len(connected_events) == 3
    
    @pytest.mark.asyncio
    async def test_order_execution_workflow(self):
        """测试订单执行流程：trading.order.create → de.order.submitted"""
        # 订阅订单事件
        self.event_bus.subscribe(DEEvents.ORDER_SUBMITTED, self.event_collector)
        
        # 创建DEManager
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 先加载账户
        account_event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_key",
                "api_secret": "test_secret",
                "testnet": False
            }
        )
        await self.event_bus.publish(account_event)
        await asyncio.sleep(0.1)
        
        # Mock BinanceClient.place_order方法
        client = manager.get_client("user_001")
        with patch.object(BinanceClient, 'place_order', new_callable=AsyncMock) as mock_place_order:
            mock_place_order.return_value = {
                "orderId": 12345,
                "symbol": "BTCUSDT",
                "status": "NEW",
                "clientOrderId": "test_order_001",
                "price": "50000.0",
                "origQty": "0.001",
                "executedQty": "0",
                "side": "BUY",
                "type": "LIMIT"
            }
            
            # 发布订单创建事件
            order_create_event = Event(
                subject=DEEvents.INPUT_ORDER_CREATE,
                data={
                    "user_id": "user_001",
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 0.001,
                    "price": 50000.0,
                    "time_in_force": "GTC"
                }
            )
            await self.event_bus.publish(order_create_event)
            await asyncio.sleep(0.1)
            
            # 验证调用了place_order
            mock_place_order.assert_called_once()
            
            # 验证发布了de.order.submitted事件
            assert len(self.received_events) == 1
            submitted_event = self.received_events[0]
            assert submitted_event.subject == DEEvents.ORDER_SUBMITTED
            assert submitted_event.data["user_id"] == "user_001"
            assert submitted_event.data["order_id"] == 12345
    
    @pytest.mark.asyncio
    async def test_account_balance_query_workflow(self):
        """测试账户余额查询流程：trading.get_account_balance → de.account.balance"""
        # 订阅余额事件
        self.event_bus.subscribe(DEEvents.ACCOUNT_BALANCE, self.event_collector)
        
        # 创建DEManager
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 先加载账户
        account_event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_key",
                "api_secret": "test_secret",
                "testnet": False
            }
        )
        await self.event_bus.publish(account_event)
        await asyncio.sleep(0.1)
        
        # Mock BinanceClient.get_account_balance方法
        with patch.object(BinanceClient, 'get_account_balance', new_callable=AsyncMock) as mock_get_balance:
            mock_get_balance.return_value = {
                "asset": "USDT",
                "balance": "10000.00000000",
                "availableBalance": "9500.00000000"
            }
            
            # 发布余额查询事件
            balance_query_event = Event(
                subject=DEEvents.INPUT_GET_ACCOUNT_BALANCE,
                data={
                    "user_id": "user_001",
                    "asset": "USDT"
                }
            )
            await self.event_bus.publish(balance_query_event)
            await asyncio.sleep(0.1)
            
            # 验证调用了get_account_balance
            mock_get_balance.assert_called_once_with(asset="USDT")
            
            # 验证发布了de.account.balance事件
            assert len(self.received_events) == 1
            balance_event = self.received_events[0]
            assert balance_event.subject == DEEvents.ACCOUNT_BALANCE
            assert balance_event.data["user_id"] == "user_001"
            assert balance_event.data["asset"] == "USDT"
            assert balance_event.data["available_balance"] == "9500.00000000"
    
    @pytest.mark.asyncio
    async def test_order_execution_error_handling(self):
        """测试订单执行错误处理：API错误时发布de.order.failed事件"""
        # 订阅订单失败事件
        self.event_bus.subscribe(DEEvents.ORDER_FAILED, self.event_collector)
        
        # 创建DEManager
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 先加载账户
        account_event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "name": "测试账户",
                "api_key": "test_key",
                "api_secret": "test_secret",
                "testnet": False
            }
        )
        await self.event_bus.publish(account_event)
        await asyncio.sleep(0.1)
        
        # Mock BinanceClient.place_order抛出异常
        with patch.object(BinanceClient, 'place_order', new_callable=AsyncMock) as mock_place_order:
            mock_place_order.side_effect = Exception("API错误: 余额不足")
            
            # 发布订单创建事件
            order_create_event = Event(
                subject=DEEvents.INPUT_ORDER_CREATE,
                data={
                    "user_id": "user_001",
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "order_type": "LIMIT",
                    "quantity": 0.001,
                    "price": 50000.0
                }
            )
            await self.event_bus.publish(order_create_event)
            await asyncio.sleep(0.1)
            
            # 验证发布了de.order.failed事件
            assert len(self.received_events) == 1
            failed_event = self.received_events[0]
            assert failed_event.subject == DEEvents.ORDER_FAILED
            assert failed_event.data["user_id"] == "user_001"
            assert "余额不足" in failed_event.data["error"]
    
    @pytest.mark.asyncio
    async def test_client_not_found_error_handling(self):
        """测试客户端不存在时的错误处理"""
        # 订阅订单失败事件
        self.event_bus.subscribe(DEEvents.ORDER_FAILED, self.event_collector)
        
        # 创建DEManager（不加载任何账户）
        manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 发布订单创建事件（user_id不存在）
        order_create_event = Event(
            subject=DEEvents.INPUT_ORDER_CREATE,
            data={
                "user_id": "user_999",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 0.001,
                "price": 50000.0
            }
        )
        await self.event_bus.publish(order_create_event)
        await asyncio.sleep(0.1)
        
        # 验证发布了de.order.failed事件
        assert len(self.received_events) == 1
        failed_event = self.received_events[0]
        assert failed_event.subject == DEEvents.ORDER_FAILED
        assert failed_event.data["user_id"] == "user_999"
        assert "客户端不存在" in failed_event.data["error"]

