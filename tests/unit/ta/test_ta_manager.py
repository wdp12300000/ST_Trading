"""
TAManager类单元测试

测试TAManager类的完整功能，包括：
- 单例模式
- 事件订阅
- 指标实例管理
- K线数据处理
- 指标聚合和事件发布

遵循TDD原则：先编写测试，再实现功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, call
from src.core.ta.ta_manager import TAManager
from src.core.ta.ta_events import TAEvents
from src.core.event import Event


class TestTAManagerSingleton:
    """测试TAManager的单例模式"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()
    
    def test_get_instance_creates_singleton(self):
        """测试get_instance创建单例 - 验证多次调用返回同一实例"""
        event_bus = Mock()
        
        # 多次调用 get_instance()
        manager1 = TAManager.get_instance(event_bus=event_bus)
        manager2 = TAManager.get_instance()
        
        # 验证是同一个对象
        assert manager1 is manager2
        # 验证 id 相同
        assert id(manager1) == id(manager2)
    
    def test_get_instance_requires_event_bus_on_first_call(self):
        """测试首次调用必须提供event_bus"""
        with pytest.raises(ValueError, match="首次调用必须提供event_bus"):
            TAManager.get_instance()
    
    def test_reset_instance(self):
        """测试重置单例"""
        event_bus = Mock()
        
        manager1 = TAManager.get_instance(event_bus=event_bus)
        TAManager.reset_instance()
        manager2 = TAManager.get_instance(event_bus=event_bus)
        
        # 重置后应该是不同的实例
        assert manager1 is not manager2


class TestTAManagerInitialization:
    """测试TAManager的初始化"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()
    
    def test_initialization_creates_empty_indicators_dict(self):
        """测试初始化时创建空的指标字典"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证指标字典为空
        assert hasattr(manager, '_indicators')
        assert isinstance(manager._indicators, dict)
        assert len(manager._indicators) == 0
    
    def test_initialization_creates_empty_aggregators_dict(self):
        """测试初始化时创建空的聚合器字典"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证聚合器字典为空
        assert hasattr(manager, '_aggregators')
        assert isinstance(manager._aggregators, dict)
        assert len(manager._aggregators) == 0
    
    def test_initialization_stores_event_bus(self):
        """测试初始化时存储事件总线引用"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证事件总线被存储
        assert hasattr(manager, '_event_bus')
        assert manager._event_bus is event_bus


class TestTAManagerEventSubscription:
    """测试TAManager的事件订阅"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()
    
    def test_subscribes_to_indicator_subscribe_event(self):
        """测试TAManager订阅了st.indicator.subscribe事件"""
        event_bus = Mock()
        
        # 创建TAManager实例
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证订阅了st.indicator.subscribe事件
        # subscribe应该被调用4次：
        # 1. st.indicator.subscribe
        # 2. de.historical_klines.success
        # 3. de.historical_klines.failed
        # 4. de.kline.update
        assert event_bus.subscribe.call_count == 4
        
        # 验证第一次调用是订阅st.indicator.subscribe
        first_call = event_bus.subscribe.call_args_list[0]
        assert first_call[0][0] == TAEvents.INPUT_INDICATOR_SUBSCRIBE
        assert first_call[0][1] == manager._handle_indicator_subscribe
    
    def test_subscribes_to_historical_klines_success_event(self):
        """测试TAManager订阅了de.historical_klines.success事件"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证第二次调用是订阅de.historical_klines.success
        second_call = event_bus.subscribe.call_args_list[1]
        assert second_call[0][0] == TAEvents.INPUT_HISTORICAL_KLINES_SUCCESS
        assert second_call[0][1] == manager._handle_historical_klines_success
    
    def test_subscribes_to_historical_klines_failed_event(self):
        """测试TAManager订阅了de.historical_klines.failed事件"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证第三次调用是订阅de.historical_klines.failed
        third_call = event_bus.subscribe.call_args_list[2]
        assert third_call[0][0] == TAEvents.INPUT_HISTORICAL_KLINES_FAILED
        assert third_call[0][1] == manager._handle_historical_klines_failed
    
    def test_subscribes_to_kline_update_event(self):
        """测试TAManager订阅了de.kline.update事件"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证第四次调用是订阅de.kline.update
        fourth_call = event_bus.subscribe.call_args_list[3]
        assert fourth_call[0][0] == TAEvents.INPUT_KLINE_UPDATE
        assert fourth_call[0][1] == manager._handle_kline_update


