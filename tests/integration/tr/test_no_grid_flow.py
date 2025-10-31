"""
无网格模式集成测试

测试完整的事件流转：
ST信号 → TR建仓 → DE成交 → TR发布持仓事件 → ST出场信号 → TR平仓
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.tr.tr_manager import TRManager
from src.core.tr.tr_events import TREvents
from src.core.st.st_events import STEvents
from src.core.de.de_events import DEEvents


@pytest_asyncio.fixture
async def event_bus():
    """创建事件总线"""
    bus = EventBus.get_instance()
    yield bus
    # 清理
    EventBus._instance = None


@pytest_asyncio.fixture
async def tr_manager(event_bus):
    """创建TR管理器"""
    manager = TRManager.get_instance(event_bus)
    await manager.start()
    yield manager
    await manager.shutdown()
    # 清理
    TRManager._instance = None


class TestNoGridEntryFlow:
    """测试无网格模式入场流程"""
    
    @pytest.mark.asyncio
    async def test_entry_signal_to_position_opened(self, event_bus, tr_manager):
        """测试从入场信号到持仓开启的完整流程"""
        # 记录发布的事件
        published_events = []
        
        def capture_event(event: Event):
            published_events.append(event)
        
        # 订阅TR发布的事件
        event_bus.subscribe(TREvents.ORDER_CREATE, capture_event)
        event_bus.subscribe(TREvents.POSITION_OPENED, capture_event)
        
        # 1. 发布账户加载事件
        account_event = Event(
            subject=TREvents.INPUT_ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "account_info": {
                    "totalWalletBalance": "10000.0",
                    "availableBalance": "9500.0"
                }
            }
        )
        await event_bus.publish(account_event)
        await event_bus.process_events()
        
        # 2. 发布ST入场信号（无网格模式）
        signal_event = Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "signal_type": "ENTRY",
                "side": "LONG",
                "price": 1.0,
                "strategy_config": {
                    "grid_trading": {
                        "enabled": False
                    }
                }
            }
        )
        await event_bus.publish(signal_event)
        await event_bus.process_events()
        
        # 验证：TR应该发布订单创建请求
        order_requests = [e for e in published_events if e.subject == TREvents.ORDER_CREATE]
        assert len(order_requests) == 1
        
        order_req = order_requests[0].data
        assert order_req["symbol"] == "XRPUSDC"
        assert order_req["side"] == "BUY"
        assert order_req["order_type"] == "MARKET"
        
        # 3. 模拟DE订单成交事件
        order_filled_event = Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "order_id": "order_123",
                "side": "BUY",
                "price": 1.0,
                "quantity": 100.0,
                "status": "FILLED"
            }
        )
        await event_bus.publish(order_filled_event)
        await event_bus.process_events()
        
        # 验证：TR应该发布持仓开启事件
        position_events = [e for e in published_events if e.subject == TREvents.POSITION_OPENED]
        assert len(position_events) == 1
        
        pos_data = position_events[0].data
        assert pos_data["symbol"] == "XRPUSDC"
        assert pos_data["side"] == "LONG"
        assert pos_data["entry_price"] == 1.0
        assert pos_data["quantity"] == 100.0


class TestNoGridExitFlow:
    """测试无网格模式出场流程"""
    
    @pytest.mark.asyncio
    async def test_exit_signal_to_position_closed(self, event_bus, tr_manager):
        """测试从出场信号到持仓关闭的完整流程"""
        published_events = []
        
        def capture_event(event: Event):
            published_events.append(event)
        
        event_bus.subscribe(TREvents.ORDER_CREATE, capture_event)
        event_bus.subscribe(TREvents.POSITION_OPENED, capture_event)
        event_bus.subscribe(TREvents.POSITION_CLOSED, capture_event)
        
        # 1. 先建立持仓（入场流程）
        account_event = Event(
            subject=TREvents.INPUT_ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "account_info": {
                    "totalWalletBalance": "10000.0",
                    "availableBalance": "9500.0"
                }
            }
        )
        await event_bus.publish(account_event)
        await event_bus.process_events()
        
        entry_signal = Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "signal_type": "ENTRY",
                "side": "LONG",
                "price": 1.0,
                "strategy_config": {
                    "grid_trading": {"enabled": False}
                }
            }
        )
        await event_bus.publish(entry_signal)
        await event_bus.process_events()
        
        entry_filled = Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "order_id": "order_entry",
                "side": "BUY",
                "price": 1.0,
                "quantity": 100.0,
                "status": "FILLED"
            }
        )
        await event_bus.publish(entry_filled)
        await event_bus.process_events()
        
        # 清空已记录的事件
        published_events.clear()
        
        # 2. 发布ST出场信号
        exit_signal = Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "signal_type": "EXIT",
                "price": 1.1
            }
        )
        await event_bus.publish(exit_signal)
        await event_bus.process_events()
        
        # 验证：TR应该发布平仓订单请求
        order_requests = [e for e in published_events if e.subject == TREvents.ORDER_CREATE]
        assert len(order_requests) == 1
        
        exit_order = order_requests[0].data
        assert exit_order["symbol"] == "XRPUSDC"
        assert exit_order["side"] == "SELL"  # 平多头仓位
        assert exit_order["order_type"] == "MARKET"
        
        # 3. 模拟平仓订单成交
        exit_filled = Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "order_id": "order_exit",
                "side": "SELL",
                "price": 1.1,
                "quantity": 100.0,
                "status": "FILLED"
            }
        )
        await event_bus.publish(exit_filled)
        await event_bus.process_events()
        
        # 验证：TR应该发布持仓关闭事件
        closed_events = [e for e in published_events if e.subject == TREvents.POSITION_CLOSED]
        assert len(closed_events) == 1
        
        closed_data = closed_events[0].data
        assert closed_data["symbol"] == "XRPUSDC"
        assert closed_data["side"] == "LONG"
        assert closed_data["exit_price"] == 1.1
        # 验证利润计算（包含手续费）
        # 毛利 = (1.1 - 1.0) × 100 = 10.0
        # 手续费 = 1.0 × 100 × 0.0004 + 1.1 × 100 × 0.0004 = 0.084
        # 净利 = 10.0 - 0.084 = 9.916
        assert abs(closed_data["profit"] - 9.916) < 0.001


class TestNoGridShortPosition:
    """测试无网格模式空头持仓"""
    
    @pytest.mark.asyncio
    async def test_short_position_flow(self, event_bus, tr_manager):
        """测试空头持仓的完整流程"""
        published_events = []
        
        def capture_event(event: Event):
            published_events.append(event)
        
        event_bus.subscribe(TREvents.ORDER_CREATE, capture_event)
        event_bus.subscribe(TREvents.POSITION_OPENED, capture_event)
        event_bus.subscribe(TREvents.POSITION_CLOSED, capture_event)
        
        # 1. 账户加载
        await event_bus.publish(Event(
            subject=TREvents.INPUT_ACCOUNT_LOADED,
            data={
                "user_id": "user_001",
                "account_info": {
                    "totalWalletBalance": "10000.0",
                    "availableBalance": "9500.0"
                }
            }
        ))
        await event_bus.process_events()
        
        # 2. 空头入场信号
        await event_bus.publish(Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "signal_type": "ENTRY",
                "side": "SHORT",
                "price": 1.0,
                "strategy_config": {"grid_trading": {"enabled": False}}
            }
        ))
        await event_bus.process_events()
        
        # 验证：应该是卖单
        order_req = [e for e in published_events if e.subject == TREvents.ORDER_CREATE][0]
        assert order_req.data["side"] == "SELL"
        
        # 3. 入场成交
        await event_bus.publish(Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "order_id": "short_entry",
                "side": "SELL",
                "price": 1.0,
                "quantity": 100.0,
                "status": "FILLED"
            }
        ))
        await event_bus.process_events()
        
        # 验证：持仓开启
        pos_opened = [e for e in published_events if e.subject == TREvents.POSITION_OPENED][0]
        assert pos_opened.data["side"] == "SHORT"
        
        published_events.clear()
        
        # 4. 出场信号
        await event_bus.publish(Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "signal_type": "EXIT",
                "price": 0.9
            }
        ))
        await event_bus.process_events()
        
        # 验证：平空头应该是买单
        exit_order = [e for e in published_events if e.subject == TREvents.ORDER_CREATE][0]
        assert exit_order.data["side"] == "BUY"
        
        # 5. 出场成交
        await event_bus.publish(Event(
            subject=DEEvents.ORDER_FILLED,
            data={
                "user_id": "user_001",
                "symbol": "XRPUSDC",
                "order_id": "short_exit",
                "side": "BUY",
                "price": 0.9,
                "quantity": 100.0,
                "status": "FILLED"
            }
        ))
        await event_bus.process_events()
        
        # 验证：持仓关闭，空头盈利
        closed = [e for e in published_events if e.subject == TREvents.POSITION_CLOSED][0]
        assert closed.data["side"] == "SHORT"
        # 空头盈利：(1.0 - 0.9) × 100 - 手续费 = 9.924
        assert closed.data["profit"] > 0

