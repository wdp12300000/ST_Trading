"""
OrderManager单元测试

测试OrderManager类的基本功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.core.tr.order_manager import OrderManager
from src.core.event.event_bus import EventBus
from src.core.tr.tr_events import TREvents


class TestOrderManagerCreation:
    """测试OrderManager的创建"""
    
    def test_create_order_manager(self):
        """测试创建订单管理器"""
        event_bus = Mock(spec=EventBus)
        order_manager = OrderManager(event_bus)
        
        assert order_manager is not None
        assert order_manager._event_bus == event_bus


class TestSubmitOrders:
    """测试提交订单"""
    
    @pytest.mark.asyncio
    async def test_submit_market_order(self):
        """测试提交市价单"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        await order_manager.submit_market_order("user_001", "XRPUSDC", "BUY", 100)
        
        # 验证发布了订单创建事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.subject == TREvents.ORDER_CREATE
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "XRPUSDC"
        assert call_args.data["side"] == "BUY"
        assert call_args.data["order_type"] == "MARKET"
        assert call_args.data["quantity"] == 100
    
    @pytest.mark.asyncio
    async def test_submit_limit_order(self):
        """测试提交限价单"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        await order_manager.submit_limit_order("user_001", "XRPUSDC", "BUY", 100, 1.0)
        
        # 验证发布了订单创建事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.subject == TREvents.ORDER_CREATE
        assert call_args.data["order_type"] == "LIMIT"
        assert call_args.data["price"] == 1.0
        assert call_args.data["quantity"] == 100
    
    @pytest.mark.asyncio
    async def test_submit_post_only_order(self):
        """测试提交POST_ONLY订单"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        await order_manager.submit_post_only_order("user_001", "XRPUSDC", "BUY", 100, 1.0)
        
        # 验证发布了订单创建事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.data["order_type"] == "POST_ONLY"
        assert call_args.data["price"] == 1.0


class TestCancelOrders:
    """测试撤销订单"""
    
    @pytest.mark.asyncio
    async def test_cancel_order(self):
        """测试撤销单个订单"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        await order_manager.cancel_order("user_001", "XRPUSDC", "12345")
        
        # 验证发布了订单撤销事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.subject == TREvents.ORDER_CANCEL
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "XRPUSDC"
        assert call_args.data["order_id"] == "12345"
    
    @pytest.mark.asyncio
    async def test_cancel_all_orders(self):
        """测试批量撤销订单"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        order_ids = ["12345", "12346", "12347"]
        await order_manager.cancel_all_orders("user_001", "XRPUSDC", order_ids)
        
        # 验证发布了3次撤销事件
        assert event_bus.publish.call_count == 3


class TestAccountBalance:
    """测试账户余额请求"""
    
    @pytest.mark.asyncio
    async def test_request_account_balance(self):
        """测试请求账户余额"""
        event_bus = Mock(spec=EventBus)
        event_bus.publish = AsyncMock()
        
        order_manager = OrderManager(event_bus)
        await order_manager.request_account_balance("user_001", "USDC")
        
        # 验证发布了余额请求事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.subject == TREvents.ACCOUNT_BALANCE_REQUEST
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["asset"] == "USDC"


class TestPrecisionHandling:
    """测试精度处理"""
    
    def test_round_price(self):
        """测试价格精度处理"""
        assert OrderManager.round_price(1.23456, 2) == 1.23
        assert OrderManager.round_price(1.23456, 4) == 1.2346
        assert OrderManager.round_price(1.23456, 0) == 1.0
    
    def test_round_quantity(self):
        """测试数量精度处理"""
        assert OrderManager.round_quantity(100.123, 0) == 100.0
        assert OrderManager.round_quantity(100.123, 2) == 100.12
        assert OrderManager.round_quantity(100.999, 0) == 101.0

