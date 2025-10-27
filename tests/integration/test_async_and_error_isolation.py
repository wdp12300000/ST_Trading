"""
集成测试 - 异步处理与错误隔离

测试多个异步处理器并发执行、单个处理器失败不影响其他、告警事件发布等真实协作场景

测试场景：
1. 多个处理器并发执行
2. 处理器异常不影响其他处理器
3. 异常处理器触发告警事件
4. 告警事件被正确处理
5. 异步处理器的执行顺序
"""

import pytest
import asyncio
from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.event_store import SQLiteEventStore


class TestAsyncAndErrorIsolation:
    """异步处理与错误隔离集成测试"""
    
    def setup_method(self):
        """每个测试前重置 EventBus 单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_execute_concurrently(self):
        """测试多个处理器并发执行"""
        bus = EventBus.get_instance()
        
        execution_log = []
        
        async def handler1(event):
            execution_log.append("handler1_start")
            await asyncio.sleep(0.1)
            execution_log.append("handler1_end")
        
        async def handler2(event):
            execution_log.append("handler2_start")
            await asyncio.sleep(0.05)
            execution_log.append("handler2_end")
        
        async def handler3(event):
            execution_log.append("handler3_start")
            await asyncio.sleep(0.02)
            execution_log.append("handler3_end")
        
        # 订阅同一事件
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        bus.subscribe("test.event", handler3)
        
        # 发布事件
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        # 验证所有处理器都执行了
        assert "handler1_start" in execution_log, "handler1 应该开始执行"
        assert "handler1_end" in execution_log, "handler1 应该执行完成"
        assert "handler2_start" in execution_log, "handler2 应该开始执行"
        assert "handler2_end" in execution_log, "handler2 应该执行完成"
        assert "handler3_start" in execution_log, "handler3 应该开始执行"
        assert "handler3_end" in execution_log, "handler3 应该执行完成"
        
        # 验证并发执行（快的处理器先完成）
        handler3_end_index = execution_log.index("handler3_end")
        handler2_end_index = execution_log.index("handler2_end")
        handler1_end_index = execution_log.index("handler1_end")
        
        assert handler3_end_index < handler2_end_index, "handler3 应该先完成"
        assert handler2_end_index < handler1_end_index, "handler2 应该在 handler1 之前完成"
    
    @pytest.mark.asyncio
    async def test_handler_exception_does_not_stop_others(self):
        """测试处理器异常不影响其他处理器"""
        bus = EventBus.get_instance()
        
        successful_handlers = []
        
        async def failing_handler(event):
            raise ValueError("Handler failed intentionally")
        
        async def successful_handler1(event):
            successful_handlers.append("handler1")
        
        async def successful_handler2(event):
            successful_handlers.append("handler2")
        
        # 订阅事件
        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", successful_handler1)
        bus.subscribe("test.event", successful_handler2)
        
        # 发布事件
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        # 验证成功的处理器都执行了
        assert len(successful_handlers) == 2, "两个成功的处理器应该都执行"
        assert "handler1" in successful_handlers, "handler1 应该执行"
        assert "handler2" in successful_handlers, "handler2 应该执行"
    
    @pytest.mark.asyncio
    async def test_handler_exception_publishes_alert_event(self):
        """测试处理器异常触发告警事件"""
        bus = EventBus.get_instance()
        
        alert_events = []
        
        async def failing_handler(event):
            raise ValueError("Test error message")
        
        async def alert_handler(event):
            alert_events.append(event)
        
        # 订阅告警事件
        bus.subscribe("system.alert.handler_error", alert_handler)
        
        # 订阅普通事件（会失败）
        bus.subscribe("test.event", failing_handler)
        
        # 发布事件
        event = Event(subject="test.event", data={"key": "value"})
        await bus.publish(event)
        
        # 等待告警事件发布
        await asyncio.sleep(0.1)
        
        # 验证告警事件被发布
        assert len(alert_events) >= 1, "应该发布告警事件"
        
        alert = alert_events[0]
        assert alert.subject == "system.alert.handler_error", "应该是告警事件"
        assert alert.data["original_subject"] == "test.event", "应该包含原始事件主题"
        assert alert.data["handler_name"] == "failing_handler", "应该包含失败的处理器名称"
        assert alert.data["error_type"] == "ValueError", "应该包含错误类型"
        assert "Test error message" in alert.data["error_message"], "应该包含错误消息"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_fail_independently(self):
        """测试多个处理器独立失败"""
        bus = EventBus.get_instance()
        
        alert_events = []
        successful_count = []
        
        async def failing_handler1(event):
            raise ValueError("Error 1")
        
        async def failing_handler2(event):
            raise TypeError("Error 2")
        
        async def successful_handler(event):
            successful_count.append(1)
        
        async def alert_handler(event):
            alert_events.append(event)
        
        # 订阅告警事件
        bus.subscribe("system.alert.handler_error", alert_handler)
        
        # 订阅普通事件
        bus.subscribe("test.event", failing_handler1)
        bus.subscribe("test.event", failing_handler2)
        bus.subscribe("test.event", successful_handler)
        
        # 发布事件
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        # 等待告警事件发布
        await asyncio.sleep(0.1)
        
        # 验证成功的处理器执行了
        assert len(successful_count) == 1, "成功的处理器应该执行"
        
        # 验证两个告警事件被发布
        assert len(alert_events) >= 2, "应该发布两个告警事件"
    
    @pytest.mark.asyncio
    async def test_async_handlers_with_persistence(self, tmp_path):
        """测试异步处理器与持久化同时工作"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        processed_events = []
        
        async def async_handler(event):
            await asyncio.sleep(0.05)
            processed_events.append(event.subject)
        
        # 订阅事件
        bus.subscribe("order.*", async_handler)
        
        # 发布多个事件
        events = [
            Event(subject="order.created", data={"order_id": "1"}),
            Event(subject="order.updated", data={"order_id": "1"}),
            Event(subject="order.filled", data={"order_id": "1"}),
        ]
        
        for event in events:
            await bus.publish(event)
        
        # 验证所有事件都被处理
        assert len(processed_events) == 3, "所有事件应该被处理"
        
        # 验证所有事件都被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 3, "所有事件应该被持久化"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_error_isolation_with_persistence(self, tmp_path):
        """测试错误隔离不影响持久化"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        async def failing_handler(event):
            raise RuntimeError("Handler error")
        
        # 订阅事件（会失败）
        bus.subscribe("test.event", failing_handler)
        
        # 发布事件
        event = Event(subject="test.event", data={"key": "value"})
        await bus.publish(event)
        
        # 验证事件仍然被持久化（即使处理器失败）
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 1, "事件应该被持久化"
        assert persisted_events[0]["subject"] == "test.event", "应该是正确的事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_alert_events_not_persisted_by_default(self, tmp_path):
        """测试告警事件默认不被持久化（避免无限循环）"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        async def failing_handler(event):
            raise ValueError("Test error")
        
        # 订阅事件（会失败）
        bus.subscribe("test.event", failing_handler)
        
        # 发布事件
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        # 等待告警事件发布
        await asyncio.sleep(0.1)
        
        # 验证只有原始事件被持久化，告警事件不被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 1, "应该只有原始事件被持久化"
        assert persisted_events[0]["subject"] == "test.event", "应该是原始事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_complex_async_workflow(self, tmp_path):
        """测试复杂的异步工作流"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        workflow_log = []
        
        async def risk_check_handler(event):
            await asyncio.sleep(0.05)
            workflow_log.append("risk_checked")
        
        async def position_update_handler(event):
            await asyncio.sleep(0.03)
            workflow_log.append("position_updated")
        
        async def notification_handler(event):
            await asyncio.sleep(0.01)
            workflow_log.append("notification_sent")
        
        async def failing_handler(event):
            raise Exception("Audit failed")
        
        # 订阅事件
        bus.subscribe("order.created", risk_check_handler)
        bus.subscribe("order.created", position_update_handler)
        bus.subscribe("order.created", notification_handler)
        bus.subscribe("order.created", failing_handler)
        
        # 发布事件
        event = Event(subject="order.created", data={"order_id": "12345"})
        await bus.publish(event)
        
        # 验证所有成功的处理器都执行了
        assert "risk_checked" in workflow_log, "风控检查应该执行"
        assert "position_updated" in workflow_log, "持仓更新应该执行"
        assert "notification_sent" in workflow_log, "通知应该发送"
        
        # 验证事件被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 1, "事件应该被持久化"
        
        store.close()

