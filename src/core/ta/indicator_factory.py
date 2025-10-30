"""
指标工厂

负责根据指标名称创建对应的指标实例。

使用工厂模式，遵循开闭原则：
- 对扩展开放：添加新指标只需注册到工厂
- 对修改关闭：不需要修改现有代码

使用方式：
    from src.core.ta.indicator_factory import IndicatorFactory
    from src.core.event.event_bus import EventBus
    
    event_bus = EventBus.get_instance()
    indicator = IndicatorFactory.create_indicator(
        user_id="user_001",
        symbol="XRPUSDC",
        indicator_name="ma_stop_ta",
        params={"period": 3, "percent": 2},
        event_bus=event_bus
    )

设计原则：
- 工厂模式：集中管理指标实例的创建
- 依赖倒置原则：返回BaseIndicator抽象类型
- 开闭原则：通过注册机制扩展新指标
"""

from typing import Dict, Any
from src.core.event.event_bus import EventBus
from src.core.ta.base_indicator import BaseIndicator
from src.utils.logger import logger


class IndicatorFactory:
    """
    指标工厂类
    
    使用静态方法创建指标实例，支持通过注册机制扩展新指标。
    
    Attributes:
        _indicator_registry: 类变量，存储指标名称到指标类的映射
    
    Example:
        >>> indicator = IndicatorFactory.create_indicator(
        ...     user_id="user_001",
        ...     symbol="XRPUSDC",
        ...     indicator_name="ma_stop_ta",
        ...     params={"period": 3},
        ...     event_bus=event_bus
        ... )
    """
    
    # 指标注册表：{indicator_name: IndicatorClass}
    _indicator_registry: Dict[str, type] = {}
    
    @classmethod
    def register_indicator(cls, indicator_name: str, indicator_class: type) -> None:
        """
        注册指标类
        
        将指标名称与指标类关联，用于后续创建实例。
        
        Args:
            indicator_name: 指标名称（如"ma_stop_ta"）
            indicator_class: 指标类（必须继承自BaseIndicator）
        
        Raises:
            ValueError: 如果指标类不是BaseIndicator的子类
        
        Example:
            >>> IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)
        """
        if not issubclass(indicator_class, BaseIndicator):
            raise ValueError(f"指标类必须继承自BaseIndicator: {indicator_class}")
        
        cls._indicator_registry[indicator_name] = indicator_class
        logger.debug(f"注册指标: {indicator_name} -> {indicator_class.__name__}")
    
    @classmethod
    def create_indicator(
        cls,
        user_id: str,
        symbol: str,
        interval: str,
        indicator_name: str,
        params: Dict[str, Any],
        event_bus: EventBus
    ) -> BaseIndicator:
        """
        创建指标实例

        根据指标名称从注册表中查找对应的指标类，并创建实例。

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            interval: 时间周期（如"15m", "1h", "4h"）
            indicator_name: 指标名称
            params: 指标参数字典
            event_bus: 事件总线实例

        Returns:
            BaseIndicator: 指标实例

        Raises:
            ValueError: 如果指标名称未注册

        Example:
            >>> indicator = IndicatorFactory.create_indicator(
            ...     user_id="user_001",
            ...     symbol="XRPUSDC",
            ...     interval="15m",
            ...     indicator_name="ma_stop_ta",
            ...     params={"period": 3, "percent": 2},
            ...     event_bus=event_bus
            ... )
        """
        if indicator_name not in cls._indicator_registry:
            raise ValueError(
                f"未知的指标名称: {indicator_name}。"
                f"可用指标: {list(cls._indicator_registry.keys())}"
            )

        indicator_class = cls._indicator_registry[indicator_name]

        logger.debug(
            f"创建指标实例: user_id={user_id}, symbol={symbol}, interval={interval}, "
            f"indicator_name={indicator_name}, params={params}"
        )

        # 创建指标实例
        indicator = indicator_class(
            user_id=user_id,
            symbol=symbol,
            interval=interval,
            indicator_name=indicator_name,
            params=params,
            event_bus=event_bus
        )

        logger.info(
            f"指标实例创建成功: indicator_id={indicator.get_indicator_id()}"
        )

        return indicator
    
    @classmethod
    def get_registered_indicators(cls) -> list:
        """
        获取所有已注册的指标名称列表
        
        Returns:
            list: 已注册的指标名称列表
        
        Example:
            >>> indicators = IndicatorFactory.get_registered_indicators()
            >>> print(indicators)
            ['ma_stop_ta', 'rsi_ta']
        """
        return list(cls._indicator_registry.keys())
    
    @classmethod
    def is_registered(cls, indicator_name: str) -> bool:
        """
        检查指标是否已注册
        
        Args:
            indicator_name: 指标名称
        
        Returns:
            bool: 如果已注册返回True，否则返回False
        
        Example:
            >>> if IndicatorFactory.is_registered("ma_stop_ta"):
            ...     print("指标已注册")
        """
        return indicator_name in cls._indicator_registry

