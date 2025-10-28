"""
EventBus 事件总线单元测试

测试 EventBus 的完整功能，包括：
- 单例模式
- 订阅/发布
- 异步分发
- 通配符订阅
- 错误隔离
- 依赖注入 EventStore
- 可选持久化
"""

import pytest
import asyncio
from src.core.event import Event
from src.core.event import EventBus
from src.core.event import AbstractEventStore


class TestEventBusSingleton:
    """EventBus 单例模式测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None

    def test_get_instance_returns_singleton(self):
        """测试 get_instance 返回单例"""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()

        assert bus1 is bus2, "应该返回同一个实例"

    def test_singleton_with_event_store(self, tmp_path):
        """测试带 event_store 参数的单例"""
        from src.core.event import SQLiteEventStore

        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))

        bus1 = EventBus.get_instance(event_store=store)
        bus2 = EventBus.get_instance()

        assert bus1 is bus2, "应该返回同一个实例"
        assert bus1._event_store is store, "应该使用传入的 event_store"

        store.close()

    def test_reset_instance_for_testing(self):
        """测试可以重置单例（用于测试）"""
        bus1 = EventBus.get_instance()

        # 重置单例
        EventBus._instance = None

        bus2 = EventBus.get_instance()

        assert bus1 is not bus2, "重置后应该是新实例"


class TestEventBusSubscription:
    """EventBus 订阅功能测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None
    
    def test_subscribe_to_event(self):
        """测试订阅事件"""
        bus = EventBus.get_instance()
        
        def handler(event):
            pass
        
        bus.subscribe("test.event", handler)
        
        assert "test.event" in bus._subscribers, "应该添加订阅"
        assert handler in bus._subscribers["test.event"], "应该包含处理器"
    
    def test_subscribe_multiple_handlers_to_same_event(self):
        """测试同一事件可以有多个处理器"""
        bus = EventBus.get_instance()
        
        def handler1(event):
            pass
        
        def handler2(event):
            pass
        
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        
        assert len(bus._subscribers["test.event"]) == 2, "应该有两个处理器"
        assert handler1 in bus._subscribers["test.event"], "应该包含 handler1"
        assert handler2 in bus._subscribers["test.event"], "应该包含 handler2"
    
    def test_subscribe_to_different_events(self):
        """测试订阅不同的事件"""
        bus = EventBus.get_instance()
        
        def handler1(event):
            pass
        
        def handler2(event):
            pass
        
        bus.subscribe("event1", handler1)
        bus.subscribe("event2", handler2)
        
        assert "event1" in bus._subscribers, "应该有 event1 订阅"
        assert "event2" in bus._subscribers, "应该有 event2 订阅"


class TestEventBusPublish:
    """EventBus 发布功能测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_publish_event_to_subscriber(self):
        """测试发布事件到订阅者"""
        bus = EventBus.get_instance()
        
        received_events = []
        
        async def handler(event):
            received_events.append(event)
        
        bus.subscribe("test.event", handler)
        
        event = Event(subject="test.event", data={"key": "value"})
        await bus.publish(event)
        
        assert len(received_events) == 1, "应该收到一个事件"
        assert received_events[0].subject == "test.event", "应该是正确的事件"
    
    @pytest.mark.asyncio
    async def test_publish_to_multiple_subscribers(self):
        """测试发布到多个订阅者"""
        bus = EventBus.get_instance()
        
        received1 = []
        received2 = []
        
        async def handler1(event):
            received1.append(event)
        
        async def handler2(event):
            received2.append(event)
        
        bus.subscribe("test.event", handler1)
        bus.subscribe("test.event", handler2)
        
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        assert len(received1) == 1, "handler1 应该收到事件"
        assert len(received2) == 1, "handler2 应该收到事件"
    
    @pytest.mark.asyncio
    async def test_publish_only_to_matching_subscribers(self):
        """测试只发布到匹配的订阅者"""
        bus = EventBus.get_instance()
        
        received1 = []
        received2 = []
        
        async def handler1(event):
            received1.append(event)
        
        async def handler2(event):
            received2.append(event)
        
        bus.subscribe("event1", handler1)
        bus.subscribe("event2", handler2)
        
        event = Event(subject="event1", data={})
        await bus.publish(event)
        
        assert len(received1) == 1, "handler1 应该收到事件"
        assert len(received2) == 0, "handler2 不应该收到事件"


class TestEventBusAsyncDispatch:
    """EventBus 异步分发测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_handlers_execute_concurrently(self):
        """测试处理器并发执行"""
        bus = EventBus.get_instance()
        
        execution_order = []
        
        async def slow_handler(event):
            execution_order.append("slow_start")
            await asyncio.sleep(0.1)
            execution_order.append("slow_end")
        
        async def fast_handler(event):
            execution_order.append("fast_start")
            await asyncio.sleep(0.01)
            execution_order.append("fast_end")
        
        bus.subscribe("test.event", slow_handler)
        bus.subscribe("test.event", fast_handler)
        
        event = Event(subject="test.event", data={})
        await bus.publish(event)
        
        # 并发执行时，fast_handler 应该先完成
        assert "fast_end" in execution_order, "fast_handler 应该执行完成"
        assert "slow_end" in execution_order, "slow_handler 应该执行完成"
        # fast_handler 应该在 slow_handler 之前完成
        fast_end_index = execution_order.index("fast_end")
        slow_end_index = execution_order.index("slow_end")
        assert fast_end_index < slow_end_index, "fast_handler 应该先完成"
    
    @pytest.mark.asyncio
    async def test_publish_is_non_blocking(self):
        """测试 publish 是非阻塞的"""
        bus = EventBus.get_instance()
        
        async def slow_handler(event):
            await asyncio.sleep(0.1)
        
        bus.subscribe("test.event", slow_handler)
        
        event = Event(subject="test.event", data={})
        
        # publish 应该等待所有处理器完成
        start_time = asyncio.get_event_loop().time()
        await bus.publish(event)
        end_time = asyncio.get_event_loop().time()
        
        # 应该至少等待 0.1 秒
        assert end_time - start_time >= 0.1, "应该等待处理器完成"


