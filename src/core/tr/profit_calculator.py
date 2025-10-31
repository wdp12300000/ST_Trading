"""
利润计算器

ProfitCalculator负责计算交易利润，包括：
1. 单个订单利润计算
2. 网格订单配对利润计算
3. 交易任务总盈亏计算
4. 手续费计算

使用方式:
    calculator = ProfitCalculator()
    
    # 单个订单利润
    profit = calculator.calculate_order_profit(
        entry_price=1.0,
        exit_price=1.05,
        quantity=100.0,
        side="LONG",
        fee_rate=0.0004
    )
    
    # 网格配对利润
    profit = calculator.calculate_grid_pair_profit(
        buy_price=0.95,
        sell_price=1.05,
        quantity=100.0,
        fee_rate=0.0004
    )
"""

from typing import List, Dict, Any, Optional
from loguru import logger


class ProfitCalculator:
    """
    利润计算器
    
    负责计算各种类型的交易利润。
    
    Attributes:
        DEFAULT_FEE_RATE: 默认手续费率（0.04%）
    """
    
    DEFAULT_FEE_RATE = 0.0004  # 0.04% Taker费率
    
    def __init__(self):
        """初始化利润计算器"""
        logger.info(f"[profit_calculator.py:{self._get_line_number()}] 利润计算器初始化完成")
    
    def calculate_order_profit(
        self,
        entry_price: float,
        exit_price: float,
        quantity: float,
        side: str,
        fee_rate: Optional[float] = None
    ) -> float:
        """
        计算单个订单的利润
        
        Args:
            entry_price: 入场价格
            exit_price: 出场价格
            quantity: 数量
            side: 持仓方向（"LONG" 或 "SHORT"）
            fee_rate: 手续费率（默认使用DEFAULT_FEE_RATE）
        
        Returns:
            float: 利润金额（正数为盈利，负数为亏损）
        
        Raises:
            ValueError: 如果参数无效
        
        Example:
            >>> calculator = ProfitCalculator()
            >>> profit = calculator.calculate_order_profit(1.0, 1.05, 100.0, "LONG")
            >>> print(profit)  # 约4.92（考虑手续费）
        """
        if entry_price <= 0 or exit_price <= 0:
            raise ValueError(f"价格必须大于0: entry={entry_price}, exit={exit_price}")
        
        if quantity <= 0:
            raise ValueError(f"数量必须大于0: {quantity}")
        
        if side not in ["LONG", "SHORT"]:
            raise ValueError(f"持仓方向必须是LONG或SHORT: {side}")
        
        if fee_rate is None:
            fee_rate = self.DEFAULT_FEE_RATE
        
        # 计算价格差
        if side == "LONG":
            # 多头：买入后卖出，利润 = (出场价 - 入场价) × 数量
            price_diff = exit_price - entry_price
        else:
            # 空头：卖出后买入，利润 = (入场价 - 出场价) × 数量
            price_diff = entry_price - exit_price
        
        # 毛利润
        gross_profit = price_diff * quantity
        
        # 手续费 = 入场手续费 + 出场手续费
        entry_fee = entry_price * quantity * fee_rate
        exit_fee = exit_price * quantity * fee_rate
        total_fee = entry_fee + exit_fee
        
        # 净利润
        net_profit = gross_profit - total_fee
        
        logger.debug(
            f"[profit_calculator.py:{self._get_line_number()}] 订单利润计算: "
            f"{side} 入场={entry_price} 出场={exit_price} 数量={quantity} "
            f"毛利={gross_profit:.4f} 手续费={total_fee:.4f} 净利={net_profit:.4f}"
        )
        
        return net_profit
    
    def calculate_grid_pair_profit(
        self,
        buy_price: float,
        sell_price: float,
        quantity: float,
        fee_rate: Optional[float] = None
    ) -> float:
        """
        计算网格配对利润
        
        Args:
            buy_price: 买入价格
            sell_price: 卖出价格
            quantity: 数量
            fee_rate: 手续费率（默认使用DEFAULT_FEE_RATE）
        
        Returns:
            float: 利润金额
        
        Example:
            >>> calculator = ProfitCalculator()
            >>> profit = calculator.calculate_grid_pair_profit(0.95, 1.05, 100.0)
            >>> print(profit)  # 约9.92（考虑手续费）
        """
        if buy_price <= 0 or sell_price <= 0:
            raise ValueError(f"价格必须大于0: buy={buy_price}, sell={sell_price}")
        
        if quantity <= 0:
            raise ValueError(f"数量必须大于0: {quantity}")
        
        if fee_rate is None:
            fee_rate = self.DEFAULT_FEE_RATE
        
        # 价格差利润
        price_diff = sell_price - buy_price
        gross_profit = price_diff * quantity
        
        # 手续费
        buy_fee = buy_price * quantity * fee_rate
        sell_fee = sell_price * quantity * fee_rate
        total_fee = buy_fee + sell_fee
        
        # 净利润
        net_profit = gross_profit - total_fee
        
        logger.debug(
            f"[profit_calculator.py:{self._get_line_number()}] 网格配对利润: "
            f"买价={buy_price} 卖价={sell_price} 数量={quantity} "
            f"毛利={gross_profit:.4f} 手续费={total_fee:.4f} 净利={net_profit:.4f}"
        )
        
        return net_profit
    
    def calculate_total_profit(
        self,
        order_profits: List[float]
    ) -> Dict[str, float]:
        """
        计算总盈亏
        
        Args:
            order_profits: 订单利润列表
        
        Returns:
            Dict[str, float]: {
                "total_profit": 总利润,
                "profit_count": 盈利订单数量,
                "loss_count": 亏损订单数量,
                "win_rate": 胜率
            }
        
        Example:
            >>> calculator = ProfitCalculator()
            >>> result = calculator.calculate_total_profit([10.0, -5.0, 8.0, -3.0])
            >>> print(result["total_profit"])  # 10.0
            >>> print(result["win_rate"])  # 0.5
        """
        if not order_profits:
            return {
                "total_profit": 0.0,
                "profit_count": 0,
                "loss_count": 0,
                "win_rate": 0.0
            }
        
        total_profit = sum(order_profits)
        profit_count = sum(1 for p in order_profits if p > 0)
        loss_count = sum(1 for p in order_profits if p < 0)
        total_count = len(order_profits)
        win_rate = profit_count / total_count if total_count > 0 else 0.0
        
        logger.info(
            f"[profit_calculator.py:{self._get_line_number()}] 总盈亏计算: "
            f"总利润={total_profit:.4f} 盈利单={profit_count} 亏损单={loss_count} "
            f"胜率={win_rate:.2%}"
        )
        
        return {
            "total_profit": total_profit,
            "profit_count": profit_count,
            "loss_count": loss_count,
            "win_rate": win_rate
        }
    
    def calculate_fee(
        self,
        price: float,
        quantity: float,
        fee_rate: Optional[float] = None
    ) -> float:
        """
        计算手续费
        
        Args:
            price: 价格
            quantity: 数量
            fee_rate: 手续费率（默认使用DEFAULT_FEE_RATE）
        
        Returns:
            float: 手续费金额
        
        Example:
            >>> calculator = ProfitCalculator()
            >>> fee = calculator.calculate_fee(1.0, 100.0, 0.0004)
            >>> print(fee)  # 0.04
        """
        if fee_rate is None:
            fee_rate = self.DEFAULT_FEE_RATE
        
        fee = price * quantity * fee_rate
        
        return fee
    
    def calculate_roi(
        self,
        profit: float,
        initial_capital: float
    ) -> float:
        """
        计算投资回报率（ROI）
        
        Args:
            profit: 利润
            initial_capital: 初始资金
        
        Returns:
            float: ROI（百分比，如0.05表示5%）
        
        Example:
            >>> calculator = ProfitCalculator()
            >>> roi = calculator.calculate_roi(50.0, 1000.0)
            >>> print(roi)  # 0.05 (5%)
        """
        if initial_capital <= 0:
            raise ValueError(f"初始资金必须大于0: {initial_capital}")
        
        roi = profit / initial_capital
        
        logger.debug(
            f"[profit_calculator.py:{self._get_line_number()}] ROI计算: "
            f"利润={profit:.4f} 初始资金={initial_capital:.4f} ROI={roi:.2%}"
        )
        
        return roi
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

