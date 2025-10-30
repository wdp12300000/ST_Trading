"""
DEManager历史K线功能单元测试

测试DEManager处理历史K线请求的功能，包括：
- 订阅de.get_historical_klines事件
- 调用BinanceClient获取历史K线
- 转换K线格式（币安格式 → 标准格式）
- 发布de.historical_klines.success事件
- 发布de.historical_klines.failed事件

遵循TDD原则：先编写测试，再实现功能
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.de.de_manager import DEManager
from src.core.de.de_events import DEEvents
from src.core.event import Event, EventBus


class TestDEManagerHistoricalKlinesSubscription:
    """测试DEManager订阅历史K线请求事件"""
    
    def test_subscribes_to_get_historical_klines_event(self):
        """测试DEManager订阅de.get_historical_klines事件"""
        event_bus = Mock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # 验证订阅了de.get_historical_klines事件
        subscribe_calls = [call[0] for call in event_bus.subscribe.call_args_list]
        assert (DEEvents.INPUT_GET_HISTORICAL_KLINES, manager._on_get_historical_klines) in subscribe_calls


class TestDEManagerHistoricalKlinesProcessing:
    """测试DEManager处理历史K线请求"""
    
    @pytest.mark.asyncio
    async def test_handle_get_historical_klines_success(self):
        """测试成功获取历史K线"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # Mock BinanceClient
        mock_client = Mock()
        mock_client.get_historical_klines = AsyncMock(return_value=[
            [
                1499040000000,      # 开盘时间
                "0.01634000",       # 开盘价
                "0.80000000",       # 最高价
                "0.01575800",       # 最低价
                "0.01577100",       # 收盘价
                "148976.11427815",  # 成交量
                1499644799999,      # 收盘时间
                "2434.19055334",    # 成交额
                308,                # 成交笔数
                "1756.87402397",    # 主动买入成交量
                "28.46694368",      # 主动买入成交额
                "17928899.62484339" # 忽略
            ]
        ])
        manager._clients["user_001"] = mock_client
        
        # 创建历史K线请求事件
        event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "limit": 200
            },
            source="TA"
        )
        
        # 处理事件
        await manager._on_get_historical_klines(event)
        
        # 验证调用了BinanceClient.get_historical_klines
        mock_client.get_historical_klines.assert_called_once_with(
            symbol="XRPUSDC",
            interval="15m",
            limit=200
        )
        
        # 验证发布了de.historical_klines.success事件
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        
        assert published_event.subject == DEEvents.HISTORICAL_KLINES_SUCCESS
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["symbol"] == "XRPUSDC"
        assert published_event.data["interval"] == "15m"
        assert len(published_event.data["klines"]) == 1
        
        # 验证K线格式转换正确
        kline = published_event.data["klines"][0]
        assert kline["open"] == "0.01634000"
        assert kline["high"] == "0.80000000"
        assert kline["low"] == "0.01575800"
        assert kline["close"] == "0.01577100"
        assert kline["volume"] == "148976.11427815"
        assert kline["timestamp"] == 1499040000000
        assert kline["is_closed"] == True
    
    @pytest.mark.asyncio
    async def test_handle_get_historical_klines_client_not_found(self):
        """测试客户端不存在时的处理"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # 创建历史K线请求事件（客户端不存在）
        event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": "user_999",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "limit": 200
            },
            source="TA"
        )
        
        # 处理事件
        await manager._on_get_historical_klines(event)
        
        # 验证发布了de.historical_klines.failed事件
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        
        assert published_event.subject == DEEvents.HISTORICAL_KLINES_FAILED
        assert published_event.data["user_id"] == "user_999"
        assert published_event.data["symbol"] == "XRPUSDC"
        assert published_event.data["interval"] == "15m"
        assert "客户端不存在" in published_event.data["error"]
    
    @pytest.mark.asyncio
    async def test_handle_get_historical_klines_api_error(self):
        """测试API调用失败时的处理"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # Mock BinanceClient（抛出异常）
        mock_client = Mock()
        mock_client.get_historical_klines = AsyncMock(side_effect=Exception("API Error"))
        manager._clients["user_001"] = mock_client
        
        # 创建历史K线请求事件
        event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "limit": 200
            },
            source="TA"
        )
        
        # 处理事件
        await manager._on_get_historical_klines(event)
        
        # 验证发布了de.historical_klines.failed事件
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        
        assert published_event.subject == DEEvents.HISTORICAL_KLINES_FAILED
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["symbol"] == "XRPUSDC"
        assert published_event.data["interval"] == "15m"
        assert "API Error" in published_event.data["error"]
    
    @pytest.mark.asyncio
    async def test_handle_get_historical_klines_default_limit(self):
        """测试默认limit参数"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # Mock BinanceClient
        mock_client = Mock()
        mock_client.get_historical_klines = AsyncMock(return_value=[])
        manager._clients["user_001"] = mock_client
        
        # 创建历史K线请求事件（不包含limit）
        event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m"
            },
            source="TA"
        )
        
        # 处理事件
        await manager._on_get_historical_klines(event)
        
        # 验证使用默认limit=200
        mock_client.get_historical_klines.assert_called_once_with(
            symbol="XRPUSDC",
            interval="15m",
            limit=200
        )


class TestDEManagerHistoricalKlinesFormatConversion:
    """测试K线格式转换"""
    
    @pytest.mark.asyncio
    async def test_kline_format_conversion(self):
        """测试币安K线格式转换为标准格式"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        
        manager = DEManager(event_bus=event_bus)
        
        # Mock BinanceClient返回多根K线
        mock_client = Mock()
        mock_client.get_historical_klines = AsyncMock(return_value=[
            [1499040000000, "1.0", "1.1", "0.9", "1.05", "1000", 1499644799999, "1050", 100, "500", "525", "0"],
            [1499050000000, "1.05", "1.15", "0.95", "1.10", "2000", 1499654799999, "2200", 200, "1000", "1100", "0"]
        ])
        manager._clients["user_001"] = mock_client
        
        # 创建历史K线请求事件
        event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "interval": "15m",
                "limit": 2
            },
            source="TA"
        )
        
        # 处理事件
        await manager._on_get_historical_klines(event)
        
        # 验证K线格式转换
        published_event = event_bus.publish.call_args[0][0]
        klines = published_event.data["klines"]
        
        assert len(klines) == 2
        
        # 验证第一根K线
        assert klines[0]["open"] == "1.0"
        assert klines[0]["high"] == "1.1"
        assert klines[0]["low"] == "0.9"
        assert klines[0]["close"] == "1.05"
        assert klines[0]["volume"] == "1000"
        assert klines[0]["timestamp"] == 1499040000000
        assert klines[0]["is_closed"] == True
        
        # 验证第二根K线
        assert klines[1]["open"] == "1.05"
        assert klines[1]["high"] == "1.15"
        assert klines[1]["low"] == "0.95"
        assert klines[1]["close"] == "1.10"
        assert klines[1]["volume"] == "2000"
        assert klines[1]["timestamp"] == 1499050000000
        assert klines[1]["is_closed"] == True

