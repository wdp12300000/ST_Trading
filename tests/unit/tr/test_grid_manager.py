"""
网格管理器单元测试

测试GridManager的网格订单创建和配对管理功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.tr.grid_manager import GridManager, GridPair
from src.core.event.event_bus import EventBus
from src.core.tr.order_manager import OrderManager
from src.core.tr.precision_handler import PrecisionHandler


@pytest.fixture
def event_bus():
    """创建事件总线mock"""
    bus = MagicMock(spec=EventBus)
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def order_manager(event_bus):
    """创建订单管理器mock"""
    manager = OrderManager(event_bus)
    manager.submit_limit_order = AsyncMock()
    manager.submit_post_only_order = AsyncMock()
    manager.cancel_all_orders = AsyncMock()
    return manager


@pytest.fixture
def precision_handler():
    """创建精度处理器"""
    handler = PrecisionHandler()
    handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
    return handler


@pytest.fixture
def grid_manager(event_bus, order_manager, precision_handler):
    """创建网格管理器"""
    return GridManager(event_bus, order_manager, precision_handler)


class TestGridManagerCreation:
    """测试GridManager创建"""
    
    def test_create_grid_manager(self, grid_manager):
        """测试创建网格管理器"""
        assert grid_manager is not None


class TestGridOrderCreation:
    """测试网格订单创建"""
    
    @pytest.mark.asyncio
    async def test_create_grid_orders(self, grid_manager, order_manager):
        """测试创建网格订单"""
        order_ids = await grid_manager.create_grid_orders(
            "user_001", "XRPUSDC", 1.05, 0.95, 10, 1000.0, "BUY"
        )
        
        assert len(order_ids) == 10
        assert order_manager.submit_limit_order.call_count == 10
    
    @pytest.mark.asyncio
    async def test_create_grid_orders_post_only(self, grid_manager, order_manager):
        """测试创建POST_ONLY网格订单"""
        order_ids = await grid_manager.create_grid_orders(
            "user_001", "XRPUSDC", 1.05, 0.95, 10, 1000.0, "BUY", "POST_ONLY"
        )
        
        assert len(order_ids) == 10
        assert order_manager.submit_post_only_order.call_count == 10
    
    @pytest.mark.asyncio
    async def test_create_symmetric_grid_orders(self, grid_manager, order_manager):
        """测试创建对称网格订单"""
        result = await grid_manager.create_symmetric_grid_orders(
            "user_001", "XRPUSDC", 1.0, 1.05, 0.95, 10, 1000.0
        )
        
        assert "buy_order_ids" in result
        assert "sell_order_ids" in result
        assert len(result["buy_order_ids"]) > 0
        assert len(result["sell_order_ids"]) > 0


class TestGridPairManagement:
    """测试网格配对管理"""
    
    def test_create_grid_pair(self, grid_manager):
        """测试创建网格配对"""
        pair_id = grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        
        assert pair_id is not None
        assert "XRPUSDC" in pair_id
    
    def test_update_grid_pair_order(self, grid_manager):
        """测试更新网格配对订单"""
        pair_id = grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        
        grid_manager.update_grid_pair_order("XRPUSDC", pair_id, "order_123", "BUY")
        grid_manager.update_grid_pair_order("XRPUSDC", pair_id, "order_456", "SELL")
        
        pairs = grid_manager.get_grid_pairs("XRPUSDC")
        assert pairs[pair_id].buy_order_id == "order_123"
        assert pairs[pair_id].sell_order_id == "order_456"
    
    def test_mark_pair_completed(self, grid_manager):
        """测试标记配对完成"""
        pair_id = grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        
        profit = grid_manager.mark_pair_completed("XRPUSDC", pair_id)
        
        assert profit is not None
        assert profit > 0  # 买0.95卖1.05应该有利润
    
    def test_get_grid_pairs(self, grid_manager):
        """测试获取网格配对"""
        grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        grid_manager.create_grid_pair("XRPUSDC", 0.96, 1.06, 100.0)
        
        pairs = grid_manager.get_grid_pairs("XRPUSDC")
        
        assert len(pairs) == 2
    
    def test_clear_grid_pairs(self, grid_manager):
        """测试清除网格配对"""
        grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        grid_manager.create_grid_pair("XRPUSDC", 0.96, 1.06, 100.0)
        
        grid_manager.clear_grid_pairs("XRPUSDC")
        
        pairs = grid_manager.get_grid_pairs("XRPUSDC")
        assert len(pairs) == 0


class TestGridPair:
    """测试GridPair数据类"""
    
    def test_create_grid_pair(self):
        """测试创建GridPair"""
        pair = GridPair("pair_001", 0.95, 1.05, 100.0)
        
        assert pair.pair_id == "pair_001"
        assert pair.buy_price == 0.95
        assert pair.sell_price == 1.05
        assert pair.quantity == 100.0
        assert pair.is_completed is False
    
    def test_set_buy_order(self):
        """测试设置买单订单ID"""
        pair = GridPair("pair_001", 0.95, 1.05, 100.0)
        pair.set_buy_order("order_123")
        
        assert pair.buy_order_id == "order_123"
    
    def test_set_sell_order(self):
        """测试设置卖单订单ID"""
        pair = GridPair("pair_001", 0.95, 1.05, 100.0)
        pair.set_sell_order("order_456")
        
        assert pair.sell_order_id == "order_456"
    
    def test_mark_completed(self):
        """测试标记完成"""
        pair = GridPair("pair_001", 0.95, 1.05, 100.0)
        pair.mark_completed()
        
        assert pair.is_completed is True
    
    def test_calculate_profit(self):
        """测试计算利润"""
        pair = GridPair("pair_001", 0.95, 1.05, 100.0)
        profit = pair.calculate_profit(fee_rate=0.0004)
        
        # 利润 = (1.05 - 0.95) × 100 - 手续费
        # 手续费 = 0.95 × 100 × 0.0004 + 1.05 × 100 × 0.0004
        expected_gross = (1.05 - 0.95) * 100.0
        expected_fee = 0.95 * 100.0 * 0.0004 + 1.05 * 100.0 * 0.0004
        expected_profit = expected_gross - expected_fee
        
        assert abs(profit - expected_profit) < 0.0001
    
    def test_calculate_profit_with_loss(self):
        """测试计算亏损"""
        pair = GridPair("pair_001", 1.05, 0.95, 100.0)
        profit = pair.calculate_profit(fee_rate=0.0004)
        
        # 买高卖低应该亏损
        assert profit < 0


class TestGridOrderCancellation:
    """测试网格订单撤销"""
    
    @pytest.mark.asyncio
    async def test_cancel_all_grid_orders(self, grid_manager, order_manager):
        """测试撤销所有网格订单"""
        # 先创建一些配对
        grid_manager.create_grid_pair("XRPUSDC", 0.95, 1.05, 100.0)
        grid_manager.create_grid_pair("XRPUSDC", 0.96, 1.06, 100.0)
        
        # 撤销订单
        order_ids = ["order_1", "order_2", "order_3"]
        await grid_manager.cancel_all_grid_orders("user_001", "XRPUSDC", order_ids)
        
        # 验证订单管理器被调用
        order_manager.cancel_all_orders.assert_called_once_with(
            "user_001", "XRPUSDC", order_ids
        )
        
        # 验证配对被清除
        pairs = grid_manager.get_grid_pairs("XRPUSDC")
        assert len(pairs) == 0

