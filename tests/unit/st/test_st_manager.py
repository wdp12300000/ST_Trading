"""
STManager类单元测试

测试STManager类的完整功能，包括：
- 单例模式
- 配置文件加载
- 配置验证
- 策略实例创建和管理
- 事件订阅和处理
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, call
from src.core.st.st_manager import STManager
from src.core.st.st_events import STEvents
from src.core.event import Event


class TestSTManagerSingleton:
    """测试STManager的单例模式"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    def test_get_instance_creates_singleton(self):
        """测试get_instance创建单例 - 验证多次调用返回同一实例"""
        event_bus = Mock()

        # 多次调用 get_instance()
        manager1 = STManager.get_instance(event_bus=event_bus)
        manager2 = STManager.get_instance()

        # 验证是同一个对象
        assert manager1 is manager2
        # 验证 id 相同
        assert id(manager1) == id(manager2)

    def test_get_instance_requires_event_bus_on_first_call(self):
        """测试首次调用必须提供event_bus"""
        with pytest.raises(ValueError, match="首次调用必须提供event_bus"):
            STManager.get_instance()

    def test_reset_instance(self):
        """测试重置单例"""
        event_bus = Mock()

        manager1 = STManager.get_instance(event_bus=event_bus)
        STManager.reset_instance()
        manager2 = STManager.get_instance(event_bus=event_bus)

        # 重置后应该是不同的实例
        assert manager1 is not manager2


class TestSTManagerEventSubscription:
    """测试STManager的事件订阅"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    def test_subscribes_to_account_loaded_event(self):
        """测试STManager订阅了pm.account.loaded事件"""
        event_bus = Mock()

        # 创建STManager实例
        manager = STManager.get_instance(event_bus=event_bus)

        # 验证订阅了pm.account.loaded事件（第一次调用）
        first_call = event_bus.subscribe.call_args_list[0]
        assert first_call[0][0] == STEvents.INPUT_ACCOUNT_LOADED
        assert first_call[0][1] == manager._handle_account_loaded


class TestSTManagerConfigLoading:
    """测试STManager的配置加载"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    @pytest.mark.asyncio
    async def test_load_config_success(self):
        """测试成功加载策略配置文件"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 加载配置
        config = await manager._load_config("user_001", "ma_stop_st")

        # 验证配置加载成功
        assert config is not None
        assert "timeframe" in config
        assert "leverage" in config
        assert "trading_pairs" in config
        assert config["timeframe"] == "15m"
        assert config["leverage"] == 4

    @pytest.mark.asyncio
    async def test_load_config_file_not_found(self):
        """测试配置文件不存在"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 加载不存在的配置
        config = await manager._load_config("user_999", "nonexistent_strategy")

        # 验证返回None
        assert config is None


