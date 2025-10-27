"""
Event 数据类

定义事件驱动架构中的核心事件对象，包含：
- subject: 事件主题（必需）
- data: 事件数据（必需）
- event_id: 事件ID（自动生成UUID）
- timestamp: 时间戳（自动生成）
- source: 事件源模块（可选）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import uuid


@dataclass
class Event:
    """
    事件对象
    
    Attributes:
        subject: 事件主题，用于标识事件类型
        data: 事件数据，包含事件的具体信息
        event_id: 事件唯一标识符，自动生成UUID
        timestamp: 事件创建时间戳，自动生成
        source: 事件源模块，可选
    
    使用方式：
        event = Event(
            subject="order.created",
            data={"order_id": "12345", "symbol": "BTC/USDT"},
            source="order_manager"
        )
    """
    
    subject: str
    data: Dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None
    
    def __post_init__(self):
        """
        数据验证

        在对象初始化后自动调用，用于验证数据的有效性

        验证规则：
            - subject 必须是字符串类型
            - data 必须是字典类型

        Raises:
            TypeError: 当字段类型不正确时抛出
        """
        if not isinstance(self.subject, str):
            raise TypeError(f"subject 必须是字符串类型，当前类型: {type(self.subject)}")

        if not isinstance(self.data, dict):
            raise TypeError(f"data 必须是字典类型，当前类型: {type(self.data)}")

    def to_dict(self) -> Dict[str, Any]:
        """
        将事件对象序列化为字典

        用于将事件对象转换为可以 JSON 序列化的字典格式，
        便于存储、传输和日志记录。

        Returns:
            包含所有事件字段的字典，timestamp 转换为 ISO 格式字符串

        使用方式：
            event = Event(subject="test", data={"key": "value"})
            event_dict = event.to_dict()
            # {"event_id": "...", "subject": "test", ...}
        """
        return {
            "event_id": self.event_id,
            "subject": self.subject,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """
        从字典反序列化创建事件对象

        用于从存储或网络传输中恢复事件对象。

        Args:
            data: 包含事件字段的字典

        Returns:
            Event 对象实例

        使用方式：
            data_dict = {
                "event_id": "uuid-123",
                "subject": "order.created",
                "data": {"order_id": "12345"},
                "timestamp": "2025-10-27T10:30:00",
                "source": "order_manager"
            }
            event = Event.from_dict(data_dict)

        实现细节：
            - timestamp 从 ISO 格式字符串解析为 datetime 对象
            - 使用 object.__setattr__ 绕过 dataclass 的不可变性（如果有的话）
        """
        # 解析时间戳
        timestamp = datetime.fromisoformat(data["timestamp"])

        # 创建 Event 实例
        # 注意：不使用 default_factory，直接传入所有字段
        event = cls.__new__(cls)
        object.__setattr__(event, 'event_id', data["event_id"])
        object.__setattr__(event, 'subject', data["subject"])
        object.__setattr__(event, 'data', data["data"])
        object.__setattr__(event, 'timestamp', timestamp)
        object.__setattr__(event, 'source', data.get("source"))

        return event

    def validate(self) -> bool:
        """
        验证事件对象的有效性

        执行比 __post_init__ 更详细的验证逻辑，
        用于在运行时检查事件是否符合业务规则。

        Returns:
            True 如果事件有效，False 如果无效

        验证规则：
            - subject 必须是字符串类型（已在 __post_init__ 检查）
            - subject 不能为空字符串
            - data 必须是字典类型（已在 __post_init__ 检查）
            - data 可以为空字典

        使用方式：
            event = Event(subject="test", data={})
            if event.validate():
                # 处理事件
                pass
        """
        # 检查 subject 不为空
        if not self.subject or len(self.subject.strip()) == 0:
            return False

        # 类型检查已经在 __post_init__ 中完成
        # 这里只需要检查业务规则

        return True

