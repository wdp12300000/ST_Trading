"""
利润计算器单元测试

测试ProfitCalculator的利润计算功能。
"""

import pytest
from src.core.tr.profit_calculator import ProfitCalculator


class TestProfitCalculatorCreation:
    """测试ProfitCalculator创建"""
    
    def test_create_profit_calculator(self):
        """测试创建利润计算器"""
        calculator = ProfitCalculator()
        assert calculator is not None
        assert calculator.DEFAULT_FEE_RATE == 0.0004


class TestOrderProfitCalculation:
    """测试单个订单利润计算"""
    
    def test_calculate_long_profit(self):
        """测试多头盈利"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_order_profit(
            entry_price=1.0,
            exit_price=1.05,
            quantity=100.0,
            side="LONG",
            fee_rate=0.0004
        )
        
        # 毛利 = (1.05 - 1.0) × 100 = 5.0
        # 手续费 = 1.0 × 100 × 0.0004 + 1.05 × 100 × 0.0004 = 0.082
        # 净利 = 5.0 - 0.082 = 4.918
        assert abs(profit - 4.918) < 0.001
    
    def test_calculate_long_loss(self):
        """测试多头亏损"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_order_profit(
            entry_price=1.05,
            exit_price=1.0,
            quantity=100.0,
            side="LONG",
            fee_rate=0.0004
        )
        
        # 应该是负数（亏损）
        assert profit < 0
    
    def test_calculate_short_profit(self):
        """测试空头盈利"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_order_profit(
            entry_price=1.05,
            exit_price=1.0,
            quantity=100.0,
            side="SHORT",
            fee_rate=0.0004
        )
        
        # 空头：入场价高于出场价，盈利
        assert profit > 0
    
    def test_calculate_short_loss(self):
        """测试空头亏损"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_order_profit(
            entry_price=1.0,
            exit_price=1.05,
            quantity=100.0,
            side="SHORT",
            fee_rate=0.0004
        )
        
        # 空头：入场价低于出场价，亏损
        assert profit < 0
    
    def test_calculate_profit_with_default_fee_rate(self):
        """测试使用默认手续费率"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_order_profit(
            entry_price=1.0,
            exit_price=1.05,
            quantity=100.0,
            side="LONG"
        )
        
        # 应该使用默认费率0.0004
        assert profit > 0
    
    def test_invalid_price(self):
        """测试无效价格"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_order_profit(0, 1.05, 100.0, "LONG")
    
    def test_invalid_quantity(self):
        """测试无效数量"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_order_profit(1.0, 1.05, 0, "LONG")
    
    def test_invalid_side(self):
        """测试无效方向"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_order_profit(1.0, 1.05, 100.0, "INVALID")


class TestGridPairProfitCalculation:
    """测试网格配对利润计算"""
    
    def test_calculate_grid_pair_profit(self):
        """测试网格配对利润"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_grid_pair_profit(
            buy_price=0.95,
            sell_price=1.05,
            quantity=100.0,
            fee_rate=0.0004
        )
        
        # 毛利 = (1.05 - 0.95) × 100 = 10.0
        # 手续费 = 0.95 × 100 × 0.0004 + 1.05 × 100 × 0.0004 = 0.08
        # 净利 = 10.0 - 0.08 = 9.92
        assert abs(profit - 9.92) < 0.001
    
    def test_calculate_grid_pair_loss(self):
        """测试网格配对亏损（买高卖低）"""
        calculator = ProfitCalculator()
        profit = calculator.calculate_grid_pair_profit(
            buy_price=1.05,
            sell_price=0.95,
            quantity=100.0,
            fee_rate=0.0004
        )
        
        # 买高卖低应该亏损
        assert profit < 0
    
    def test_grid_pair_invalid_price(self):
        """测试无效价格"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_grid_pair_profit(0, 1.05, 100.0)
    
    def test_grid_pair_invalid_quantity(self):
        """测试无效数量"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_grid_pair_profit(0.95, 1.05, 0)


class TestTotalProfitCalculation:
    """测试总盈亏计算"""
    
    def test_calculate_total_profit(self):
        """测试总盈亏计算"""
        calculator = ProfitCalculator()
        result = calculator.calculate_total_profit([10.0, -5.0, 8.0, -3.0, 15.0])
        
        assert result["total_profit"] == 25.0
        assert result["profit_count"] == 3
        assert result["loss_count"] == 2
        assert abs(result["win_rate"] - 0.6) < 0.001
    
    def test_calculate_total_profit_all_wins(self):
        """测试全部盈利"""
        calculator = ProfitCalculator()
        result = calculator.calculate_total_profit([10.0, 5.0, 8.0])
        
        assert result["total_profit"] == 23.0
        assert result["profit_count"] == 3
        assert result["loss_count"] == 0
        assert result["win_rate"] == 1.0
    
    def test_calculate_total_profit_all_losses(self):
        """测试全部亏损"""
        calculator = ProfitCalculator()
        result = calculator.calculate_total_profit([-10.0, -5.0, -8.0])
        
        assert result["total_profit"] == -23.0
        assert result["profit_count"] == 0
        assert result["loss_count"] == 3
        assert result["win_rate"] == 0.0
    
    def test_calculate_total_profit_empty_list(self):
        """测试空列表"""
        calculator = ProfitCalculator()
        result = calculator.calculate_total_profit([])
        
        assert result["total_profit"] == 0.0
        assert result["profit_count"] == 0
        assert result["loss_count"] == 0
        assert result["win_rate"] == 0.0


class TestFeeCalculation:
    """测试手续费计算"""
    
    def test_calculate_fee(self):
        """测试手续费计算"""
        calculator = ProfitCalculator()
        fee = calculator.calculate_fee(1.0, 100.0, 0.0004)
        
        assert abs(fee - 0.04) < 0.0001
    
    def test_calculate_fee_with_default_rate(self):
        """测试使用默认费率"""
        calculator = ProfitCalculator()
        fee = calculator.calculate_fee(1.0, 100.0)
        
        assert abs(fee - 0.04) < 0.0001


class TestROICalculation:
    """测试ROI计算"""
    
    def test_calculate_roi_positive(self):
        """测试正ROI"""
        calculator = ProfitCalculator()
        roi = calculator.calculate_roi(50.0, 1000.0)
        
        assert abs(roi - 0.05) < 0.0001  # 5%
    
    def test_calculate_roi_negative(self):
        """测试负ROI"""
        calculator = ProfitCalculator()
        roi = calculator.calculate_roi(-50.0, 1000.0)
        
        assert abs(roi - (-0.05)) < 0.0001  # -5%
    
    def test_calculate_roi_invalid_capital(self):
        """测试无效初始资金"""
        calculator = ProfitCalculator()
        with pytest.raises(ValueError):
            calculator.calculate_roi(50.0, 0)

