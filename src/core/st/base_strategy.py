"""
策略抽象基类

定义策略的基础框架和接口，所有具体策略都应继承此类。

主要功能：
1. 持仓状态管理：使用字典管理每个交易对的持仓状态
2. 事件发布：发布策略加载和指标订阅事件
3. 抽象方法：定义子类必须实现的方法

使用方式：
    class MaStopStrategy(BaseStrategy):
        async def on_indicator_signal(self, symbol, signal_type, signal_data):
            # 实现具体的信号处理逻辑
            pass
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any
from loguru import logger
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.st.st_events import STEvents


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


class BaseStrategy(ABC):
    """
    策略抽象基类
    
    所有具体策略都应继承此类并实现抽象方法。
    
    Attributes:
        _user_id: 用户ID
        _config: 策略配置字典
        _event_bus: 事件总线实例
        _positions: 持仓状态字典，key为symbol，value为PositionState
    
    Example:
        >>> class MyStrategy(BaseStrategy):
        ...     async def on_indicator_signal(self, symbol, signal_type, signal_data):
        ...         # 处理指标信号
        ...         pass
        >>> 
        >>> strategy = MyStrategy("user_001", config, event_bus)
        >>> await strategy._publish_strategy_loaded()
    """
    
    def __init__(self, user_id: str, config: Dict[str, Any], event_bus: EventBus):
        """
        初始化策略实例
        
        Args:
            user_id: 用户ID
            config: 策略配置字典
            event_bus: 事件总线实例
        """
        self._user_id: str = user_id
        self._config: Dict[str, Any] = config
        self._event_bus: EventBus = event_bus
        self._positions: Dict[str, PositionState] = {}
        
        # 初始化所有交易对的持仓状态为NONE
        self._initialize_positions()
        
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 策略实例创建成功: {user_id}")
    
    def _initialize_positions(self) -> None:
        """初始化所有交易对的持仓状态为NONE"""
        for pair in self._config.get("trading_pairs", []):
            symbol = pair["symbol"]
            self._positions[symbol] = PositionState.NONE
        
        logger.debug(f"[base_strategy.py:{self._get_line_number()}] 持仓状态初始化完成: {list(self._positions.keys())}")
    
    def get_position(self, symbol: str) -> PositionState:
        """
        获取指定交易对的持仓状态

        Args:
            symbol: 交易对符号

        Returns:
            PositionState: 持仓状态
        """
        return self._positions.get(symbol, PositionState.NONE)

    def update_position(self, symbol: str, state: PositionState) -> None:
        """
        更新指定交易对的持仓状态

        Args:
            symbol: 交易对符号
            state: 新的持仓状态
        """
        old_state = self._positions.get(symbol, PositionState.NONE)
        self._positions[symbol] = state
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 持仓状态更新: {symbol} {old_state.value} -> {state.value}")
    
    async def _publish_strategy_loaded(self) -> None:
        """
        发布策略加载成功事件
        
        当策略实例创建成功后调用此方法，通知其他模块策略已就绪。
        """
        trading_pairs = [pair["symbol"] for pair in self._config.get("trading_pairs", [])]
        
        event = Event(
            subject=STEvents.STRATEGY_LOADED,
            data={
                "user_id": self._user_id,
                "strategy": self._config.get("strategy_name", "unknown"),
                "timeframe": self._config.get("timeframe"),
                "trading_pairs": trading_pairs
            },
            source="st"
        )
        
        await self._event_bus.publish(event)
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 发布策略加载事件: {self._user_id}")
    
    async def _publish_indicator_subscriptions(self) -> None:
        """
        为每个交易对发布指标订阅事件

        遍历所有交易对，为每个交易对的每个指标发布订阅请求事件。
        事件数据包含：user_id, symbol, indicator_name, indicator_params, timeframe
        """
        # 从配置中获取时间周期
        timeframe = self._config.get("timeframe", "15m")

        for pair in self._config.get("trading_pairs", []):
            symbol = pair["symbol"]
            indicator_params = pair.get("indicator_params", {})

            for indicator_name, params in indicator_params.items():
                event = Event(
                    subject=STEvents.INDICATOR_SUBSCRIBE,
                    data={
                        "user_id": self._user_id,
                        "symbol": symbol,
                        "indicator_name": indicator_name,
                        "indicator_params": params,
                        "timeframe": timeframe  # 添加时间周期信息
                    },
                    source="st"
                )

                await self._event_bus.publish(event)
                logger.info(f"[base_strategy.py:{self._get_line_number()}] 发布指标订阅: {symbol}/{indicator_name}, timeframe={timeframe}")
    
    async def _generate_signal(self, symbol: str, side: str, action: str) -> None:
        """
        生成交易信号并发布事件

        Args:
            symbol: 交易对符号
            side: 方向（LONG/SHORT）
            action: 动作（OPEN/CLOSE）
        """
        event = Event(
            subject=STEvents.SIGNAL_GENERATED,
            data={
                "user_id": self._user_id,
                "symbol": symbol,
                "side": side,
                "action": action
            },
            source="st"
        )

        await self._event_bus.publish(event)
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 生成交易信号: {symbol} {side} {action}")

    async def on_position_opened(self, symbol: str, side: str, entry_price: float) -> None:
        """
        处理持仓开启事件

        当持仓开启后，检查是否需要创建网格交易。

        Args:
            symbol: 交易对符号
            side: 持仓方向（LONG/SHORT）
            entry_price: 入场价格
        """
        # 检查网格交易配置
        grid_config = self._config.get("grid_trading", {})
        if not grid_config.get("enabled", False):
            logger.debug(f"[base_strategy.py:{self._get_line_number()}] 网格交易未启用: {symbol}")
            return

        # 发布网格创建事件
        await self._publish_grid_create(symbol, entry_price, grid_config)

    async def _publish_grid_create(self, symbol: str, entry_price: float, grid_config: dict) -> None:
        """
        发布网格创建事件

        Args:
            symbol: 交易对符号
            entry_price: 入场价格
            grid_config: 网格配置
        """
        from src.core.st.st_events import STEvents

        event = Event(
            subject=STEvents.GRID_CREATE,
            data={
                "user_id": self._user_id,
                "symbol": symbol,
                "entry_price": entry_price,
                "grid_levels": grid_config.get("grid_levels"),
                "grid_ratio": grid_config.get("ratio"),
                "move_up": grid_config.get("move_up"),
                "move_down": grid_config.get("move_down")
            },
            source="st"
        )

        await self._event_bus.publish(event)
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 发布网格创建事件: {symbol} 入场价={entry_price}")

    async def on_position_closed(self, symbol: str, side: str) -> None:
        """
        处理持仓关闭事件

        当持仓关闭后，检查是否需要反向建仓。

        Args:
            symbol: 交易对符号
            side: 平仓方向（LONG/SHORT）
        """
        # 检查反向建仓配置
        reverse_enabled = self._config.get("reverse", False)
        if not reverse_enabled:
            logger.debug(f"[base_strategy.py:{self._get_line_number()}] 反向建仓未启用: {symbol}")
            return

        # 生成反向开仓信号
        # 平多仓 → 开空仓
        # 平空仓 → 开多仓
        reverse_side = "SHORT" if side == "LONG" else "LONG"
        await self._generate_signal(symbol, reverse_side, "OPEN")
        logger.info(f"[base_strategy.py:{self._get_line_number()}] 反向建仓: {symbol} 平{side}仓 → 开{reverse_side}仓")

    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno
    
    @abstractmethod
    async def on_indicators_completed(self, symbol: str, indicators: Dict[str, Any]) -> None:
        """
        处理该交易对所有指标计算完成的结果（抽象方法，子类必须实现）

        当TA模块完成该交易对所有指标的计算后，会调用此方法。
        子类需要实现具体的策略逻辑，根据所有指标的结果生成交易信号。

        Args:
            symbol: 交易对符号（如 "XRPUSDC"）
            indicators: 所有指标的计算结果字典
                格式: {
                    "ma_stop_ta": {"signal": "LONG", "data": {...}},
                    "rsi_ta": {"signal": "SHORT", "data": {...}},
                    "macd_ta": {"signal": "LONG", "data": {...}}
                }

        Example:
            >>> async def on_indicators_completed(self, symbol, indicators):
            ...     # 示例：MA指标LONG + RSI未超买 → 开多仓
            ...     ma_signal = indicators.get("ma_stop_ta", {}).get("signal")
            ...     rsi_value = indicators.get("rsi_ta", {}).get("data", {}).get("value", 50)
            ...
            ...     if ma_signal == "LONG" and rsi_value < 70:
            ...         await self._generate_signal(symbol, "LONG", "OPEN")
        """
        pass

