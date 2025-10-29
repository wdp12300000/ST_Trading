"""
ST策略管理器

负责管理所有用户的策略实例，使用单例模式确保全局唯一。

主要功能：
1. 单例模式管理：确保全局只有一个策略管理器实例
2. 策略实例管理：为每个用户创建和管理独立的策略实例
3. 事件订阅：订阅PM、TA、TR模块的事件
4. 事件分发：根据user_id将事件分发到对应的策略实例
5. 配置加载：从JSON文件加载策略配置
6. 配置验证：验证配置文件的完整性和正确性

使用方式：
    from src.core.st.st_manager import STManager
    from src.core.event.event_bus import EventBus

    event_bus = EventBus.get_instance()
    st_manager = STManager.get_instance(event_bus=event_bus)
"""

from typing import Optional, Dict, TYPE_CHECKING, Any
import json
from pathlib import Path
from loguru import logger
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.st.st_events import STEvents

# 避免循环导入
if TYPE_CHECKING:
    from src.core.st.base_strategy import BaseStrategy


class STManager:
    """
    策略管理器（单例模式）

    使用单例模式确保全局只有一个策略管理器实例，负责管理所有用户的策略实例。

    Attributes:
        _instance: 类变量，存储唯一的单例实例
        _event_bus: 事件总线实例
        _strategies: 字典，存储所有用户的策略实例，key为user_id

    Example:
        >>> event_bus = EventBus.get_instance()
        >>> manager = STManager.get_instance(event_bus=event_bus)
        >>> # 后续调用无需传入event_bus
        >>> same_manager = STManager.get_instance()
        >>> assert manager is same_manager
    """

    _instance: Optional['STManager'] = None

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> 'STManager':
        """
        获取单例实例

        首次调用时必须提供event_bus参数，后续调用可省略。

        Args:
            event_bus: 事件总线实例（首次调用时必须提供）

        Returns:
            STManager: 唯一的策略管理器实例

        Raises:
            ValueError: 如果首次调用时未提供event_bus

        Example:
            >>> # 首次调用
            >>> manager = STManager.get_instance(event_bus=event_bus)
            >>> # 后续调用
            >>> same_manager = STManager.get_instance()
        """
        if cls._instance is None:
            if event_bus is None:
                raise ValueError("首次调用必须提供event_bus")
            cls._instance = cls(event_bus)
            logger.info(f"[st_manager.py:{cls._get_line_number()}] STManager 单例实例创建成功")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（仅用于测试）

        警告：此方法仅应在单元测试中使用，生产环境不应调用。
        """
        cls._instance = None
        logger.debug(f"[st_manager.py:{cls._get_line_number()}] STManager 单例实例已重置")

    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

    def __init__(self, event_bus: EventBus):
        """
        初始化策略管理器

        注意：不应直接调用此方法，应使用 get_instance() 获取单例。

        Args:
            event_bus: 事件总线实例
        """
        self._event_bus: EventBus = event_bus
        self._strategies: Dict[str, 'BaseStrategy'] = {}

        # 订阅事件
        self._subscribe_events()

        logger.info(f"[st_manager.py:{self._get_line_number()}] STManager 初始化完成")

    def _subscribe_events(self) -> None:
        """订阅所有需要的事件"""
        self._event_bus.subscribe(STEvents.INPUT_ACCOUNT_LOADED, self._handle_account_loaded)
        self._event_bus.subscribe(STEvents.INPUT_INDICATORS_COMPLETED, self._handle_indicators_completed)
        self._event_bus.subscribe(STEvents.INPUT_POSITION_OPENED, self._handle_position_opened)
        self._event_bus.subscribe(STEvents.INPUT_POSITION_CLOSED, self._handle_position_closed)
        logger.debug(f"[st_manager.py:{self._get_line_number()}] 已订阅 {STEvents.INPUT_ACCOUNT_LOADED} 事件")
        logger.debug(f"[st_manager.py:{self._get_line_number()}] 已订阅 {STEvents.INPUT_INDICATORS_COMPLETED} 事件")
        logger.debug(f"[st_manager.py:{self._get_line_number()}] 已订阅 {STEvents.INPUT_POSITION_OPENED} 事件")
        logger.debug(f"[st_manager.py:{self._get_line_number()}] 已订阅 {STEvents.INPUT_POSITION_CLOSED} 事件")

    async def _handle_account_loaded(self, event: Event) -> None:
        """
        处理账户加载事件

        当PM模块加载账户后，加载对应的策略配置并创建策略实例。

        Args:
            event: 账户加载事件
                data: {
                    "user_id": "user_001",
                    "strategy_name": "ma_stop_st"
                }
        """
        from src.core.st.base_strategy import BaseStrategy

        user_id = event.data.get("user_id")
        strategy_name = event.data.get("strategy_name")

        if not user_id or not strategy_name:
            logger.warning(f"[st_manager.py:{self._get_line_number()}] 账户加载事件缺少必要字段")
            return

        # 加载策略配置
        config = self._load_config(user_id, strategy_name)
        if not config:
            logger.error(f"[st_manager.py:{self._get_line_number()}] 策略配置加载失败: {user_id}/{strategy_name}")
            return

        # 验证配置
        if not self._validate_config(config):
            logger.error(f"[st_manager.py:{self._get_line_number()}] 策略配置验证失败: {user_id}/{strategy_name}")
            return

        # 动态导入策略类（这里使用测试策略类）
        # 在实际应用中，应该根据strategy_name动态导入对应的策略类
        # 例如：from src.strategies.ma_stop_st import MAStopStrategy
        # 这里为了测试，我们需要一个通用的策略实现

        # 创建策略实例
        # 注意：这里需要一个具体的策略类，而不是抽象基类
        # 暂时跳过策略实例创建，等待具体策略类实现
        logger.info(f"[st_manager.py:{self._get_line_number()}] 策略配置已加载: {user_id}/{strategy_name}")

        # TODO: 创建策略实例并存储到 self._strategies[user_id]

    async def _handle_indicators_completed(self, event: Event) -> None:
        """
        处理指标计算完成事件

        当TA模块完成该交易对所有指标的计算后，调用对应策略的处理方法。

        Args:
            event: 指标计算完成事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "timeframe": "15m",
                    "indicators": {
                        "ma_stop_ta": {"signal": "LONG", "data": {...}},
                        ...
                    }
                }
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        indicators = event.data.get("indicators", {})

        # 查找对应的策略实例
        strategy = self._strategies.get(user_id)
        if not strategy:
            logger.warning(f"[st_manager.py:{self._get_line_number()}] 用户策略不存在: {user_id}")
            return

        # 调用策略的指标处理方法
        await strategy.on_indicators_completed(symbol, indicators)
        logger.debug(f"[st_manager.py:{self._get_line_number()}] 已处理指标完成事件: {user_id}/{symbol}")

    async def _handle_position_opened(self, event: Event) -> None:
        """
        处理持仓开启事件

        当TR模块开启持仓后，更新策略的持仓状态为LONG或SHORT。

        Args:
            event: 持仓开启事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "side": "LONG",  # 或 "SHORT"
                    "quantity": 100,
                    "entry_price": 1.5
                }
        """
        from src.core.st.base_strategy import PositionState

        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        side = event.data.get("side")
        entry_price = event.data.get("entry_price")

        # 查找对应的策略实例
        strategy = self._strategies.get(user_id)
        if not strategy:
            logger.warning(f"[st_manager.py:{self._get_line_number()}] 用户策略不存在: {user_id}")
            return

        # 将side转换为PositionState
        position_state = PositionState.LONG if side == "LONG" else PositionState.SHORT

        # 更新持仓状态
        strategy.update_position(symbol, position_state)
        logger.info(f"[st_manager.py:{self._get_line_number()}] 持仓状态已更新: {user_id}/{symbol} -> {position_state.value}")

        # 调用策略的持仓开启处理方法（可能触发网格交易）
        await strategy.on_position_opened(symbol, side, entry_price)

    async def _handle_position_closed(self, event: Event) -> None:
        """
        处理持仓关闭事件

        当TR模块关闭持仓后，更新策略的持仓状态为NONE。

        Args:
            event: 持仓关闭事件
                data: {
                    "user_id": "user_001",
                    "symbol": "XRPUSDC",
                    "side": "LONG",
                    "exit_price": 1.6,
                    "pnl": 10.0
                }
        """
        from src.core.st.base_strategy import PositionState

        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        side = event.data.get("side")

        # 查找对应的策略实例
        strategy = self._strategies.get(user_id)
        if not strategy:
            logger.warning(f"[st_manager.py:{self._get_line_number()}] 用户策略不存在: {user_id}")
            return

        # 更新持仓状态为NONE
        strategy.update_position(symbol, PositionState.NONE)
        logger.info(f"[st_manager.py:{self._get_line_number()}] 持仓状态已更新: {user_id}/{symbol} -> NONE")

        # 调用策略的持仓关闭处理方法（可能触发反向建仓）
        await strategy.on_position_closed(symbol, side)

    async def _load_config(self, user_id: str, strategy: str) -> Optional[Dict[str, Any]]:
        """
        加载策略配置文件

        Args:
            user_id: 用户ID
            strategy: 策略名称

        Returns:
            配置字典，如果加载失败则返回None
        """
        config_path = Path(f"config/strategies/{user_id}/{strategy}.json")

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"[st_manager.py:{self._get_line_number()}] 加载策略配置成功: {user_id}/{strategy}")
            return config
        except FileNotFoundError:
            logger.error(f"[st_manager.py:{self._get_line_number()}] 配置文件不存在: {config_path}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[st_manager.py:{self._get_line_number()}] 配置文件格式错误: {e}")
            return None
        except Exception as e:
            logger.error(f"[st_manager.py:{self._get_line_number()}] 加载配置文件失败: {e}")
            return None

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """
        验证策略配置文件

        Args:
            config: 配置字典

        Returns:
            验证是否通过
        """
        required_fields = ["timeframe", "leverage", "position_side",
                          "margin_mode", "margin_type", "trading_pairs"]

        # 检查必需字段
        for field in required_fields:
            if field not in config:
                logger.error(f"[st_manager.py:{self._get_line_number()}] 配置缺少必需字段: {field}")
                return False

        # 检查trading_pairs
        if not isinstance(config["trading_pairs"], list) or len(config["trading_pairs"]) == 0:
            logger.error(f"[st_manager.py:{self._get_line_number()}] trading_pairs 必须是非空数组")
            return False

        logger.debug(f"[st_manager.py:{self._get_line_number()}] 配置验证通过")
        return True

