"""
TA模块事件主题常量

定义TA模块订阅和发布的所有事件主题，避免硬编码字符串。
遵循事件命名规范：模块.对象.动作

使用方式：
    from src.core.ta.ta_events import TAEvents
    
    # 订阅事件
    event_bus.subscribe(TAEvents.INPUT_INDICATOR_SUBSCRIBE, handler)
    
    # 发布事件
    event = Event(
        subject=TAEvents.CALCULATION_COMPLETED,
        data={"user_id": "user_001", ...}
    )
"""


class TAEvents:
    """
    TA模块事件主题常量类
    
    包含两类事件：
    1. 订阅的事件（输入）：TA模块监听的其他模块发布的事件
    2. 发布的事件（输出）：TA模块发布的事件供其他模块订阅
    
    所有事件主题都定义在这里，确保：
    - 避免硬编码字符串
    - 统一事件命名规范
    - 便于维护和查找
    """
    
    # ==================== 订阅的事件（输入） ====================
    
    # ST模块发布的指标订阅请求事件
    # 触发TA模块创建指标实例并请求历史K线数据
    # 数据格式: {user_id, symbol, indicator_name, indicator_params}
    # 示例: {
    #     "user_id": "user_001",
    #     "symbol": "XRPUSDC",
    #     "indicator_name": "ma_stop_ta",
    #     "indicator_params": {"period": 3, "percent": 2}
    # }
    INPUT_INDICATOR_SUBSCRIBE = "st.indicator.subscribe"
    
    # DE模块发布的历史K线数据成功事件
    # 触发TA模块初始化指标实例的历史数据
    # 数据格式: {user_id, symbol, interval, klines: [...]}
    # klines格式: 每个元素为[开盘时间, 开盘价, 最高价, 最低价, 收盘价, 成交量, ...]
    INPUT_HISTORICAL_KLINES_SUCCESS = "de.historical_klines.success"
    
    # DE模块发布的历史K线数据失败事件
    # 触发TA模块记录错误并可能重试
    # 数据格式: {user_id, symbol, interval, error}
    INPUT_HISTORICAL_KLINES_FAILED = "de.historical_klines.failed"
    
    # DE模块发布的实时K线更新事件
    # 触发TA模块更新指标计算
    # 数据格式: {user_id, symbol, interval, klines: [{open, high, low, close, volume, timestamp, is_closed}, ...]}
    # 注意：DE模块只在K线关闭时发布此事件，klines包含完整的历史K线列表（包括最新关闭的K线）
    INPUT_KLINE_UPDATE = "de.kline.update"
    
    # ==================== 发布的事件（输出） ====================
    
    # 指标计算完成事件
    # 当同一交易对的所有指标都计算完成后发布，供ST模块订阅
    # 数据格式: {user_id, symbol, timeframe, indicators}
    # indicators格式: {
    #     "ma_stop_ta": {"signal": "LONG", "data": {...}},
    #     "rsi_ta": {"signal": "SHORT", "data": {...}}
    # }
    # signal取值: "LONG"（多头）, "SHORT"（空头）, "NONE"（无信号）
    CALCULATION_COMPLETED = "ta.calculation.completed"
    
    # 指标创建成功事件
    # 当指标实例创建成功时发布（用于调试和监控）
    # 数据格式: {user_id, symbol, indicator_name, indicator_id}
    INDICATOR_CREATED = "ta.indicator.created"
    
    # 指标创建失败事件
    # 当指标实例创建失败时发布
    # 数据格式: {user_id, symbol, indicator_name, error}
    INDICATOR_CREATE_FAILED = "ta.indicator.create_failed"

