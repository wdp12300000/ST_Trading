"""
AbstractEventStore 抽象接口

定义事件存储的抽象接口，遵循依赖倒置原则。
具体实现可以是 SQLite、Redis、内存存储等。

使用方式：
    class SQLiteEventStore(AbstractEventStore):
        def insert_event(self, event: Event):
            # 具体实现
            pass
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

from src.core.event.event import Event


class AbstractEventStore(ABC):
    """
    事件存储抽象接口
    
    定义事件存储的标准接口，所有具体实现必须遵循此接口。
    
    设计原则：
        - 依赖倒置原则：高层模块（EventBus）依赖抽象接口，而非具体实现
        - 开闭原则：对扩展开放（可以添加新的存储实现），对修改关闭
    
    使用场景：
        - SQLite 存储：用于本地持久化
        - Redis 存储：用于高性能缓存
        - 内存存储：用于测试环境
        - 远程存储：用于分布式系统
    """
    
    @abstractmethod
    def insert_event(self, event: Event):
        """
        插入事件到存储
        
        Args:
            event: Event 对象
        
        实现要求：
            - 必须持久化事件的所有字段
            - 必须处理并发插入
            - 失败时应该抛出异常
        """
        pass
    
    @abstractmethod
    def query_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        查询最近的事件
        
        Args:
            limit: 返回的最大事件数量
        
        Returns:
            事件列表，按时间倒序排列（最新的在前）
        
        实现要求：
            - 必须按时间倒序排列
            - 返回的字典必须包含所有事件字段
            - timestamp 应该是 datetime 对象
        """
        pass
    
    @abstractmethod
    def query_events_by_subject(self, subject: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        按主题查询事件
        
        Args:
            subject: 事件主题
            limit: 返回的最大事件数量
        
        Returns:
            匹配主题的事件列表，按时间倒序排列
        
        实现要求：
            - 必须精确匹配 subject
            - 必须按时间倒序排列
        """
        pass
    
    @abstractmethod
    def cleanup_old_events(self):
        """
        清理旧事件
        
        实现要求：
            - 具体的清理策略由实现类决定
            - 例如：保留最近 N 条记录，或删除 N 天前的记录
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        关闭存储连接
        
        实现要求：
            - 必须释放所有资源
            - 必须提交未完成的事务
        """
        pass