class TestTAManagerProperties:
    """测试TAManager的属性访问"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()
    
    def test_has_indicators_property(self):
        """测试TAManager有_indicators属性"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证有_indicators属性
        assert hasattr(manager, '_indicators')
    
    def test_has_aggregators_property(self):
        """测试TAManager有_aggregators属性"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证有_aggregators属性
        assert hasattr(manager, '_aggregators')
    
    def test_has_event_bus_property(self):
        """测试TAManager有_event_bus属性"""
        event_bus = Mock()
        
        manager = TAManager.get_instance(event_bus=event_bus)
        
        # 验证有_event_bus属性
        assert hasattr(manager, '_event_bus')


class TestTAManagerHandlerMethods:
    """测试TAManager的事件处理方法存在性"""

    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()

    def test_has_handle_indicator_subscribe_method(self):
        """测试TAManager有_handle_indicator_subscribe方法"""
        event_bus = Mock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 验证有_handle_indicator_subscribe方法
        assert hasattr(manager, '_handle_indicator_subscribe')
        assert callable(manager._handle_indicator_subscribe)

    def test_has_handle_historical_klines_success_method(self):
        """测试TAManager有_handle_historical_klines_success方法"""
        event_bus = Mock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 验证有_handle_historical_klines_success方法
        assert hasattr(manager, '_handle_historical_klines_success')
        assert callable(manager._handle_historical_klines_success)

    def test_has_handle_historical_klines_failed_method(self):
        """测试TAManager有_handle_historical_klines_failed方法"""
        event_bus = Mock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 验证有_handle_historical_klines_failed方法
        assert hasattr(manager, '_handle_historical_klines_failed')
        assert callable(manager._handle_historical_klines_failed)

    def test_has_handle_kline_update_method(self):
        """测试TAManager有_handle_kline_update方法"""
        event_bus = Mock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 验证有_handle_kline_update方法
        assert hasattr(manager, '_handle_kline_update')
        assert callable(manager._handle_kline_update)


class TestTAManagerIndicatorSubscription:
    """测试TAManager的指标订阅功能"""

    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()

    @pytest.mark.asyncio
    async def test_handle_indicator_subscribe_creates_indicator(self):
        """测试处理指标订阅事件时创建指标实例"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建指标订阅事件（包含timeframe字段）
        event = Event(
            subject=TAEvents.INPUT_INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {"period": 3, "percent": 2},
                "timeframe": "15m"
            },
            source="ST"
        )

        # Mock指标工厂
        with patch('src.core.ta.ta_manager.IndicatorFactory') as mock_factory:
            mock_indicator = Mock()
            mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
            mock_indicator.get_min_klines_required.return_value = 200
            mock_factory.create_indicator.return_value = mock_indicator

            # 处理事件
            await manager._handle_indicator_subscribe(event)

            # 验证指标被创建（包含interval参数）
            mock_factory.create_indicator.assert_called_once_with(
                user_id="user_001",
                symbol="XRPUSDC",
                interval="15m",
                indicator_name="ma_stop_ta",
                params={"period": 3, "percent": 2},
                event_bus=event_bus
            )

            # 验证指标被存储（ID包含interval）
            assert "user_001_XRPUSDC_15m_ma_stop_ta" in manager._indicators

    @pytest.mark.asyncio
    async def test_handle_indicator_subscribe_requests_historical_klines(self):
        """测试处理指标订阅事件时请求历史K线数据"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建指标订阅事件（包含timeframe字段）
        event = Event(
            subject=TAEvents.INPUT_INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {"period": 3, "percent": 2},
                "timeframe": "15m"
            },
            source="ST"
        )

        # Mock指标工厂
        with patch('src.core.ta.ta_manager.IndicatorFactory') as mock_factory:
            mock_indicator = Mock()
            mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
            mock_indicator.get_min_klines_required.return_value = 200
            mock_factory.create_indicator.return_value = mock_indicator

            # 处理事件
            await manager._handle_indicator_subscribe(event)

            # 验证发布了2个事件：历史K线请求 + 指标创建成功
            assert event_bus.publish.call_count == 2

            # 验证第一个事件是历史K线请求
            first_event = event_bus.publish.call_args_list[0][0][0]
            assert first_event.subject == "de.get_historical_klines"

            # 验证事件数据
            assert first_event.data["user_id"] == "user_001"
            assert first_event.data["symbol"] == "XRPUSDC"
            assert first_event.data["interval"] == "15m"  # 从事件数据获取
            assert first_event.data["limit"] == 200  # 从指标获取

    @pytest.mark.asyncio
    async def test_handle_indicator_subscribe_publishes_indicator_created_event(self):
        """测试处理指标订阅事件时发布指标创建成功事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建指标订阅事件（包含timeframe字段）
        event = Event(
            subject=TAEvents.INPUT_INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {"period": 3, "percent": 2},
                "timeframe": "15m"
            },
            source="ST"
        )

        # Mock指标工厂
        with patch('src.core.ta.ta_manager.IndicatorFactory') as mock_factory:
            mock_indicator = Mock()
            mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
            mock_indicator.get_min_klines_required.return_value = 200
            mock_factory.create_indicator.return_value = mock_indicator

            # 处理事件
            await manager._handle_indicator_subscribe(event)

            # 验证发布了两个事件：历史K线请求 + 指标创建成功
            assert event_bus.publish.call_count == 2

            # 第二个事件应该是指标创建成功事件
            second_event = event_bus.publish.call_args_list[1][0][0]
            assert second_event.subject == TAEvents.INDICATOR_CREATED
            assert second_event.data["user_id"] == "user_001"
            assert second_event.data["symbol"] == "XRPUSDC"
            assert second_event.data["indicator_name"] == "ma_stop_ta"
            assert second_event.data["indicator_id"] == "user_001_XRPUSDC_15m_ma_stop_ta"


