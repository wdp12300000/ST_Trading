"""
BaseIndicator抽象基类单元测试

测试BaseIndicator抽象基类的功能，包括：
- 指标实例创建
- 最小K线数量属性
- 抽象方法定义
- K线数据处理
- 信号生成

遵循TDD原则：先编写测试，再实现功能
"""

import pytest
from unittest.mock import Mock, AsyncMock
from src.core.ta.base_indicator import BaseIndicator, IndicatorSignal
from src.core.event import EventBus


# 创建一个具体的指标类用于测试（因为BaseIndicator是抽象类）
class ConcreteIndicator(BaseIndicator):
    """测试用的具体指标类"""

    def __init__(self, user_id: str, symbol: str, interval: str, indicator_name: str,
                 params: dict, event_bus: EventBus):
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)
        self._min_klines_required = params.get("period", 20)  # 默认需要20根K线

    async def calculate(self, klines: list) -> dict:
        """实现抽象方法：计算指标（接收完整的历史K线列表）"""
        # 简单的测试实现：返回固定信号
        return {
            "signal": IndicatorSignal.LONG,
            "data": {"value": 100}
        }


class TestBaseIndicatorCreation:
    """测试BaseIndicator的创建"""
    
    def test_create_indicator_instance(self):
        """测试创建指标实例"""
        event_bus = Mock()
        params = {"period": 20, "percent": 2}

        # 创建指标实例
        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params=params,
            event_bus=event_bus
        )

        # 验证属性
        assert indicator._user_id == "user_001"
        assert indicator._symbol == "XRPUSDC"
        assert indicator._interval == "15m"
        assert indicator._indicator_name == "ma_stop_ta"
        assert indicator._params == params
        assert indicator._event_bus == event_bus
        assert indicator._is_ready == False  # 初始化时未就绪

    def test_indicator_id_generation(self):
        """测试指标实例ID生成：格式为 {user_id}_{symbol}_{interval}_{indicator_name}"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        # 验证ID格式（包含interval）
        expected_id = "user_001_XRPUSDC_15m_ma_stop_ta"
        assert indicator.get_indicator_id() == expected_id

    def test_different_indicators_have_different_ids(self):
        """测试不同指标实例有不同的ID"""
        event_bus = Mock()

        indicator1 = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        indicator2 = ConcreteIndicator(
            user_id="user_001",
            symbol="BTCUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        # 验证ID不同
        assert indicator1.get_indicator_id() != indicator2.get_indicator_id()


class TestBaseIndicatorMinKlinesRequired:
    """测试BaseIndicator的最小K线数量属性"""
    
    def test_min_klines_required_default(self):
        """测试最小K线数量默认值"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        # 验证默认值为20
        assert indicator.get_min_klines_required() == 20

    def test_min_klines_required_custom(self):
        """测试自定义最小K线数量"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={"period": 50},
            event_bus=event_bus
        )

        # 验证自定义值
        assert indicator.get_min_klines_required() == 50


class TestBaseIndicatorAbstractMethods:
    """测试BaseIndicator的抽象方法"""
    
    def test_calculate_method_is_abstract(self):
        """测试calculate方法是抽象方法"""
        # 尝试创建一个没有实现calculate方法的类
        class IncompleteIndicator(BaseIndicator):
            pass

        event_bus = Mock()

        # 应该抛出TypeError，因为没有实现抽象方法
        with pytest.raises(TypeError):
            IncompleteIndicator(
                user_id="user_001",
                symbol="XRPUSDC",
                interval="15m",
                indicator_name="test",
                params={},
                event_bus=event_bus
            )
    
    @pytest.mark.asyncio
    async def test_calculate_method_returns_result(self):
        """测试calculate方法返回计算结果"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        # 调用calculate方法（传入K线列表）
        klines = [
            {
                "open": "1.0",
                "high": "1.1",
                "low": "0.9",
                "close": "1.05",
                "volume": "1000",
                "timestamp": 1234567890,
                "is_closed": True
            }
        ]

        result = await indicator.calculate(klines)

        # 验证返回结果包含signal和data
        assert "signal" in result
        assert "data" in result
        assert result["signal"] == IndicatorSignal.LONG


class TestIndicatorSignalEnum:
    """测试IndicatorSignal枚举"""
    
    def test_signal_enum_values(self):
        """测试信号枚举的值"""
        assert IndicatorSignal.LONG.value == "LONG"
        assert IndicatorSignal.SHORT.value == "SHORT"
        assert IndicatorSignal.NONE.value == "NONE"
    
    def test_signal_enum_has_three_values(self):
        """测试信号枚举只有三个值"""
        signals = list(IndicatorSignal)
        assert len(signals) == 3


class TestBaseIndicatorProperties:
    """测试BaseIndicator的属性访问"""
    
    def test_get_user_id(self):
        """测试获取用户ID"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        assert indicator.get_user_id() == "user_001"

    def test_get_symbol(self):
        """测试获取交易对"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        assert indicator.get_symbol() == "XRPUSDC"

    def test_get_indicator_name(self):
        """测试获取指标名称"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        assert indicator.get_indicator_name() == "ma_stop_ta"

    def test_get_interval(self):
        """测试获取时间周期"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        assert indicator.get_interval() == "15m"

    def test_is_ready_initial_state(self):
        """测试指标初始状态为未就绪"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        assert indicator.is_ready() == False

    @pytest.mark.asyncio
    async def test_initialize_method(self):
        """测试initialize方法"""
        event_bus = Mock()

        indicator = ConcreteIndicator(
            user_id="user_001",
            symbol="XRPUSDC",
            interval="15m",
            indicator_name="ma_stop_ta",
            params={},
            event_bus=event_bus
        )

        # 初始状态未就绪
        assert indicator.is_ready() == False

        # 调用initialize方法
        historical_klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05",
             "volume": "1000", "timestamp": 1234567890, "is_closed": True}
        ]
        await indicator.initialize(historical_klines)

        # 初始化后应该就绪
        assert indicator.is_ready() == True

