"""
EventBus 事件总线

实现事件驱动架构的核心组件，提供：
- 单例模式：全局唯一的事件总线
- 订阅/发布：支持多个订阅者订阅同一事件
- 异步分发：并发执行所有处理器
- 通配符订阅：支持 fnmatch 模式匹配（如 order.*）
- 错误隔离：单个处理器失败不影响其他处理器
- 依赖注入：可选的 EventStore 持久化
- 可选持久化：可以选择是否持久化事件

使用方式：
    # 初始化（带持久化）
    store = SQLiteEventStore(db_path="data/events.db")
    bus = EventBus.get_instance(event_store=store)
    
    # 订阅事件
    async def handler(event):
        print(f"收到事件: {event.subject}")
    
    bus.subscribe("order.created", handler)
    bus.subscribe("order.*", handler)  # 通配符订阅
    
    # 发布事件
    event = Event(subject="order.created", data={"order_id": "12345"})
    await bus.publish(event)
"""

import asyncio
import fnmatch
from typing import Callable, Optional, List, Dict
from collections import defaultdict

from src.core.event.event import Event
from src.core.event.abstract_event_store import AbstractEventStore
from src.utils.logger import get_logger

logger = get_logger()


class EventBus:
    """
    事件总线 - 单例模式
    
    负责事件的订阅、发布和分发，是事件驱动架构的核心组件。
    
    Attributes:
        _instance: 单例实例
        _subscribers: 订阅者字典 {subject: [handler1, handler2, ...]}
        _event_store: 可选的事件存储
    
    设计原则：
        - 单例模式：全局唯一的事件总线
        - 依赖注入：通过构造函数注入 EventStore
        - 开闭原则：可以添加新的订阅者，不需要修改 EventBus
        - 错误隔离：单个处理器失败不影响其他处理器
    """
    
    _instance: Optional['EventBus'] = None
    
    def __init__(self, event_store: Optional[AbstractEventStore] = None):
        """
        初始化事件总线
        
        Args:
            event_store: 可选的事件存储，如果提供则自动持久化事件
        
        注意：
            不应该直接调用此方法，应该使用 get_instance() 获取单例
        """
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_store = event_store
        
        logger.info("事件总线初始化完成")
    
    @classmethod
    def get_instance(cls, event_store: Optional[AbstractEventStore] = None) -> 'EventBus':
        """
        获取事件总线单例
        
        Args:
            event_store: 可选的事件存储，仅在首次调用时有效
        
        Returns:
            EventBus 单例实例
        
        使用方式：
            bus = EventBus.get_instance()
            # 或
            store = SQLiteEventStore()
            bus = EventBus.get_instance(event_store=store)
        """
        if cls._instance is None:
            cls._instance = cls(event_store=event_store)
            logger.info("创建事件总线单例")
        return cls._instance
    
    def subscribe(self, subject: str, handler: Callable):
        """
        订阅事件
        
        Args:
            subject: 事件主题，支持通配符（如 order.*）
            handler: 事件处理器，必须是 async 函数
        
        使用方式：
            async def my_handler(event):
                print(event.subject)
            
            bus.subscribe("order.created", my_handler)
            bus.subscribe("order.*", my_handler)  # 通配符订阅
        
        实现细节：
            - 同一个 handler 可以订阅多个 subject
            - 同一个 subject 可以有多个 handler
            - 支持通配符模式（使用 fnmatch）
        """
        self._subscribers[subject].append(handler)
        logger.debug(f"订阅事件: {subject}, 处理器: {handler.__name__}")
    
    async def publish(self, event: Event, persist: bool = True):
        """
        发布事件
        
        Args:
            event: Event 对象
            persist: 是否持久化事件，默认 True
        
        使用方式：
            event = Event(subject="order.created", data={"order_id": "12345"})
            await bus.publish(event)
            
            # 不持久化
            await bus.publish(event, persist=False)
        
        实现细节：
            1. 可选持久化：如果提供了 EventStore 且 persist=True，则持久化事件
            2. 获取匹配的处理器：支持精确匹配和通配符匹配
            3. 异步分发：并发执行所有处理器
            4. 错误隔离：单个处理器失败不影响其他处理器
        """
        logger.info(f"发布事件: {event.subject}")
        
        # 1. 可选持久化
        if persist and self._event_store:
            try:
                self._event_store.insert_event(event)
                logger.debug(f"事件已持久化: {event.event_id}")
            except Exception as e:
                logger.error(f"事件持久化失败: {e}")
                # 持久化失败不影响事件分发
        
        # 2. 获取匹配的处理器
        handlers = self._get_matching_handlers(event.subject)
        
        if not handlers:
            logger.debug(f"没有订阅者订阅事件: {event.subject}")
            return
        
        logger.debug(f"找到 {len(handlers)} 个处理器")
        
        # 3. 异步分发事件
        await self._dispatch_event(event, handlers)
    
    def _get_matching_handlers(self, subject: str) -> List[Callable]:
        """
        获取匹配的处理器
        
        Args:
            subject: 事件主题
        
        Returns:
            匹配的处理器列表
        
        实现细节：
            - 精确匹配：subject 完全相同
            - 通配符匹配：使用 fnmatch 模式匹配
            - 去重：同一个处理器只返回一次
        """
        handlers = []
        
        for pattern, pattern_handlers in self._subscribers.items():
            # 使用 fnmatch 进行模式匹配
            if fnmatch.fnmatch(subject, pattern):
                handlers.extend(pattern_handlers)
        
        # 去重（保持顺序）
        seen = set()
        unique_handlers = []
        for handler in handlers:
            if handler not in seen:
                seen.add(handler)
                unique_handlers.append(handler)
        
        return unique_handlers
    
    async def _dispatch_event(self, event: Event, handlers: List[Callable]):
        """
        分发事件给处理器
        
        Args:
            event: Event 对象
            handlers: 处理器列表
        
        实现细节：
            - 并发执行所有处理器（使用 asyncio.gather）
            - 错误隔离：使用 return_exceptions=True
            - 处理器异常时记录日志并发布告警事件
        """
        # 创建所有处理器的任务
        tasks = [self._execute_handler(handler, event) for handler in handlers]
        
        # 并发执行所有任务，捕获异常
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有异常
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                handler = handlers[i]
                logger.error(
                    f"处理器执行失败: {handler.__name__}, "
                    f"事件: {event.subject}, "
                    f"错误: {result}"
                )
                
                # 发布告警事件（不持久化，避免无限循环）
                await self._publish_alert_event(event, handler, result)
    
    async def _execute_handler(self, handler: Callable, event: Event):
        """
        执行单个处理器
        
        Args:
            handler: 事件处理器
            event: Event 对象
        
        实现细节：
            - 调用处理器并传入事件
            - 如果处理器抛出异常，异常会被传播到 _dispatch_event
        """
        await handler(event)
    
    async def _publish_alert_event(self, original_event: Event, handler: Callable, error: Exception):
        """
        发布告警事件
        
        Args:
            original_event: 原始事件
            handler: 失败的处理器
            error: 异常对象
        
        实现细节：
            - 创建告警事件
            - 不持久化告警事件（避免无限循环）
            - 异步发布（不等待）
        """
        alert_event = Event(
            subject="system.alert.handler_error",
            data={
                "original_subject": original_event.subject,
                "original_event_id": original_event.event_id,
                "handler_name": handler.__name__,
                "error_type": type(error).__name__,
                "error_message": str(error)
            },
            source="event_bus"
        )
        
        # 不持久化告警事件，避免无限循环
        # 使用 asyncio.create_task 异步发布，不等待
        asyncio.create_task(self.publish(alert_event, persist=False))

