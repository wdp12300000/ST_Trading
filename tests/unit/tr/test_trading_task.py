"""
TradingTask单元测试

测试TradingTask类的基本功能。
"""

import pytest
from src.core.tr.trading_task import TradingTask, PositionState, OrderInfo


class TestTradingTaskCreation:
    """测试TradingTask的创建"""
    
    def test_create_trading_task(self):
        """测试创建交易任务"""
        config = {"leverage": 4, "margin_type": "USDC"}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.user_id == "user_001"
        assert task.symbol == "XRPUSDC"
        assert task.strategy_config == config
        assert task.position_state == PositionState.NONE
        assert task.entry_price is None
        assert task.entry_quantity is None
        assert len(task.orders) == 0
        assert len(task.grid_orders) == 0
    
    def test_initial_position_state_is_none(self):
        """测试初始持仓状态为NONE"""
        task = TradingTask("user_001", "XRPUSDC", {})
        assert task.get_position_state() == PositionState.NONE
        assert task.is_position_open() is False


class TestPositionManagement:
    """测试持仓管理"""
    
    @pytest.mark.asyncio
    async def test_open_long_position(self):
        """测试开多头持仓"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("LONG", 1.0, 100)
        
        assert task.get_position_state() == PositionState.LONG
        assert task.is_position_open() is True
        assert task.entry_price == 1.0
        assert task.entry_quantity == 100
        assert task.entry_side == "LONG"
        assert task.opened_at is not None
    
    @pytest.mark.asyncio
    async def test_open_short_position(self):
        """测试开空头持仓"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("SHORT", 1.0, 100)
        
        assert task.get_position_state() == PositionState.SHORT
        assert task.is_position_open() is True
        assert task.entry_side == "SHORT"
    
    @pytest.mark.asyncio
    async def test_open_position_twice_raises_error(self):
        """测试重复开仓会抛出异常"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("LONG", 1.0, 100)
        
        with pytest.raises(ValueError, match="持仓已存在"):
            await task.open_position("LONG", 1.0, 100)
    
    @pytest.mark.asyncio
    async def test_close_long_position_with_profit(self):
        """测试平多头持仓（盈利）"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("LONG", 1.0, 100)

        # 出场价格高于入场价格，盈利
        pnl = await task.close_position(1.1)

        assert task.get_position_state() == PositionState.NONE
        assert task.is_position_open() is False
        # 毛利 = (1.1 - 1.0) × 100 = 10.0
        # 手续费 = 1.0 × 100 × 0.0004 + 1.1 × 100 × 0.0004 = 0.084
        # 净利 = 10.0 - 0.084 = 9.916
        assert abs(pnl - 9.916) < 0.001
        assert task.closed_at is not None

    @pytest.mark.asyncio
    async def test_close_long_position_with_loss(self):
        """测试平多头持仓（亏损）"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("LONG", 1.0, 100)

        # 出场价格低于入场价格，亏损
        pnl = await task.close_position(0.9)

        # 毛利 = (0.9 - 1.0) × 100 = -10.0
        # 手续费 = 1.0 × 100 × 0.0004 + 0.9 × 100 × 0.0004 = 0.076
        # 净利 = -10.0 - 0.076 = -10.076
        assert abs(pnl - (-10.076)) < 0.001

    @pytest.mark.asyncio
    async def test_close_short_position_with_profit(self):
        """测试平空头持仓（盈利）"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("SHORT", 1.0, 100)

        # 出场价格低于入场价格，盈利
        pnl = await task.close_position(0.9)

        # 毛利 = (1.0 - 0.9) × 100 = 10.0
        # 手续费 = 1.0 × 100 × 0.0004 + 0.9 × 100 × 0.0004 = 0.076
        # 净利 = 10.0 - 0.076 = 9.924
        assert abs(pnl - 9.924) < 0.001

    @pytest.mark.asyncio
    async def test_close_short_position_with_loss(self):
        """测试平空头持仓（亏损）"""
        task = TradingTask("user_001", "XRPUSDC", {})
        await task.open_position("SHORT", 1.0, 100)

        # 出场价格高于入场价格，亏损
        pnl = await task.close_position(1.1)

        # 毛利 = (1.0 - 1.1) × 100 = -10.0
        # 手续费 = 1.0 × 100 × 0.0004 + 1.1 × 100 × 0.0004 = 0.084
        # 净利 = -10.0 - 0.084 = -10.084
        assert abs(pnl - (-10.084)) < 0.001
    
    @pytest.mark.asyncio
    async def test_close_position_without_open_raises_error(self):
        """测试未开仓时平仓会抛出异常"""
        task = TradingTask("user_001", "XRPUSDC", {})
        
        with pytest.raises(ValueError, match="无持仓"):
            await task.close_position(1.0)


