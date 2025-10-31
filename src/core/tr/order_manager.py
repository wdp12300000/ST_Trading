"""
订单管理器

OrderManager负责订单的提交、跟踪和撤销，包括：
1. 向DE模块发布订单创建事件
2. 向DE模块发布订单撤销事件
3. 跟踪订单状态
4. 处理订单精度

使用方式：
    order_manager = OrderManager(event_bus)
    await order_manager.submit_market_order(
        user_id="user_001",
        symbol="XRPUSDC",
        side="BUY",
        quantity=100
    )
"""

from typing import Optional
from loguru import logger
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.tr.tr_events import TREvents


class OrderManager:
    """
    订单管理器
    
    负责订单的提交、撤销和状态跟踪。
    
    Attributes:
        _event_bus: 事件总线实例
    
    Example:
        >>> event_bus = EventBus()
        >>> order_manager = OrderManager(event_bus)
        >>> await order_manager.submit_market_order("user_001", "XRPUSDC", "BUY", 100)
    """
    
    def __init__(self, event_bus: EventBus):
        """
        初始化订单管理器
        
        Args:
            event_bus: 事件总线实例
        """
        self._event_bus = event_bus
        logger.info(f"[order_manager.py:{self._get_line_number()}] OrderManager初始化完成")
    
    async def submit_market_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float
    ) -> None:
        """
        提交市价单
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            side: 方向（"BUY" 或 "SELL"）
            quantity: 数量
        
        Example:
            >>> await order_manager.submit_market_order("user_001", "XRPUSDC", "BUY", 100)
        """
        event = Event(
            subject=TREvents.ORDER_CREATE,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "order_type": "MARKET",
                "quantity": quantity
            },
            source="tr"
        )
        
        await self._event_bus.publish(event)
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 提交市价单: "
            f"{user_id}/{symbol} {side} 数量={quantity}"
        )
    
    async def submit_limit_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> None:
        """
        提交限价单
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            side: 方向（"BUY" 或 "SELL"）
            quantity: 数量
            price: 价格
        
        Example:
            >>> await order_manager.submit_limit_order("user_001", "XRPUSDC", "BUY", 100, 1.0)
        """
        event = Event(
            subject=TREvents.ORDER_CREATE,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "order_type": "LIMIT",
                "quantity": quantity,
                "price": price
            },
            source="tr"
        )
        
        await self._event_bus.publish(event)
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 提交限价单: "
            f"{user_id}/{symbol} {side} 价格={price} 数量={quantity}"
        )
    
    async def submit_post_only_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float
    ) -> None:
        """
        提交POST_ONLY订单（只做Maker）
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            side: 方向（"BUY" 或 "SELL"）
            quantity: 数量
            price: 价格
        
        Example:
            >>> await order_manager.submit_post_only_order("user_001", "XRPUSDC", "BUY", 100, 1.0)
        """
        event = Event(
            subject=TREvents.ORDER_CREATE,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "side": side,
                "order_type": "POST_ONLY",
                "quantity": quantity,
                "price": price
            },
            source="tr"
        )
        
        await self._event_bus.publish(event)
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 提交POST_ONLY订单: "
            f"{user_id}/{symbol} {side} 价格={price} 数量={quantity}"
        )
    
    async def cancel_order(
        self,
        user_id: str,
        symbol: str,
        order_id: str
    ) -> None:
        """
        撤销订单
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            order_id: 订单ID
        
        Example:
            >>> await order_manager.cancel_order("user_001", "XRPUSDC", "12345")
        """
        event = Event(
            subject=TREvents.ORDER_CANCEL,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "order_id": order_id
            },
            source="tr"
        )
        
        await self._event_bus.publish(event)
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 撤销订单: "
            f"{user_id}/{symbol} 订单ID={order_id}"
        )
    
    async def cancel_all_orders(
        self,
        user_id: str,
        symbol: str,
        order_ids: list
    ) -> None:
        """
        批量撤销订单
        
        Args:
            user_id: 用户ID
            symbol: 交易对符号
            order_ids: 订单ID列表
        
        Example:
            >>> await order_manager.cancel_all_orders("user_001", "XRPUSDC", ["12345", "12346"])
        """
        for order_id in order_ids:
            await self.cancel_order(user_id, symbol, order_id)
        
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 批量撤销订单: "
            f"{user_id}/{symbol} 数量={len(order_ids)}"
        )
    
    async def request_account_balance(
        self,
        user_id: str,
        asset: str
    ) -> None:
        """
        请求账户余额
        
        Args:
            user_id: 用户ID
            asset: 资产类型（如 "USDT" 或 "USDC"）
        
        Example:
            >>> await order_manager.request_account_balance("user_001", "USDC")
        """
        event = Event(
            subject=TREvents.ACCOUNT_BALANCE_REQUEST,
            data={
                "user_id": user_id,
                "asset": asset
            },
            source="tr"
        )
        
        await self._event_bus.publish(event)
        logger.info(
            f"[order_manager.py:{self._get_line_number()}] 请求账户余额: "
            f"{user_id} 资产={asset}"
        )
    
    @staticmethod
    def round_price(price: float, precision: int) -> float:
        """
        价格精度处理
        
        Args:
            price: 原始价格
            precision: 精度（小数位数）
        
        Returns:
            float: 处理后的价格
        
        Example:
            >>> OrderManager.round_price(1.23456, 2)
            1.23
        """
        return round(price, precision)
    
    @staticmethod
    def round_quantity(quantity: float, precision: int) -> float:
        """
        数量精度处理
        
        Args:
            quantity: 原始数量
            precision: 精度（小数位数）
        
        Returns:
            float: 处理后的数量
        
        Example:
            >>> OrderManager.round_quantity(100.123, 0)
            100.0
        """
        return round(quantity, precision)
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

