"""
TR模块事件主题常量

定义TR模块订阅和发布的所有事件主题，避免硬编码字符串。
遵循事件命名规范：模块.对象.动作

使用方式：
    from src.core.tr.tr_events import TREvents
    
    # 订阅事件
    event_bus.subscribe(TREvents.INPUT_ACCOUNT_LOADED, handler)
    
    # 发布事件
    event = Event(
        subject=TREvents.POSITION_OPENED,
        data={"user_id": "user_001", ...}
    )
"""


class TREvents:
    """
    TR模块事件主题常量类
    
    包含两类事件：
    1. 订阅的事件（输入）：TR模块监听的其他模块发布的事件
    2. 发布的事件（输出）：TR模块发布的事件供其他模块订阅
    
    所有事件主题都定义在这里，确保：
    - 避免硬编码字符串
    - 统一事件命名规范
    - 便于维护和查找
    """
    
    # ==================== 订阅的事件（输入） ====================
    
    # PM模块发布的账户加载事件
    # 触发TR模块初始化资金管理，获取账户余额
    # 数据格式: {user_id, name, api_key, api_secret, strategy, testnet}
    INPUT_ACCOUNT_LOADED = "pm.account.loaded"
    
    # ST模块发布的交易信号事件
    # 触发TR模块执行订单（建仓或平仓）
    # 数据格式: {user_id, symbol, side, action}
    # side: "LONG" 或 "SHORT"
    # action: "OPEN" 或 "CLOSE"
    INPUT_SIGNAL_GENERATED = "st.signal.generated"
    
    # ST模块发布的网格创建事件
    # 触发TR模块创建网格订单
    # 数据格式: {user_id, symbol, entry_price, upper_price, lower_price, grid_levels, grid_ratio, move_up, move_down, side}
    # upper_price: 网格上边价格（由ST策略计算）
    # lower_price: 网格下边价格（由ST策略计算）
    # side: 网格方向，"LONG"表示多头网格，"SHORT"表示空头网格
    INPUT_GRID_CREATE = "st.grid.create"
    
    # DE模块发布的订单成交事件
    # 触发TR模块更新订单状态和持仓信息
    # 数据格式: {user_id, order_id, symbol, price, quantity, timestamp}
    INPUT_ORDER_FILLED = "de.order.filled"
    
    # DE模块发布的订单状态更新事件
    # 触发TR模块更新订单状态
    # 数据格式: {user_id, order_id, status, filled_quantity, remaining_quantity}
    INPUT_ORDER_UPDATE = "de.order.update"
    
    # DE模块发布的订单提交成功事件
    # 触发TR模块记录订单ID
    # 数据格式: {user_id, order_id, symbol, side, type, quantity, price}
    INPUT_ORDER_SUBMITTED = "de.order.submitted"
    
    # DE模块发布的订单提交失败事件
    # 触发TR模块记录失败信息并可能重试
    # 数据格式: {user_id, symbol, error, retry_count}
    INPUT_ORDER_FAILED = "de.order.failed"
    
    # DE模块发布的订单取消成功事件
    # 触发TR模块更新订单状态
    # 数据格式: {user_id, order_id, symbol}
    INPUT_ORDER_CANCELLED = "de.order.cancelled"
    
    # DE模块发布的账户余额事件
    # 触发TR模块更新可用保证金
    # 数据格式: {user_id, asset, available_balance}
    INPUT_ACCOUNT_BALANCE = "de.account.balance"
    
    # ==================== 发布的事件（输出） ====================
    
    # 持仓开启事件
    # 当入场订单成交后发布，通知ST模块持仓已建立
    # 数据格式: {user_id, symbol, side, quantity, entry_price}
    # side: "LONG" 或 "SHORT"
    POSITION_OPENED = "tr.position.opened"
    
    # 持仓关闭事件
    # 当平仓完成后发布，通知ST模块持仓已关闭
    # 数据格式: {user_id, symbol, side, exit_price, pnl}
    # side: "LONG" 或 "SHORT"
    # pnl: 盈亏金额
    POSITION_CLOSED = "tr.position.closed"
    
    # 订单创建请求事件
    # 向DE模块发送订单创建请求
    # 数据格式: {user_id, symbol, side, order_type, quantity, price?, stopPrice?}
    # side: "BUY" 或 "SELL"
    # order_type: "MARKET", "LIMIT", "POST_ONLY", "STOP", "TAKE_PROFIT"等
    ORDER_CREATE = "trading.order.create"
    
    # 订单取消请求事件
    # 向DE模块发送订单取消请求
    # 数据格式: {user_id, symbol, order_id}
    ORDER_CANCEL = "trading.order.cancel"
    
    # 账户余额查询请求事件
    # 向DE模块发送账户余额查询请求
    # 数据格式: {user_id, asset}
    # asset: 保证金资产类型，如 "USDT" 或 "USDC"
    ACCOUNT_BALANCE_REQUEST = "trading.get_account_balance"
    
    # TR管理器启动完成事件
    # 当TR管理器初始化完成后发布
    # 数据格式: {timestamp, user_count}
    MANAGER_STARTED = "tr.manager.started"
    
    # TR管理器关闭事件
    # 当TR管理器关闭时发布
    # 数据格式: {timestamp}
    MANAGER_SHUTDOWN = "tr.manager.shutdown"
    
    # 网格订单创建完成事件
    # 当网格订单全部创建完成后发布
    # 数据格式: {user_id, symbol, grid_count, total_quantity}
    GRID_CREATED = "tr.grid.created"
    
    # 网格移动事件
    # 当网格因价格突破边界而移动时发布
    # 数据格式: {user_id, symbol, direction, new_upper_price, new_lower_price}
    # direction: "UP" 或 "DOWN"
    GRID_MOVED = "tr.grid.moved"
    
    # 交易任务创建事件
    # 当创建新的交易任务时发布
    # 数据格式: {user_id, symbol, task_id, side}
    TASK_CREATED = "tr.task.created"
    
    # 交易任务完成事件
    # 当交易任务完成（平仓）时发布
    # 数据格式: {user_id, symbol, task_id, pnl, duration}
    TASK_COMPLETED = "tr.task.completed"



