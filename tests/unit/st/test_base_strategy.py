"""
BaseStrategy类单元测试

测试BaseStrategy抽象基类的功能，包括：
- 策略实例创建
- 持仓状态初始化
- 事件发布（strategy.loaded, indicator.subscribe）
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.core.st.base_strategy import BaseStrategy, PositionState
from src.core.st.st_events import STEvents
from src.core.event import Event


# 创建一个具体的策略类用于测试（因为BaseStrategy是抽象类）
class ConcreteStrategy(BaseStrategy):
    """测试用的具体策略类"""

    async def on_indicators_completed(self, symbol: str, indicators: dict):
        """实现抽象方法"""
        pass


class TestBaseStrategyCreation:
    """测试BaseStrategy的创建"""
    
    def test_create_strategy_instance(self):
        """测试创建策略实例"""
        event_bus = Mock()
        config = {
            "timeframe": "15m",
            "leverage": 4,
            "position_side": "BOTH",
            "margin_mode": "CROSS",
            "margin_type": "USDC",
            "reverse": True,
            "grid_trading": {"enabled": True, "ratio": 0.5, "grid_levels": 10},
            "trading_pairs": [
                {"symbol": "XRPUSDC", "indicator_params": {"ma_stop_ta": {"period": 3, "percent": 2}}}
            ]
        }
        
        # 创建策略实例
        strategy = ConcreteStrategy("user_001", config, event_bus)
        
        # 验证属性
        assert strategy._user_id == "user_001"
        assert strategy._config == config
        assert strategy._event_bus == event_bus
        assert isinstance(strategy._positions, dict)


class TestBaseStrategyPositionInitialization:
    """测试BaseStrategy的持仓状态初始化"""
    
    def test_position_initialization_single_pair(self):
        """测试单个交易对的持仓状态初始化为NONE"""
        event_bus = Mock()
        config = {
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        
        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 验证持仓状态初始化为NONE
        assert strategy.get_position("XRPUSDC") == PositionState.NONE

    def test_position_initialization_multiple_pairs(self):
        """测试多个交易对的持仓状态初始化"""
        event_bus = Mock()
        config = {
            "trading_pairs": [
                {"symbol": "XRPUSDC", "indicator_params": {}},
                {"symbol": "BTCUSDC", "indicator_params": {}},
                {"symbol": "ETHUSDC", "indicator_params": {}}
            ]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)
        
        # 验证所有交易对的持仓状态都初始化为NONE
        assert strategy.get_position("XRPUSDC") == PositionState.NONE
        assert strategy.get_position("BTCUSDC") == PositionState.NONE
        assert strategy.get_position("ETHUSDC") == PositionState.NONE


class TestBaseStrategyEventPublishing:
    """测试BaseStrategy的事件发布"""
    
    @pytest.mark.asyncio
    async def test_publish_strategy_loaded(self):
        """测试发布strategy.loaded事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        
        config = {
            "timeframe": "15m",
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        
        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 发布strategy.loaded事件
        await strategy._publish_strategy_loaded()
        
        # 验证事件发布
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]
        
        assert call_args.subject == STEvents.STRATEGY_LOADED
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["timeframe"] == "15m"
        assert "XRPUSDC" in call_args.data["trading_pairs"]
        assert call_args.source == "st"
    
    @pytest.mark.asyncio
    async def test_publish_indicator_subscriptions(self):
        """测试为每个交易对发布indicator.subscribe事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        config = {
            "timeframe": "15m",  # 添加timeframe配置
            "trading_pairs": [
                {
                    "symbol": "XRPUSDC",
                    "indicator_params": {
                        "ma_stop_ta": {"period": 3, "percent": 2}
                    }
                },
                {
                    "symbol": "BTCUSDC",
                    "indicator_params": {
                        "ma_stop_ta": {"period": 5, "percent": 3}
                    }
                }
            ]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 发布indicator.subscribe事件
        await strategy._publish_indicator_subscriptions()

        # 验证发布了2次事件（2个交易对）
        assert event_bus.publish.call_count == 2

        # 验证第一个事件
        first_call = event_bus.publish.call_args_list[0][0][0]
        assert first_call.subject == STEvents.INDICATOR_SUBSCRIBE
        assert first_call.data["user_id"] == "user_001"
        assert first_call.data["symbol"] == "XRPUSDC"
        assert first_call.data["indicator_name"] == "ma_stop_ta"
        assert first_call.data["indicator_params"] == {"period": 3, "percent": 2}
        assert first_call.data["timeframe"] == "15m"  # 验证timeframe字段

        # 验证第二个事件
        second_call = event_bus.publish.call_args_list[1][0][0]
        assert second_call.data["symbol"] == "BTCUSDC"
        assert second_call.data["indicator_params"] == {"period": 5, "percent": 3}
        assert second_call.data["timeframe"] == "15m"  # 验证timeframe字段


class TestBaseStrategySignalGeneration:
    """测试BaseStrategy的交易信号生成"""

    @pytest.mark.asyncio
    async def test_generate_open_long_signal(self):
        """测试生成开多仓信号"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        config = {
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 生成开多仓信号
        await strategy._generate_signal("XRPUSDC", "LONG", "OPEN")

        # 验证发布了signal.generated事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]

        assert call_args.subject == STEvents.SIGNAL_GENERATED
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "XRPUSDC"
        assert call_args.data["side"] == "LONG"
        assert call_args.data["action"] == "OPEN"
        assert call_args.source == "st"

    @pytest.mark.asyncio
    async def test_generate_close_short_signal(self):
        """测试生成平空仓信号"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        config = {
            "trading_pairs": [{"symbol": "BTCUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 生成平空仓信号
        await strategy._generate_signal("BTCUSDC", "SHORT", "CLOSE")

        # 验证发布了signal.generated事件
        call_args = event_bus.publish.call_args[0][0]

        assert call_args.data["symbol"] == "BTCUSDC"
        assert call_args.data["side"] == "SHORT"
        assert call_args.data["action"] == "CLOSE"


class TestBaseStrategyPositionUpdate:
    """测试BaseStrategy的持仓状态更新"""

    def test_update_position_to_long(self):
        """测试更新持仓状态为LONG"""
        event_bus = Mock()
        config = {
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 初始状态应该是NONE
        assert strategy.get_position("XRPUSDC") == PositionState.NONE

        # 更新为LONG
        strategy.update_position("XRPUSDC", PositionState.LONG)

        # 验证状态已更新
        assert strategy.get_position("XRPUSDC") == PositionState.LONG

    def test_update_position_to_short(self):
        """测试更新持仓状态为SHORT"""
        event_bus = Mock()
        config = {
            "trading_pairs": [{"symbol": "BTCUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 更新为SHORT
        strategy.update_position("BTCUSDC", PositionState.SHORT)

        # 验证状态已更新
        assert strategy.get_position("BTCUSDC") == PositionState.SHORT

    def test_update_position_to_none(self):
        """测试更新持仓状态为NONE"""
        event_bus = Mock()
        config = {
            "trading_pairs": [{"symbol": "ETHUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 先设置为LONG
        strategy.update_position("ETHUSDC", PositionState.LONG)
        assert strategy.get_position("ETHUSDC") == PositionState.LONG

        # 更新为NONE
        strategy.update_position("ETHUSDC", PositionState.NONE)

        # 验证状态已更新
        assert strategy.get_position("ETHUSDC") == PositionState.NONE


class TestBaseStrategyGridTrading:
    """测试BaseStrategy的网格交易功能"""

    @pytest.mark.asyncio
    async def test_grid_enabled_publishes_event(self):
        """测试网格交易启用时发布st.grid.create事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()  # 使用AsyncMock支持await
        config = {
            "grid_trading": {
                "enabled": True,
                "ratio": 0.5,
                "move_up": True,
                "move_down": False,
                "grid_levels": 10
            },
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓开启
        entry_price = 1.5
        await strategy.on_position_opened("XRPUSDC", "LONG", entry_price)

        # 验证发布了st.grid.create事件
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]

        assert call_args.subject == STEvents.GRID_CREATE
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "XRPUSDC"
        assert call_args.data["entry_price"] == 1.5
        assert call_args.data["grid_levels"] == 10
        assert call_args.data["grid_ratio"] == 0.5
        assert call_args.data["move_up"] is True
        assert call_args.data["move_down"] is False

    @pytest.mark.asyncio
    async def test_grid_disabled_no_event(self):
        """测试网格交易禁用时不发布事件"""
        event_bus = Mock()
        config = {
            "grid_trading": {
                "enabled": False,
                "ratio": 0.5,
                "grid_levels": 10
            },
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓开启
        await strategy.on_position_opened("XRPUSDC", "LONG", 1.5)

        # 验证没有发布事件
        event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_grid_not_configured_no_event(self):
        """测试未配置网格交易时不发布事件"""
        event_bus = Mock()
        config = {
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓开启
        await strategy.on_position_opened("XRPUSDC", "LONG", 1.5)

        # 验证没有发布事件
        event_bus.publish.assert_not_called()


class TestBaseStrategyReverseTrading:
    """测试BaseStrategy的反向建仓功能"""

    @pytest.mark.asyncio
    async def test_reverse_enabled_long_to_short(self):
        """测试反向建仓启用时，平多仓后开空仓"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        config = {
            "reverse": True,
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓关闭（平多仓）
        await strategy.on_position_closed("XRPUSDC", "LONG")

        # 验证发布了开空仓信号
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]

        assert call_args.subject == STEvents.SIGNAL_GENERATED
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "XRPUSDC"
        assert call_args.data["side"] == "SHORT"
        assert call_args.data["action"] == "OPEN"

    @pytest.mark.asyncio
    async def test_reverse_enabled_short_to_long(self):
        """测试反向建仓启用时，平空仓后开多仓"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        config = {
            "reverse": True,
            "trading_pairs": [{"symbol": "BTCUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓关闭（平空仓）
        await strategy.on_position_closed("BTCUSDC", "SHORT")

        # 验证发布了开多仓信号
        event_bus.publish.assert_called_once()
        call_args = event_bus.publish.call_args[0][0]

        assert call_args.subject == STEvents.SIGNAL_GENERATED
        assert call_args.data["user_id"] == "user_001"
        assert call_args.data["symbol"] == "BTCUSDC"
        assert call_args.data["side"] == "LONG"
        assert call_args.data["action"] == "OPEN"

    @pytest.mark.asyncio
    async def test_reverse_disabled_no_signal(self):
        """测试反向建仓禁用时不生成信号"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        config = {
            "reverse": False,
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓关闭
        await strategy.on_position_closed("XRPUSDC", "LONG")

        # 验证没有发布事件
        event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_reverse_not_configured_no_signal(self):
        """测试未配置reverse时不生成信号"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        config = {
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        strategy = ConcreteStrategy("user_001", config, event_bus)

        # 模拟持仓关闭
        await strategy.on_position_closed("XRPUSDC", "LONG")

        # 验证没有发布事件
        event_bus.publish.assert_not_called()

