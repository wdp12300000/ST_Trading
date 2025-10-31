"""
网格计算器

GridCalculator负责计算网格交易的价格和数量，包括：
1. 网格价格间隔计算
2. 网格订单价格计算
3. 网格订单数量分配

使用方式:
    calculator = GridCalculator()
    
    grid_orders = calculator.calculate_grid_orders(
        upper_price=1.05,
        lower_price=0.95,
        grid_levels=10,
        total_quantity=1000.0,
        side="BUY"
    )
"""

from typing import List, Dict, Any
from loguru import logger


class GridOrder:
    """
    网格订单数据类
    
    Attributes:
        price: 订单价格
        quantity: 订单数量
        side: 订单方向（BUY/SELL）
        level: 网格层级（0-based）
    """
    
    def __init__(self, price: float, quantity: float, side: str, level: int):
        self.price = price
        self.quantity = quantity
        self.side = side
        self.level = level
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "price": self.price,
            "quantity": self.quantity,
            "side": self.side,
            "level": self.level
        }


class GridCalculator:
    """
    网格计算器
    
    负责计算网格交易的价格和数量分配。
    
    Example:
        >>> calculator = GridCalculator()
        >>> orders = calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "BUY")
        >>> print(len(orders))  # 10
    """
    
    def __init__(self):
        """初始化网格计算器"""
        logger.info(f"[grid_calculator.py:{self._get_line_number()}] 网格计算器初始化完成")
    
    def calculate_price_interval(
        self,
        upper_price: float,
        lower_price: float,
        grid_levels: int
    ) -> float:
        """
        计算网格价格间隔
        
        公式：价格间隔 = (上边价格 - 下边价格) / 网格层数
        
        Args:
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
        
        Returns:
            float: 价格间隔
        
        Raises:
            ValueError: 如果参数无效
        
        Example:
            >>> calculator = GridCalculator()
            >>> interval = calculator.calculate_price_interval(1.05, 0.95, 10)
            >>> print(interval)  # 0.01
        """
        if upper_price <= lower_price:
            raise ValueError(f"上边价格必须大于下边价格: {upper_price} <= {lower_price}")
        
        if grid_levels <= 0:
            raise ValueError(f"网格层数必须大于0: {grid_levels}")
        
        interval = (upper_price - lower_price) / grid_levels
        
        logger.debug(
            f"[grid_calculator.py:{self._get_line_number()}] 价格间隔计算: "
            f"上边={upper_price} 下边={lower_price} 层数={grid_levels} 间隔={interval}"
        )
        
        return interval
    
    def calculate_grid_prices(
        self,
        upper_price: float,
        lower_price: float,
        grid_levels: int
    ) -> List[float]:
        """
        计算所有网格价格
        
        Args:
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
        
        Returns:
            List[float]: 网格价格列表（从下到上）
        
        Example:
            >>> calculator = GridCalculator()
            >>> prices = calculator.calculate_grid_prices(1.05, 0.95, 10)
            >>> print(prices)  # [0.95, 0.96, 0.97, ..., 1.04, 1.05]
        """
        interval = self.calculate_price_interval(upper_price, lower_price, grid_levels)
        
        prices = []
        for i in range(grid_levels + 1):
            price = lower_price + i * interval
            prices.append(price)
        
        logger.debug(
            f"[grid_calculator.py:{self._get_line_number()}] 网格价格计算完成: "
            f"层数={grid_levels} 价格数量={len(prices)}"
        )
        
        return prices
    
    def calculate_grid_orders(
        self,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        total_quantity: float,
        side: str
    ) -> List[GridOrder]:
        """
        计算网格订单
        
        平均分配数量到每个网格层级。
        
        Args:
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
            total_quantity: 总数量
            side: 订单方向（"BUY" 或 "SELL"）
        
        Returns:
            List[GridOrder]: 网格订单列表
        
        Example:
            >>> calculator = GridCalculator()
            >>> orders = calculator.calculate_grid_orders(1.05, 0.95, 10, 1000.0, "BUY")
            >>> print(len(orders))  # 10
            >>> print(orders[0].quantity)  # 100.0
        """
        if total_quantity <= 0:
            raise ValueError(f"总数量必须大于0: {total_quantity}")
        
        if side not in ["BUY", "SELL"]:
            raise ValueError(f"订单方向必须是BUY或SELL: {side}")
        
        # 计算网格价格
        prices = self.calculate_grid_prices(upper_price, lower_price, grid_levels)
        
        # 平均分配数量
        quantity_per_level = total_quantity / grid_levels
        
        # 创建网格订单
        orders = []
        for i in range(grid_levels):
            order = GridOrder(
                price=prices[i],
                quantity=quantity_per_level,
                side=side,
                level=i
            )
            orders.append(order)
        
        logger.info(
            f"[grid_calculator.py:{self._get_line_number()}] 网格订单计算完成: "
            f"层数={grid_levels} 总数量={total_quantity} 每层数量={quantity_per_level}"
        )
        
        return orders
    
    def calculate_symmetric_grid_orders(
        self,
        entry_price: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        total_quantity: float
    ) -> Dict[str, List[GridOrder]]:
        """
        计算对称网格订单（买单和卖单）
        
        根据入场价格，在上方创建卖单，在下方创建买单。
        
        Args:
            entry_price: 入场价格
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
            total_quantity: 总数量
        
        Returns:
            Dict[str, List[GridOrder]]: {"buy_orders": [...], "sell_orders": [...]}
        
        Example:
            >>> calculator = GridCalculator()
            >>> orders = calculator.calculate_symmetric_grid_orders(1.0, 1.05, 0.95, 10, 1000.0)
            >>> print(len(orders["buy_orders"]))  # 下方买单数量
            >>> print(len(orders["sell_orders"]))  # 上方卖单数量
        """
        if not (lower_price < entry_price < upper_price):
            raise ValueError(
                f"入场价格必须在网格范围内: {lower_price} < {entry_price} < {upper_price}"
            )
        
        # 计算所有网格价格
        prices = self.calculate_grid_prices(upper_price, lower_price, grid_levels)
        
        # 分离买单和卖单价格
        buy_prices = [p for p in prices if p < entry_price]
        sell_prices = [p for p in prices if p > entry_price]
        
        # 计算每个订单的数量
        total_orders = len(buy_prices) + len(sell_prices)
        if total_orders == 0:
            logger.warning(
                f"[grid_calculator.py:{self._get_line_number()}] "
                f"没有可用的网格价格"
            )
            return {"buy_orders": [], "sell_orders": []}
        
        quantity_per_order = total_quantity / total_orders
        
        # 创建买单
        buy_orders = []
        for i, price in enumerate(buy_prices):
            order = GridOrder(
                price=price,
                quantity=quantity_per_order,
                side="BUY",
                level=i
            )
            buy_orders.append(order)
        
        # 创建卖单
        sell_orders = []
        for i, price in enumerate(sell_prices):
            order = GridOrder(
                price=price,
                quantity=quantity_per_order,
                side="SELL",
                level=i
            )
            sell_orders.append(order)
        
        logger.info(
            f"[grid_calculator.py:{self._get_line_number()}] 对称网格订单计算完成: "
            f"买单={len(buy_orders)} 卖单={len(sell_orders)} 每单数量={quantity_per_order}"
        )
        
        return {
            "buy_orders": buy_orders,
            "sell_orders": sell_orders
        }
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

