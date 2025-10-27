"""
集成测试 - 通配符订阅混合场景

测试通配符订阅与精确订阅混合使用、事件正确分发到所有匹配的处理器等真实协作场景

测试场景：
1. 通配符订阅与精确订阅混合使用
2. 多层级通配符订阅
3. 全局通配符订阅
4. 通配符订阅与持久化
5. 复杂的事件路由场景
"""

import pytest
import asyncio
from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.event_store import SQLiteEventStore


class TestWildcardSubscription:
    """通配符订阅混合场景集成测试"""
    
    def setup_method(self):
        """每个测试前重置 EventBus 单例"""
        EventBus._instance = None
    
    @pytest.mark.asyncio
    async def test_wildcard_and_exact_subscription_mixed(self):
        """测试通配符订阅与精确订阅混合使用"""
        bus = EventBus.get_instance()
        
        wildcard_events = []
        exact_events = []
        
        async def wildcard_handler(event):
            wildcard_events.append(event.subject)
        
        async def exact_handler(event):
            exact_events.append(event.subject)
        
        # 订阅通配符和精确主题
        bus.subscribe("order.*", wildcard_handler)
        bus.subscribe("order.created", exact_handler)
        
        # 发布不同的事件
        await bus.publish(Event(subject="order.created", data={}))
        await bus.publish(Event(subject="order.updated", data={}))
        await bus.publish(Event(subject="order.cancelled", data={}))
        await bus.publish(Event(subject="position.updated", data={}))
        
        # 验证通配符处理器收到所有 order.* 事件
        assert len(wildcard_events) == 3, "通配符处理器应该收到 3 个 order.* 事件"
        assert "order.created" in wildcard_events, "应该包含 order.created"
        assert "order.updated" in wildcard_events, "应该包含 order.updated"
        assert "order.cancelled" in wildcard_events, "应该包含 order.cancelled"
        
        # 验证精确处理器只收到 order.created 事件
        assert len(exact_events) == 1, "精确处理器应该只收到 1 个事件"
        assert exact_events[0] == "order.created", "应该是 order.created"
    
    @pytest.mark.asyncio
    async def test_multiple_wildcard_patterns(self):
        """测试多个通配符模式"""
        bus = EventBus.get_instance()
        
        order_events = []
        position_events = []
        all_events = []
        
        async def order_handler(event):
            order_events.append(event.subject)
        
        async def position_handler(event):
            position_events.append(event.subject)
        
        async def all_handler(event):
            all_events.append(event.subject)
        
        # 订阅不同的通配符模式
        bus.subscribe("order.*", order_handler)
        bus.subscribe("position.*", position_handler)
        bus.subscribe("*", all_handler)
        
        # 发布事件
        await bus.publish(Event(subject="order.created", data={}))
        await bus.publish(Event(subject="position.updated", data={}))
        await bus.publish(Event(subject="market.tick", data={}))
        
        # 验证各个处理器收到的事件
        assert len(order_events) == 1, "order_handler 应该收到 1 个事件"
        assert len(position_events) == 1, "position_handler 应该收到 1 个事件"
        assert len(all_events) == 3, "all_handler 应该收到所有 3 个事件"
    
    @pytest.mark.asyncio
    async def test_nested_wildcard_patterns(self):
        """测试嵌套的通配符模式"""
        bus = EventBus.get_instance()
        
        received_events = {
            "order_all": [],
            "order_created": [],
            "all": []
        }
        
        async def order_all_handler(event):
            received_events["order_all"].append(event.subject)
        
        async def order_created_handler(event):
            received_events["order_created"].append(event.subject)
        
        async def all_handler(event):
            received_events["all"].append(event.subject)
        
        # 订阅不同层级的模式
        bus.subscribe("order.*", order_all_handler)
        bus.subscribe("order.created.*", order_created_handler)
        bus.subscribe("*", all_handler)
        
        # 发布事件
        await bus.publish(Event(subject="order.created.success", data={}))
        await bus.publish(Event(subject="order.updated", data={}))
        await bus.publish(Event(subject="position.updated", data={}))
        
        # 验证事件分发
        assert "order.created.success" in received_events["order_created"], \
            "order.created.* 应该匹配 order.created.success"
        assert "order.updated" in received_events["order_all"], \
            "order.* 应该匹配 order.updated"
        assert len(received_events["all"]) == 3, "* 应该匹配所有事件"
    
    @pytest.mark.asyncio
    async def test_wildcard_subscription_with_persistence(self, tmp_path):
        """测试通配符订阅与持久化"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        received_events = []
        
        async def wildcard_handler(event):
            received_events.append(event.subject)
        
        # 订阅通配符
        bus.subscribe("order.*", wildcard_handler)
        
        # 发布多个事件
        await bus.publish(Event(subject="order.created", data={"order_id": "1"}))
        await bus.publish(Event(subject="order.updated", data={"order_id": "1"}))
        await bus.publish(Event(subject="order.filled", data={"order_id": "1"}))
        
        # 验证处理器收到所有事件
        assert len(received_events) == 3, "处理器应该收到 3 个事件"
        
        # 验证所有事件都被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 3, "所有事件应该被持久化"
        
        # 验证可以按主题查询
        order_created_events = store.query_events_by_subject("order.created", limit=10)
        assert len(order_created_events) == 1, "应该能查询到 order.created 事件"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_complex_event_routing(self, tmp_path):
        """测试复杂的事件路由场景"""
        db_path = tmp_path / "events.db"
        store = SQLiteEventStore(db_path=str(db_path))
        bus = EventBus.get_instance(event_store=store)
        
        routing_log = {
            "risk_manager": [],
            "order_manager": [],
            "position_manager": [],
            "notification_service": [],
            "audit_service": []
        }
        
        async def risk_manager_handler(event):
            routing_log["risk_manager"].append(event.subject)
        
        async def order_manager_handler(event):
            routing_log["order_manager"].append(event.subject)
        
        async def position_manager_handler(event):
            routing_log["position_manager"].append(event.subject)
        
        async def notification_handler(event):
            routing_log["notification_service"].append(event.subject)
        
        async def audit_handler(event):
            routing_log["audit_service"].append(event.subject)
        
        # 配置复杂的订阅关系
        bus.subscribe("order.*", risk_manager_handler)  # 风控关注所有订单事件
        bus.subscribe("order.created", order_manager_handler)  # 订单管理器只关注创建
        bus.subscribe("order.filled", order_manager_handler)  # 订单管理器也关注成交
        bus.subscribe("order.filled", position_manager_handler)  # 持仓管理器关注成交
        bus.subscribe("position.*", position_manager_handler)  # 持仓管理器关注持仓事件
        bus.subscribe("*", notification_handler)  # 通知服务关注所有事件
        bus.subscribe("*", audit_handler)  # 审计服务关注所有事件
        
        # 发布一系列事件
        await bus.publish(Event(subject="order.created", data={"order_id": "1"}))
        await bus.publish(Event(subject="order.filled", data={"order_id": "1"}))
        await bus.publish(Event(subject="position.updated", data={"symbol": "BTC/USDT"}))
        await bus.publish(Event(subject="market.tick", data={"symbol": "BTC/USDT"}))
        
        # 验证事件路由
        assert len(routing_log["risk_manager"]) == 2, "风控应该收到 2 个订单事件"
        assert len(routing_log["order_manager"]) == 2, "订单管理器应该收到 2 个事件"
        assert len(routing_log["position_manager"]) == 2, "持仓管理器应该收到 2 个事件"
        assert len(routing_log["notification_service"]) == 4, "通知服务应该收到所有 4 个事件"
        assert len(routing_log["audit_service"]) == 4, "审计服务应该收到所有 4 个事件"
        
        # 验证所有事件都被持久化
        persisted_events = store.query_recent_events(limit=10)
        assert len(persisted_events) == 4, "所有事件应该被持久化"
        
        store.close()
    
    @pytest.mark.asyncio
    async def test_wildcard_with_error_isolation(self):
        """测试通配符订阅与错误隔离"""
        bus = EventBus.get_instance()
        
        successful_events = []
        alert_events = []
        
        async def failing_wildcard_handler(event):
            if "error" in event.subject:
                raise ValueError("Intentional error")
            successful_events.append(event.subject)
        
        async def alert_handler(event):
            alert_events.append(event)
        
        # 订阅通配符和告警
        bus.subscribe("order.*", failing_wildcard_handler)
        bus.subscribe("system.alert.handler_error", alert_handler)
        
        # 发布事件
        await bus.publish(Event(subject="order.created", data={}))
        await bus.publish(Event(subject="order.error", data={}))
        await bus.publish(Event(subject="order.updated", data={}))
        
        # 等待告警事件
        await asyncio.sleep(0.1)
        
        # 验证成功的事件被处理
        assert len(successful_events) == 2, "应该有 2 个成功处理的事件"
        assert "order.created" in successful_events, "应该包含 order.created"
        assert "order.updated" in successful_events, "应该包含 order.updated"
        
        # 验证告警事件被发布
        assert len(alert_events) >= 1, "应该发布告警事件"
    
    @pytest.mark.asyncio
    async def test_same_handler_multiple_patterns(self):
        """测试同一个处理器订阅多个模式"""
        bus = EventBus.get_instance()
        
        received_events = []
        
        async def multi_pattern_handler(event):
            received_events.append(event.subject)
        
        # 同一个处理器订阅多个模式
        bus.subscribe("order.*", multi_pattern_handler)
        bus.subscribe("position.*", multi_pattern_handler)
        bus.subscribe("market.tick", multi_pattern_handler)
        
        # 发布事件
        await bus.publish(Event(subject="order.created", data={}))
        await bus.publish(Event(subject="position.updated", data={}))
        await bus.publish(Event(subject="market.tick", data={}))
        await bus.publish(Event(subject="user.login", data={}))
        
        # 验证处理器收到匹配的事件（去重后）
        assert len(received_events) == 3, "应该收到 3 个匹配的事件"
        assert "order.created" in received_events, "应该包含 order.created"
        assert "position.updated" in received_events, "应该包含 position.updated"
        assert "market.tick" in received_events, "应该包含 market.tick"
        assert "user.login" not in received_events, "不应该包含 user.login"

