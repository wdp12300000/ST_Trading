"""
TR模块管理器

TRManager是TR模块的核心管理类，采用单例模式，负责：
1. 管理所有用户的交易任务
2. 订阅和处理事件
3. 协调各个子模块（资金管理、订单管理、网格管理）
4. 维护用户到交易任务的映射关系

使用方式：
    from src.core.tr.tr_manager import TRManager
    from src.core.event.event_bus import EventBus
    
    event_bus = EventBus()
    tr_manager = TRManager.get_instance(event_bus=event_bus)
    await tr_manager.start()
"""

from typing import Dict, Optional, Any
from loguru import logger
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.tr.tr_events import TREvents
from src.core.tr.order_manager import OrderManager
from src.core.tr.capital_manager import CapitalManager
from src.core.tr.precision_handler import PrecisionHandler
from src.core.tr.trading_task import TradingTask, TradingMode, PositionState
from src.core.tr.grid_manager import GridManager


class TRManager:
    """
    TR模块管理器（单例模式）
    
    负责管理所有用户的交易任务，协调订单执行、持仓管理、网格交易等功能。
    
    Attributes:
        _instance: 单例实例
        _event_bus: 事件总线实例
        _tasks: 交易任务字典，key为(user_id, symbol)，value为TradingTask实例
        _user_configs: 用户配置字典，key为user_id，value为配置信息
        _is_started: 是否已启动
    
    Example:
        >>> event_bus = EventBus()
        >>> tr_manager = TRManager.get_instance(event_bus=event_bus)
        >>> await tr_manager.start()
    """
    
    _instance: Optional['TRManager'] = None
    
    def __init__(self, event_bus: EventBus):
        """
        初始化TR管理器
        
        注意：不要直接调用此方法，请使用 get_instance() 获取单例实例
        
        Args:
            event_bus: 事件总线实例
        """
        if TRManager._instance is not None:
            raise RuntimeError("TRManager是单例类，请使用get_instance()方法获取实例")
        
        self._event_bus: EventBus = event_bus
        self._tasks: Dict[tuple, Any] = {}  # key: (user_id, symbol), value: TradingTask
        self._user_configs: Dict[str, Dict[str, Any]] = {}  # key: user_id, value: config
        self._capital_managers: Dict[str, CapitalManager] = {}  # key: user_id, value: CapitalManager
        self._is_started: bool = False

        # 初始化子模块
        self._order_manager = OrderManager(event_bus)
        self._precision_handler = PrecisionHandler()
        self._grid_manager = GridManager(event_bus, self._order_manager, self._precision_handler)

        logger.info(f"[tr_manager.py:{self._get_line_number()}] TRManager实例创建成功")
    
    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> 'TRManager':
        """
        获取TRManager单例实例
        
        Args:
            event_bus: 事件总线实例（首次调用时必须提供）
        
        Returns:
            TRManager: 单例实例
        
        Raises:
            ValueError: 首次调用时未提供event_bus
        
        Example:
            >>> event_bus = EventBus()
            >>> tr_manager = TRManager.get_instance(event_bus=event_bus)
        """
        if cls._instance is None:
            if event_bus is None:
                raise ValueError("首次调用get_instance()时必须提供event_bus参数")
            cls._instance = cls(event_bus)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（仅用于测试）
        
        警告：此方法仅用于单元测试，生产环境不应调用
        """
        cls._instance = None
        logger.warning(f"[tr_manager.py:{cls._get_line_number_static()}] TRManager实例已重置")
    
    async def start(self) -> None:
        """
        启动TR管理器
        
        订阅所有必要的事件，初始化各个子模块
        
        Raises:
            RuntimeError: 如果已经启动
        """
        if self._is_started:
            raise RuntimeError("TRManager已经启动，不能重复启动")
        
        # 订阅事件
        await self._subscribe_events()
        
        self._is_started = True
        logger.info(f"[tr_manager.py:{self._get_line_number()}] TRManager启动成功")
        
        # 发布启动完成事件
        await self._publish_manager_started()
    
    async def _subscribe_events(self) -> None:
        """
        订阅所有必要的事件
        
        订阅来自PM、ST、DE模块的事件
        """
        # 订阅PM模块的账户加载事件
        self._event_bus.subscribe(
            TREvents.INPUT_ACCOUNT_LOADED,
            self._on_account_loaded
        )

        # 订阅ST模块的交易信号事件
        self._event_bus.subscribe(
            TREvents.INPUT_SIGNAL_GENERATED,
            self._on_signal_generated
        )

        # 订阅ST模块的网格创建事件
        self._event_bus.subscribe(
            TREvents.INPUT_GRID_CREATE,
            self._on_grid_create
        )

        # 订阅DE模块的订单成交事件
        self._event_bus.subscribe(
            TREvents.INPUT_ORDER_FILLED,
            self._on_order_filled
        )

        # 订阅DE模块的订单状态更新事件
        self._event_bus.subscribe(
            TREvents.INPUT_ORDER_UPDATE,
            self._on_order_update
        )

        # 订阅DE模块的订单提交成功事件
        self._event_bus.subscribe(
            TREvents.INPUT_ORDER_SUBMITTED,
            self._on_order_submitted
        )

        # 订阅DE模块的账户余额事件
        self._event_bus.subscribe(
            TREvents.INPUT_ACCOUNT_BALANCE,
            self._on_account_balance
        )
        
        logger.info(f"[tr_manager.py:{self._get_line_number()}] 事件订阅完成")
    
    async def _on_account_loaded(self, event: Event) -> None:
        """
        处理账户加载事件

        当PM模块加载账户后，初始化该用户的资金管理

        Args:
            event: 账户加载事件
        """
        user_id = event.data.get("user_id")
        strategy_config = event.data.get("strategy_config", {})

        logger.info(f"[tr_manager.py:{self._get_line_number()}] 收到账户加载事件: {user_id}")

        # 获取杠杆和保证金类型
        leverage = strategy_config.get("leverage", 1)
        margin_type = strategy_config.get("margin_type", "USDC")

        # 创建资金管理器
        capital_manager = CapitalManager(user_id, leverage, margin_type)
        self._capital_managers[user_id] = capital_manager

        # 保存用户配置
        self._user_configs[user_id] = strategy_config

        # 请求账户余额
        await self._order_manager.request_account_balance(user_id, margin_type)

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 资金管理器创建完成: "
            f"{user_id} 杠杆={leverage}x 保证金类型={margin_type}"
        )
    
    async def _on_signal_generated(self, event: Event) -> None:
        """
        处理交易信号事件

        根据交易模式执行不同的逻辑：
        - NO_GRID: 直接提交市价单
        - NORMAL_GRID: 创建网格交易（TODO: 第四阶段实现）
        - ABNORMAL_GRID: 提交入场订单，等待ST发送网格信息

        Args:
            event: 交易信号事件
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        side = event.data.get("side")  # "LONG" or "SHORT"
        action = event.data.get("action")  # "OPEN" or "CLOSE"

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 收到交易信号: "
            f"{user_id}/{symbol} {side} {action}"
        )

        # 获取或创建交易任务
        task_key = (user_id, symbol)
        if task_key not in self._tasks:
            strategy_config = self._user_configs.get(user_id, {})
            task = TradingTask(user_id, symbol, strategy_config)
            self._tasks[task_key] = task

            # 发布任务创建事件
            await self._event_bus.publish(Event(
                subject=TREvents.TASK_CREATED,
                data={"user_id": user_id, "symbol": symbol, "mode": task.get_trading_mode().value}
            ))
        else:
            task = self._tasks[task_key]

        # 处理入场信号
        if action == "OPEN":
            await self._handle_entry_signal(task, side, event.data)
        # 处理出场信号
        elif action == "CLOSE":
            await self._handle_exit_signal(task, event.data)
    
    async def _on_grid_create(self, event: Event) -> None:
        """
        处理网格创建事件

        当ST模块发送网格创建请求后，创建网格订单（特殊网格模式）

        Args:
            event: 网格创建事件
        """
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        upper_price = float(event.data.get("upper_price", 0))
        lower_price = float(event.data.get("lower_price", 0))
        grid_levels = int(event.data.get("grid_levels", 10))
        move_up = event.data.get("move_up", False)
        move_down = event.data.get("move_down", False)

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 收到网格创建请求: "
            f"{user_id}/{symbol} 上边={upper_price} 下边={lower_price} 层数={grid_levels}"
        )

        # 获取交易任务
        task_key = (user_id, symbol)
        if task_key not in self._tasks:
            logger.error(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"未找到交易任务: {user_id}/{symbol}"
            )
            return

        task = self._tasks[task_key]

        # 设置网格配置
        task.set_grid_config(upper_price, lower_price, grid_levels, move_up, move_down)

        # 获取资金管理器
        capital_manager = self._capital_managers.get(user_id)
        if not capital_manager:
            logger.error(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"未找到用户{user_id}的资金管理器"
            )
            return

        # 计算网格仓位（使用剩余资金，即1-ratio）
        strategy_config = self._user_configs.get(user_id, {})
        trading_pairs = strategy_config.get("trading_pairs", [])
        symbol_count = len(trading_pairs)
        margin_per_symbol = capital_manager.calculate_margin_per_symbol(symbol_count)

        # 获取入场价格和持仓方向
        if not task.is_position_open():
            logger.warning(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"持仓未开启，无法创建网格"
            )
            return

        entry_price = task.entry_price
        ratio = task.get_grid_ratio()
        grid_ratio = 1.0 - ratio  # 网格使用剩余资金

        # 计算网格总数量
        total_quantity = capital_manager.calculate_grid_position_size(
            margin_per_symbol, entry_price, grid_levels, grid_ratio
        )

        # 创建网格订单
        order_side = "SELL" if task.entry_side == "LONG" else "BUY"
        order_ids = await self._grid_manager.create_grid_orders(
            user_id, symbol, upper_price, lower_price, grid_levels,
            total_quantity, order_side, "POST_ONLY"
        )

        # 保存网格订单ID到任务
        for order_id in order_ids:
            task.add_grid_order(order_id)

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 网格订单创建完成: "
            f"{symbol} 订单数量={len(order_ids)}"
        )
    
    async def _on_order_filled(self, event: Event) -> None:
        """
        处理订单成交事件

        当DE模块报告订单成交后：
        1. 更新订单状态
        2. 如果是入场订单，开启持仓并发布 tr.position.opened 事件
        3. 如果是出场订单，关闭持仓并发布 tr.position.closed 事件

        Args:
            event: 订单成交事件
        """
        user_id = event.data.get("user_id")
        order_id = event.data.get("order_id")
        symbol = event.data.get("symbol")
        price = float(event.data.get("price", 0))
        quantity = float(event.data.get("quantity", 0))
        side = event.data.get("side")  # "BUY" or "SELL"

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 收到订单成交事件: "
            f"{user_id}/{symbol} {order_id} {side} {quantity}@{price}"
        )

        # 获取交易任务
        task_key = (user_id, symbol)
        if task_key not in self._tasks:
            logger.warning(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"未找到交易任务: {user_id}/{symbol}"
            )
            return

        task = self._tasks[task_key]

        # 更新订单状态
        task.update_order_status(order_id, "FILLED", quantity)

        # 判断是入场还是出场
        if not task.is_position_open():
            # 入场订单成交
            position_side = "LONG" if side == "BUY" else "SHORT"
            await task.open_position(position_side, price, quantity)

            # 发布持仓开启事件
            await self._event_bus.publish(Event(
                subject=TREvents.POSITION_OPENED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "side": position_side,
                    "entry_price": price,
                    "quantity": quantity,
                    "mode": task.get_trading_mode().value
                }
            ))

            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] 持仓开启: "
                f"{symbol} {position_side} {quantity}@{price}"
            )
        else:
            # 出场订单成交
            pnl = await task.close_position(price)

            # 发布持仓关闭事件
            await self._event_bus.publish(Event(
                subject=TREvents.POSITION_CLOSED,
                data={
                    "user_id": user_id,
                    "symbol": symbol,
                    "side": task.entry_side,
                    "exit_price": price,
                    "pnl": pnl
                }
            ))

            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] 持仓关闭: "
                f"{symbol} 盈亏={pnl}"
            )
    
    async def _on_order_update(self, event: Event) -> None:
        """
        处理订单状态更新事件
        
        Args:
            event: 订单状态更新事件
        """
        user_id = event.data.get("user_id")
        order_id = event.data.get("order_id")
        logger.debug(f"[tr_manager.py:{self._get_line_number()}] 收到订单状态更新: {user_id}/{order_id}")
        # TODO: 实现订单状态更新逻辑
    
    async def _on_order_submitted(self, event: Event) -> None:
        """
        处理订单提交成功事件
        
        Args:
            event: 订单提交成功事件
        """
        user_id = event.data.get("user_id")
        order_id = event.data.get("order_id")
        logger.info(f"[tr_manager.py:{self._get_line_number()}] 订单提交成功: {user_id}/{order_id}")
        # TODO: 实现订单提交成功处理逻辑
    
    async def _on_account_balance(self, event: Event) -> None:
        """
        处理账户余额事件

        Args:
            event: 账户余额事件
        """
        user_id = event.data.get("user_id")
        available_balance = float(event.data.get("available_balance", 0))
        total_balance = float(event.data.get("balance", 0))

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 收到账户余额: "
            f"{user_id} 可用={available_balance} 总额={total_balance}"
        )

        # 更新资金管理器
        if user_id in self._capital_managers:
            self._capital_managers[user_id].update_balance(available_balance, total_balance)
        else:
            logger.warning(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"未找到用户{user_id}的资金管理器"
            )
    
    async def _publish_manager_started(self) -> None:
        """发布管理器启动完成事件"""
        event = Event(
            subject=TREvents.MANAGER_STARTED,
            data={
                "user_count": len(self._user_configs)
            },
            source="tr"
        )
        await self._event_bus.publish(event)
    
    async def shutdown(self) -> None:
        """
        关闭TR管理器
        
        清理资源，发布关闭事件
        """
        if not self._is_started:
            logger.warning(f"[tr_manager.py:{self._get_line_number()}] TRManager未启动，无需关闭")
            return
        
        logger.info(f"[tr_manager.py:{self._get_line_number()}] 正在关闭TRManager...")
        
        # 发布关闭事件
        event = Event(
            subject=TREvents.MANAGER_SHUTDOWN,
            data={},
            source="tr"
        )
        await self._event_bus.publish(event)
        
        self._is_started = False
        logger.info(f"[tr_manager.py:{self._get_line_number()}] TRManager已关闭")
    
    async def _handle_entry_signal(self, task: TradingTask, side: str, signal_data: Dict[str, Any]) -> None:
        """
        处理入场信号

        根据交易模式执行不同逻辑：
        - NO_GRID: 提交市价单
        - NORMAL_GRID: 创建网格交易（TODO: 第四阶段实现）
        - ABNORMAL_GRID: 提交入场订单（使用ratio比例资金）

        Args:
            task: 交易任务
            side: 持仓方向（"LONG" or "SHORT"）
            signal_data: 信号数据
        """
        user_id = task.user_id
        symbol = task.symbol
        trading_mode = task.get_trading_mode()

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 处理入场信号: "
            f"{symbol} {side} 模式={trading_mode.value}"
        )

        # 获取资金管理器
        capital_manager = self._capital_managers.get(user_id)
        if not capital_manager:
            logger.error(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"未找到用户{user_id}的资金管理器"
            )
            return

        # 计算保证金分配
        strategy_config = self._user_configs.get(user_id, {})
        trading_pairs = strategy_config.get("trading_pairs", [])
        symbol_count = len(trading_pairs)
        margin_per_symbol = capital_manager.calculate_margin_per_symbol(symbol_count)

        # 获取入场价格（从信号数据或使用市价）
        entry_price = signal_data.get("price")
        if not entry_price:
            # TODO: 从市场数据获取当前价格
            logger.warning(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"信号未提供价格，暂时使用占位符"
            )
            entry_price = 1.0  # 占位符，实际应从市场数据获取

        # 根据交易模式计算仓位
        if trading_mode == TradingMode.NO_GRID:
            # 无网格模式：使用全部保证金
            quantity = capital_manager.calculate_position_size(margin_per_symbol, entry_price, 1.0)

            # 提交市价单
            order_side = "BUY" if side == "LONG" else "SELL"
            self._order_manager.submit_market_order(user_id, symbol, order_side, quantity)

            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] 提交市价单: "
                f"{symbol} {order_side} 数量={quantity}"
            )

        elif trading_mode == TradingMode.NORMAL_GRID:
            # 普通网格模式：直接创建网格交易
            # 需要等待ST模块发送网格配置（st.grid.create事件）
            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"普通网格模式，等待ST模块发送网格配置"
            )
            # 网格配置会通过 _on_grid_create 事件处理器接收
            # 但普通网格模式不需要先建仓，所以这里需要特殊处理

            # 获取网格配置（如果已经设置）
            grid_config = task.grid_config
            if grid_config:
                upper_price = grid_config.get("upper_price")
                lower_price = grid_config.get("lower_price")
                grid_levels = grid_config.get("grid_levels", 10)

                # 计算网格总数量（使用全部保证金）
                total_quantity = capital_manager.calculate_grid_position_size(
                    margin_per_symbol, entry_price, grid_levels, 1.0
                )

                # 创建对称网格订单（买单和卖单）
                result = await self._grid_manager.create_symmetric_grid_orders(
                    user_id, symbol, entry_price, upper_price, lower_price,
                    grid_levels, total_quantity, "POST_ONLY"
                )

                # 保存网格订单ID
                for order_id in result["buy_order_ids"] + result["sell_order_ids"]:
                    task.add_grid_order(order_id)

                logger.info(
                    f"[tr_manager.py:{self._get_line_number()}] 普通网格订单创建完成: "
                    f"{symbol} 买单={len(result['buy_order_ids'])} 卖单={len(result['sell_order_ids'])}"
                )
            else:
                logger.warning(
                    f"[tr_manager.py:{self._get_line_number()}] "
                    f"普通网格模式但未收到网格配置"
                )

        elif trading_mode == TradingMode.ABNORMAL_GRID:
            # 特殊网格模式：使用ratio比例资金建仓
            ratio = task.get_grid_ratio()
            quantity = capital_manager.calculate_position_size(margin_per_symbol, entry_price, ratio)

            # 提交市价单
            order_side = "BUY" if side == "LONG" else "SELL"
            self._order_manager.submit_market_order(user_id, symbol, order_side, quantity)

            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] 提交入场订单: "
                f"{symbol} {order_side} 数量={quantity} 资金比例={ratio}"
            )

    async def _handle_exit_signal(self, task: TradingTask, signal_data: Dict[str, Any]) -> None:
        """
        处理出场信号

        步骤：
        1. 撤销所有网格挂单（如果有）
        2. 提交平仓市价单

        Args:
            task: 交易任务
            signal_data: 信号数据
        """
        user_id = task.user_id
        symbol = task.symbol

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 处理出场信号: {symbol}"
        )

        # 检查是否有持仓
        if not task.is_position_open():
            logger.warning(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"无持仓，忽略出场信号: {symbol}"
            )
            return

        # 撤销所有网格订单
        if task.get_grid_order_count() > 0:
            grid_order_ids = list(task.grid_orders.keys())
            self._order_manager.cancel_all_orders(user_id, symbol, grid_order_ids)
            logger.info(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"撤销网格订单: {symbol} 数量={len(grid_order_ids)}"
            )

        # 提交平仓市价单
        position_state = task.get_position_state()
        quantity = task.entry_quantity

        # 平仓方向与持仓方向相反
        if position_state == PositionState.LONG:
            order_side = "SELL"
        elif position_state == PositionState.SHORT:
            order_side = "BUY"
        else:
            logger.error(
                f"[tr_manager.py:{self._get_line_number()}] "
                f"持仓状态异常: {symbol} {position_state}"
            )
            return

        self._order_manager.submit_market_order(user_id, symbol, order_side, quantity)

        logger.info(
            f"[tr_manager.py:{self._get_line_number()}] 提交平仓订单: "
            f"{symbol} {order_side} 数量={quantity}"
        )

    @staticmethod
    def _get_line_number() -> int:
        """获取当前行号（用于日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

    @staticmethod
    def _get_line_number_static() -> int:
        """获取当前行号（用于静态方法日志）"""
        import inspect
        return inspect.currentframe().f_back.f_lineno

