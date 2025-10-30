"""
BaseIndicator 指标抽象基类

定义技术指标的基础框架和接口，所有具体指标都应继承此类。

主要功能：
1. 指标实例标识：生成唯一的指标ID
2. 最小K线数量：定义指标计算所需的最小K线数量
3. 抽象方法：定义子类必须实现的计算方法
4. 属性访问：提供获取指标属性的方法

使用方式：
    class MaStopIndicator(BaseIndicator):
        def __init__(self, user_id, symbol, interval, indicator_name, params, event_bus):
            super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)
            self._min_klines_required = params.get("period", 20)

        async def calculate(self, klines):
            # 实现具体的指标计算逻辑（接收完整的历史K线列表）
            return {"signal": IndicatorSignal.LONG, "data": {...}}

设计原则：
- 开闭原则：对扩展开放（可以创建新指标），对修改关闭（不修改基类）
- 依赖倒置原则：高层模块（TAManager）依赖抽象（BaseIndicator）而非具体实现
- 面向对象设计：充分使用类方法和属性
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any
from src.core.event.event_bus import EventBus
from src.utils.logger import logger


class IndicatorSignal(Enum):
    """
    指标信号枚举
    
    定义三种指标信号：
    - LONG: 多头信号（看涨）
    - SHORT: 空头信号（看跌）
    - NONE: 无信号（中性）
    """
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class BaseIndicator(ABC):
    """
    指标抽象基类
    
    所有具体指标都应继承此类并实现抽象方法。
    
    Attributes:
        _user_id: 用户ID（私有，只读）
        _symbol: 交易对符号（私有，只读）
        _interval: 时间周期（私有，只读）
        _indicator_name: 指标名称（私有，只读）
        _params: 指标参数字典（私有，只读）
        _event_bus: 事件总线实例（私有）
        _min_klines_required: 最小K线数量（私有，子类设置）
        _is_ready: 指标是否已就绪（私有，初始化后设置为True）

    Example:
        >>> class MyIndicator(BaseIndicator):
        ...     def __init__(self, user_id, symbol, interval, indicator_name, params, event_bus):
        ...         super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)
        ...         self._min_klines_required = params.get("period", 20)
        ...
        ...     async def calculate(self, klines):
        ...         # 计算指标（接收完整的历史K线列表）
        ...         return {"signal": IndicatorSignal.LONG, "data": {"value": 100}}
        >>>
        >>> indicator = MyIndicator("user_001", "XRPUSDC", "15m", "my_indicator", {}, event_bus)
        >>> indicator.get_indicator_id()
        'user_001_XRPUSDC_15m_my_indicator'
    """
    
    def __init__(
        self,
        user_id: str,
        symbol: str,
        interval: str,
        indicator_name: str,
        params: Dict[str, Any],
        event_bus: EventBus
    ):
        """
        初始化指标实例

        Args:
            user_id: 用户ID
            symbol: 交易对符号（如 "XRPUSDC"）
            interval: 时间周期（如 "15m", "1h", "4h"）
            indicator_name: 指标名称（如 "ma_stop_ta"）
            params: 指标参数字典（如 {"period": 20, "percent": 2}）
            event_bus: 事件总线实例

        实现细节：
            1. 初始化所有私有属性
            2. 生成唯一的指标ID（包含interval）
            3. 子类需要设置 _min_klines_required 属性
            4. 初始化 _is_ready 为 False
        """
        self._user_id = user_id
        self._symbol = symbol
        self._interval = interval
        self._indicator_name = indicator_name
        self._params = params
        self._event_bus = event_bus

        # 子类需要在__init__中设置此属性
        # 默认值为200（如果子类未设置）
        self._min_klines_required = 200

        # 指标是否已就绪（初始化历史数据后设置为True）
        self._is_ready = False

        # 生成唯一的指标ID（包含interval）
        self._indicator_id = f"{user_id}_{symbol}_{interval}_{indicator_name}"

        logger.debug(f"[base_indicator.py] 指标实例初始化: {self._indicator_id}")
    
    # ==================== 属性访问方法 ====================
    
    def get_indicator_id(self) -> str:
        """
        获取指标实例的唯一ID

        Returns:
            指标ID，格式为 {user_id}_{symbol}_{interval}_{indicator_name}

        Example:
            >>> indicator.get_indicator_id()
            'user_001_XRPUSDC_15m_ma_stop_ta'
        """
        return self._indicator_id
    
    def get_user_id(self) -> str:
        """
        获取用户ID
        
        Returns:
            用户ID
        """
        return self._user_id
    
    def get_symbol(self) -> str:
        """
        获取交易对符号
        
        Returns:
            交易对符号（如 "XRPUSDC"）
        """
        return self._symbol
    
    def get_indicator_name(self) -> str:
        """
        获取指标名称

        Returns:
            指标名称（如 "ma_stop_ta"）
        """
        return self._indicator_name

    def get_interval(self) -> str:
        """
        获取时间周期

        Returns:
            时间周期（如 "15m", "1h", "4h"）
        """
        return self._interval

    def get_min_klines_required(self) -> int:
        """
        获取指标计算所需的最小K线数量

        Returns:
            最小K线数量（默认200）

        实现细节：
            - 子类应在__init__中根据参数设置此值
            - 例如：MA(20)需要至少20根K线
            - 如果子类未设置，默认返回200
        """
        return self._min_klines_required

    def is_ready(self) -> bool:
        """
        检查指标是否已就绪

        Returns:
            True: 指标已完成历史数据初始化，可以处理实时K线
            False: 指标尚未初始化，需要等待历史数据

        实现细节：
            - 初始化时为False
            - 调用initialize()方法后设置为True
        """
        return self._is_ready
    
    # ==================== 抽象方法 ====================

    @abstractmethod
    async def calculate(self, klines: list[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算指标（抽象方法，子类必须实现）

        接收完整的历史K线列表，计算指标并返回结果。

        设计原因：
            - 系统不缓存K线数据
            - 每次计算都需要完整的历史窗口
            - 每次K线更新后，DE模块会重新发送最新的历史K线列表

        Args:
            klines: K线数据列表，每个元素为K线字典
                格式: [
                    {
                        "open": "1.0",
                        "high": "1.1",
                        "low": "0.9",
                        "close": "1.05",
                        "volume": "1000",
                        "timestamp": 1234567890,
                        "is_closed": True
                    },
                    # ... 更多K线
                ]

        Returns:
            指标计算结果字典
                格式: {
                    "signal": IndicatorSignal.LONG,  # 或 SHORT, NONE
                    "data": {
                        "value": 100,  # 指标值
                        # 其他指标相关数据
                    }
                }

        Example:
            >>> async def calculate(self, klines):
            ...     # 提取收盘价列表
            ...     closes = [float(k["close"]) for k in klines]
            ...
            ...     # 计算移动平均线
            ...     ma_value = sum(closes[-20:]) / 20
            ...
            ...     # 判断信号（使用最新K线）
            ...     latest_close = closes[-1]
            ...     if latest_close > ma_value:
            ...         signal = IndicatorSignal.LONG
            ...     elif latest_close < ma_value:
            ...         signal = IndicatorSignal.SHORT
            ...     else:
            ...         signal = IndicatorSignal.NONE
            ...
            ...     return {
            ...         "signal": signal,
            ...         "data": {"ma_value": ma_value}
            ...     }
        """
        pass

    # ==================== 初始化方法 ====================

    async def initialize(self, historical_klines: list[Dict[str, Any]]) -> None:
        """
        使用历史K线数据初始化指标

        在指标实例创建后调用，用于初始化指标状态。
        默认实现：调用calculate()方法并标记为已就绪。

        子类可以重写此方法实现特殊的初始化逻辑。

        Args:
            historical_klines: 历史K线列表，每个元素为标准格式的K线字典

        实现细节：
            1. 调用calculate()方法进行首次计算
            2. 标记指标为已就绪（_is_ready = True）
            3. 记录日志

        Example:
            >>> await indicator.initialize(historical_klines)
            >>> assert indicator.is_ready() == True
        """
        logger.debug(
            f"{self._log_prefix()} "
            f"开始初始化指标: {self._indicator_id}, 历史K线数量={len(historical_klines)}"
        )

        # 调用calculate()方法进行首次计算
        await self.calculate(historical_klines)

        # 标记为已就绪
        self._is_ready = True

        logger.info(
            f"{self._log_prefix()} "
            f"指标初始化完成: {self._indicator_id}, 历史K线数量={len(historical_klines)}"
        )
    
    # ==================== 辅助方法 ====================

    @staticmethod
    def _get_line_number() -> int:
        """
        获取当前代码行号（用于日志记录）

        Returns:
            当前行号
        """
        import inspect
        return inspect.currentframe().f_back.f_lineno

    def _log_prefix(self) -> str:
        """
        生成日志前缀

        Returns:
            str: 格式化的日志前缀，包含文件名和行号
        """
        return f"[base_indicator.py:{self._get_line_number()}]"

