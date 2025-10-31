"""
网格计算器单元测试

测试GridCalculator的网格价格和数量计算功能。
"""

import pytest
from src.core.tr.grid_calculator import GridCalculator, GridOrder


class TestGridCalculatorCreation:
    """测试GridCalculator创建"""
    
    def test_create_grid_calculator(self):
        """测试创建网格计算器"""
        calculator = GridCalculator()
        assert calculator is not None


class TestPriceIntervalCalculation:
    """测试价格间隔计算"""
    
    def test_calculate_price_interval(self):
        """测试计算价格间隔"""
        calculator = GridCalculator()
        interval = calculator.calculate_price_interval(1.05, 0.95, 10)
        assert abs(interval - 0.01) < 0.0001
    
    def test_calculate_price_interval_different_range(self):
        """测试不同价格范围的间隔计算"""
        calculator = GridCalculator()
        interval = calculator.calculate_price_interval(2.0, 1.0, 20)
        assert abs(interval - 0.05) < 0.0001
    
    def test_calculate_price_interval_invalid_prices(self):
        """测试无效价格（上边价格小于等于下边价格）"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_price_interval(0.95, 1.05, 10)
    
    def test_calculate_price_interval_equal_prices(self):
        """测试相等价格"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_price_interval(1.0, 1.0, 10)
    
    def test_calculate_price_interval_invalid_levels(self):
        """测试无效网格层数"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_price_interval(1.05, 0.95, 0)


class TestGridPricesCalculation:
    """测试网格价格计算"""
    
    def test_calculate_grid_prices(self):
        """测试计算网格价格"""
        calculator = GridCalculator()
        prices = calculator.calculate_grid_prices(1.05, 0.95, 10)
        
        assert len(prices) == 11  # 10层网格有11个价格点
        assert abs(prices[0] - 0.95) < 0.0001
        assert abs(prices[-1] - 1.05) < 0.0001
    
    def test_calculate_grid_prices_spacing(self):
        """测试网格价格间隔均匀"""
        calculator = GridCalculator()
        prices = calculator.calculate_grid_prices(1.05, 0.95, 10)
        
        # 检查间隔是否均匀
        for i in range(len(prices) - 1):
            interval = prices[i + 1] - prices[i]
            assert abs(interval - 0.01) < 0.0001


class TestGridOrdersCalculation:
    """测试网格订单计算"""
    
    def test_calculate_grid_orders(self):
        """测试计算网格订单"""
        calculator = GridCalculator()
        orders = calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "BUY")
        
        assert len(orders) == 10
        assert all(isinstance(order, GridOrder) for order in orders)
        assert all(order.side == "BUY" for order in orders)
    
    def test_calculate_grid_orders_quantity_distribution(self):
        """测试网格订单数量分配"""
        calculator = GridCalculator()
        orders = calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "BUY")
        
        # 每个订单数量应该是100
        for order in orders:
            assert abs(order.quantity - 100.0) < 0.0001
    
    def test_calculate_grid_orders_sell_side(self):
        """测试卖单方向"""
        calculator = GridCalculator()
        orders = calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "SELL")
        
        assert all(order.side == "SELL" for order in orders)
    
    def test_calculate_grid_orders_invalid_quantity(self):
        """测试无效数量"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_grid_orders(1.05, 0.95, 10, 0, "BUY")
    
    def test_calculate_grid_orders_invalid_side(self):
        """测试无效订单方向"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "INVALID")


class TestSymmetricGridOrders:
    """测试对称网格订单"""
    
    def test_calculate_symmetric_grid_orders(self):
        """测试计算对称网格订单"""
        calculator = GridCalculator()
        orders = calculator.calculate_symmetric_grid_orders(1.0, 1.05, 0.95, 10, 1000.0)
        
        assert "buy_orders" in orders
        assert "sell_orders" in orders
        assert len(orders["buy_orders"]) > 0
        assert len(orders["sell_orders"]) > 0
    
    def test_symmetric_grid_orders_sides(self):
        """测试对称网格订单方向"""
        calculator = GridCalculator()
        orders = calculator.calculate_symmetric_grid_orders(1.0, 1.05, 0.95, 10, 1000.0)
        
        # 买单价格应该低于入场价格
        for order in orders["buy_orders"]:
            assert order.price < 1.0
            assert order.side == "BUY"
        
        # 卖单价格应该高于入场价格
        for order in orders["sell_orders"]:
            assert order.price > 1.0
            assert order.side == "SELL"
    
    def test_symmetric_grid_orders_quantity_distribution(self):
        """测试对称网格订单数量分配"""
        calculator = GridCalculator()
        orders = calculator.calculate_symmetric_grid_orders(1.0, 1.05, 0.95, 10, 1000.0)
        
        total_orders = len(orders["buy_orders"]) + len(orders["sell_orders"])
        expected_quantity = 1000.0 / total_orders
        
        # 检查每个订单的数量
        for order in orders["buy_orders"] + orders["sell_orders"]:
            assert abs(order.quantity - expected_quantity) < 0.0001
    
    def test_symmetric_grid_orders_invalid_entry_price(self):
        """测试无效入场价格（不在网格范围内）"""
        calculator = GridCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_symmetric_grid_orders(1.1, 1.05, 0.95, 10, 1000.0)


class TestGridOrder:
    """测试GridOrder数据类"""
    
    def test_create_grid_order(self):
        """测试创建GridOrder"""
        order = GridOrder(1.0, 100.0, "BUY", 0)
        
        assert order.price == 1.0
        assert order.quantity == 100.0
        assert order.side == "BUY"
        assert order.level == 0
    
    def test_grid_order_to_dict(self):
        """测试GridOrder转换为字典"""
        order = GridOrder(1.0, 100.0, "BUY", 0)
        data = order.to_dict()
        
        assert data["price"] == 1.0
        assert data["quantity"] == 100.0
        assert data["side"] == "BUY"
        assert data["level"] == 0

