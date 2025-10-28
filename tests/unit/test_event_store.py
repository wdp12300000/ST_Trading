"""
EventStore 持久化层单元测试

测试 SQLite3 事件持久化层的功能，包括：
- 数据库初始化
- 事件插入
- 历史查询
- 1000条记录限制
"""

import pytest
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from src.core.event import Event, SQLiteEventStore as EventStore


class TestEventStore:
    """EventStore 持久化层测试"""
    
    def test_event_store_initialization(self, tmp_path):
        """测试数据库初始化"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 验证数据库文件已创建
        assert db_path.exists(), "数据库文件应该被创建"
        
        # 验证表结构已创建
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        )
        result = cursor.fetchone()
        conn.close()
        
        assert result is not None, "events 表应该被创建"
    
    def test_insert_event(self, tmp_path):
        """测试插入事件"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        event = Event(
            subject="test.event",
            data={"key": "value"},
            source="test_module"
        )
        
        # 插入事件
        store.insert_event(event)
        
        # 验证事件已插入
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1, "应该插入1条事件记录"
    
    def test_insert_event_stores_all_fields(self, tmp_path):
        """测试插入事件时所有字段都被正确存储"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        event = Event(
            subject="order.created",
            data={"order_id": "12345", "symbol": "BTC/USDT"},
            source="order_manager"
        )
        
        store.insert_event(event)
        
        # 查询并验证所有字段
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT event_id, subject, data, timestamp, source FROM events")
        row = cursor.fetchone()
        conn.close()
        
        assert row[0] == event.event_id, "event_id 应该正确存储"
        assert row[1] == event.subject, "subject 应该正确存储"
        assert "order_id" in row[2], "data 应该正确存储"
        assert row[4] == event.source, "source 应该正确存储"
    
    def test_query_recent_events(self, tmp_path):
        """测试查询最近的事件"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入多个事件
        for i in range(5):
            event = Event(
                subject=f"test.event.{i}",
                data={"index": i}
            )
            store.insert_event(event)
        
        # 查询最近3条事件
        events = store.query_recent_events(limit=3)
        
        assert len(events) == 3, "应该返回3条事件"
        # 最新的事件应该在前面
        assert events[0]["data"]["index"] == 4, "最新的事件应该排在第一位"
        assert events[1]["data"]["index"] == 3, "第二新的事件应该排在第二位"
        assert events[2]["data"]["index"] == 2, "第三新的事件应该排在第三位"
    
    def test_query_events_by_subject(self, tmp_path):
        """测试按主题查询事件"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入不同主题的事件
        store.insert_event(Event(subject="order.created", data={"id": 1}))
        store.insert_event(Event(subject="order.updated", data={"id": 2}))
        store.insert_event(Event(subject="order.created", data={"id": 3}))
        
        # 查询特定主题的事件
        events = store.query_events_by_subject(subject="order.created")
        
        assert len(events) == 2, "应该返回2条 order.created 事件"
        assert all(e["subject"] == "order.created" for e in events), "所有事件主题应该是 order.created"
    
    def test_query_all_events(self, tmp_path):
        """测试查询所有事件"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入多个事件
        for i in range(10):
            store.insert_event(Event(subject=f"test.{i}", data={}))
        
        # 查询所有事件
        events = store.query_recent_events(limit=100)
        
        assert len(events) == 10, "应该返回所有10条事件"
    
    def test_cleanup_old_events_keeps_1000_records(self, tmp_path):
        """测试清理机制保留最近1000条记录"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入1050条事件
        for i in range(1050):
            event = Event(subject=f"test.event.{i}", data={"index": i})
            store.insert_event(event)
        
        # 执行清理
        store.cleanup_old_events()
        
        # 验证只保留1000条
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1000, "清理后应该只保留1000条记录"
    
    def test_cleanup_keeps_most_recent_events(self, tmp_path):
        """测试清理机制保留最新的事件"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入1050条事件
        for i in range(1050):
            event = Event(subject=f"test.event.{i}", data={"index": i})
            store.insert_event(event)
        
        # 执行清理
        store.cleanup_old_events()
        
        # 查询剩余的事件
        events = store.query_recent_events(limit=1000)
        
        # 验证保留的是最新的1000条（索引50-1049）
        assert len(events) == 1000, "应该保留1000条事件"
        assert events[0]["data"]["index"] == 1049, "最新的事件应该被保留"
        assert events[-1]["data"]["index"] == 50, "第1000新的事件应该被保留"
    
    def test_auto_cleanup_on_insert(self, tmp_path):
        """测试插入事件时自动清理"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入1001条事件（应该触发自动清理）
        for i in range(1001):
            event = Event(subject=f"test.event.{i}", data={"index": i})
            store.insert_event(event)
        
        # 验证自动清理后只保留1000条
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM events")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count == 1000, "自动清理后应该只保留1000条记录"
    
    def test_event_data_json_serialization(self, tmp_path):
        """测试事件数据的JSON序列化和反序列化"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        complex_data = {
            "order_id": "12345",
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "quantity": 0.01,
            "metadata": {
                "strategy": "grid_trading",
                "params": [1, 2, 3]
            }
        }
        
        event = Event(subject="order.created", data=complex_data)
        store.insert_event(event)
        
        # 查询并验证数据
        events = store.query_recent_events(limit=1)
        retrieved_data = events[0]["data"]
        
        assert retrieved_data == complex_data, "复杂数据结构应该正确序列化和反序列化"
        assert retrieved_data["metadata"]["strategy"] == "grid_trading", "嵌套数据应该正确恢复"
    
    def test_close_connection(self, tmp_path):
        """测试关闭数据库连接"""
        db_path = tmp_path / "test.db"
        store = EventStore(db_path=str(db_path))
        
        # 插入一条事件
        store.insert_event(Event(subject="test", data={}))
        
        # 关闭连接
        store.close()
        
        # 验证连接已关闭（尝试操作应该失败）
        with pytest.raises(Exception):
            store.insert_event(Event(subject="test", data={}))

