"""
Event模块

事件驱动架构的核心模块，包含：
- Event: 事件数据类
- EventBus: 事件总线（单例）
- AbstractEventStore: 事件存储抽象接口
- SQLiteEventStore: SQLite事件存储实现
"""

from src.core.event.event import Event
from src.core.event.event_bus import EventBus
from src.core.event.abstract_event_store import AbstractEventStore
from src.core.event.event_store import SQLiteEventStore

__all__ = [
    "Event",
    "EventBus",
    "AbstractEventStore",
    "SQLiteEventStore",
]