class TestOrderManagement:
    """测试订单管理"""
    
    def test_add_order(self):
        """测试添加订单"""
        task = TradingTask("user_001", "XRPUSDC", {})
        order = OrderInfo("12345", "XRPUSDC", "BUY", "MARKET", 1.0, 100)
        
        task.add_order(order)
        
        assert len(task.orders) == 1
        assert task.orders[0] == order
    
    def test_add_grid_order(self):
        """测试添加网格订单"""
        task = TradingTask("user_001", "XRPUSDC", {})
        order = OrderInfo("12345", "XRPUSDC", "BUY", "LIMIT", 1.0, 100)
        
        task.add_grid_order(order, pair_id="pair_001")
        
        assert len(task.orders) == 1
        assert len(task.grid_orders) == 1
        assert order.is_grid_order is True
        assert order.grid_pair_id == "pair_001"
        assert task.grid_orders["12345"] == order
    
    def test_get_order(self):
        """测试获取订单"""
        task = TradingTask("user_001", "XRPUSDC", {})
        order = OrderInfo("12345", "XRPUSDC", "BUY", "MARKET", 1.0, 100)
        task.add_order(order)
        
        found_order = task.get_order("12345")
        
        assert found_order == order
    
    def test_get_nonexistent_order_returns_none(self):
        """测试获取不存在的订单返回None"""
        task = TradingTask("user_001", "XRPUSDC", {})
        
        found_order = task.get_order("nonexistent")
        
        assert found_order is None
    
    def test_update_order_status(self):
        """测试更新订单状态"""
        task = TradingTask("user_001", "XRPUSDC", {})
        order = OrderInfo("12345", "XRPUSDC", "BUY", "MARKET", 1.0, 100)
        task.add_order(order)
        
        task.update_order_status("12345", "FILLED", 100)
        
        assert order.status == "FILLED"
        assert order.filled_quantity == 100
        assert order.filled_at is not None
    
    def test_get_grid_order_count(self):
        """测试获取网格订单数量"""
        task = TradingTask("user_001", "XRPUSDC", {})
        
        order1 = OrderInfo("12345", "XRPUSDC", "BUY", "LIMIT", 1.0, 100)
        order2 = OrderInfo("12346", "XRPUSDC", "SELL", "LIMIT", 1.1, 100)
        
        task.add_grid_order(order1)
        task.add_grid_order(order2)
        
        assert task.get_grid_order_count() == 2
    
    def test_clear_grid_orders(self):
        """测试清空网格订单"""
        task = TradingTask("user_001", "XRPUSDC", {})
        
        order = OrderInfo("12345", "XRPUSDC", "BUY", "LIMIT", 1.0, 100)
        task.add_grid_order(order)
        
        task.clear_grid_orders()
        
        assert len(task.grid_orders) == 0
        # 注意：orders列表不会被清空，只是grid_orders字典被清空
        assert len(task.orders) == 1


class TestOrderInfo:
    """测试OrderInfo类"""
    
    def test_create_order_info(self):
        """测试创建订单信息"""
        order = OrderInfo("12345", "XRPUSDC", "BUY", "MARKET", 1.0, 100)
        
        assert order.order_id == "12345"
        assert order.symbol == "XRPUSDC"
        assert order.side == "BUY"
        assert order.order_type == "MARKET"
        assert order.price == 1.0
        assert order.quantity == 100
        assert order.filled_quantity == 0.0
        assert order.status == "NEW"
        assert order.is_grid_order is False
        assert order.grid_pair_id is None
        assert order.created_at is not None
        assert order.filled_at is None

