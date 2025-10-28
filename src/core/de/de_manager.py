"""
DEManager（DE管理器）类

负责管理多个BinanceClient实例，包括：
- 订阅pm.account.loaded事件
- 创建和管理多个BinanceClient实例
- 维护user_id到BinanceClient的映射关系
- 提供BinanceClient实例的查询接口
- 系统关闭时的清理工作

使用方式：
    from src.core.de.de_manager import DEManager
    from src.core.event_bus import EventBus

    bus = EventBus.get_instance()
    manager = DEManager.get_instance(event_bus=bus)

    # 获取BinanceClient实例
    client = manager.get_client("user_001")

    # 系统关闭
    await manager.shutdown()
"""

import time
from typing import Dict, List, Optional
from src.core.event import Event, EventBus
from src.core.de.binance_client import BinanceClient
from src.core.de.de_events import DEEvents
from src.core.pm.pm_events import PMEvents
from src.utils.logger import logger


class DEManager:
    """
    DE管理器，负责管理多个BinanceClient实例（单例模式）

    职责：
    - 订阅pm.account.loaded事件
    - 创建和管理多个BinanceClient实例
    - 维护user_id到BinanceClient的映射关系
    - 提供BinanceClient实例的查询接口
    - 发布de.client.connected和de.client.connection_failed事件
    - 系统关闭时的清理工作

    设计原则：
    - 单例模式：全局唯一的DE管理器
    - 面向对象：所有功能封装在类方法中
    - 错误隔离：单个账户创建失败不影响其他账户
    - 事件驱动：通过事件与其他模块通信

    Attributes:
        _instance: 单例实例（类属性）
        _clients: 用户ID到BinanceClient实例的映射（私有）
        _event_bus: 事件总线（私有）
    """

    _instance = None  # 单例实例

    def __init__(self, event_bus: EventBus):
        """
        私有构造函数（通过get_instance调用）

        Args:
            event_bus: 事件总线实例

        实现细节：
            - 初始化客户端字典
            - 订阅pm.account.loaded事件
            - 订阅trading.order.create事件
            - 订阅trading.order.cancel事件
            - 订阅trading.get_account_balance事件
        """
        self._event_bus = event_bus
        self._clients: Dict[str, BinanceClient] = {}

        # 订阅pm.account.loaded事件
        self._event_bus.subscribe(PMEvents.ACCOUNT_LOADED, self._on_account_loaded)

        # 订阅订单事件
        self._event_bus.subscribe(DEEvents.INPUT_ORDER_CREATE, self._on_order_create)
        self._event_bus.subscribe(DEEvents.INPUT_ORDER_CANCEL, self._on_order_cancel)

        # 订阅账户余额查询事件
        self._event_bus.subscribe(DEEvents.INPUT_GET_ACCOUNT_BALANCE, self._on_get_account_balance)

        logger.info("DEManager初始化完成")

    @classmethod
    def get_instance(cls, event_bus: EventBus = None) -> "DEManager":
        """
        获取DEManager单例实例

        Args:
            event_bus: 事件总线实例（首次调用必需）

        Returns:
            DEManager单例实例

        Raises:
            ValueError: 首次调用时未提供event_bus

        实现细节：
            - 首次调用时创建实例
            - 后续调用返回已有实例
            - 首次调用必须提供event_bus
        """
        if cls._instance is None:
            if event_bus is None:
                raise ValueError("首次调用必须提供event_bus")
            cls._instance = cls(event_bus)
            logger.info("DEManager单例实例已创建")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（主要用于测试）

        实现细节：
            - 将_instance设为None
            - 下次调用get_instance时会创建新实例
        """
        cls._instance = None
        logger.debug("DEManager单例实例已重置")

    async def _on_account_loaded(self, event: Event) -> None:
        """
        处理pm.account.loaded事件（私有方法）

        Args:
            event: pm.account.loaded事件

        实现细节：
            1. 从事件数据中提取user_id、api_key、api_secret
            2. 创建BinanceClient实例
            3. 如果成功，发布de.client.connected事件
            4. 如果失败，发布de.client.connection_failed事件
            5. 记录日志
        """
        try:
            # 提取事件数据
            user_id = event.data.get("user_id")
            api_key = event.data.get("api_key")
            api_secret = event.data.get("api_secret")

            # 验证必需字段
            if not user_id or not api_key or not api_secret:
                missing_fields = []
                if not user_id:
                    missing_fields.append("user_id")
                if not api_key:
                    missing_fields.append("api_key")
                if not api_secret:
                    missing_fields.append("api_secret")

                error_msg = f"缺少必需字段: {', '.join(missing_fields)}"
                logger.error(f"账户加载失败: user_id={user_id}, error={error_msg}")

                # 发布连接失败事件
                await self._publish_connection_failed(user_id or "unknown", "missing_fields", error_msg)
                return

            # 创建BinanceClient实例
            logger.info(f"创建BinanceClient: user_id={user_id}")
            client = BinanceClient(
                user_id=user_id,
                api_key=api_key,
                api_secret=api_secret
            )

            # 保存到字典
            self._clients[user_id] = client

            # 发布连接成功事件
            await self._publish_client_connected(user_id)

            logger.info(f"BinanceClient创建成功: user_id={user_id}")

        except Exception as e:
            user_id = event.data.get("user_id", "unknown")
            error_msg = str(e)
            logger.error(f"创建BinanceClient失败: user_id={user_id}, error={error_msg}")

            # 发布连接失败事件
            await self._publish_connection_failed(user_id, "creation_error", error_msg)

    async def _publish_client_connected(self, user_id: str) -> None:
        """
        发布de.client.connected事件（私有方法）

        Args:
            user_id: 用户ID

        实现细节：
            - 创建de.client.connected事件
            - 包含user_id和timestamp
            - 异步发布到事件总线
        """
        event = Event(
            subject=DEEvents.CLIENT_CONNECTED,
            data={
                "user_id": user_id,
                "timestamp": int(time.time() * 1000)
            },
            source="DE"
        )

        await self._event_bus.publish(event)
        logger.debug(f"发布de.client.connected事件: user_id={user_id}")

    async def _publish_connection_failed(self, user_id: str, error_type: str, error_message: str) -> None:
        """
        发布de.client.connection_failed事件（私有方法）

        Args:
            user_id: 用户ID
            error_type: 错误类型
            error_message: 错误消息

        实现细节：
            - 创建de.client.connection_failed事件
            - 包含user_id、error_type、error_message
            - 异步发布到事件总线
        """
        event = Event(
            subject=DEEvents.CLIENT_CONNECTION_FAILED,
            data={
                "user_id": user_id,
                "error_type": error_type,
                "error_message": error_message
            },
            source="DE"
        )

        await self._event_bus.publish(event)
        logger.debug(f"发布de.client.connection_failed事件: user_id={user_id}, error={error_message}")

    # ==================== 公共查询接口 ====================

    def get_client(self, user_id: str) -> Optional[BinanceClient]:
        """
        获取指定用户的BinanceClient实例

        Args:
            user_id: 用户ID

        Returns:
            BinanceClient实例，如果不存在则返回None

        使用方式：
            client = manager.get_client("user_001")
            if client:
                klines = await client.get_historical_klines("BTCUSDT", "1h", 100)
        """
        return self._clients.get(user_id)

    def get_all_user_ids(self) -> List[str]:
        """
        获取所有已创建BinanceClient的用户ID列表

        Returns:
            用户ID列表

        使用方式：
            user_ids = manager.get_all_user_ids()
            for user_id in user_ids:
                client = manager.get_client(user_id)
        """
        return list(self._clients.keys())

    def has_client(self, user_id: str) -> bool:
        """
        检查是否存在指定用户的BinanceClient

        Args:
            user_id: 用户ID

        Returns:
            如果存在返回True，否则返回False

        使用方式：
            if manager.has_client("user_001"):
                client = manager.get_client("user_001")
        """
        return user_id in self._clients

    def get_client_count(self) -> int:
        """
        获取当前管理的BinanceClient数量

        Returns:
            客户端数量

        使用方式：
            count = manager.get_client_count()
            logger.info(f"当前管理{count}个客户端")
        """
        return len(self._clients)

    # ==================== 系统关闭 ====================

    async def shutdown(self) -> None:
        """
        关闭DE管理器，清理所有资源

        实现细节：
            1. 清空所有BinanceClient实例
            2. 记录日志

        使用方式：
            await manager.shutdown()
        """
        logger.info(f"DEManager关闭中，清理{len(self._clients)}个客户端")

        # 清空客户端字典
        self._clients.clear()

        logger.info("DEManager已关闭")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"DEManager(clients={len(self._clients)})"

    # ==================== 订单事件处理 ====================

    async def _on_order_create(self, event: Event) -> None:
        """
        处理trading.order.create事件（私有方法）

        Args:
            event: trading.order.create事件

        实现细节：
            1. 从事件数据中提取user_id、symbol、side、order_type、quantity等参数
            2. 获取对应的BinanceClient实例
            3. 调用BinanceClient.place_order方法
            4. 成功时发布de.order.submitted事件
            5. 失败时发布de.order.failed事件
        """
        data = event.data
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        side = data.get("side")
        order_type = data.get("order_type")
        quantity = data.get("quantity")
        price = data.get("price")

        logger.debug(f"处理订单创建事件: user_id={user_id}, symbol={symbol}, side={side}, type={order_type}")

        # 检查客户端是否存在
        if user_id not in self._clients:
            logger.error(f"订单创建失败: user_id={user_id}的客户端不存在")
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_FAILED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "error": f"客户端不存在: user_id={user_id}",
                    "retry_count": 0
                }
            ))
            return

        client = self._clients[user_id]

        try:
            # 调用BinanceClient.place_order
            result = await client.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price
            )

            # 发布订单提交成功事件
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_SUBMITTED,
                data={
                    "user_id": user_id,
                    "order_id": result.get("orderId"),
                    "symbol": result.get("symbol"),
                    "side": result.get("side"),
                    "type": result.get("type"),
                    "quantity": result.get("origQty"),
                    "price": result.get("price", "0")
                }
            ))

            logger.info(f"订单提交成功: user_id={user_id}, order_id={result.get('orderId')}, symbol={symbol}")

        except Exception as e:
            logger.error(f"订单提交失败: user_id={user_id}, symbol={symbol}, error={e}")
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_FAILED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "error": str(e),
                    "retry_count": 0
                }
            ))

    async def _on_order_cancel(self, event: Event) -> None:
        """
        处理trading.order.cancel事件（私有方法）

        Args:
            event: trading.order.cancel事件

        实现细节：
            1. 从事件数据中提取user_id、symbol、order_id等参数
            2. 获取对应的BinanceClient实例
            3. 调用BinanceClient.cancel_order方法
            4. 成功时发布de.order.cancelled事件
            5. 失败时发布de.order.failed事件
        """
        data = event.data
        user_id = data.get("user_id")
        symbol = data.get("symbol")
        order_id = data.get("order_id")
        client_order_id = data.get("client_order_id")

        logger.debug(f"处理订单取消事件: user_id={user_id}, symbol={symbol}, order_id={order_id}")

        # 检查客户端是否存在
        if user_id not in self._clients:
            logger.error(f"订单取消失败: user_id={user_id}的客户端不存在")
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_FAILED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "error": f"客户端不存在: user_id={user_id}",
                    "retry_count": 0
                }
            ))
            return

        client = self._clients[user_id]

        try:
            # 调用BinanceClient.cancel_order
            result = await client.cancel_order(
                symbol=symbol,
                order_id=order_id,
                client_order_id=client_order_id
            )

            # 发布订单取消成功事件
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_CANCELLED,
                data={
                    "user_id": user_id,
                    "order_id": result.get("orderId"),
                    "symbol": result.get("symbol"),
                    "status": result.get("status")
                }
            ))

            logger.info(f"订单取消成功: user_id={user_id}, order_id={result.get('orderId')}, symbol={symbol}")

        except Exception as e:
            logger.error(f"订单取消失败: user_id={user_id}, symbol={symbol}, order_id={order_id}, error={e}")
            await self._event_bus.publish(Event(
                subject=DEEvents.ORDER_FAILED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "error": str(e),
                    "retry_count": 0
                }
            ))

    # ==================== 账户余额查询事件处理 ====================

    async def _on_get_account_balance(self, event: Event) -> None:
        """
        处理trading.get_account_balance事件（私有方法）

        Args:
            event: trading.get_account_balance事件

        实现细节：
            1. 从事件数据中提取user_id和asset参数
            2. 获取对应的BinanceClient实例
            3. 调用BinanceClient.get_account_balance方法
            4. 成功时发布de.account.balance事件
            5. 失败时只记录日志，不发布事件
        """
        data = event.data
        user_id = data.get("user_id")
        asset = data.get("asset", "USDT")

        logger.debug(f"处理账户余额查询事件: user_id={user_id}, asset={asset}")

        # 检查客户端是否存在
        if user_id not in self._clients:
            logger.error(f"账户余额查询失败: user_id={user_id}的客户端不存在")
            return

        client = self._clients[user_id]

        try:
            # 调用BinanceClient.get_account_balance
            result = await client.get_account_balance(asset=asset)

            # 发布账户余额事件
            await self._event_bus.publish(Event(
                subject=DEEvents.ACCOUNT_BALANCE,
                data={
                    "user_id": user_id,
                    "asset": result.get("asset"),
                    "balance": result.get("balance"),
                    "available_balance": result.get("availableBalance")
                }
            ))

            logger.info(f"账户余额查询成功: user_id={user_id}, asset={asset}, balance={result.get('availableBalance')}")

        except Exception as e:
            logger.error(f"账户余额查询失败: user_id={user_id}, asset={asset}, error={e}")
