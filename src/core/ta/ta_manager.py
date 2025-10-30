"""
TA技术分析管理器

负责管理所有技术指标实例，使用单例模式确保全局唯一。

主要功能：
1. 单例模式管理：确保全局只有一个TA管理器实例
2. 指标实例管理：为每个{user_id}_{symbol}_{indicator_name}创建和管理指标实例
3. 事件订阅：订阅ST、DE模块的事件
4. 事件分发：处理指标订阅、K线数据等事件
5. 指标聚合：等待同一交易对的所有指标计算完成后统一发布事件
6. 历史数据请求：向DE模块请求历史K线数据

使用方式：
    from src.core.ta.ta_manager import TAManager
    from src.core.event.event_bus import EventBus
    
    event_bus = EventBus.get_instance()
    ta_manager = TAManager.get_instance(event_bus=event_bus)

设计原则：
- 单例模式：全局唯一的管理器实例
- 面向对象设计：充分使用类方法
- 依赖倒置原则：依赖抽象（BaseIndicator）而非具体实现
- 事件驱动架构：通过事件总线与其他模块通信
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
from src.utils.logger import logger
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.ta.ta_events import TAEvents
from src.core.ta.indicator_factory import IndicatorFactory
from src.core.de.de_events import DEEvents

# 避免循环导入
if TYPE_CHECKING:
    from src.core.ta.base_indicator import BaseIndicator

# 常量定义
DEFAULT_HISTORICAL_KLINES_LIMIT = 200  # 默认请求的历史K线数量


class TAManager:
    """
    技术分析管理器（单例模式）
    
    使用单例模式确保全局只有一个TA管理器实例，负责管理所有指标实例。
    
    Attributes:
        _instance: 类变量，存储唯一的单例实例
        _event_bus: 事件总线实例
        _indicators: 字典，存储所有指标实例，key为indicator_id（{user_id}_{symbol}_{indicator_name}）
        _aggregators: 字典，存储指标聚合器，key为{user_id}_{symbol}
    
    Example:
        >>> event_bus = EventBus.get_instance()
        >>> manager = TAManager.get_instance(event_bus=event_bus)
        >>> # 后续调用无需传入event_bus
        >>> same_manager = TAManager.get_instance()
        >>> assert manager is same_manager
    """
    
    _instance: Optional['TAManager'] = None
    
    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> 'TAManager':
        """
        获取单例实例
        
        首次调用时必须提供event_bus参数，后续调用可省略。
        
        Args:
            event_bus: 事件总线实例（首次调用时必须提供）
        
        Returns:
            TAManager: 唯一的技术分析管理器实例
        
        Raises:
            ValueError: 如果首次调用时未提供event_bus
        
        Example:
            >>> # 首次调用
            >>> manager = TAManager.get_instance(event_bus=event_bus)
            >>> # 后续调用
            >>> same_manager = TAManager.get_instance()
        """
        if cls._instance is None:
            if event_bus is None:
                raise ValueError("首次调用必须提供event_bus")
            cls._instance = cls(event_bus)
            logger.info(f"[ta_manager.py:{cls._get_line_number()}] TAManager 单例实例创建成功")
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（仅用于测试）
        
        警告：此方法仅应在单元测试中使用，生产环境不应调用。
        """
        cls._instance = None
        logger.debug(f"[ta_manager.py:{cls._get_line_number()}] TAManager 单例实例已重置")
    
    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

    def _log_prefix(self) -> str:
        """
        生成日志前缀

        Returns:
            str: 格式化的日志前缀，包含文件名和行号
        """
        return f"[ta_manager.py:{self._get_line_number()}]"
    
    def __init__(self, event_bus: EventBus):
        """
        私有构造函数（通过get_instance调用）
        
        Args:
            event_bus: 事件总线实例
        
        实现细节：
            1. 初始化指标字典
            2. 初始化聚合器字典
            3. 订阅ST模块的指标订阅事件
            4. 订阅DE模块的历史K线事件
            5. 订阅DE模块的实时K线事件
        """
        self._event_bus = event_bus
        
        # 存储所有指标实例，key为indicator_id（{user_id}_{symbol}_{indicator_name}）
        self._indicators: Dict[str, 'BaseIndicator'] = {}
        
        # 存储指标聚合器，key为{user_id}_{symbol}
        # 聚合器负责等待同一交易对的所有指标计算完成后统一发布事件
        self._aggregators: Dict[str, Dict] = {}
        
        # 订阅ST模块的指标订阅事件
        self._event_bus.subscribe(
            TAEvents.INPUT_INDICATOR_SUBSCRIBE,
            self._handle_indicator_subscribe
        )
        
        # 订阅DE模块的历史K线成功事件
        self._event_bus.subscribe(
            TAEvents.INPUT_HISTORICAL_KLINES_SUCCESS,
            self._handle_historical_klines_success
        )
        
        # 订阅DE模块的历史K线失败事件
        self._event_bus.subscribe(
            TAEvents.INPUT_HISTORICAL_KLINES_FAILED,
            self._handle_historical_klines_failed
        )
        
        # 订阅DE模块的实时K线更新事件
        self._event_bus.subscribe(
            TAEvents.INPUT_KLINE_UPDATE,
            self._handle_kline_update
        )
        
        logger.info(f"{self._log_prefix()} TAManager 初始化完成")

    # ==================== 辅助方法 ====================

    async def _request_historical_klines(
        self,
        user_id: str,
        symbol: str,
        interval: str,
        indicator: 'BaseIndicator'
    ) -> None:
        """
        向DE模块请求历史K线数据

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            interval: 时间周期
            indicator: 指标实例

        实现细节：
            1. 获取指标所需的最小K线数量
            2. 构造历史K线请求事件
            3. 发布事件到DE模块
        """
        min_klines = indicator.get_min_klines_required()
        historical_klines_event = Event(
            subject=DEEvents.INPUT_GET_HISTORICAL_KLINES,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "interval": interval,
                "limit": min_klines
            },
            source="ta"
        )
        await self._event_bus.publish(historical_klines_event)

        logger.info(
            f"{self._log_prefix()} "
            f"已请求历史K线数据: symbol={symbol}, interval={interval}, limit={min_klines}"
        )

    async def _publish_indicator_created(
        self,
        user_id: str,
        symbol: str,
        indicator_name: str,
        indicator_id: str
    ) -> None:
        """
        发布指标创建成功事件

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            indicator_name: 指标名称
            indicator_id: 指标ID

        实现细节：
            1. 构造指标创建成功事件
            2. 发布事件到事件总线
        """
        indicator_created_event = Event(
            subject=TAEvents.INDICATOR_CREATED,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "indicator_name": indicator_name,
                "indicator_id": indicator_id
            },
            source="ta"
        )
        await self._event_bus.publish(indicator_created_event)

        logger.info(
            f"{self._log_prefix()} "
            f"指标创建成功事件已发布: indicator_id={indicator_id}"
        )

    async def _publish_indicator_create_failed(
        self,
        user_id: str,
        symbol: str,
        indicator_name: str,
        error: str
    ) -> None:
        """
        发布指标创建失败事件

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            indicator_name: 指标名称
            error: 错误信息

        实现细节：
            1. 构造指标创建失败事件
            2. 发布事件到事件总线
        """
        indicator_create_failed_event = Event(
            subject=TAEvents.INDICATOR_CREATE_FAILED,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "indicator_name": indicator_name,
                "error": error
            },
            source="ta"
        )
        await self._event_bus.publish(indicator_create_failed_event)

    # ==================== 事件处理方法 ====================
    
    async def _handle_indicator_subscribe(self, event: Event) -> None:
        """
        处理指标订阅事件（来自ST模块）

        Args:
            event: 指标订阅事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "indicator_name": "ma_stop_ta",
                    "indicator_params": {"period": 3, "percent": 2},
                    "timeframe": "15m"
                }

        实现细节：
            1. 提取事件数据
            2. 使用IndicatorFactory创建指标实例
            3. 存储指标实例到_indicators字典
            4. 向DE模块请求历史K线数据
            5. 发布指标创建成功事件
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        indicator_name = event.data.get("indicator_name")
        indicator_params = event.data.get("indicator_params", {})
        timeframe = event.data.get("timeframe", "15m")

        logger.debug(
            f"{self._log_prefix()} "
            f"收到指标订阅请求: user_id={user_id}, symbol={symbol}, "
            f"indicator_name={indicator_name}, timeframe={timeframe}"
        )

        try:
            # 1. 使用工厂创建指标实例
            indicator = IndicatorFactory.create_indicator(
                user_id=user_id,
                symbol=symbol,
                interval=timeframe,
                indicator_name=indicator_name,
                params=indicator_params,
                event_bus=self._event_bus
            )

            # 2. 存储指标实例
            indicator_id = indicator.get_indicator_id()
            self._indicators[indicator_id] = indicator

            logger.info(
                f"{self._log_prefix()} "
                f"指标实例已创建并存储: indicator_id={indicator_id}"
            )

            # 3. 向DE模块请求历史K线数据
            await self._request_historical_klines(
                user_id=user_id,
                symbol=symbol,
                interval=timeframe,
                indicator=indicator
            )

            # 4. 发布指标创建成功事件
            await self._publish_indicator_created(
                user_id=user_id,
                symbol=symbol,
                indicator_name=indicator_name,
                indicator_id=indicator_id
            )

        except Exception as e:
            # 发布指标创建失败事件
            logger.error(
                f"{self._log_prefix()} "
                f"指标创建失败: user_id={user_id}, symbol={symbol}, "
                f"indicator_name={indicator_name}, error={str(e)}"
            )

            await self._publish_indicator_create_failed(
                user_id=user_id,
                symbol=symbol,
                indicator_name=indicator_name,
                error=str(e)
            )
    
    async def _handle_historical_klines_success(self, event: Event) -> None:
        """
        处理历史K线数据成功事件（来自DE模块）
        
        Args:
            event: 历史K线成功事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "interval": "15m",
                    "klines": [...]
                }
        
        实现细节：
            1. 提取事件数据
            2. 找到对应的指标实例（后续任务实现）
            3. 初始化指标的历史数据（后续任务实现）
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        interval = event.data.get("interval")
        klines = event.data.get("klines", [])
        
        logger.debug(
            f"{self._log_prefix()} "
            f"收到历史K线数据: user_id={user_id}, symbol={symbol}, "
            f"interval={interval}, count={len(klines)}"
        )

        # 遍历所有指标，找到匹配的指标并初始化
        for indicator_id, indicator in self._indicators.items():
            # 匹配条件：user_id、symbol、interval都相同
            if (indicator.get_user_id() == user_id and
                indicator.get_symbol() == symbol and
                indicator.get_interval() == interval):

                try:
                    # 调用指标的initialize方法
                    await indicator.initialize(klines)

                    logger.info(
                        f"{self._log_prefix()} "
                        f"指标初始化成功: indicator_id={indicator_id}"
                    )

                except Exception as e:
                    logger.error(
                        f"{self._log_prefix()} "
                        f"指标初始化失败: indicator_id={indicator_id}, error={e}"
                    )
    
    async def _handle_historical_klines_failed(self, event: Event) -> None:
        """
        处理历史K线数据失败事件（来自DE模块）
        
        Args:
            event: 历史K线失败事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "interval": "15m",
                    "error": "错误信息"
                }
        
        实现细节：
            1. 提取事件数据
            2. 记录错误日志
            3. 可能需要重试（后续任务实现）
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        interval = event.data.get("interval")
        error = event.data.get("error")
        
        logger.error(
            f"{self._log_prefix()} "
            f"历史K线数据获取失败: user_id={user_id}, symbol={symbol}, "
            f"interval={interval}, error={error}"
        )

        # TODO: 在后续任务中实现错误处理和重试逻辑
        pass
    
    async def _handle_kline_update(self, event: Event) -> None:
        """
        处理实时K线更新事件（来自DE模块）

        设计原则：
            - DE模块只在K线关闭时发布此事件
            - 事件包含完整的历史K线列表（包括最新关闭的K线）
            - 只处理已就绪的指标（is_ready=True）

        Args:
            event: K线更新事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "interval": "15m",
                    "klines": [{open, high, low, close, volume, timestamp, is_closed}, ...]
                }

        实现细节：
            1. 提取事件数据（user_id, symbol, interval, klines）
            2. 遍历所有指标，找到匹配的指标
            3. 检查指标是否已就绪（is_ready）
            4. 调用指标的calculate方法
            5. 聚合同一交易对的所有指标结果（后续任务实现）
            6. 发布ta.calculation.completed事件（后续任务实现）
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        interval = event.data.get("interval")
        klines = event.data.get("klines", [])

        logger.debug(
            f"{self._log_prefix()} "
            f"收到K线更新: user_id={user_id}, symbol={symbol}, "
            f"interval={interval}, klines_count={len(klines)}"
        )

        # 遍历所有指标，找到匹配的指标并计算
        for indicator_id, indicator in self._indicators.items():
            # 匹配条件：user_id、symbol、interval都相同
            if (indicator.get_user_id() == user_id and
                indicator.get_symbol() == symbol and
                indicator.get_interval() == interval):

                # 检查指标是否已就绪
                if not indicator.is_ready():
                    logger.debug(
                        f"{self._log_prefix()} "
                        f"指标未就绪，跳过: indicator_id={indicator_id}"
                    )
                    continue

                try:
                    # 调用指标的calculate方法
                    result = await indicator.calculate(klines)

                    logger.debug(
                        f"{self._log_prefix()} "
                        f"指标计算完成: indicator_id={indicator_id}, result={result}"
                    )

                    # 将结果添加到聚合器
                    await self._aggregate_indicator_result(
                        user_id=user_id,
                        symbol=symbol,
                        interval=interval,
                        indicator_name=indicator.get_indicator_name(),
                        result=result
                    )

                except Exception as e:
                    logger.error(
                        f"{self._log_prefix()} "
                        f"指标计算失败: indicator_id={indicator_id}, error={e}"
                    )

    async def _aggregate_indicator_result(
        self,
        user_id: str,
        symbol: str,
        interval: str,
        indicator_name: str,
        result: Dict[str, Any]
    ) -> None:
        """
        聚合指标结果并在所有指标完成后发布事件

        设计原则：
            - 聚合键为{user_id}_{symbol}
            - 等待该交易对的所有指标都计算完成
            - 所有指标完成后发布ta.calculation.completed事件

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            interval: 时间周期
            indicator_name: 指标名称
            result: 指标计算结果

        实现细节：
            1. 创建聚合键{user_id}_{symbol}
            2. 初始化聚合器（如果不存在）
            3. 将指标结果添加到聚合器
            4. 检查该交易对的所有指标是否都已完成
            5. 如果都完成，发布ta.calculation.completed事件
            6. 清空聚合器
        """
        # 创建聚合键
        aggregation_key = f"{user_id}_{symbol}"

        # 初始化聚合器（如果不存在）
        if aggregation_key not in self._aggregators:
            self._aggregators[aggregation_key] = {
                "user_id": user_id,
                "symbol": symbol,
                "interval": interval,
                "indicators": {},
                "expected_count": 0,
                "completed_count": 0
            }

        aggregator = self._aggregators[aggregation_key]

        # 计算该交易对应该有多少个指标
        expected_count = sum(
            1 for ind in self._indicators.values()
            if (ind.get_user_id() == user_id and
                ind.get_symbol() == symbol and
                ind.get_interval() == interval)
        )
        aggregator["expected_count"] = expected_count

        # 将指标结果添加到聚合器
        aggregator["indicators"][indicator_name] = result
        aggregator["completed_count"] = len(aggregator["indicators"])

        logger.debug(
            f"{self._log_prefix()} "
            f"指标结果已聚合: {aggregation_key}, "
            f"completed={aggregator['completed_count']}/{aggregator['expected_count']}"
        )

        # 检查是否所有指标都已完成
        if aggregator["completed_count"] >= aggregator["expected_count"]:
            # 发布ta.calculation.completed事件
            await self._publish_calculation_completed(
                user_id=user_id,
                symbol=symbol,
                timeframe=interval,
                indicators=aggregator["indicators"]
            )

            # 清空聚合器
            del self._aggregators[aggregation_key]

            logger.info(
                f"{self._log_prefix()} "
                f"所有指标计算完成，已发布事件: {aggregation_key}"
            )

    async def _publish_calculation_completed(
        self,
        user_id: str,
        symbol: str,
        timeframe: str,
        indicators: Dict[str, Any]
    ) -> None:
        """
        发布指标计算完成事件

        Args:
            user_id: 用户ID
            symbol: 交易对符号
            timeframe: 时间周期
            indicators: 所有指标的计算结果
        """
        event = Event(
            subject=TAEvents.CALCULATION_COMPLETED,
            data={
                "user_id": user_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": indicators
            },
            source="ta"
        )

        await self._event_bus.publish(event)

        logger.info(
            f"{self._log_prefix()} "
            f"已发布ta.calculation.completed事件: user_id={user_id}, symbol={symbol}, "
            f"indicators_count={len(indicators)}"
        )

