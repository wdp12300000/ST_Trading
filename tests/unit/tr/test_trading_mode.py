"""
交易模式单元测试

测试TradingTask的交易模式识别和相关功能。
"""

import pytest
from src.core.tr.trading_task import TradingTask, TradingMode, PositionState


class TestTradingModeDetection:
    """测试交易模式识别"""
    
    def test_no_grid_mode(self):
        """测试无网格模式识别"""
        config = {
            "grid_trading": {
                "enabled": False
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_trading_mode() == TradingMode.NO_GRID
        assert not task.is_grid_enabled()
        assert task.get_grid_ratio() == 1.0
    
    def test_normal_grid_mode(self):
        """测试普通网格模式识别"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "normal",
                "ratio": 1.0
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_trading_mode() == TradingMode.NORMAL_GRID
        assert task.is_grid_enabled()
        assert task.get_grid_ratio() == 1.0
    
    def test_abnormal_grid_mode(self):
        """测试特殊网格模式识别"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "abnormal",
                "ratio": 0.5
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_trading_mode() == TradingMode.ABNORMAL_GRID
        assert task.is_grid_enabled()
        assert task.get_grid_ratio() == 0.5
    
    def test_abnormal_grid_mode_with_ratio_less_than_1(self):
        """测试ratio<1时识别为特殊网格模式"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "normal",
                "ratio": 0.7
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        # 即使grid_type是normal，但ratio<1，也应识别为ABNORMAL_GRID
        assert task.get_trading_mode() == TradingMode.ABNORMAL_GRID
        assert task.get_grid_ratio() == 0.7
    
    def test_default_config(self):
        """测试默认配置（无grid_trading配置）"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_trading_mode() == TradingMode.NO_GRID
        assert not task.is_grid_enabled()


class TestGridConfiguration:
    """测试网格配置"""
    
    def test_set_grid_config(self):
        """测试设置网格配置"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "normal",
                "ratio": 1.0
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        task.set_grid_config(
            upper_price=1.05,
            lower_price=0.95,
            grid_levels=10,
            move_up=True,
            move_down=False
        )
        
        assert task.grid_config is not None
        assert task.grid_config["upper_price"] == 1.05
        assert task.grid_config["lower_price"] == 0.95
        assert task.grid_config["grid_levels"] == 10
        assert task.grid_config["move_up"] is True
        assert task.grid_config["move_down"] is False
        assert task.grid_upper_price == 1.05
        assert task.grid_lower_price == 0.95
    
    def test_grid_config_initially_none(self):
        """测试网格配置初始为None"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.grid_config is None
        assert task.grid_upper_price is None
        assert task.grid_lower_price is None


class TestPositionManagementEnhanced:
    """测试增强的持仓管理功能"""
    
    @pytest.mark.asyncio
    async def test_open_position_updates_state(self):
        """测试开启持仓更新状态"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        await task.open_position("LONG", 1.0, 100.0)
        
        assert task.is_position_open()
        assert task.get_position_state() == PositionState.LONG
        assert task.entry_price == 1.0
        assert task.entry_quantity == 100.0
        assert task.entry_side == "LONG"
        assert task.opened_at is not None
    
    @pytest.mark.asyncio
    async def test_open_short_position(self):
        """测试开启空头持仓"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        await task.open_position("SHORT", 1.0, 100.0)
        
        assert task.get_position_state() == PositionState.SHORT
        assert task.entry_side == "SHORT"
    
    @pytest.mark.asyncio
    async def test_close_position_updates_state(self):
        """测试关闭持仓更新状态"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        await task.open_position("LONG", 1.0, 100.0)
        pnl = await task.close_position(1.1)
        
        assert not task.is_position_open()
        assert task.get_position_state() == PositionState.NONE
        assert task.closed_at is not None
        assert pnl > 0  # 盈利
    
    @pytest.mark.asyncio
    async def test_cannot_open_position_twice(self):
        """测试不能重复开仓"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        await task.open_position("LONG", 1.0, 100.0)
        
        with pytest.raises(ValueError, match="持仓已存在"):
            await task.open_position("LONG", 1.1, 100.0)
    
    @pytest.mark.asyncio
    async def test_cannot_close_without_position(self):
        """测试没有持仓时不能平仓"""
        config = {}
        task = TradingTask("user_001", "XRPUSDC", config)
        
        with pytest.raises(ValueError, match="无持仓"):
            await task.close_position(1.0)


class TestTradingModeEnum:
    """测试TradingMode枚举"""
    
    def test_trading_mode_values(self):
        """测试交易模式枚举值"""
        assert TradingMode.NO_GRID.value == "NO_GRID"
        assert TradingMode.NORMAL_GRID.value == "NORMAL_GRID"
        assert TradingMode.ABNORMAL_GRID.value == "ABNORMAL_GRID"
    
    def test_trading_mode_comparison(self):
        """测试交易模式比较"""
        mode1 = TradingMode.NO_GRID
        mode2 = TradingMode.NO_GRID
        mode3 = TradingMode.NORMAL_GRID
        
        assert mode1 == mode2
        assert mode1 != mode3


class TestGridRatioCalculation:
    """测试网格资金比例计算"""
    
    def test_no_grid_ratio_is_1(self):
        """测试无网格模式ratio为1"""
        config = {
            "grid_trading": {
                "enabled": False
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_grid_ratio() == 1.0
    
    def test_normal_grid_ratio_is_1(self):
        """测试普通网格模式ratio为1"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "normal",
                "ratio": 1.0
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_grid_ratio() == 1.0
    
    def test_abnormal_grid_ratio_from_config(self):
        """测试特殊网格模式ratio从配置读取"""
        config = {
            "grid_trading": {
                "enabled": True,
                "grid_type": "abnormal",
                "ratio": 0.3
            }
        }
        task = TradingTask("user_001", "XRPUSDC", config)
        
        assert task.get_grid_ratio() == 0.3

