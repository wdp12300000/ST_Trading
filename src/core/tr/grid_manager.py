"""
网格管理器

GridManager负责网格订单的创建、管理和配对，包括：
1. 批量创建网格订单
2. 网格订单配对管理
3. 网格移动逻辑
4. 网格订单撤销

使用方式:
    manager = GridManager(event_bus, order_manager, precision_handler)
    
    await manager.create_grid_orders(
        user_id="user_001",
        symbol="XRPUSDC",
        upper_price=1.05,
        lower_price=0.95,
        grid_levels=10,
        total_quantity=1000.0,
        side="BUY"
    )
"""

from typing import Dict, List, Optional, Any
from loguru import logger
from src.core.event.event_bus import EventBus
from src.core.tr.order_manager import OrderManager
from src.core.tr.precision_handler import PrecisionHandler
from src.core.tr.grid_calculator import GridCalculator, GridOrder


class GridPair:
    """
    网格配对数据类
    
    记录买单和卖单的配对关系，用于利润计算。
    
    Attributes:
        pair_id: 配对ID
        buy_order_id: 买单订单ID
        sell_order_id: 卖单订单ID
        buy_price: 买入价格
        sell_price: 卖出价格
        quantity: 数量
        is_completed: 是否完成（两个订单都成交）
    """
    
    def __init__(
        self,
        pair_id: str,
        buy_price: float,
        sell_price: float,
        quantity: float
    ):
        self.pair_id = pair_id
        self.buy_order_id: Optional[str] = None
        self.sell_order_id: Optional[str] = None
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.quantity = quantity
        self.is_completed = False
    
    def set_buy_order(self, order_id: str) -> None:
        """设置买单订单ID"""
        self.buy_order_id = order_id
    
    def set_sell_order(self, order_id: str) -> None:
        """设置卖单订单ID"""
        self.sell_order_id = order_id
    
    def mark_completed(self) -> None:
        """标记为完成"""
        self.is_completed = True
    
    def calculate_profit(self, fee_rate: float = 0.0004) -> float:
        """
        计算配对利润
        
        Args:
            fee_rate: 手续费率（默认0.04%）
        
        Returns:
            float: 利润金额
        """
        # 利润 = (卖价 - 买价) × 数量 - 手续费
        price_diff = self.sell_price - self.buy_price
        gross_profit = price_diff * self.quantity
        
        # 手续费 = 买入手续费 + 卖出手续费
        buy_fee = self.buy_price * self.quantity * fee_rate
        sell_fee = self.sell_price * self.quantity * fee_rate
        total_fee = buy_fee + sell_fee
        
        net_profit = gross_profit - total_fee
        
        return net_profit