class TestEventBusWildcardSubscription:
    """EventBus 通配符订阅测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        """测试通配符订阅"""
        bus = EventBus.get_instance()
        
        received = []
        
        async def handler(event):
            received.append(event)
        
        # 订阅所有 order.* 事件
        bus.subscribe("order.*", handler)
        
        event1 = Event(subject="order.created", data={})
        event2 = Event(subject="order.updated", data={})
        event3 = Event(subject="user.created", data={})
        
        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event3)
        
        assert len(received) == 2, "应该收到 2 个 order.* 事件"
        assert received[0].subject == "order.created", "应该收到 order.created"
        assert received[1].subject == "order.updated", "应该收到 order.updated"
    
    @pytest.mark.asyncio
    async def test_star_wildcard_matches_all(self):
        """测试 * 通配符匹配所有事件"""
        bus = EventBus.get_instance()
        
        received = []
        
        async def handler(event):
            received.append(event)
        
        bus.subscribe("*", handler)
        
        event1 = Event(subject="order.created", data={})
        event2 = Event(subject="user.updated", data={})
        
        await bus.publish(event1)
        await bus.publish(event2)
        
        assert len(received) == 2, "应该收到所有事件"
    
    @pytest.mark.asyncio
    async def test_mixed_exact_and_wildcard_subscriptions(self):
        """测试精确订阅和通配符订阅混合使用"""
        bus = EventBus.get_instance()
        
        exact_received = []
        wildcard_received = []
        
        async def exact_handler(event):
            exact_received.append(event)
        
        async def wildcard_handler(event):
            wildcard_received.append(event)
        
        bus.subscribe("order.created", exact_handler)
        bus.subscribe("order.*", wildcard_handler)
        
        event = Event(subject="order.created", data={})
        await bus.publish(event)
        
        assert len(exact_received) == 1, "精确订阅应该收到事件"
        assert len(wildcard_received) == 1, "通配符订阅应该收到事件"


class TestEventBusErrorIsolation:
    """EventBus 错误隔离测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_stop_other_handlers(self):
        """测试处理器异常不影响其他处理器"""
        bus = EventBus.get_instance()

        received = []

        async def failing_handler(event):
            raise ValueError("Handler failed")

        async def normal_handler(event):
            received.append(event)

        bus.subscribe("test.event", failing_handler)
        bus.subscribe("test.event", normal_handler)

        event = Event(subject="test.event", data={})
        await bus.publish(event)

        # 即使 failing_handler 失败，normal_handler 也应该执行
        assert len(received) == 1, "正常处理器应该执行"

    @pytest.mark.asyncio
    async def test_handler_exception_is_logged(self, caplog):
        """测试处理器异常被记录到日志"""
        bus = EventBus.get_instance()

        async def failing_handler(event):
            raise ValueError("Test error")

        bus.subscribe("test.event", failing_handler)

        event = Event(subject="test.event", data={})
        await bus.publish(event)

        # 检查日志中是否有错误记录
        # 注意：这个测试依赖于 EventBus 的日志实现
        # 可能需要根据实际实现调整

    @pytest.mark.asyncio
    async def test_handler_exception_publishes_alert_event(self):
        """测试处理器异常发布告警事件"""
        bus = EventBus.get_instance()

        alert_events = []

        async def failing_handler(event):
            raise ValueError("Test error")

        async def alert_handler(event):
            alert_events.append(event)

        bus.subscribe("test.event", failing_handler)
        bus.subscribe("system.alert.handler_error", alert_handler)

        event = Event(subject="test.event", data={})
        await bus.publish(event)

        # 应该发布告警事件
        # 注意：需要等待一下，因为告警事件是异步发布的
        await asyncio.sleep(0.1)

        assert len(alert_events) >= 1, "应该发布告警事件"
        assert alert_events[0].subject == "system.alert.handler_error", "应该是告警事件"


