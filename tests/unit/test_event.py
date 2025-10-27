"""
Event 类单元测试

测试 Event 数据类的功能，包括：
- 字段验证
- UUID 自动生成
- 时间戳自动生成
- 必需字段检查
"""

import pytest
from datetime import datetime
from src.core.event import Event


class TestEvent:
    """Event 类测试"""
    
    def test_event_creation_with_required_fields(self):
        """测试使用必需字段创建事件"""
        subject = "test.event"
        data = {"key": "value"}
        
        event = Event(subject=subject, data=data)
        
        assert event.subject == subject, "事件主题应该正确设置"
        assert event.data == data, "事件数据应该正确设置"
    
    def test_event_id_auto_generation(self):
        """测试事件ID自动生成（UUID）"""
        event = Event(subject="test.event", data={})
        
        assert event.event_id is not None, "事件ID不应为空"
        assert isinstance(event.event_id, str), "事件ID应该是字符串类型"
        assert len(event.event_id) > 0, "事件ID应该有内容"
        
        # 验证是否为有效的UUID格式（包含连字符）
        assert "-" in event.event_id, "事件ID应该是UUID格式"
    
    def test_event_id_uniqueness(self):
        """测试每个事件的ID是唯一的"""
        event1 = Event(subject="test.event", data={})
        event2 = Event(subject="test.event", data={})
        
        assert event1.event_id != event2.event_id, "不同事件的ID应该不同"
    
    def test_timestamp_auto_generation(self):
        """测试时间戳自动生成"""
        before = datetime.now()
        event = Event(subject="test.event", data={})
        after = datetime.now()
        
        assert event.timestamp is not None, "时间戳不应为空"
        assert isinstance(event.timestamp, datetime), "时间戳应该是datetime类型"
        assert before <= event.timestamp <= after, "时间戳应该在创建时间范围内"
    
    def test_event_with_source(self):
        """测试带有source字段的事件创建"""
        source = "test_module"
        event = Event(subject="test.event", data={}, source=source)
        
        assert event.source == source, "事件源应该正确设置"
    
    def test_event_without_source(self):
        """测试不带source字段的事件创建（source应为None）"""
        event = Event(subject="test.event", data={})
        
        assert event.source is None, "未指定source时应为None"
    
    def test_event_missing_subject(self):
        """测试缺少subject字段时应该抛出异常"""
        with pytest.raises(TypeError):
            Event(data={})
    
    def test_event_missing_data(self):
        """测试缺少data字段时应该抛出异常"""
        with pytest.raises(TypeError):
            Event(subject="test.event")
    
    def test_event_data_is_dict(self):
        """测试data字段必须是字典类型"""
        event = Event(subject="test.event", data={"key": "value"})
        
        assert isinstance(event.data, dict), "data字段应该是字典类型"
    
    def test_event_data_can_be_empty_dict(self):
        """测试data可以是空字典"""
        event = Event(subject="test.event", data={})
        
        assert event.data == {}, "data可以是空字典"
    
    def test_event_data_with_complex_structure(self):
        """测试data可以包含复杂的数据结构"""
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
        
        assert event.data == complex_data, "data应该支持复杂的嵌套结构"
        assert event.data["metadata"]["strategy"] == "grid_trading", "应该能访问嵌套数据"
    
    def test_event_subject_is_string(self):
        """测试subject字段必须是字符串类型"""
        event = Event(subject="test.event", data={})
        
        assert isinstance(event.subject, str), "subject应该是字符串类型"
    
    def test_event_representation(self):
        """测试事件的字符串表示"""
        event = Event(subject="test.event", data={"key": "value"})
        
        # dataclass 应该自动提供 __repr__
        repr_str = repr(event)
        assert "Event" in repr_str, "repr应该包含类名"
        assert "test.event" in repr_str, "repr应该包含subject"

