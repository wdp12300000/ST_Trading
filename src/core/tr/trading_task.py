"""
交易任务类

TradingTask管理单个交易对的所有订单和状态，包括：
1. 持仓状态管理（NONE/LONG/SHORT）
2. 订单记录和跟踪
3. 网格订单管理
4. 利润计算

每个交易对对应一个TradingTask实例。

使用方式：
    task = TradingTask(
        user_id="user_001",
        symbol="XRPUSDC",
        strategy_config=config
    )
    await task.open_position("LONG", 1.0, 100)
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger
from src.core.tr.profit_calculator import ProfitCalculator


class PositionState(Enum):
    """
    持仓状态枚举

    定义三种持仓状态：
    - NONE: 无持仓
    - LONG: 多头持仓
    - SHORT: 空头持仓
    """
    NONE = "NONE"
    LONG = "LONG"
    SHORT = "SHORT"


class TradingMode(Enum):
    """
    交易模式枚举

    定义三种交易模式：
    - NO_GRID: 无网格模式（grid_trading.enabled = false）
    - NORMAL_GRID: 普通网格模式（grid_type = "normal", ratio = 1）
    - ABNORMAL_GRID: 特殊网格模式（grid_type = "abnormal", ratio < 1）
    """
    NO_GRID = "NO_GRID"
    NORMAL_GRID = "NORMAL_GRID"
    ABNORMAL_GRID = "ABNORMAL_GRID"


class OrderInfo:
    """
    订单信息类
    
    记录单个订单的详细信息
    
    Attributes:
        order_id: 订单ID
        symbol: 交易对
        side: 方向（BUY/SELL）
        order_type: 订单类型（MARKET/LIMIT/POST_ONLY等）
        price: 价格
        quantity: 数量
        filled_quantity: 已成交数量
        status: 状态（NEW/FILLED/CANCELLED等）
        is_grid_order: 是否网格订单
        grid_pair_id: 网格配对ID（如果是网格订单）
        created_at: 创建时间
        filled_at: 成交时间
    """
    
    def __init__(
        self,
        order_id: str,
        symbol: str,
        side: str,
        order_type: str,
        price: float,
        quantity: float
    ):
        self.order_id = order_id
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        self.price = price
        self.quantity = quantity
        self.filled_quantity = 0.0
        self.status = "NEW"
        self.is_grid_order = False
        self.grid_pair_id: Optional[str] = None
        self.created_at = datetime.now()
        self.filled_at: Optional[datetime] = None


class TradingTask:
    """
    交易任务类
    
    管理单个交易对的所有订单和状态。
    
    Attributes:
        user_id: 用户ID
        symbol: 交易对符号
        strategy_config: 策略配置
        position_state: 持仓状态
        entry_price: 入场价格
        entry_quantity: 入场数量
        orders: 订单列表
        grid_orders: 网格订单字典
    
    Example:
        >>> task = TradingTask("user_001", "XRPUSDC", config)
        >>> await task.open_position("LONG", 1.0, 100)
        >>> task.get_position_state()
        PositionState.LONG
    """
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        strategy_config: Dict[str, Any]
    ):
        """
        初始化交易任务

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            strategy_config: 策略配置字典
        """
        self.user_id = user_id
        self.symbol = symbol
        self.strategy_config = strategy_config

        # 持仓状态
        self.position_state = PositionState.NONE
        self.entry_price: Optional[float] = None
        self.entry_quantity: Optional[float] = None
        self.entry_side: Optional[str] = None  # "LONG" or "SHORT"

        # 订单管理
        self.orders: List[OrderInfo] = []
        self.grid_orders: Dict[str, OrderInfo] = {}  # key: order_id, value: OrderInfo

        # 网格配置
        self.grid_config: Optional[Dict[str, Any]] = None
        self.grid_upper_price: Optional[float] = None
        self.grid_lower_price: Optional[float] = None

        # 交易模式识别
        self.trading_mode = self._determine_trading_mode()

        # 时间记录
        self.created_at = datetime.now()
        self.opened_at: Optional[datetime] = None
        self.closed_at: Optional[datetime] = None

        # 利润计算器
        self._profit_calculator = ProfitCalculator()

        # 利润统计
        self.total_profit: float = 0.0
        self.realized_profits: List[float] = []  # 已实现利润列表

        logger.info(
            f"[trading_task.py:{self._get_line_number()}] 交易任务创建: "
            f"{user_id}/{symbol} 模式={self.trading_mode.value}"
        )
    
    def get_position_state(self) -> PositionState:
        """
        获取当前持仓状态
        
        Returns:
            PositionState: 持仓状态
        """
        return self.position_state
    
    def is_position_open(self) -> bool:
        """
        判断是否有持仓
        
        Returns:
            bool: True表示有持仓，False表示无持仓
        """
        return self.position_state != PositionState.NONE
    
    async def open_position(self, side: str, entry_price: float, quantity: float) -> None:
        """
        开启持仓
        
        Args:
            side: 持仓方向（"LONG" 或 "SHORT"）
            entry_price: 入场价格
            quantity: 入场数量
        
        Raises:
            ValueError: 如果已有持仓
        """
        if self.is_position_open():
            raise ValueError(f"持仓已存在: {self.symbol} {self.position_state.value}")
        
        # 更新持仓状态
        self.position_state = PositionState.LONG if side == "LONG" else PositionState.SHORT
        self.entry_price = entry_price
        self.entry_quantity = quantity
        self.entry_side = side
        self.opened_at = datetime.now()
        
        logger.info(
            f"[trading_task.py:{self._get_line_number()}] 持仓开启: {self.symbol} "
            f"{side} 价格={entry_price} 数量={quantity}"
        )
    
    async def close_position(self, exit_price: float, fee_rate: Optional[float] = None) -> float:
        """
        关闭持仓

        Args:
            exit_price: 出场价格
            fee_rate: 手续费率（可选）

        Returns:
            float: 盈亏金额（扣除手续费）

        Raises:
            ValueError: 如果无持仓
        """
        if not self.is_position_open():
            raise ValueError(f"无持仓: {self.symbol}")

        # 使用利润计算器计算盈亏（包含手续费）
        pnl = self._profit_calculator.calculate_order_profit(
            entry_price=self.entry_price,
            exit_price=exit_price,
            quantity=self.entry_quantity,
            side=self.entry_side,
            fee_rate=fee_rate
        )

        # 记录已实现利润
        self.realized_profits.append(pnl)
        self.total_profit += pnl

        # 更新状态
        old_state = self.position_state
        self.position_state = PositionState.NONE
        self.closed_at = datetime.now()

        logger.info(
            f"[trading_task.py:{self._get_line_number()}] 持仓关闭: {self.symbol} "
            f"{old_state.value} 出场价={exit_price} 盈亏={pnl:.4f}"
        )

        return pnl
    
    def _calculate_position_pnl(self, exit_price: float) -> float:
        """
        计算持仓盈亏
        
        Args:
            exit_price: 出场价格
        
        Returns:
            float: 盈亏金额（未扣除手续费）
        """
        if self.entry_price is None or self.entry_quantity is None:
            return 0.0
        
        if self.position_state == PositionState.LONG:
            # 多头：(出场价 - 入场价) × 数量
            pnl = (exit_price - self.entry_price) * self.entry_quantity
        else:
            # 空头：(入场价 - 出场价) × 数量
            pnl = (self.entry_price - exit_price) * self.entry_quantity
        
        return pnl
    
    def add_order(self, order: OrderInfo) -> None:
        """
        添加订单记录
        
        Args:
            order: 订单信息
        """
        self.orders.append(order)
        logger.debug(f"[trading_task.py:{self._get_line_number()}] 添加订单: {order.order_id}")
    
    def add_grid_order(self, order: OrderInfo, pair_id: Optional[str] = None) -> None:
        """
        添加网格订单
        
        Args:
            order: 订单信息
            pair_id: 配对ID（可选）
        """
        order.is_grid_order = True
        order.grid_pair_id = pair_id
        self.grid_orders[order.order_id] = order
        self.orders.append(order)
        logger.debug(f"[trading_task.py:{self._get_line_number()}] 添加网格订单: {order.order_id}")
    
    def get_order(self, order_id: str) -> Optional[OrderInfo]:
        """
        获取订单信息
        
        Args:
            order_id: 订单ID
        
        Returns:
            OrderInfo: 订单信息，如果不存在返回None
        """
        for order in self.orders:
            if order.order_id == order_id:
                return order
        return None
    
    def update_order_status(self, order_id: str, status: str, filled_quantity: float = 0.0) -> None:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            status: 新状态
            filled_quantity: 已成交数量
        """
        order = self.get_order(order_id)
        if order:
            order.status = status
            order.filled_quantity = filled_quantity
            if status == "FILLED":
                order.filled_at = datetime.now()
            logger.debug(f"[trading_task.py:{self._get_line_number()}] 订单状态更新: {order_id} -> {status}")
    
    def get_grid_order_count(self) -> int:
        """
        获取网格订单数量
        
        Returns:
            int: 网格订单数量
        """
        return len(self.grid_orders)
    
    def clear_grid_orders(self) -> None:
        """清空网格订单记录"""
        self.grid_orders.clear()
        logger.debug(f"[trading_task.py:{self._get_line_number()}] 网格订单已清空")

    def _determine_trading_mode(self) -> TradingMode:
        """
        根据策略配置确定交易模式

        Returns:
            TradingMode: 交易模式

        规则：
        1. 如果 grid_trading.enabled = false，返回 NO_GRID
        2. 如果 grid_type = "normal" 且 ratio = 1，返回 NORMAL_GRID
        3. 如果 grid_type = "abnormal" 或 ratio < 1，返回 ABNORMAL_GRID
        """
        grid_config = self.strategy_config.get("grid_trading", {})

        # 检查是否启用网格交易
        if not grid_config.get("enabled", False):
            return TradingMode.NO_GRID

        # 检查网格类型和资金比例
        grid_type = grid_config.get("grid_type", "normal")
        ratio = grid_config.get("ratio", 1.0)

        if grid_type == "normal" and ratio == 1.0:
            return TradingMode.NORMAL_GRID
        else:
            return TradingMode.ABNORMAL_GRID

    def get_trading_mode(self) -> TradingMode:
        """
        获取交易模式

        Returns:
            TradingMode: 交易模式
        """
        return self.trading_mode

    def is_grid_enabled(self) -> bool:
        """
        判断是否启用网格交易

        Returns:
            bool: True表示启用网格，False表示未启用
        """
        return self.trading_mode != TradingMode.NO_GRID

    def get_grid_ratio(self) -> float:
        """
        获取网格资金比例

        Returns:
            float: 资金比例（0.0-1.0）

        说明：
        - NO_GRID模式：返回1.0（使用全部资金）
        - NORMAL_GRID模式：返回1.0（使用全部资金）
        - ABNORMAL_GRID模式：返回配置的ratio值（如0.5）
        """
        if self.trading_mode == TradingMode.ABNORMAL_GRID:
            grid_config = self.strategy_config.get("grid_trading", {})
            return grid_config.get("ratio", 1.0)
        return 1.0

    def set_grid_config(
        self,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        move_up: bool = False,
        move_down: bool = False
    ) -> None:
        """
        设置网格配置

        Args:
            upper_price: 网格上边价格
            lower_price: 网格下边价格
            grid_levels: 网格层数
            move_up: 是否向上移动
            move_down: 是否向下移动
        """
        self.grid_config = {
            "upper_price": upper_price,
            "lower_price": lower_price,
            "grid_levels": grid_levels,
            "move_up": move_up,
            "move_down": move_down
        }
        self.grid_upper_price = upper_price
        self.grid_lower_price = lower_price

        logger.info(
            f"[trading_task.py:{self._get_line_number()}] 网格配置设置: "
            f"{self.symbol} 上边={upper_price} 下边={lower_price} 层数={grid_levels}"
        )

    def get_total_profit(self) -> float:
        """
        获取总盈亏

        Returns:
            float: 总盈亏金额
        """
        return self.total_profit

    def get_profit_statistics(self) -> Dict[str, Any]:
        """
        获取利润统计信息

        Returns:
            Dict[str, Any]: 利润统计数据
        """
        stats = self._profit_calculator.calculate_total_profit(self.realized_profits)
        stats["total_profit"] = self.total_profit
        stats["order_count"] = len(self.realized_profits)

        return stats

    def add_grid_profit(self, profit: float) -> None:
        """
        添加网格订单利润

        Args:
            profit: 网格订单利润
        """
        self.realized_profits.append(profit)
        self.total_profit += profit

        logger.debug(
            f"[trading_task.py:{self._get_line_number()}] 网格利润记录: "
            f"{self.symbol} 利润={profit:.4f} 总利润={self.total_profit:.4f}"
        )

    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