class TestTAManagerHistoricalKlinesProcessing:
    """测试TAManager处理历史K线数据"""

    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()

    @pytest.mark.asyncio
    async def test_handle_historical_klines_success_calls_indicator_initialize(self):
        """测试处理历史K线成功事件时调用指标的initialize方法"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建Mock指标
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.initialize = AsyncMock()

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建历史K线成功事件
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True},
            {"open": "1.05", "high": "1.15", "low": "0.95", "close": "1.10", "volume": "2000", "timestamp": 1499050000000, "is_closed": True}
        ]

        event = Event(
            subject=TAEvents.INPUT_HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_historical_klines_success(event)

        # 验证调用了指标的initialize方法
        mock_indicator.initialize.assert_called_once_with(klines)

    @pytest.mark.asyncio
    async def test_handle_historical_klines_success_matches_correct_indicator(self):
        """测试历史K线数据匹配正确的指标"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建多个Mock指标
        mock_indicator_1 = Mock()
        mock_indicator_1.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator_1.get_user_id.return_value = "user_001"
        mock_indicator_1.get_symbol.return_value = "XRPUSDC"
        mock_indicator_1.get_interval.return_value = "15m"
        mock_indicator_1.initialize = AsyncMock()

        mock_indicator_2 = Mock()
        mock_indicator_2.get_indicator_id.return_value = "user_001_BTCUSDC_15m_ma_stop_ta"
        mock_indicator_2.get_user_id.return_value = "user_001"
        mock_indicator_2.get_symbol.return_value = "BTCUSDC"
        mock_indicator_2.get_interval.return_value = "15m"
        mock_indicator_2.initialize = AsyncMock()

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator_1
        manager._indicators["user_001_BTCUSDC_15m_ma_stop_ta"] = mock_indicator_2

        # 创建XRPUSDC的历史K线成功事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_historical_klines_success(event)

        # 验证只有XRPUSDC的指标被调用
        mock_indicator_1.initialize.assert_called_once_with(klines)
        mock_indicator_2.initialize.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_historical_klines_success_handles_exception(self):
        """测试处理历史K线时的异常处理"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建Mock指标（initialize抛出异常）
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.initialize = AsyncMock(side_effect=Exception("计算错误"))

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建历史K线成功事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件（不应该抛出异常）
        await manager._handle_historical_klines_success(event)

        # 验证调用了initialize方法
        mock_indicator.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_historical_klines_failed_logs_error(self):
        """测试处理历史K线失败事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建历史K线失败事件
        event = Event(
            subject=TAEvents.INPUT_HISTORICAL_KLINES_FAILED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "error": "API错误"
            },
            source="DE"
        )

        # 处理事件（不应该抛出异常）
        await manager._handle_historical_klines_failed(event)

        # 验证没有发布任何事件
        event_bus.publish.assert_not_called()


