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


class TestEventEnhancedMethods:
    """Event 类增强方法测试"""

    def test_to_dict_basic(self):
        """测试 to_dict 方法基本功能"""
        event = Event(
            subject="order.created",
            data={"order_id": "12345", "symbol": "BTC/USDT"},
            source="order_manager"
        )

        result = event.to_dict()

        assert isinstance(result, dict), "to_dict 应该返回字典"
        assert result["subject"] == "order.created", "应该包含 subject"
        assert result["data"] == {"order_id": "12345", "symbol": "BTC/USDT"}, "应该包含 data"
        assert result["event_id"] == event.event_id, "应该包含 event_id"
        assert result["source"] == "order_manager", "应该包含 source"
        assert "timestamp" in result, "应该包含 timestamp"

    def test_to_dict_timestamp_format(self):
        """测试 to_dict 中时间戳的格式"""
        event = Event(subject="test", data={})
        result = event.to_dict()

        # 时间戳应该是 ISO 格式字符串
        assert isinstance(result["timestamp"], str), "timestamp 应该是字符串"
        assert "T" in result["timestamp"], "timestamp 应该是 ISO 格式"

        # 应该能够反序列化
        from datetime import datetime
        parsed_time = datetime.fromisoformat(result["timestamp"])
        assert isinstance(parsed_time, datetime), "timestamp 应该能够解析为 datetime"

    def test_to_dict_with_none_source(self):
        """测试 to_dict 处理 None 的 source"""
        event = Event(subject="test", data={})
        result = event.to_dict()

        assert result["source"] is None, "source 为 None 时应该保持 None"

    def test_from_dict_basic(self):
        """测试 from_dict 方法基本功能"""
        data_dict = {
            "event_id": "test-uuid-123",
            "subject": "order.created",
            "data": {"order_id": "12345"},
            "timestamp": "2025-10-27T10:30:00",
            "source": "order_manager"
        }

        event = Event.from_dict(data_dict)

        assert isinstance(event, Event), "from_dict 应该返回 Event 实例"
        assert event.event_id == "test-uuid-123", "应该正确设置 event_id"
        assert event.subject == "order.created", "应该正确设置 subject"
        assert event.data == {"order_id": "12345"}, "应该正确设置 data"
        assert event.source == "order_manager", "应该正确设置 source"

    def test_from_dict_timestamp_parsing(self):
        """测试 from_dict 正确解析时间戳"""
        from datetime import datetime

        data_dict = {
            "event_id": "test-uuid",
            "subject": "test",
            "data": {},
            "timestamp": "2025-10-27T10:30:00.123456",
            "source": None
        }

        event = Event.from_dict(data_dict)

        assert isinstance(event.timestamp, datetime), "timestamp 应该是 datetime 对象"
        assert event.timestamp.year == 2025, "应该正确解析年份"
        assert event.timestamp.month == 10, "应该正确解析月份"
        assert event.timestamp.day == 27, "应该正确解析日期"

    def test_from_dict_with_none_source(self):
        """测试 from_dict 处理 None 的 source"""
        data_dict = {
            "event_id": "test-uuid",
            "subject": "test",
            "data": {},
            "timestamp": "2025-10-27T10:30:00",
            "source": None
        }

        event = Event.from_dict(data_dict)
        assert event.source is None, "应该正确处理 None 的 source"

    def test_to_dict_from_dict_roundtrip(self):
        """测试 to_dict 和 from_dict 的往返转换"""
        original = Event(
            subject="order.created",
            data={"order_id": "12345", "price": 50000.0},
            source="order_manager"
        )

        # 转换为字典
        dict_data = original.to_dict()

        # 从字典恢复
        restored = Event.from_dict(dict_data)

        # 验证所有字段都正确恢复
        assert restored.event_id == original.event_id, "event_id 应该一致"
        assert restored.subject == original.subject, "subject 应该一致"
        assert restored.data == original.data, "data 应该一致"
        assert restored.source == original.source, "source 应该一致"
        # 时间戳可能有微小差异，只比较到秒
        assert restored.timestamp.replace(microsecond=0) == original.timestamp.replace(microsecond=0), "timestamp 应该基本一致"

    def test_validate_valid_event(self):
        """测试 validate 方法对有效事件返回 True"""
        event = Event(
            subject="order.created",
            data={"order_id": "12345"},
            source="order_manager"
        )

        assert event.validate() is True, "有效事件应该通过验证"

    def test_validate_checks_subject_not_empty(self):
        """测试 validate 检查 subject 不为空"""
        event = Event(subject="", data={})

        assert event.validate() is False, "空 subject 应该验证失败"

    def test_validate_checks_subject_type(self):
        """测试 validate 检查 subject 类型"""
        # 这个测试会在 __post_init__ 阶段就失败
        with pytest.raises(TypeError):
            Event(subject=123, data={})

    def test_validate_checks_data_type(self):
        """测试 validate 检查 data 类型"""
        # 这个测试会在 __post_init__ 阶段就失败
        with pytest.raises(TypeError):
            Event(subject="test", data="not a dict")

    def test_validate_allows_empty_data(self):
        """测试 validate 允许空的 data 字典"""
        event = Event(subject="test", data={})

        assert event.validate() is True, "空 data 字典应该是有效的"

    def test_validate_with_complex_data(self):
        """测试 validate 处理复杂的 data 结构"""
        event = Event(
            subject="order.created",
            data={
                "order_id": "12345",
                "items": [1, 2, 3],
                "metadata": {
                    "nested": "value"
                }
            }
        )

        assert event.validate() is True, "复杂 data 结构应该是有效的"