class GridManager:
    """
    网格管理器
    
    负责网格订单的创建、管理和配对。
    
    Attributes:
        _event_bus: 事件总线
        _order_manager: 订单管理器
        _precision_handler: 精度处理器
        _calculator: 网格计算器
        _grid_pairs: 网格配对字典 {symbol: {pair_id: GridPair}}
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        order_manager: OrderManager,
        precision_handler: PrecisionHandler
    ):
        """
        初始化网格管理器
        
        Args:
            event_bus: 事件总线
            order_manager: 订单管理器
            precision_handler: 精度处理器
        """
        self._event_bus = event_bus
        self._order_manager = order_manager
        self._precision_handler = precision_handler
        self._calculator = GridCalculator()
        
        # 网格配对管理: {symbol: {pair_id: GridPair}}
        self._grid_pairs: Dict[str, Dict[str, GridPair]] = {}
        
        logger.info(f"[grid_manager.py:{self._get_line_number()}] 网格管理器初始化完成")
    
    async def create_grid_orders(
        self,
        user_id: str,
        symbol: str,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        total_quantity: float,
        side: str,
        order_type: str = "LIMIT"
    ) -> List[str]:
        """
        创建网格订单
        
        Args:
            user_id: 用户ID
            symbol: 交易对
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
            total_quantity: 总数量
            side: 订单方向（"BUY" 或 "SELL"）
            order_type: 订单类型（"LIMIT" 或 "POST_ONLY"）
        
        Returns:
            List[str]: 订单ID列表（占位符，实际由DE模块返回）
        
        Example:
            >>> await manager.create_grid_orders(
            ...     "user_001", "XRPUSDC", 1.05, 0.95, 10, 1000.0, "BUY"
            ... )
        """
        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 创建网格订单: "
            f"{symbol} 上边={upper_price} 下边={lower_price} 层数={grid_levels}"
        )
        
        # 计算网格订单
        grid_orders = self._calculator.calculate_grid_orders(
            upper_price, lower_price, grid_levels, total_quantity, side
        )
        
        # 批量提交订单
        order_ids = []
        for grid_order in grid_orders:
            # 精度处理
            price, quantity = self._precision_handler.process_order_params(
                symbol, grid_order.price, grid_order.quantity
            )
            
            # 验证订单
            is_valid, error = self._precision_handler.validate_order(symbol, price, quantity)
            if not is_valid:
                logger.warning(
                    f"[grid_manager.py:{self._get_line_number()}] "
                    f"网格订单无效，跳过: {error}"
                )
                continue
            
            # 提交订单
            if order_type == "POST_ONLY":
                await self._order_manager.submit_post_only_order(
                    user_id, symbol, grid_order.side, quantity, price
                )
            else:
                await self._order_manager.submit_limit_order(
                    user_id, symbol, grid_order.side, quantity, price
                )
            
            # TODO: 实际订单ID应该从DE模块的订单提交成功事件中获取
            order_ids.append(f"grid_{symbol}_{grid_order.level}")
        
        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 网格订单创建完成: "
            f"{symbol} 订单数量={len(order_ids)}"
        )
        
        return order_ids
    
    async def create_symmetric_grid_orders(
        self,
        user_id: str,
        symbol: str,
        entry_price: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        total_quantity: float,
        order_type: str = "LIMIT"
    ) -> Dict[str, List[str]]:
        """
        创建对称网格订单（买单和卖单）
        
        Args:
            user_id: 用户ID
            symbol: 交易对
            entry_price: 入场价格
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
            total_quantity: 总数量
            order_type: 订单类型
        
        Returns:
            Dict[str, List[str]]: {"buy_order_ids": [...], "sell_order_ids": [...]}
        """
        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 创建对称网格订单: "
            f"{symbol} 入场价={entry_price}"
        )
        
        # 计算对称网格订单
        orders = self._calculator.calculate_symmetric_grid_orders(
            entry_price, upper_price, lower_price, grid_levels, total_quantity
        )
        
        buy_order_ids = []
        sell_order_ids = []
        
        # 创建买单
        for grid_order in orders["buy_orders"]:
            price, quantity = self._precision_handler.process_order_params(
                symbol, grid_order.price, grid_order.quantity
            )
            
            is_valid, error = self._precision_handler.validate_order(symbol, price, quantity)
            if not is_valid:
                logger.warning(
                    f"[grid_manager.py:{self._get_line_number()}] "
                    f"买单无效，跳过: {error}"
                )
                continue
            
            if order_type == "POST_ONLY":
                await self._order_manager.submit_post_only_order(
                    user_id, symbol, "BUY", quantity, price
                )
            else:
                await self._order_manager.submit_limit_order(
                    user_id, symbol, "BUY", quantity, price
                )
            
            buy_order_ids.append(f"grid_buy_{symbol}_{grid_order.level}")
        
        # 创建卖单
        for grid_order in orders["sell_orders"]:
            price, quantity = self._precision_handler.process_order_params(
                symbol, grid_order.price, grid_order.quantity
            )
            
            is_valid, error = self._precision_handler.validate_order(symbol, price, quantity)
            if not is_valid:
                logger.warning(
                    f"[grid_manager.py:{self._get_line_number()}] "
                    f"卖单无效，跳过: {error}"
                )
                continue
            
            if order_type == "POST_ONLY":
                await self._order_manager.submit_post_only_order(
                    user_id, symbol, "SELL", quantity, price
                )
            else:
                await self._order_manager.submit_limit_order(
                    user_id, symbol, "SELL", quantity, price
                )
            
            sell_order_ids.append(f"grid_sell_{symbol}_{grid_order.level}")
        
        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 对称网格订单创建完成: "
            f"{symbol} 买单={len(buy_order_ids)} 卖单={len(sell_order_ids)}"
        )
        
        return {
            "buy_order_ids": buy_order_ids,
            "sell_order_ids": sell_order_ids
        }
    
    def create_grid_pair(
        self,
        symbol: str,
        buy_price: float,
        sell_price: float,
        quantity: float
    ) -> str:
        """
        创建网格配对

        Args:
            symbol: 交易对
            buy_price: 买入价格
            sell_price: 卖出价格
            quantity: 数量

        Returns:
            str: 配对ID
        """
        if symbol not in self._grid_pairs:
            self._grid_pairs[symbol] = {}

        # 生成配对ID
        pair_id = f"{symbol}_{len(self._grid_pairs[symbol])}"

        # 创建配对
        pair = GridPair(pair_id, buy_price, sell_price, quantity)
        self._grid_pairs[symbol][pair_id] = pair

        logger.debug(
            f"[grid_manager.py:{self._get_line_number()}] 创建网格配对: "
            f"{pair_id} 买价={buy_price} 卖价={sell_price}"
        )

        return pair_id

    def update_grid_pair_order(
        self,
        symbol: str,
        pair_id: str,
        order_id: str,
        side: str
    ) -> None:
        """
        更新网格配对的订单ID

        Args:
            symbol: 交易对
            pair_id: 配对ID
            order_id: 订单ID
            side: 订单方向（"BUY" 或 "SELL"）
        """
        if symbol not in self._grid_pairs:
            logger.warning(
                f"[grid_manager.py:{self._get_line_number()}] "
                f"交易对不存在: {symbol}"
            )
            return

        if pair_id not in self._grid_pairs[symbol]:
            logger.warning(
                f"[grid_manager.py:{self._get_line_number()}] "
                f"配对不存在: {pair_id}"
            )
            return

        pair = self._grid_pairs[symbol][pair_id]

        if side == "BUY":
            pair.set_buy_order(order_id)
        elif side == "SELL":
            pair.set_sell_order(order_id)

        logger.debug(
            f"[grid_manager.py:{self._get_line_number()}] 更新网格配对订单: "
            f"{pair_id} {side}={order_id}"
        )

    def mark_pair_completed(self, symbol: str, pair_id: str) -> Optional[float]:
        """
        标记配对完成并计算利润

        Args:
            symbol: 交易对
            pair_id: 配对ID

        Returns:
            Optional[float]: 利润金额，如果配对不存在则返回None
        """
        if symbol not in self._grid_pairs:
            return None

        if pair_id not in self._grid_pairs[symbol]:
            return None

        pair = self._grid_pairs[symbol][pair_id]
        pair.mark_completed()

        profit = pair.calculate_profit()

        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 网格配对完成: "
            f"{pair_id} 利润={profit}"
        )

        return profit

    def get_grid_pairs(self, symbol: str) -> Dict[str, GridPair]:
        """
        获取交易对的所有网格配对

        Args:
            symbol: 交易对

        Returns:
            Dict[str, GridPair]: 配对字典
        """
        return self._grid_pairs.get(symbol, {})

    def clear_grid_pairs(self, symbol: str) -> None:
        """
        清除交易对的所有网格配对

        Args:
            symbol: 交易对
        """
        if symbol in self._grid_pairs:
            count = len(self._grid_pairs[symbol])
            del self._grid_pairs[symbol]

            logger.info(
                f"[grid_manager.py:{self._get_line_number()}] 清除网格配对: "
                f"{symbol} 数量={count}"
            )

    async def cancel_all_grid_orders(
        self,
        user_id: str,
        symbol: str,
        order_ids: List[str]
    ) -> None:
        """
        撤销所有网格订单

        Args:
            user_id: 用户ID
            symbol: 交易对
            order_ids: 订单ID列表
        """
        logger.info(
            f"[grid_manager.py:{self._get_line_number()}] 撤销网格订单: "
            f"{symbol} 数量={len(order_ids)}"
        )

        await self._order_manager.cancel_all_orders(user_id, symbol, order_ids)

        # 清除配对
        self.clear_grid_pairs(symbol)

    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

