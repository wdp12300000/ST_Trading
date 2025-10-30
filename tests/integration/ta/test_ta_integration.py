"""
TA模块集成测试

测试TA模块与ST、DE模块的完整交互，包括：
- 指标订阅流程（st.indicator.subscribe → ta.indicator.created）
- 历史K线请求流程（ta → de.get_historical_klines → de.historical_klines.success）
- 指标初始化流程（历史K线 → 指标初始化）
- 实时K线处理流程（de.kline.update → ta.calculation.completed）
- 指标聚合流程（多个指标 → 统一发布）
- 多用户/多交易对隔离
- 错误处理和恢复
"""

import pytest
import asyncio
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from src.core.event import EventBus, Event
from src.core.ta.ta_manager import TAManager
from src.core.ta.ta_events import TAEvents
from src.core.st.st_events import STEvents
from src.core.de.de_events import DEEvents
from src.core.ta.base_indicator import BaseIndicator, IndicatorSignal
from src.core.ta.indicator_factory import IndicatorFactory


class TestIndicator(BaseIndicator):
    """测试用的指标实现"""

    def __init__(self, user_id: str, symbol: str, interval: str, indicator_name: str, params: Dict[str, Any], event_bus: EventBus):
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)

    async def calculate(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """简单返回LONG信号"""
        return {
            "signal": IndicatorSignal.LONG.value,
            "data": {"test": "data"}
        }


class MAStopIndicator(BaseIndicator):
    """MA Stop指标的测试实现"""

    def __init__(self, user_id: str, symbol: str, interval: str, indicator_name: str, params: Dict[str, Any], event_bus: EventBus):
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)

    async def calculate(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """简单返回LONG信号"""
        return {
            "signal": IndicatorSignal.LONG.value,
            "data": {"ma": 1.05}
        }


class RSIIndicator(BaseIndicator):
    """RSI指标的测试实现"""

    def __init__(self, user_id: str, symbol: str, interval: str, indicator_name: str, params: Dict[str, Any], event_bus: EventBus):
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)

    async def calculate(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """简单返回SHORT信号"""
        return {
            "signal": IndicatorSignal.SHORT.value,
            "data": {"rsi": 70}
        }


class TestTAIntegration:
    """TA模块集成测试"""
    
    def setup_method(self):
        """每个测试前的设置"""
        # 重置TAManager单例
        TAManager.reset_instance()

        # 创建EventBus（单例，不需要重置）
        self.event_bus = EventBus.get_instance()

        # 注册测试指标
        IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)
        IndicatorFactory.register_indicator("rsi_ta", RSIIndicator)
        IndicatorFactory.register_indicator("test_indicator", TestIndicator)

        # 用于收集事件
        self.received_events = []

    def teardown_method(self):
        """每个测试后的清理"""
        # 只重置TAManager，EventBus是全局单例
        TAManager.reset_instance()

        # 清空指标注册表
        IndicatorFactory._indicator_registry.clear()
    
    async def event_collector(self, event: Event):
        """事件收集器"""
        self.received_events.append(event)
    
    @pytest.mark.asyncio
    async def test_complete_indicator_subscription_flow(self):
        """
        测试完整的指标订阅流程
        
        流程：
        1. ST模块发布st.indicator.subscribe事件
        2. TA模块创建指标实例
        3. TA模块发布ta.indicator.created事件
        4. TA模块向DE模块请求历史K线（de.get_historical_klines）
        """
        # 订阅相关事件
        self.event_bus.subscribe(TAEvents.INDICATOR_CREATED, self.event_collector)
        self.event_bus.subscribe(DEEvents.INPUT_GET_HISTORICAL_KLINES, self.event_collector)
        
        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)
        
        # 模拟ST模块发布指标订阅事件
        subscribe_event = Event(
            subject=STEvents.INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {"period": 3, "percent": 2},
                "timeframe": "15m"
            },
            source="st"
        )
        
        await self.event_bus.publish(subscribe_event)
        await asyncio.sleep(0.1)
        
        # 验证ta.indicator.created事件
        created_events = [e for e in self.received_events if e.subject == TAEvents.INDICATOR_CREATED]
        assert len(created_events) == 1, "应该发布一个指标创建事件"
        
        created_event = created_events[0]
        assert created_event.data["user_id"] == "user_001"
        assert created_event.data["symbol"] == "XRPUSDC"
        assert created_event.data["indicator_name"] == "ma_stop_ta"
        assert created_event.data["indicator_id"] == "user_001_XRPUSDC_15m_ma_stop_ta"
        
        # 验证de.get_historical_klines事件
        kline_request_events = [e for e in self.received_events if e.subject == DEEvents.INPUT_GET_HISTORICAL_KLINES]
        assert len(kline_request_events) == 1, "应该发布一个历史K线请求事件"
        
        kline_request = kline_request_events[0]
        assert kline_request.data["user_id"] == "user_001"
        assert kline_request.data["symbol"] == "XRPUSDC"
        assert kline_request.data["interval"] == "15m"
        assert kline_request.data["limit"] == 200
    
    @pytest.mark.asyncio
    async def test_historical_klines_initialization_flow(self):
        """
        测试历史K线初始化流程
        
        流程：
        1. ST模块订阅指标
        2. TA模块请求历史K线
        3. DE模块返回历史K线（de.historical_klines.success）
        4. TA模块初始化指标
        """
        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)
        
        # 1. 模拟ST模块发布指标订阅事件
        subscribe_event = Event(
            subject=STEvents.INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {"period": 3, "percent": 2},
                "timeframe": "15m"
            },
            source="st"
        )
        
        await self.event_bus.publish(subscribe_event)
        await asyncio.sleep(0.1)
        
        # 验证指标已创建
        assert len(manager._indicators) == 1
        indicator_id = "user_001_XRPUSDC_15m_ma_stop_ta"
        assert indicator_id in manager._indicators
        
        # 验证指标未就绪
        indicator = manager._indicators[indicator_id]
        assert indicator.is_ready() is False
        
        # 2. 模拟DE模块返回历史K线
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True},
            {"open": "1.05", "high": "1.15", "low": "0.95", "close": "1.10", "volume": "2000", "timestamp": 1499050000000, "is_closed": True}
        ]
        
        historical_klines_event = Event(
            subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )
        
        await self.event_bus.publish(historical_klines_event)
        await asyncio.sleep(0.1)
        
        # 验证指标已就绪
        assert indicator.is_ready() is True
    
    @pytest.mark.asyncio
    async def test_realtime_kline_processing_and_aggregation_flow(self):
        """
        测试实时K线处理和指标聚合流程
        
        流程：
        1. ST模块订阅两个指标（同一交易对）
        2. DE模块返回历史K线，初始化指标
        3. DE模块发布实时K线更新（de.kline.update）
        4. TA模块计算所有指标
        5. TA模块聚合结果并发布ta.calculation.completed事件
        """
        # 订阅ta.calculation.completed事件
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)
        
        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)
        
        # 1. 订阅两个指标
        for indicator_name in ["ma_stop_ta", "rsi_ta"]:
            subscribe_event = Event(
                subject=STEvents.INDICATOR_SUBSCRIBE,
                data={
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "indicator_name": indicator_name,
                    "indicator_params": {},
                    "timeframe": "15m"
                },
                source="st"
            )
            await self.event_bus.publish(subscribe_event)
        
        await asyncio.sleep(0.1)
        
        # 验证两个指标已创建
        assert len(manager._indicators) == 2
        
        # 2. 初始化指标（模拟DE返回历史K线）
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True},
            {"open": "1.05", "high": "1.15", "low": "0.95", "close": "1.10", "volume": "2000", "timestamp": 1499050000000, "is_closed": True}
        ]
        
        historical_klines_event = Event(
            subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )
        
        await self.event_bus.publish(historical_klines_event)
        await asyncio.sleep(0.1)
        
        # 验证所有指标已就绪
        for indicator in manager._indicators.values():
            assert indicator.is_ready() is True
        
        # 清空事件列表
        self.received_events.clear()
        
        # 3. 模拟DE发布实时K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )
        
        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)
        
        # 4. 验证ta.calculation.completed事件
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "应该发布一个计算完成事件"
        
        completed_event = completed_events[0]
        assert completed_event.data["user_id"] == "user_001"
        assert completed_event.data["symbol"] == "XRPUSDC"
        assert completed_event.data["timeframe"] == "15m"
        assert "ma_stop_ta" in completed_event.data["indicators"]
        assert "rsi_ta" in completed_event.data["indicators"]
        
        # 验证指标结果包含signal字段
        assert "signal" in completed_event.data["indicators"]["ma_stop_ta"]
        assert "signal" in completed_event.data["indicators"]["rsi_ta"]

    @pytest.mark.asyncio
    async def test_multi_user_isolation(self):
        """
        测试多用户隔离

        验证：
        1. 不同用户的指标互不干扰
        2. 每个用户的K线更新只触发自己的指标计算
        3. 每个用户独立发布ta.calculation.completed事件
        """
        # 订阅ta.calculation.completed事件
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)

        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)

        # 1. 两个用户订阅相同的指标
        for user_id in ["user_001", "user_002"]:
            subscribe_event = Event(
                subject=STEvents.INDICATOR_SUBSCRIBE,
                data={
                    "user_id": user_id,
                    "symbol": "XRPUSDC",
                    "indicator_name": "ma_stop_ta",
                    "indicator_params": {},
                    "timeframe": "15m"
                },
                source="st"
            )
            await self.event_bus.publish(subscribe_event)

        await asyncio.sleep(0.1)

        # 验证两个指标已创建
        assert len(manager._indicators) == 2
        assert "user_001_XRPUSDC_15m_ma_stop_ta" in manager._indicators
        assert "user_002_XRPUSDC_15m_ma_stop_ta" in manager._indicators

        # 2. 初始化两个用户的指标
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}
        ]

        for user_id in ["user_001", "user_002"]:
            historical_klines_event = Event(
                subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
                data={
                    "user_id": user_id,
                    "symbol": "XRPUSDC",
                    "interval": "15m",
                    "klines": klines
                },
                source="de"
            )
            await self.event_bus.publish(historical_klines_event)

        await asyncio.sleep(0.1)

        # 清空事件列表
        self.received_events.clear()

        # 3. 只发布user_001的K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 4. 验证只有user_001的事件被发布
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "应该只发布一个计算完成事件"
        assert completed_events[0].data["user_id"] == "user_001"

    @pytest.mark.asyncio
    async def test_multi_symbol_isolation(self):
        """
        测试多交易对隔离

        验证：
        1. 同一用户的不同交易对指标互不干扰
        2. 每个交易对独立聚合和发布事件
        """
        # 订阅ta.calculation.completed事件
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)

        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)

        # 1. 订阅两个交易对的指标
        for symbol in ["XRPUSDC", "BTCUSDC"]:
            subscribe_event = Event(
                subject=STEvents.INDICATOR_SUBSCRIBE,
                data={
                    "user_id": "user_001",
                    "symbol": symbol,
                    "indicator_name": "ma_stop_ta",
                    "indicator_params": {},
                    "timeframe": "15m"
                },
                source="st"
            )
            await self.event_bus.publish(subscribe_event)

        await asyncio.sleep(0.1)

        # 验证两个指标已创建
        assert len(manager._indicators) == 2

        # 2. 初始化两个交易对的指标
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}
        ]

        for symbol in ["XRPUSDC", "BTCUSDC"]:
            historical_klines_event = Event(
                subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
                data={
                    "user_id": "user_001",
                    "symbol": symbol,
                    "interval": "15m",
                    "klines": klines
                },
                source="de"
            )
            await self.event_bus.publish(historical_klines_event)

        await asyncio.sleep(0.1)

        # 清空事件列表
        self.received_events.clear()

        # 3. 只发布XRPUSDC的K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 4. 验证只有XRPUSDC的事件被发布
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "应该只发布一个计算完成事件"
        assert completed_events[0].data["symbol"] == "XRPUSDC"

    @pytest.mark.asyncio
    async def test_historical_klines_failed_handling(self):
        """
        测试历史K线获取失败的处理

        验证：
        1. 收到de.historical_klines.failed事件时不会崩溃
        2. 指标保持未就绪状态
        3. 后续K线更新不会触发计算
        """
        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)

        # 1. 订阅指标
        subscribe_event = Event(
            subject=STEvents.INDICATOR_SUBSCRIBE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "indicator_name": "ma_stop_ta",
                "indicator_params": {},
                "timeframe": "15m"
            },
            source="st"
        )

        await self.event_bus.publish(subscribe_event)
        await asyncio.sleep(0.1)

        # 验证指标已创建但未就绪
        indicator_id = "user_001_XRPUSDC_15m_ma_stop_ta"
        assert indicator_id in manager._indicators
        assert manager._indicators[indicator_id].is_ready() is False

        # 2. 模拟DE返回失败事件
        failed_event = Event(
            subject=DEEvents.HISTORICAL_KLINES_FAILED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "error": "API rate limit exceeded"
            },
            source="de"
        )

        await self.event_bus.publish(failed_event)
        await asyncio.sleep(0.1)

        # 3. 验证指标仍未就绪
        assert manager._indicators[indicator_id].is_ready() is False

        # 4. 发布K线更新，验证不会触发计算
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)

        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}
        ]

        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 验证没有发布计算完成事件
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 0, "未就绪的指标不应该触发计算"

    @pytest.mark.asyncio
    async def test_partial_indicator_aggregation(self):
        """
        测试部分指标就绪时的聚合行为

        验证：
        1. 只有部分指标就绪时，K线更新只计算就绪的指标
        2. 只有所有指标都就绪后，才会发布聚合事件
        """
        # 订阅ta.calculation.completed事件
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)

        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)

        # 1. 订阅两个指标
        for indicator_name in ["ma_stop_ta", "rsi_ta"]:
            subscribe_event = Event(
                subject=STEvents.INDICATOR_SUBSCRIBE,
                data={
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "indicator_name": indicator_name,
                    "indicator_params": {},
                    "timeframe": "15m"
                },
                source="st"
            )
            await self.event_bus.publish(subscribe_event)

        await asyncio.sleep(0.1)

        # 2. 只初始化第一个指标
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}
        ]

        historical_klines_event = Event(
            subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        # 只初始化ma_stop_ta（通过修改指标ID匹配）
        # 实际上这个事件会初始化所有匹配的指标，所以我们需要手动设置状态
        indicator_ma = manager._indicators["user_001_XRPUSDC_15m_ma_stop_ta"]
        indicator_rsi = manager._indicators["user_001_XRPUSDC_15m_rsi_ta"]

        # 手动初始化ma_stop_ta
        await indicator_ma.initialize(klines)

        # 验证只有ma_stop_ta就绪
        assert indicator_ma.is_ready() is True
        assert indicator_rsi.is_ready() is False

        # 3. 发布K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 4. 验证没有发布聚合事件（因为rsi_ta未就绪）
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 0, "部分指标未就绪时不应该发布聚合事件"

        # 5. 初始化第二个指标
        await indicator_rsi.initialize(klines)
        assert indicator_rsi.is_ready() is True

        # 清空事件列表
        self.received_events.clear()

        # 6. 再次发布K线更新
        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 7. 验证现在发布了聚合事件
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "所有指标就绪后应该发布聚合事件"
        assert "ma_stop_ta" in completed_events[0].data["indicators"]
        assert "rsi_ta" in completed_events[0].data["indicators"]

    @pytest.mark.asyncio
    async def test_multi_interval_isolation(self):
        """
        测试多时间周期隔离

        验证：
        1. 同一交易对的不同时间周期指标互不干扰
        2. 每个时间周期独立聚合和发布事件
        """
        # 订阅ta.calculation.completed事件
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self.event_collector)

        # 创建TAManager
        manager = TAManager.get_instance(event_bus=self.event_bus)

        # 1. 订阅两个时间周期的指标
        for interval in ["15m", "1h"]:
            subscribe_event = Event(
                subject=STEvents.INDICATOR_SUBSCRIBE,
                data={
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "indicator_name": "ma_stop_ta",
                    "indicator_params": {},
                    "timeframe": interval
                },
                source="st"
            )
            await self.event_bus.publish(subscribe_event)

        await asyncio.sleep(0.1)

        # 验证两个指标已创建
        assert len(manager._indicators) == 2
        assert "user_001_XRPUSDC_15m_ma_stop_ta" in manager._indicators
        assert "user_001_XRPUSDC_1h_ma_stop_ta" in manager._indicators

        # 2. 初始化两个时间周期的指标
        klines = [
            {"open": "1.0", "high": "1.1", "low": "0.9", "close": "1.05", "volume": "1000", "timestamp": 1499040000000, "is_closed": True}
        ]

        for interval in ["15m", "1h"]:
            historical_klines_event = Event(
                subject=DEEvents.HISTORICAL_KLINES_SUCCESS,
                data={
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "interval": interval,
                    "klines": klines
                },
                source="de"
            )
            await self.event_bus.publish(historical_klines_event)

        await asyncio.sleep(0.1)

        # 清空事件列表
        self.received_events.clear()

        # 3. 只发布15m的K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 4. 验证只有15m的事件被发布
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "应该只发布一个计算完成事件"
        assert completed_events[0].data["timeframe"] == "15m"

        # 清空事件列表
        self.received_events.clear()

        # 5. 发布1h的K线更新
        kline_update_event = Event(
            subject=DEEvents.KLINE_UPDATE,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "1h",
                "klines": klines
            },
            source="de"
        )

        await self.event_bus.publish(kline_update_event)
        await asyncio.sleep(0.1)

        # 6. 验证只有1h的事件被发布
        completed_events = [e for e in self.received_events if e.subject == TAEvents.CALCULATION_COMPLETED]
        assert len(completed_events) == 1, "应该只发布一个计算完成事件"
        assert completed_events[0].data["timeframe"] == "1h"

