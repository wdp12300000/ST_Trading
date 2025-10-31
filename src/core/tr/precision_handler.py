"""
精度处理器

PrecisionHandler负责订单精度处理和验证，包括：
1. 价格精度处理
2. 数量精度处理
3. 最小名义价值检查
4. 交易对精度配置管理

使用方式:
    handler = PrecisionHandler()
    
    # 设置交易对精度
    handler.set_symbol_precision("XRPUSDC", price_precision=4, quantity_precision=0)
    
    # 处理价格和数量
    price = handler.round_price("XRPUSDC", 1.23456)
    quantity = handler.round_quantity("XRPUSDC", 100.123)
    
    # 验证订单
    is_valid = handler.validate_order("XRPUSDC", price, quantity)
"""

from typing import Dict, Tuple, Optional
from loguru import logger
from decimal import Decimal, ROUND_DOWN


class PrecisionHandler:
    """
    精度处理器
    
    负责订单价格和数量的精度处理、验证。
    
    Attributes:
        _symbol_precision: 交易对精度配置字典
            key: symbol (str)
            value: (price_precision, quantity_precision, min_notional)
    
    Example:
        >>> handler = PrecisionHandler()
        >>> handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        >>> price = handler.round_price("XRPUSDC", 1.23456)
        >>> print(price)  # 1.2345
    """
    
    # 默认精度配置
    DEFAULT_PRICE_PRECISION = 2
    DEFAULT_QUANTITY_PRECISION = 0
    DEFAULT_MIN_NOTIONAL = 5.0  # 最小名义价值（USDT/USDC）
    
    def __init__(self):
        """初始化精度处理器"""
        # 交易对精度配置: {symbol: (price_precision, quantity_precision, min_notional)}
        self._symbol_precision: Dict[str, Tuple[int, int, float]] = {}
        
        logger.info(f"[precision_handler.py:{self._get_line_number()}] 精度处理器初始化完成")
    
    def set_symbol_precision(
        self,
        symbol: str,
        price_precision: int,
        quantity_precision: int,
        min_notional: float = DEFAULT_MIN_NOTIONAL
    ) -> None:
        """
        设置交易对精度配置
        
        Args:
            symbol: 交易对符号
            price_precision: 价格精度（小数位数）
            quantity_precision: 数量精度（小数位数）
            min_notional: 最小名义价值（默认5.0）
        
        Example:
            >>> handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
        """
        self._symbol_precision[symbol] = (price_precision, quantity_precision, min_notional)
        
        logger.debug(
            f"[precision_handler.py:{self._get_line_number()}] 设置精度配置: "
            f"{symbol} 价格精度={price_precision} 数量精度={quantity_precision} "
            f"最小名义价值={min_notional}"
        )
    
    def get_symbol_precision(self, symbol: str) -> Tuple[int, int, float]:
        """
        获取交易对精度配置
        
        Args:
            symbol: 交易对符号
        
        Returns:
            Tuple[int, int, float]: (价格精度, 数量精度, 最小名义价值)
        
        Example:
            >>> price_prec, qty_prec, min_notional = handler.get_symbol_precision("XRPUSDC")
        """
        if symbol not in self._symbol_precision:
            # 返回默认配置
            logger.warning(
                f"[precision_handler.py:{self._get_line_number()}] "
                f"未找到{symbol}的精度配置，使用默认值"
            )
            return (
                self.DEFAULT_PRICE_PRECISION,
                self.DEFAULT_QUANTITY_PRECISION,
                self.DEFAULT_MIN_NOTIONAL
            )
        
        return self._symbol_precision[symbol]
    
    def round_price(self, symbol: str, price: float) -> float:
        """
        价格精度处理
        
        Args:
            symbol: 交易对符号
            price: 原始价格
        
        Returns:
            float: 处理后的价格
        
        Example:
            >>> handler.set_symbol_precision("XRPUSDC", 4, 0)
            >>> price = handler.round_price("XRPUSDC", 1.23456)
            >>> print(price)  # 1.2345
        """
        price_precision, _, _ = self.get_symbol_precision(symbol)
        
        # 使用Decimal进行精确计算，避免浮点数误差
        decimal_price = Decimal(str(price))
        rounded_price = float(decimal_price.quantize(
            Decimal(10) ** -price_precision,
            rounding=ROUND_DOWN
        ))
        
        logger.debug(
            f"[precision_handler.py:{self._get_line_number()}] 价格精度处理: "
            f"{symbol} 原始={price} 处理后={rounded_price} 精度={price_precision}"
        )
        
        return rounded_price
    
    def round_quantity(self, symbol: str, quantity: float) -> float:
        """
        数量精度处理
        
        Args:
            symbol: 交易对符号
            quantity: 原始数量
        
        Returns:
            float: 处理后的数量
        
        Example:
            >>> handler.set_symbol_precision("XRPUSDC", 4, 0)
            >>> qty = handler.round_quantity("XRPUSDC", 100.123)
            >>> print(qty)  # 100.0
        """
        _, quantity_precision, _ = self.get_symbol_precision(symbol)
        
        # 使用Decimal进行精确计算
        decimal_quantity = Decimal(str(quantity))
        rounded_quantity = float(decimal_quantity.quantize(
            Decimal(10) ** -quantity_precision,
            rounding=ROUND_DOWN
        ))
        
        logger.debug(
            f"[precision_handler.py:{self._get_line_number()}] 数量精度处理: "
            f"{symbol} 原始={quantity} 处理后={rounded_quantity} 精度={quantity_precision}"
        )
        
        return rounded_quantity
    
    def validate_min_notional(self, symbol: str, price: float, quantity: float) -> bool:
        """
        验证最小名义价值
        
        名义价值 = 价格 × 数量
        
        Args:
            symbol: 交易对符号
            price: 价格
            quantity: 数量
        
        Returns:
            bool: True表示满足最小名义价值要求，False表示不满足
        
        Example:
            >>> handler.set_symbol_precision("XRPUSDC", 4, 0, 5.0)
            >>> is_valid = handler.validate_min_notional("XRPUSDC", 1.0, 10.0)
            >>> print(is_valid)  # True (1.0 * 10.0 = 10.0 >= 5.0)
        """
        _, _, min_notional = self.get_symbol_precision(symbol)
        
        notional_value = price * quantity
        is_valid = notional_value >= min_notional
        
        if not is_valid:
            logger.warning(
                f"[precision_handler.py:{self._get_line_number()}] 名义价值不足: "
                f"{symbol} 价格={price} 数量={quantity} "
                f"名义价值={notional_value} 最小要求={min_notional}"
            )
        
        return is_valid
    
    def validate_order(
        self,
        symbol: str,
        price: float,
        quantity: float
    ) -> Tuple[bool, Optional[str]]:
        """
        验证订单参数
        
        检查：
        1. 价格和数量是否大于0
        2. 是否满足最小名义价值要求
        
        Args:
            symbol: 交易对符号
            price: 价格
            quantity: 数量
        
        Returns:
            Tuple[bool, Optional[str]]: (是否有效, 错误信息)
        
        Example:
            >>> is_valid, error = handler.validate_order("XRPUSDC", 1.0, 10.0)
            >>> if not is_valid:
            >>>     print(f"订单无效: {error}")
        """
        # 检查价格
        if price <= 0:
            error_msg = f"价格必须大于0: {price}"
            logger.error(f"[precision_handler.py:{self._get_line_number()}] {error_msg}")
            return False, error_msg
        
        # 检查数量
        if quantity <= 0:
            error_msg = f"数量必须大于0: {quantity}"
            logger.error(f"[precision_handler.py:{self._get_line_number()}] {error_msg}")
            return False, error_msg
        
        # 检查最小名义价值
        if not self.validate_min_notional(symbol, price, quantity):
            _, _, min_notional = self.get_symbol_precision(symbol)
            error_msg = f"名义价值不足: {price * quantity} < {min_notional}"
            return False, error_msg
        
        return True, None
    
    def process_order_params(
        self,
        symbol: str,
        price: float,
        quantity: float
    ) -> Tuple[float, float]:
        """
        处理订单参数（精度处理）
        
        Args:
            symbol: 交易对符号
            price: 原始价格
            quantity: 原始数量
        
        Returns:
            Tuple[float, float]: (处理后的价格, 处理后的数量)
        
        Example:
            >>> handler.set_symbol_precision("XRPUSDC", 4, 0)
            >>> price, qty = handler.process_order_params("XRPUSDC", 1.23456, 100.123)
            >>> print(f"价格={price}, 数量={qty}")  # 价格=1.2345, 数量=100.0
        """
        rounded_price = self.round_price(symbol, price)
        rounded_quantity = self.round_quantity(symbol, quantity)
        
        logger.debug(
            f"[precision_handler.py:{self._get_line_number()}] 订单参数处理: "
            f"{symbol} 价格 {price}->{rounded_price} 数量 {quantity}->{rounded_quantity}"
        )
        
        return rounded_price, rounded_quantity
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

