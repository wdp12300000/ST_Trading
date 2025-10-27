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