class TestTAManagerKlineUpdateProcessing:
    """测试TAManager处理实时K线更新"""

    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()

    @pytest.mark.asyncio
    async def test_handle_kline_update_calls_indicator_calculate(self):
        """测试处理K线更新事件时调用指标的calculate方法"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建Mock指标
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.is_ready.return_value = True
        mock_indicator.calculate = AsyncMock(return_value={"signal": "LONG", "data": {"ma": 1.05}})

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建K线更新事件（包含完整历史K线列表）
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True},
            {"open": "1.05", "high": "1.15", "low": "0.95", "close": "1.10", "volume": "2000", "timestamp": 1499050000000, "is_closed": True}
        ]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证调用了指标的calculate方法
        mock_indicator.calculate.assert_called_once_with(klines)

    @pytest.mark.asyncio
    async def test_handle_kline_update_filters_by_user_symbol_interval(self):
        """测试K线更新事件只触发匹配的指标"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建多个Mock指标
        mock_indicator_1 = Mock()
        mock_indicator_1.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator_1.get_user_id.return_value = "user_001"
        mock_indicator_1.get_symbol.return_value = "XRPUSDC"
        mock_indicator_1.get_interval.return_value = "15m"
        mock_indicator_1.is_ready.return_value = True
        mock_indicator_1.calculate = AsyncMock(return_value={"signal": "LONG", "data": {}})

        mock_indicator_2 = Mock()
        mock_indicator_2.get_indicator_id.return_value = "user_001_BTCUSDC_15m_ma_stop_ta"
        mock_indicator_2.get_user_id.return_value = "user_001"
        mock_indicator_2.get_symbol.return_value = "BTCUSDC"
        mock_indicator_2.get_interval.return_value = "15m"
        mock_indicator_2.is_ready.return_value = True
        mock_indicator_2.calculate = AsyncMock(return_value={"signal": "SHORT", "data": {}})

        mock_indicator_3 = Mock()
        mock_indicator_3.get_indicator_id.return_value = "user_001_XRPUSDC_1h_ma_stop_ta"
        mock_indicator_3.get_user_id.return_value = "user_001"
        mock_indicator_3.get_symbol.return_value = "XRPUSDC"
        mock_indicator_3.get_interval.return_value = "1h"
        mock_indicator_3.is_ready.return_value = True
        mock_indicator_3.calculate = AsyncMock(return_value={"signal": "NONE", "data": {}})

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator_1
        manager._indicators["user_001_BTCUSDC_15m_ma_stop_ta"] = mock_indicator_2
        manager._indicators["user_001_XRPUSDC_1h_ma_stop_ta"] = mock_indicator_3

        # 创建XRPUSDC 15m的K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证只有XRPUSDC 15m的指标被调用
        mock_indicator_1.calculate.assert_called_once_with(klines)
        mock_indicator_2.calculate.assert_not_called()
        mock_indicator_3.calculate.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_kline_update_skips_not_ready_indicators(self):
        """测试K线更新事件跳过未就绪的指标"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建Mock指标（未就绪）
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.is_ready.return_value = False  # 未就绪
        mock_indicator.calculate = AsyncMock()

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证未调用calculate方法
        mock_indicator.calculate.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_kline_update_handles_exception(self):
        """测试K线更新处理时的异常处理"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建Mock指标（calculate抛出异常）
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.is_ready.return_value = True
        mock_indicator.calculate = AsyncMock(side_effect=Exception("计算错误"))

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件（不应该抛出异常）
        await manager._handle_kline_update(event)

        # 验证调用了calculate方法
        mock_indicator.calculate.assert_called_once()


