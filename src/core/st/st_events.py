"""
ST模块事件主题常量

定义ST模块订阅和发布的所有事件主题，避免硬编码字符串。
遵循事件命名规范：模块.对象.动作

使用方式：
    from src.core.st.st_events import STEvents
    
    # 订阅事件
    event_bus.subscribe(STEvents.INPUT_ACCOUNT_LOADED, handler)
    
    # 发布事件
    event = Event(
        subject=STEvents.STRATEGY_LOADED,
        data={"user_id": "user_001", ...}
    )
"""


class STEvents:
    """
    ST模块事件主题常量类
    
    包含两类事件：
    1. 订阅的事件（输入）：ST模块监听的其他模块发布的事件
    2. 发布的事件（输出）：ST模块发布的事件供其他模块订阅
    
    所有事件主题都定义在这里，确保：
    - 避免硬编码字符串
    - 统一事件命名规范
    - 便于维护和查找
    """
    
    # ==================== 订阅的事件（输入） ====================
    
    # PM模块发布的账户加载事件
    # 触发ST模块加载策略配置并创建策略实例
    # 数据格式: {user_id, name, api_key, api_secret, strategy, testnet}
    INPUT_ACCOUNT_LOADED = "pm.account.loaded"
    
    # TA模块发布的指标计算完成事件
    # 触发ST模块处理所有指标结果并生成交易决策
    # 数据格式: {user_id, symbol, timeframe, indicators}
    # indicators: {"ma_stop_ta": {"signal": "LONG", "data": {...}}, ...}
    INPUT_INDICATORS_COMPLETED = "ta.calculation.completed"
    
    # TR模块发布的持仓开启事件
    # 触发ST模块更新持仓状态为LONG/SHORT，可能触发网格交易
    # 数据格式: {user_id, symbol, side, quantity, entry_price}
    INPUT_POSITION_OPENED = "tr.position.opened"
    
    # TR模块发布的持仓关闭事件
    # 触发ST模块更新持仓状态为NONE，可能触发反向建仓
    # 数据格式: {user_id, symbol, side, exit_price, pnl}
    INPUT_POSITION_CLOSED = "tr.position.closed"
    
    # ==================== 发布的事件（输出） ====================
    
    # 策略加载成功事件
    # 当策略实例创建成功时发布
    # 数据格式: {user_id, strategy, timeframe, trading_pairs}
    STRATEGY_LOADED = "st.strategy.loaded"
    
    # 指标订阅请求事件
    # 当策略实例创建后，为每个交易对发布此事件请求TA模块订阅指标
    # 数据格式: {user_id, symbol, indicator_name, indicator_params, timeframe}
    # 示例: {
    #     "user_id": "user_001",
    #     "symbol": "XRPUSDC",
    #     "indicator_name": "ma_stop_ta",
    #     "indicator_params": {"period": 3, "percent": 2},
    #     "timeframe": "15m"
    # }
    INDICATOR_SUBSCRIBE = "st.indicator.subscribe"
    
    # 交易信号生成事件
    # 当策略生成交易信号时发布，供TR模块执行交易
    # 数据格式: {user_id, symbol, side, action, quantity}
    # side: "LONG" 或 "SHORT"
    # action: "OPEN" 或 "CLOSE"
    SIGNAL_GENERATED = "st.signal.generated"
    
    # 网格交易创建事件
    # 当持仓开启后且配置开启网格交易时发布，供TR模块创建网格订单
    # 数据格式: {user_id, symbol, entry_price, grid_levels, grid_ratio, move_up, move_down}
    GRID_CREATE = "st.grid.create"

