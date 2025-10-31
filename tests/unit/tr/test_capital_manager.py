"""
CapitalManager单元测试

测试CapitalManager类的资金管理功能。
"""

import pytest
from src.core.tr.capital_manager import CapitalManager


class TestCapitalManagerCreation:
    """测试CapitalManager的创建"""
    
    def test_create_capital_manager(self):
        """测试创建资金管理器"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        assert capital_manager.user_id == "user_001"
        assert capital_manager.leverage == 4
        assert capital_manager.margin_type == "USDC"
        assert capital_manager.available_balance is None
        assert capital_manager.total_balance is None
    
    def test_get_leverage(self):
        """测试获取杠杆倍数"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        assert capital_manager.get_leverage() == 4
    
    def test_get_margin_type(self):
        """测试获取保证金类型"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        assert capital_manager.get_margin_type() == "USDC"


class TestBalanceManagement:
    """测试余额管理"""
    
    def test_update_balance(self):
        """测试更新余额"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0, 12000.0)
        
        assert capital_manager.available_balance == 10000.0
        assert capital_manager.total_balance == 12000.0
    
    def test_update_balance_without_total(self):
        """测试更新余额（不提供总余额）"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        assert capital_manager.available_balance == 10000.0
        assert capital_manager.total_balance == 10000.0
    
    def test_get_available_balance(self):
        """测试获取可用余额"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        assert capital_manager.get_available_balance() == 10000.0
    
    def test_get_available_balance_not_initialized(self):
        """测试获取未初始化的余额会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        with pytest.raises(ValueError, match="账户余额未初始化"):
            capital_manager.get_available_balance()
    
    def test_get_usable_balance(self):
        """测试获取可使用余额（应用安全系数）"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        usable = capital_manager.get_usable_balance()
        expected = 10000.0 * 0.95  # 9500.0
        
        assert abs(usable - expected) < 0.01


class TestMarginCalculation:
    """测试保证金计算"""
    
    def test_calculate_margin_per_symbol(self):
        """测试计算每个交易对的保证金"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        margin = capital_manager.calculate_margin_per_symbol(5)
        expected = 10000.0 * 0.95 / 5  # 1900.0
        
        assert abs(margin - expected) < 0.01
    
    def test_calculate_margin_with_zero_symbols_raises_error(self):
        """测试交易对数量为0会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        with pytest.raises(ValueError, match="交易对数量必须大于0"):
            capital_manager.calculate_margin_per_symbol(0)
    
    def test_calculate_margin_with_negative_symbols_raises_error(self):
        """测试交易对数量为负数会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        capital_manager.update_balance(10000.0)
        
        with pytest.raises(ValueError, match="交易对数量必须大于0"):
            capital_manager.calculate_margin_per_symbol(-1)


class TestPositionSizeCalculation:
    """测试仓位大小计算"""
    
    def test_calculate_position_size_full_ratio(self):
        """测试计算仓位大小（100%资金）"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        # 保证金2000，杠杆4x，入场价1.0，使用100%资金
        size = capital_manager.calculate_position_size(2000.0, 1.0, 1.0)
        expected = 2000.0 * 1.0 * 4 / 1.0  # 8000.0
        
        assert abs(size - expected) < 0.01
    
    def test_calculate_position_size_half_ratio(self):
        """测试计算仓位大小（50%资金）"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        # 保证金2000，杠杆4x，入场价1.0，使用50%资金
        size = capital_manager.calculate_position_size(2000.0, 1.0, 0.5)
        expected = 2000.0 * 0.5 * 4 / 1.0  # 4000.0
        
        assert abs(size - expected) < 0.01
    
    def test_calculate_position_size_different_price(self):
        """测试不同入场价格的仓位计算"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        # 保证金2000，杠杆4x，入场价2.0，使用100%资金
        size = capital_manager.calculate_position_size(2000.0, 2.0, 1.0)
        expected = 2000.0 * 1.0 * 4 / 2.0  # 4000.0
        
        assert abs(size - expected) < 0.01
    
    def test_calculate_position_size_invalid_margin(self):
        """测试无效保证金会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        with pytest.raises(ValueError, match="保证金必须大于0"):
            capital_manager.calculate_position_size(0, 1.0, 1.0)
    
    def test_calculate_position_size_invalid_price(self):
        """测试无效价格会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        with pytest.raises(ValueError, match="入场价格必须大于0"):
            capital_manager.calculate_position_size(2000.0, 0, 1.0)
    
    def test_calculate_position_size_invalid_ratio(self):
        """测试无效资金比例会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        with pytest.raises(ValueError, match="资金比例必须在"):
            capital_manager.calculate_position_size(2000.0, 1.0, 0)
        
        with pytest.raises(ValueError, match="资金比例必须在"):
            capital_manager.calculate_position_size(2000.0, 1.0, 1.5)


class TestGridPositionSizeCalculation:
    """测试网格仓位大小计算"""
    
    def test_calculate_grid_position_size(self):
        """测试计算网格仓位大小"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        # 保证金2000，杠杆4x，入场价1.0，10层网格
        size = capital_manager.calculate_grid_position_size(2000.0, 1.0, 10, 1.0)
        expected = 2000.0 * 1.0 * 4 / 1.0 / 10  # 800.0
        
        assert abs(size - expected) < 0.01
    
    def test_calculate_grid_position_size_with_ratio(self):
        """测试计算网格仓位大小（使用资金比例）"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        # 保证金2000，杠杆4x，入场价1.0，10层网格，使用50%资金
        size = capital_manager.calculate_grid_position_size(2000.0, 1.0, 10, 0.5)
        expected = 2000.0 * 0.5 * 4 / 1.0 / 10  # 400.0
        
        assert abs(size - expected) < 0.01
    
    def test_calculate_grid_position_size_invalid_levels(self):
        """测试无效网格层数会抛出异常"""
        capital_manager = CapitalManager("user_001", 4, "USDC")
        
        with pytest.raises(ValueError, match="网格层数必须大于0"):
            capital_manager.calculate_grid_position_size(2000.0, 1.0, 0, 1.0)