class TestTAManagerIndicatorAggregation:
    """测试TAManager的指标聚合功能"""

    def teardown_method(self):
        """每个测试后重置单例"""
        TAManager.reset_instance()

    @pytest.mark.asyncio
    async def test_aggregation_waits_for_all_indicators(self):
        """测试聚合器等待所有指标完成"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建两个Mock指标（同一交易对）
        mock_indicator_1 = Mock()
        mock_indicator_1.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator_1.get_user_id.return_value = "user_001"
        mock_indicator_1.get_symbol.return_value = "XRPUSDC"
        mock_indicator_1.get_interval.return_value = "15m"
        mock_indicator_1.get_indicator_name.return_value = "ma_stop_ta"
        mock_indicator_1.is_ready.return_value = True
        mock_indicator_1.calculate = AsyncMock(return_value={"signal": "LONG", "data": {"ma": 1.05}})

        mock_indicator_2 = Mock()
        mock_indicator_2.get_indicator_id.return_value = "user_001_XRPUSDC_15m_rsi_ta"
        mock_indicator_2.get_user_id.return_value = "user_001"
        mock_indicator_2.get_symbol.return_value = "XRPUSDC"
        mock_indicator_2.get_interval.return_value = "15m"
        mock_indicator_2.get_indicator_name.return_value = "rsi_ta"
        mock_indicator_2.is_ready.return_value = True
        mock_indicator_2.calculate = AsyncMock(return_value={"signal": "SHORT", "data": {"rsi": 70}})

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator_1
        manager._indicators["user_001_XRPUSDC_15m_rsi_ta"] = mock_indicator_2

        # 创建K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证两个指标都被调用
        mock_indicator_1.calculate.assert_called_once()
        mock_indicator_2.calculate.assert_called_once()

        # 验证发布了ta.calculation.completed事件
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]

        assert published_event.subject == TAEvents.CALCULATION_COMPLETED
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["symbol"] == "XRPUSDC"
        assert published_event.data["timeframe"] == "15m"
        assert "ma_stop_ta" in published_event.data["indicators"]
        assert "rsi_ta" in published_event.data["indicators"]
        assert published_event.data["indicators"]["ma_stop_ta"]["signal"] == "LONG"
        assert published_event.data["indicators"]["rsi_ta"]["signal"] == "SHORT"

    @pytest.mark.asyncio
    async def test_aggregation_only_for_same_trading_pair(self):
        """测试聚合器只聚合同一交易对的指标"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建两个不同交易对的指标
        mock_indicator_1 = Mock()
        mock_indicator_1.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator_1.get_user_id.return_value = "user_001"
        mock_indicator_1.get_symbol.return_value = "XRPUSDC"
        mock_indicator_1.get_interval.return_value = "15m"
        mock_indicator_1.get_indicator_name.return_value = "ma_stop_ta"
        mock_indicator_1.is_ready.return_value = True
        mock_indicator_1.calculate = AsyncMock(return_value={"signal": "LONG", "data": {}})

        mock_indicator_2 = Mock()
        mock_indicator_2.get_indicator_id.return_value = "user_001_BTCUSDC_15m_ma_stop_ta"
        mock_indicator_2.get_user_id.return_value = "user_001"
        mock_indicator_2.get_symbol.return_value = "BTCUSDC"
        mock_indicator_2.get_interval.return_value = "15m"
        mock_indicator_2.get_indicator_name.return_value = "ma_stop_ta"
        mock_indicator_2.is_ready.return_value = True
        mock_indicator_2.calculate = AsyncMock(return_value={"signal": "SHORT", "data": {}})

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator_1
        manager._indicators["user_001_BTCUSDC_15m_ma_stop_ta"] = mock_indicator_2

        # 创建XRPUSDC的K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证只有XRPUSDC的指标被调用
        mock_indicator_1.calculate.assert_called_once()
        mock_indicator_2.calculate.assert_not_called()

        # 验证发布了ta.calculation.completed事件（只包含XRPUSDC的指标）
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]

        assert published_event.data["symbol"] == "XRPUSDC"
        assert "ma_stop_ta" in published_event.data["indicators"]
        assert len(published_event.data["indicators"]) == 1

    @pytest.mark.asyncio
    async def test_aggregation_handles_single_indicator(self):
        """测试聚合器处理单个指标的情况"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        manager = TAManager.get_instance(event_bus=event_bus)

        # 创建单个指标
        mock_indicator = Mock()
        mock_indicator.get_indicator_id.return_value = "user_001_XRPUSDC_15m_ma_stop_ta"
        mock_indicator.get_user_id.return_value = "user_001"
        mock_indicator.get_symbol.return_value = "XRPUSDC"
        mock_indicator.get_interval.return_value = "15m"
        mock_indicator.get_indicator_name.return_value = "ma_stop_ta"
        mock_indicator.is_ready.return_value = True
        mock_indicator.calculate = AsyncMock(return_value={"signal": "LONG", "data": {}})

        # 将指标添加到管理器
        manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"] = mock_indicator

        # 创建K线更新事件
        klines = [{"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}]

        event = Event(
            subject=TAEvents.INPUT_KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="DE"
        )

        # 处理事件
        await manager._handle_kline_update(event)

        # 验证指标被调用
        mock_indicator.calculate.assert_called_once()

        # 验证发布了ta.calculation.completed事件
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]

        assert published_event.subject == TAEvents.CALCULATION_COMPLETED
        assert len(published_event.data["indicators"]) == 1