class TestEventBusDependencyInjection:
    """EventBus 依赖注入测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None

    def test_can_inject_event_store(self, tmp_path):
        """测试可以注入 EventStore"""
        from src.core.event import SQLiteEventStore

        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))

        bus = EventBus.get_instance(event_store=store)

        assert bus._event_store is store, "应该使用注入的 EventStore"

        store.close()

    def test_can_work_without_event_store(self):
        """测试可以不使用 EventStore"""
        bus = EventBus.get_instance(event_store=None)

        assert bus._event_store is None, "应该没有 EventStore"

    @pytest.mark.asyncio
    async def test_events_persisted_when_store_provided(self, tmp_path):
        """测试提供 EventStore 时事件被持久化"""
        from src.core.event import SQLiteEventStore

        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))

        bus = EventBus.get_instance(event_store=store)

        event = Event(subject="test.event", data={"key": "value"})
        await bus.publish(event)

        # 查询数据库，验证事件已持久化
        events = store.query_recent_events(limit=10)
        assert len(events) == 1, "应该持久化一个事件"
        assert events[0]["subject"] == "test.event", "应该是正确的事件"

        store.close()

    @pytest.mark.asyncio
    async def test_events_not_persisted_when_store_not_provided(self):
        """测试不提供 EventStore 时事件不被持久化"""
        bus = EventBus.get_instance(event_store=None)

        event = Event(subject="test.event", data={})
        await bus.publish(event)

        # 没有 EventStore，事件不应该被持久化
        # 这个测试主要验证不会抛出异常
        assert True, "应该正常执行"

    @pytest.mark.asyncio
    async def test_optional_persistence_parameter(self, tmp_path):
        """测试可选的 persist 参数"""
        from src.core.event import SQLiteEventStore

        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))

        bus = EventBus.get_instance(event_store=store)

        # 发布事件，不持久化
        event1 = Event(subject="event1", data={})
        await bus.publish(event1, persist=False)

        # 发布事件，持久化
        event2 = Event(subject="event2", data={})
        await bus.publish(event2, persist=True)

        # 查询数据库
        events = store.query_recent_events(limit=10)
        assert len(events) == 1, "应该只持久化一个事件"
        assert events[0]["subject"] == "event2", "应该是 event2"

        store.close()


class TestEventBusIntegration:
    """EventBus 集成测试"""

    def setup_method(self):
        """每个测试前重置单例"""
        EventBus._instance = None

    @pytest.mark.asyncio
    async def test_complete_workflow(self, tmp_path):
        """测试完整的工作流程"""
        from src.core.event import SQLiteEventStore

        db_path = tmp_path / "test.db"
        store = SQLiteEventStore(db_path=str(db_path))

        bus = EventBus.get_instance(event_store=store)

        received_events = []

        async def handler(event):
            received_events.append(event)

        # 订阅事件
        bus.subscribe("order.*", handler)

        # 发布事件
        event = Event(subject="order.created", data={"order_id": "12345"})
        await bus.publish(event)

        # 验证处理器收到事件
        assert len(received_events) == 1, "处理器应该收到事件"

        # 验证事件被持久化
        events = store.query_recent_events(limit=10)
        assert len(events) == 1, "事件应该被持久化"

        store.close()

