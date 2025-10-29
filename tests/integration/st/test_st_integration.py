"""
ST模块集成测试

测试完整的事件流程、多策略隔离、错误处理等。
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from src.core.event.event import Event
from src.core.event.event_bus import EventBus
from src.core.st.st_manager import STManager
from src.core.st.base_strategy import BaseStrategy, PositionState
from src.core.st.st_events import STEvents


class TestStrategy(BaseStrategy):
    """测试用的具体策略实现"""
    
    async def on_indicators_completed(self, symbol: str, indicators: dict) -> None:
        """
        处理指标计算完成事件
        
        简单策略：如果所有指标都是LONG，则开多仓；如果所有指标都是SHORT，则开空仓。
        """
        # 检查所有指标信号
        signals = [ind.get("signal") for ind in indicators.values()]
        
        # 获取当前持仓
        current_position = self.get_position(symbol)
        
        # 所有指标都是LONG
        if all(s == "LONG" for s in signals):
            if current_position == PositionState.NONE:
                await self._generate_signal(symbol, "LONG", "OPEN")
            elif current_position == PositionState.SHORT:
                await self._generate_signal(symbol, "SHORT", "CLOSE")
        
        # 所有指标都是SHORT
        elif all(s == "SHORT" for s in signals):
            if current_position == PositionState.NONE:
                await self._generate_signal(symbol, "SHORT", "OPEN")
            elif current_position == PositionState.LONG:
                await self._generate_signal(symbol, "LONG", "CLOSE")


class TestSTIntegrationCompleteFlow:
    """测试完整事件流程"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_complete_flow_from_account_to_signal(self):
        """测试从账户加载到生成交易信号的完整流程"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 手动创建并注册策略实例（模拟账户加载）
        config = {
            "timeframe": "15m",
            "reverse": True,
            "grid_trading": {"enabled": True, "grid_levels": 10, "ratio": 0.5, "move_up": True, "move_down": False},
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        strategy = TestStrategy("user_001", config, event_bus)
        manager._strategies["user_001"] = strategy

        # 用于收集发布的事件
        published_events = []

        # 保存原始publish方法
        original_publish = event_bus.publish

        # 包装publish方法以收集事件
        async def wrapped_publish(event: Event):
            published_events.append(event)
            await original_publish(event)

        event_bus.publish = wrapped_publish

        # 1. 发布指标计算完成事件
        indicators_event = Event(
            subject="ta.calculation.completed",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "timeframe": "15m",
                "indicators": {
                    "ma_stop_ta": {"signal": "LONG", "data": {}},
                    "rsi_ta": {"signal": "LONG", "data": {}}
                }
            },
            source="ta"
        )
        await event_bus.publish(indicators_event)

        # 等待事件处理
        await asyncio.sleep(0.1)

        # 验证发布了signal.generated事件
        signal_events = [e for e in published_events if e.subject == STEvents.SIGNAL_GENERATED]
        assert len(signal_events) == 1
        assert signal_events[0].data["symbol"] == "XRPUSDC"
        assert signal_events[0].data["side"] == "LONG"
        assert signal_events[0].data["action"] == "OPEN"

        # 2. 发布持仓开启事件
        position_opened_event = Event(
            subject="tr.position.opened",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "quantity": 100,
                "entry_price": 1.5
            },
            source="tr"
        )
        await event_bus.publish(position_opened_event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证持仓状态已更新
        strategy = manager._strategies.get("user_001")
        assert strategy is not None
        assert strategy.get_position("XRPUSDC") == PositionState.LONG

        # 3. 发布持仓关闭事件
        position_closed_event = Event(
            subject="tr.position.closed",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "exit_price": 1.6,
                "pnl": 10.0
            },
            source="tr"
        )
        await event_bus.publish(position_closed_event)
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证持仓状态已更新为NONE
        assert strategy.get_position("XRPUSDC") == PositionState.NONE
    
    @pytest.mark.asyncio
    async def test_grid_trading_flow(self):
        """测试网格交易完整流程"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 手动创建并注册策略实例
        config = {
            "timeframe": "15m",
            "reverse": False,
            "grid_trading": {"enabled": True, "grid_levels": 10, "ratio": 0.5, "move_up": True, "move_down": False},
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        strategy = TestStrategy("user_001", config, event_bus)
        manager._strategies["user_001"] = strategy

        # 用于收集发布的事件
        published_events = []

        # 保存原始publish方法
        original_publish = event_bus.publish

        # 包装publish方法以收集事件
        async def wrapped_publish(event: Event):
            published_events.append(event)
            await original_publish(event)

        event_bus.publish = wrapped_publish

        # 1. 发布持仓开启事件（配置中启用了网格交易）
        position_opened_event = Event(
            subject="tr.position.opened",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "quantity": 100,
                "entry_price": 1.5
            },
            source="tr"
        )
        await event_bus.publish(position_opened_event)
        await asyncio.sleep(0.1)
        
        # 验证发布了grid.create事件
        grid_events = [e for e in published_events if e.subject == STEvents.GRID_CREATE]
        assert len(grid_events) == 1
        assert grid_events[0].data["symbol"] == "XRPUSDC"
        assert grid_events[0].data["entry_price"] == 1.5
        assert grid_events[0].data["grid_levels"] == 10
    
    @pytest.mark.asyncio
    async def test_reverse_trading_flow(self):
        """测试反向建仓完整流程"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 手动创建并注册策略实例
        config = {
            "timeframe": "15m",
            "reverse": True,
            "grid_trading": {"enabled": False},
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        strategy = TestStrategy("user_001", config, event_bus)
        manager._strategies["user_001"] = strategy

        # 用于收集发布的事件
        published_events = []

        # 保存原始publish方法
        original_publish = event_bus.publish

        # 包装publish方法以收集事件
        async def wrapped_publish(event: Event):
            published_events.append(event)
            await original_publish(event)

        event_bus.publish = wrapped_publish

        # 1. 发布持仓关闭事件（配置中启用了反向建仓）
        position_closed_event = Event(
            subject="tr.position.closed",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "exit_price": 1.6,
                "pnl": 10.0
            },
            source="tr"
        )
        await event_bus.publish(position_closed_event)
        await asyncio.sleep(0.1)
        
        # 验证发布了反向开仓信号
        signal_events = [e for e in published_events if e.subject == STEvents.SIGNAL_GENERATED]
        reverse_signals = [e for e in signal_events if e.data.get("side") == "SHORT" and e.data.get("action") == "OPEN"]
        assert len(reverse_signals) == 1
        assert reverse_signals[0].data["symbol"] == "XRPUSDC"


class TestSTIntegrationMultiStrategy:
    """测试多策略隔离"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self):
        """测试多个用户的策略互不干扰"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 手动创建并注册两个用户的策略实例
        config_1 = {
            "timeframe": "15m",
            "reverse": False,
            "grid_trading": {"enabled": False},
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        strategy_1 = TestStrategy("user_001", config_1, event_bus)
        manager._strategies["user_001"] = strategy_1

        config_2 = {
            "timeframe": "15m",
            "reverse": False,
            "grid_trading": {"enabled": False},
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }
        strategy_2 = TestStrategy("user_002", config_2, event_bus)
        manager._strategies["user_002"] = strategy_2

        # 验证两个策略都已加载
        assert "user_001" in manager._strategies
        assert "user_002" in manager._strategies
        assert manager._strategies["user_001"] != manager._strategies["user_002"]

        # 1. user_001开多仓
        position_opened_1 = Event(
            subject="tr.position.opened",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "quantity": 100,
                "entry_price": 1.5
            },
            source="tr"
        )
        await event_bus.publish(position_opened_1)
        await asyncio.sleep(0.1)

        # 2. user_002开空仓
        position_opened_2 = Event(
            subject="tr.position.opened",
            data={
                "user_id": "user_002",
                "symbol": "XRPUSDC",
                "side": "SHORT",
                "quantity": 50,
                "entry_price": 1.5
            },
            source="tr"
        )
        await event_bus.publish(position_opened_2)
        await asyncio.sleep(0.1)

        # 验证持仓状态隔离
        strategy_1 = manager._strategies["user_001"]
        strategy_2 = manager._strategies["user_002"]

        assert strategy_1.get_position("XRPUSDC") == PositionState.LONG
        assert strategy_2.get_position("XRPUSDC") == PositionState.SHORT

        # 3. user_001平仓
        position_closed_1 = Event(
            subject="tr.position.closed",
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "side": "LONG",
                "exit_price": 1.6,
                "pnl": 10.0
            },
            source="tr"
        )
        await event_bus.publish(position_closed_1)
        await asyncio.sleep(0.1)

        # 验证只有user_001的持仓被更新
        assert strategy_1.get_position("XRPUSDC") == PositionState.NONE
        assert strategy_2.get_position("XRPUSDC") == PositionState.SHORT  # 未变化


class TestSTIntegrationErrorHandling:
    """测试错误处理"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    @pytest.mark.asyncio
    async def test_handle_missing_user_id(self):
        """测试处理缺失user_id的事件"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 发布缺失user_id的指标事件
        indicators_event = Event(
            subject="ta.calculation.completed",
            data={
                # "user_id": "user_001",  # 缺失
                "symbol": "XRPUSDC",
                "timeframe": "15m",
                "indicators": {
                    "ma_stop_ta": {"signal": "LONG", "data": {}}
                }
            },
            source="ta"
        )

        # 不应该抛出异常
        await event_bus.publish(indicators_event)
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_handle_unknown_user(self):
        """测试处理未知用户的事件"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 发布未知用户的指标事件
        indicators_event = Event(
            subject="ta.calculation.completed",
            data={
                "user_id": "unknown_user",
                "symbol": "XRPUSDC",
                "timeframe": "15m",
                "indicators": {
                    "ma_stop_ta": {"signal": "LONG", "data": {}}
                }
            },
            source="ta"
        )

        # 不应该抛出异常
        await event_bus.publish(indicators_event)
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_handle_invalid_config(self):
        """测试处理无效配置文件"""
        # 创建EventBus
        event_bus = EventBus()

        # 创建STManager
        manager = STManager.get_instance(event_bus=event_bus)

        # 发布账户加载事件（配置文件不存在）
        account_event = Event(
            subject="pm.account.loaded",
            data={
                "user_id": "invalid_user",
                "strategy_name": "nonexistent_strategy"
            },
            source="pm"
        )

        # 不应该抛出异常
        await event_bus.publish(account_event)
        await asyncio.sleep(0.1)

        # 验证策略未加载
        assert "invalid_user" not in manager._strategies