class TestSTManagerIndicatorHandling:
    """测试STManager的指标处理"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    def test_subscribes_to_indicators_completed_event(self):
        """测试STManager订阅了ta.calculation.completed事件"""
        event_bus = Mock()

        # 创建STManager实例
        manager = STManager.get_instance(event_bus=event_bus)

        # 验证订阅了ta.calculation.completed事件
        # subscribe应该被调用4次：pm.account.loaded, ta.calculation.completed, tr.position.opened, tr.position.closed
        assert event_bus.subscribe.call_count == 4

        # 验证第二次调用是订阅ta.calculation.completed
        second_call = event_bus.subscribe.call_args_list[1]
        assert second_call[0][0] == STEvents.INPUT_INDICATORS_COMPLETED
        assert second_call[0][1] == manager._handle_indicators_completed

    @pytest.mark.asyncio
    async def test_handle_indicators_calls_strategy(self):
        """测试处理指标完成事件时调用策略的on_indicators_completed方法"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.on_indicators_completed = AsyncMock()
        manager._strategies["user_001"] = mock_strategy

        # 创建指标完成事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "timeframe": "15m",
            "indicators": {
                "ma_stop_ta": {"signal": "LONG", "data": {"ma": 1.5}},
                "rsi_ta": {"signal": "SHORT", "data": {"value": 65}}
            }
        }

        # 处理事件
        await manager._handle_indicators_completed(event)

        # 验证调用了策略的on_indicators_completed方法
        mock_strategy.on_indicators_completed.assert_called_once_with(
            "XRPUSDC",
            {
                "ma_stop_ta": {"signal": "LONG", "data": {"ma": 1.5}},
                "rsi_ta": {"signal": "SHORT", "data": {"value": 65}}
            }
        )

    @pytest.mark.asyncio
    async def test_handle_indicators_user_not_found(self):
        """测试处理指标完成事件时用户不存在"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建指标完成事件（用户不存在）
        event = Mock()
        event.data = {
            "user_id": "user_999",
            "symbol": "XRPUSDC",
            "timeframe": "15m",
            "indicators": {}
        }

        # 处理事件（不应抛出异常）
        await manager._handle_indicators_completed(event)

        # 验证没有策略被调用（因为用户不存在）
        assert len(manager._strategies) == 0


class TestSTManagerPositionManagement:
    """测试STManager的持仓状态管理"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    def test_subscribes_to_position_opened_event(self):
        """测试STManager订阅了tr.position.opened事件"""
        event_bus = Mock()

        # 创建STManager实例
        manager = STManager.get_instance(event_bus=event_bus)

        # 验证订阅了tr.position.opened事件
        # subscribe应该被调用4次：pm.account.loaded, ta.calculation.completed, tr.position.opened, tr.position.closed
        assert event_bus.subscribe.call_count == 4

        # 验证第三次调用是订阅tr.position.opened
        third_call = event_bus.subscribe.call_args_list[2]
        assert third_call[0][0] == STEvents.INPUT_POSITION_OPENED
        assert third_call[0][1] == manager._handle_position_opened

    @pytest.mark.asyncio
    async def test_update_position_to_long(self):
        """测试持仓开启后更新状态为LONG"""
        from unittest.mock import AsyncMock
        from src.core.st.base_strategy import PositionState

        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.update_position = Mock()
        mock_strategy.on_position_opened = AsyncMock()  # 使用AsyncMock支持await
        manager._strategies["user_001"] = mock_strategy

        # 创建持仓开启事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "side": "LONG",
            "quantity": 100,
            "entry_price": 1.5
        }

        # 处理事件
        await manager._handle_position_opened(event)

        # 验证调用了策略的update_position方法
        mock_strategy.update_position.assert_called_once_with("XRPUSDC", PositionState.LONG)

    @pytest.mark.asyncio
    async def test_update_position_to_short(self):
        """测试持仓开启后更新状态为SHORT"""
        from unittest.mock import AsyncMock
        from src.core.st.base_strategy import PositionState

        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.update_position = Mock()
        mock_strategy.on_position_opened = AsyncMock()  # 使用AsyncMock支持await
        manager._strategies["user_001"] = mock_strategy

        # 创建持仓开启事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "BTCUSDC",
            "side": "SHORT",
            "quantity": 50,
            "entry_price": 50000
        }

        # 处理事件
        await manager._handle_position_opened(event)

        # 验证调用了策略的update_position方法
        mock_strategy.update_position.assert_called_once_with("BTCUSDC", PositionState.SHORT)

    def test_subscribes_to_position_closed_event(self):
        """测试STManager订阅了tr.position.closed事件"""
        event_bus = Mock()

        # 创建STManager实例
        manager = STManager.get_instance(event_bus=event_bus)

        # 验证订阅了tr.position.closed事件
        # subscribe应该被调用4次
        assert event_bus.subscribe.call_count == 4

        # 验证第四次调用是订阅tr.position.closed
        fourth_call = event_bus.subscribe.call_args_list[3]
        assert fourth_call[0][0] == STEvents.INPUT_POSITION_CLOSED
        assert fourth_call[0][1] == manager._handle_position_closed

    @pytest.mark.asyncio
    async def test_update_position_to_none(self):
        """测试持仓关闭后更新状态为NONE"""
        from unittest.mock import AsyncMock
        from src.core.st.base_strategy import PositionState

        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.update_position = Mock()
        mock_strategy.on_position_closed = AsyncMock()  # 使用AsyncMock支持await
        manager._strategies["user_001"] = mock_strategy

        # 创建持仓关闭事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "side": "LONG",
            "exit_price": 1.6,
            "pnl": 10.0
        }

        # 处理事件
        await manager._handle_position_closed(event)

        # 验证调用了策略的update_position方法
        mock_strategy.update_position.assert_called_once_with("XRPUSDC", PositionState.NONE)

    def test_validate_config_success(self):
        """测试配置验证成功"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        config = {
            "timeframe": "15m",
            "leverage": 4,
            "position_side": "BOTH",
            "margin_mode": "CROSS",
            "margin_type": "USDC",
            "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
        }

        # 验证配置
        result = manager._validate_config(config)

        # 验证通过
        assert result is True

    def test_validate_config_missing_field(self):
        """测试配置缺少必需字段"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        config = {"timeframe": "15m"}  # 缺少其他必需字段

        # 验证配置
        result = manager._validate_config(config)

        # 验证失败
        assert result is False

    def test_validate_config_empty_trading_pairs(self):
        """测试trading_pairs为空"""
        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        config = {
            "timeframe": "15m",
            "leverage": 4,
            "position_side": "BOTH",
            "margin_mode": "CROSS",
            "margin_type": "USDC",
            "trading_pairs": []  # 空数组
        }

        # 验证配置
        result = manager._validate_config(config)

        # 验证失败
        assert result is False


class TestSTManagerGridTrading:
    """测试STManager的网格交易功能"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    @pytest.mark.asyncio
    async def test_position_opened_triggers_grid_check(self):
        """测试持仓开启后触发网格交易检查"""
        from unittest.mock import AsyncMock

        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.update_position = Mock()
        mock_strategy.on_position_opened = AsyncMock()  # 使用AsyncMock支持await
        manager._strategies["user_001"] = mock_strategy

        # 创建持仓开启事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "side": "LONG",
            "quantity": 100,
            "entry_price": 1.5
        }

        # 处理事件
        await manager._handle_position_opened(event)

        # 验证调用了策略的on_position_opened方法
        mock_strategy.on_position_opened.assert_called_once_with("XRPUSDC", "LONG", 1.5)


class TestSTManagerReverseTrading:
    """测试STManager的反向建仓功能"""

    def teardown_method(self):
        """每个测试后重置单例"""
        STManager.reset_instance()

    @pytest.mark.asyncio
    async def test_position_closed_triggers_reverse_check(self):
        """测试持仓关闭后触发反向建仓检查"""
        from unittest.mock import AsyncMock

        event_bus = Mock()
        manager = STManager.get_instance(event_bus=event_bus)

        # 创建模拟策略实例
        mock_strategy = Mock()
        mock_strategy.update_position = Mock()
        mock_strategy.on_position_closed = AsyncMock()
        manager._strategies["user_001"] = mock_strategy

        # 创建持仓关闭事件
        event = Mock()
        event.data = {
            "user_id": "user_001",
            "symbol": "XRPUSDC",
            "side": "LONG",
            "exit_price": 1.6,
            "pnl": 10.0
        }

        # 处理事件
        await manager._handle_position_closed(event)

        # 验证调用了策略的on_position_closed方法
        mock_strategy.on_position_closed.assert_called_once_with("XRPUSDC", "LONG")

