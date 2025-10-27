"""
集成测试 - 事件发布与持久化

测试事件发布后自动持久化到数据库、历史查询、数据完整性等真实协作场景

测试场景：
1. 事件发布后自动持久化
2. 持久化的事件可以被查询
3. 事件数据完整性
4. 多个事件的持久化和查询
5. 事件清理机制
"""

import pytest
import asyncio
from datetime import datetime
from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.event_store import SQLiteEventStore


class TestEventPublishAndPersistence:
    """事件发布与持久化集成测试"""
    
    def setup_method(self):
        """每个测试前重置 EventBus 单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_event_auto_persisted_on_publish(self, tmp_path):
        """测试事件发布后自动持久化"""
        # 1. 初始化 EventBus 和 EventStore
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 2. 发布事件
        event = Event(
            subject="order.created",
            data={"order_id": "12345", "symbol": "BTC/USDT", "price": 50000.0},
            source="order_manager"
        )
        await bus.publish(event)
        
        # 3. 验证事件已持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 1, "应该持久化一个事件"
        
        # 4. 验证持久化的事件数据完整性
        persisted = persisted_events[0]
        assert persisted["event_id"] == event.event_id, "event_id 应该一致"
        assert persisted["subject"] == "order.created", "subject 应该一致"
        assert persisted["data"]["order_id"] == "12345", "data 应该一致"
        assert persisted["data"]["symbol"] == "BTC/USDT", "data 应该一致"
        assert persisted["data"]["price"] == 50000.0, "data 应该一致"
        assert persisted["source"] == "order_manager", "source 应该一致"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_multiple_events_persistence(self, tmp_path):
        """测试多个事件的持久化"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 发布多个事件
        events = [
            Event(subject="order.created", data={"order_id": "1"}),
            Event(subject="order.updated", data={"order_id": "1", "status": "filled"}),
            Event(subject="position.updated", data={"symbol": "BTC/USDT", "qty": 1.5}),
        ]
        
        for event in events:
            await bus.publish(event)
        
        # 验证所有事件都被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 3, "应该持久化三个事件"
        
        # 验证事件顺序（最新的在前）
        assert persisted_events[0]["subject"] == "position.updated", "最新的事件应该在前"
        assert persisted_events[1]["subject"] == "order.updated", "第二个事件"
        assert persisted_events[2]["subject"] == "order.created", "最早的事件应该在后"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_query_events_by_subject(self, tmp_path):
        """测试按主题查询事件"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 发布不同主题的事件
        await bus.publish(Event(subject="order.created", data={"order_id": "1"}))
        await bus.publish(Event(subject="order.created", data={"order_id": "2"}))
        await bus.publish(Event(subject="position.updated", data={"symbol": "BTC/USDT"}))
        
        # 查询特定主题的事件
        order_events = store.query_events_by_subject("order.created", limit=10)
        assert len(order_events) == 2, "应该有两个 order.created 事件"
        
        position_events = store.query_events_by_subject("position.updated", limit=10)
        assert len(position_events) == 1, "应该有一个 position.updated 事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_event_not_persisted_when_persist_false(self, tmp_path):
        """测试 persist=False 时事件不被持久化"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 发布事件，不持久化
        event1 = Event(subject="temp.event", data={})
        await bus.publish(event1, persist=False)
        
        # 发布事件，持久化
        event2 = Event(subject="persistent.event", data={})
        await bus.publish(event2, persist=True)
        
        # 验证只有一个事件被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 1, "应该只持久化一个事件"
        assert persisted_events[0]["subject"] == "persistent.event", "应该是持久化的事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_event_timestamp_preserved(self, tmp_path):
        """测试事件时间戳被正确保存和恢复"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 发布事件
        event = Event(subject="test.event", data={})
        original_timestamp = event.timestamp
        
        await bus.publish(event)
        
        # 查询事件
        persisted_events = store.query_recent_events(limit=1)
        persisted_timestamp = persisted_events[0]["timestamp"]
        
        # 验证时间戳一致（精确到秒）
        assert persisted_timestamp.replace(microsecond=0) == original_timestamp.replace(microsecond=0), \
            "时间戳应该被正确保存"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_event_cleanup_mechanism(self, tmp_path):
        """测试事件清理机制"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path), max_events=10)
        bus = EventBus.get_instance(event_store=store)
        
        # 发布 15 个事件
        for i in range(15):
            event = Event(subject=f"event.{i}", data={"index": i})
            await bus.publish(event)
        
        # 验证只保留最近 10 个事件
        persisted_events = store.query_recent_events(limit=20)
        assert len(persisted_events) == 10, "应该只保留 10 个事件"
        
        # 验证保留的是最新的事件
        assert persisted_events[0]["data"]["index"] == 14, "应该保留最新的事件"
        assert persisted_events[9]["data"]["index"] == 5, "应该保留第 5 个事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_event_with_complex_data_structure(self, tmp_path):
        """测试复杂数据结构的事件持久化"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        # 发布包含复杂数据结构的事件
        complex_data = {
            "order_id": "12345",
            "items": [
                {"symbol": "BTC/USDT", "qty": 1.5, "price": 50000.0},
                {"symbol": "ETH/USDT", "qty": 10.0, "price": 3000.0}
            ],
            "metadata": {
                "user_id": "user123",
                "strategy": "grid_trading",
                "params": {"grid_size": 100, "levels": 10}
            }
        }
        
        event = Event(subject="order.created", data=complex_data)
        await bus.publish(event)
        
        # 查询并验证数据完整性
        persisted_events = store.query_recent_events(limit=1)
        persisted_data = persisted_events[0]["data"]
        
        assert persisted_data["order_id"] == "12345", "order_id 应该一致"
        assert len(persisted_data["items"]) == 2, "items 应该有两个元素"
        assert persisted_data["items"][0]["symbol"] == "BTC/USDT", "items 数据应该一致"
        assert persisted_data["metadata"]["strategy"] == "grid_trading", "metadata 应该一致"
        assert persisted_data["metadata"]["params"]["grid_size"] == 100, "嵌套数据应该一致"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_event_persistence_with_subscribers(self, tmp_path):
        """测试事件持久化与订阅者处理同时进行"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        # 订阅事件
        bus.subscribe("order.created", handler)
        
        # 发布事件
        event = Event(subject="order.created", data={"order_id": "12345"})
        await bus.publish(event)
        
        # 验证订阅者收到事件
        assert len(received_events) == 1, "订阅者应该收到事件"
        
        # 验证事件也被持久化
        persisted_events = store.query_recent_events(limit=1)
        assert len(persisted_events) == 1, "事件应该被持久化"
        assert persisted_events[0]["subject"] == "order.created", "持久化的事件应该正确"
        
        store.close()

