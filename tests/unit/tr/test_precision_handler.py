"""
PrecisionHandler单元测试

测试PrecisionHandler类的精度处理功能。
"""

import pytest
from src.core.tr.precision_handler import PrecisionHandler


class TestPrecisionHandlerCreation:
    """测试PrecisionHandler的创建"""
    
    def test_create_precision_handler(self):
        """测试创建精度处理器"""
        handler = PrecisionHandler()
        assert handler is not None


class TestSymbolPrecisionManagement:
    """测试交易对精度管理"""
    
    def test_set_symbol_precision(self):
        """测试设置交易对精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        price_prec, qty_prec, min_notional = handler.get_symbol_precision("XRPUSDC")
        assert price_prec == 4
        assert qty_prec == 0
        assert min_notional == 5.0
    
    def test_get_symbol_precision_default(self):
        """测试获取未设置的交易对精度（返回默认值）"""
        handler = PrecisionHandler()
        
        price_prec, qty_prec, min_notional = handler.get_symbol_precision("UNKNOWN")
        assert price_prec == handler.DEFAULT_PRICE_PRECISION
        assert qty_prec == handler.DEFAULT_QUANTITY_PRECISION
        assert min_notional == handler.DEFAULT_MIN_NOTIONAL


class TestPriceRounding:
    """测试价格精度处理"""
    
    def test_round_price_4_decimals(self):
        """测试4位小数精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0)
        
        price = handler.round_price("XRPUSDC", 1.23456)
        assert price == 1.2345
    
    def test_round_price_2_decimals(self):
        """测试2位小数精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("BTCUSDC", 2, 3)
        
        price = handler.round_price("BTCUSDC", 50000.123)
        assert price == 50000.12
    
    def test_round_price_0_decimals(self):
        """测试整数精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("TEST", 0, 0)
        
        price = handler.round_price("TEST", 123.456)
        assert price == 123.0
    
    def test_round_price_down(self):
        """测试价格向下取整"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0)
        
        # 1.23459 应该向下取整为 1.2345，而不是四舍五入为 1.2346
        price = handler.round_price("XRPUSDC", 1.23459)
        assert price == 1.2345


class TestQuantityRounding:
    """测试数量精度处理"""
    
    def test_round_quantity_0_decimals(self):
        """测试整数精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0)
        
        qty = handler.round_quantity("XRPUSDC", 100.123)
        assert qty == 100.0
    
    def test_round_quantity_2_decimals(self):
        """测试2位小数精度"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("BTCUSDC", 2, 2)
        
        qty = handler.round_quantity("BTCUSDC", 0.12345)
        assert qty == 0.12
    
    def test_round_quantity_down(self):
        """测试数量向下取整"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0)
        
        # 100.9 应该向下取整为 100.0
        qty = handler.round_quantity("XRPUSDC", 100.9)
        assert qty == 100.0


class TestMinNotionalValidation:
    """测试最小名义价值验证"""
    
    def test_validate_min_notional_valid(self):
        """测试满足最小名义价值"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        # 1.0 * 10.0 = 10.0 >= 5.0
        is_valid = handler.validate_min_notional("XRPUSDC", 1.0, 10.0)
        assert is_valid is True
    
    def test_validate_min_notional_invalid(self):
        """测试不满足最小名义价值"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        # 1.0 * 3.0 = 3.0 < 5.0
        is_valid = handler.validate_min_notional("XRPUSDC", 1.0, 3.0)
        assert is_valid is False
    
    def test_validate_min_notional_exact(self):
        """测试恰好等于最小名义价值"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        # 1.0 * 5.0 = 5.0 == 5.0
        is_valid = handler.validate_min_notional("XRPUSDC", 1.0, 5.0)
        assert is_valid is True


class TestOrderValidation:
    """测试订单验证"""
    
    def test_validate_order_valid(self):
        """测试有效订单"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        is_valid, error = handler.validate_order("XRPUSDC", 1.0, 10.0)
        assert is_valid is True
        assert error is None
    
    def test_validate_order_invalid_price(self):
        """测试无效价格"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        is_valid, error = handler.validate_order("XRPUSDC", 0, 10.0)
        assert is_valid is False
        assert "价格必须大于0" in error
    
    def test_validate_order_invalid_quantity(self):
        """测试无效数量"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        is_valid, error = handler.validate_order("XRPUSDC", 1.0, 0)
        assert is_valid is False
        assert "数量必须大于0" in error
    
    def test_validate_order_insufficient_notional(self):
        """测试名义价值不足"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        
        is_valid, error = handler.validate_order("XRPUSDC", 1.0, 3.0)
        assert is_valid is False
        assert "名义价值不足" in error


class TestProcessOrderParams:
    """测试订单参数处理"""
    
    def test_process_order_params(self):
        """测试处理订单参数"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("XRPUSDC", 4, 0)
        
        price, qty = handler.process_order_params("XRPUSDC", 1.23456, 100.123)
        
        assert price == 1.2345
        assert qty == 100.0
    
    def test_process_order_params_different_precision(self):
        """测试不同精度的订单参数处理"""
        handler = PrecisionHandler()
        handler.set_symbol_precision("BTCUSDC", 2, 3)
        
        price, qty = handler.process_order_params("BTCUSDC", 50000.123, 0.12345)
        
        assert price == 50000.12
        assert qty == 0.123

