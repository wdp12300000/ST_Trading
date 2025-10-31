"""
资金管理器

CapitalManager负责资金管理和仓位计算，包括：
1. 账户余额管理
2. 保证金分配计算
3. 仓位大小计算
4. 杠杆倍数管理

使用方式:
    capital_manager = CapitalManager(
        user_id="user_001",
        leverage=4,
        margin_type="USDC"
    )
    
    # 更新账户余额
    capital_manager.update_balance(10000.0)
    
    # 计算每个交易对的保证金
    margin_per_symbol = capital_manager.calculate_margin_per_symbol(5)
    
    # 计算仓位大小
    position_size = capital_manager.calculate_position_size(
        margin=2000.0,
        entry_price=1.0,
        ratio=1.0
    )
"""

from typing import Optional
from loguru import logger


class CapitalManager:
    """
    资金管理器
    
    负责账户余额管理、保证金分配和仓位计算。
    
    Attributes:
        user_id: 用户ID
        leverage: 杠杆倍数
        margin_type: 保证金类型（USDT或USDC）
        available_balance: 可用余额
        total_balance: 总余额
        safety_ratio: 安全系数（默认0.95，使用95%的可用余额）
    
    Example:
        >>> capital_manager = CapitalManager("user_001", 4, "USDC")
        >>> capital_manager.update_balance(10000.0)
        >>> margin = capital_manager.calculate_margin_per_symbol(5)
        >>> print(f"每个交易对保证金: {margin}")
    """
    
    # 安全系数：使用可用余额的95%
    SAFETY_RATIO = 0.95
    
    def __init__(
        self,
        user_id: str,
        leverage: int,
        margin_type: str = "USDC"
    ):
        """
        初始化资金管理器
        
        Args:
            user_id: 用户ID
            leverage: 杠杆倍数
            margin_type: 保证金类型（USDT或USDC）
        """
        self.user_id = user_id
        self.leverage = leverage
        self.margin_type = margin_type
        self.available_balance: Optional[float] = None
        self.total_balance: Optional[float] = None
        
        logger.info(
            f"[capital_manager.py:{self._get_line_number()}] 资金管理器初始化: "
            f"{user_id} 杠杆={leverage}x 保证金类型={margin_type}"
        )
    
    def update_balance(self, available_balance: float, total_balance: Optional[float] = None) -> None:
        """
        更新账户余额
        
        Args:
            available_balance: 可用余额
            total_balance: 总余额（可选）
        
        Example:
            >>> capital_manager.update_balance(10000.0, 12000.0)
        """
        self.available_balance = available_balance
        self.total_balance = total_balance if total_balance is not None else available_balance
        
        logger.info(
            f"[capital_manager.py:{self._get_line_number()}] 账户余额更新: "
            f"{self.user_id} 可用={available_balance} 总额={self.total_balance}"
        )
    
    def get_available_balance(self) -> float:
        """
        获取可用余额
        
        Returns:
            float: 可用余额
        
        Raises:
            ValueError: 如果余额未初始化
        """
        if self.available_balance is None:
            raise ValueError(f"账户余额未初始化: {self.user_id}")
        return self.available_balance
    
    def get_usable_balance(self) -> float:
        """
        获取可使用余额（应用安全系数）
        
        Returns:
            float: 可使用余额 = 可用余额 × 安全系数
        
        Raises:
            ValueError: 如果余额未初始化
        
        Example:
            >>> capital_manager.update_balance(10000.0)
            >>> usable = capital_manager.get_usable_balance()
            >>> print(usable)  # 9500.0 (10000 * 0.95)
        """
        available = self.get_available_balance()
        usable = available * self.SAFETY_RATIO
        
        logger.debug(
            f"[capital_manager.py:{self._get_line_number()}] 可使用余额: "
            f"{self.user_id} 可用={available} 可使用={usable} (安全系数={self.SAFETY_RATIO})"
        )
        
        return usable
    
    def calculate_margin_per_symbol(self, symbol_count: int) -> float:
        """
        计算每个交易对分配的保证金
        
        公式: 每个交易对保证金 = 可使用余额 ÷ 交易对数量
        
        Args:
            symbol_count: 交易对数量
        
        Returns:
            float: 每个交易对分配的保证金
        
        Raises:
            ValueError: 如果交易对数量 <= 0 或余额未初始化
        
        Example:
            >>> capital_manager.update_balance(10000.0)
            >>> margin = capital_manager.calculate_margin_per_symbol(5)
            >>> print(margin)  # 1900.0 (10000 * 0.95 / 5)
        """
        if symbol_count <= 0:
            raise ValueError(f"交易对数量必须大于0: {symbol_count}")
        
        usable_balance = self.get_usable_balance()
        margin_per_symbol = usable_balance / symbol_count
        
        logger.info(
            f"[capital_manager.py:{self._get_line_number()}] 保证金分配: "
            f"{self.user_id} 可使用={usable_balance} 交易对数={symbol_count} "
            f"每个={margin_per_symbol}"
        )
        
        return margin_per_symbol
    
    def calculate_position_size(
        self,
        margin: float,
        entry_price: float,
        ratio: float = 1.0
    ) -> float:
        """
        计算仓位大小（数量）
        
        公式: 仓位大小 = (保证金 × ratio × 杠杆) ÷ 入场价格
        
        Args:
            margin: 分配的保证金
            entry_price: 入场价格
            ratio: 资金使用比例（默认1.0，即100%）
        
        Returns:
            float: 仓位大小（数量）
        
        Raises:
            ValueError: 如果参数无效
        
        Example:
            >>> # 保证金2000，杠杆4x，入场价1.0，使用100%资金
            >>> size = capital_manager.calculate_position_size(2000, 1.0, 1.0)
            >>> print(size)  # 8000.0 (2000 * 1.0 * 4 / 1.0)
            
            >>> # 使用50%资金
            >>> size = capital_manager.calculate_position_size(2000, 1.0, 0.5)
            >>> print(size)  # 4000.0 (2000 * 0.5 * 4 / 1.0)
        """
        if margin <= 0:
            raise ValueError(f"保证金必须大于0: {margin}")
        if entry_price <= 0:
            raise ValueError(f"入场价格必须大于0: {entry_price}")
        if ratio <= 0 or ratio > 1:
            raise ValueError(f"资金比例必须在(0, 1]范围内: {ratio}")
        
        # 计算仓位大小
        position_size = (margin * ratio * self.leverage) / entry_price
        
        logger.info(
            f"[capital_manager.py:{self._get_line_number()}] 仓位计算: "
            f"{self.user_id} 保证金={margin} 价格={entry_price} "
            f"比例={ratio} 杠杆={self.leverage}x 仓位={position_size}"
        )
        
        return position_size
    
    def calculate_grid_position_size(
        self,
        margin: float,
        entry_price: float,
        grid_levels: int,
        ratio: float = 1.0
    ) -> float:
        """
        计算单个网格订单的仓位大小
        
        公式: 单个网格仓位 = (保证金 × ratio × 杠杆) ÷ 入场价格 ÷ 网格层数
        
        Args:
            margin: 分配的保证金
            entry_price: 入场价格
            grid_levels: 网格层数
            ratio: 资金使用比例（默认1.0）
        
        Returns:
            float: 单个网格订单的仓位大小
        
        Raises:
            ValueError: 如果参数无效
        
        Example:
            >>> # 保证金2000，杠杆4x，入场价1.0，10层网格
            >>> size = capital_manager.calculate_grid_position_size(2000, 1.0, 10)
            >>> print(size)  # 800.0 (2000 * 1.0 * 4 / 1.0 / 10)
        """
        if grid_levels <= 0:
            raise ValueError(f"网格层数必须大于0: {grid_levels}")
        
        # 先计算总仓位大小
        total_position_size = self.calculate_position_size(margin, entry_price, ratio)
        
        # 平均分配到每个网格
        grid_position_size = total_position_size / grid_levels
        
        logger.info(
            f"[capital_manager.py:{self._get_line_number()}] 网格仓位计算: "
            f"{self.user_id} 总仓位={total_position_size} 网格层数={grid_levels} "
            f"单个网格={grid_position_size}"
        )
        
        return grid_position_size
    
    def get_leverage(self) -> int:
        """
        获取杠杆倍数
        
        Returns:
            int: 杠杆倍数
        """
        return self.leverage
    
    def get_margin_type(self) -> str:
        """
        获取保证金类型
        
        Returns:
            str: 保证金类型（USDT或USDC）
        """
        return self.margin_type
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

