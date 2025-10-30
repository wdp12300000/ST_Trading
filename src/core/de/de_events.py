"""
DE模块事件主题常量

定义DE模块订阅和发布的所有事件主题，避免硬编码字符串。
遵循事件命名规范：模块.对象.动作

使用方式：
    from src.core.de.de_events import DEEvents

    # 订阅事件
    event_bus.subscribe(DEEvents.INPUT_ACCOUNT_LOADED, handler)

    # 发布事件
    event = Event(
        subject=DEEvents.CLIENT_CONNECTED,
        data={"user_id": "user_001", ...}
    )
"""


class DEEvents:
    """
    DE模块事件主题常量类

    包含两类事件：
    1. 订阅的事件（输入）：DE模块监听的其他模块发布的事件
    2. 发布的事件（输出）：DE模块发布的事件供其他模块订阅

    所有事件主题都定义在这里，确保：
    - 避免硬编码字符串
    - 统一事件命名规范
    - 便于维护和查找
    """

    # ==================== 订阅的事件（输入） ====================

    # PM模块发布的账户加载事件
    # 触发DE模块创建BinanceClient
    # 数据格式: {user_id, name, api_key, api_secret, strategy, testnet}
    INPUT_ACCOUNT_LOADED = "pm.account.loaded"

    # 策略模块发布的K线订阅事件
    # 触发MarketWebSocket订阅K线数据流
    # 数据格式: {user_id, symbol, interval}
    INPUT_SUBSCRIBE_KLINE = "de.subscribe.kline"

    # 策略模块/TA模块发布的历史K线获取事件
    # 触发BinanceClient通过REST API获取历史数据
    # 数据格式: {user_id, symbol, interval, limit}
    INPUT_GET_HISTORICAL_KLINES = "de.get_historical_klines"

    # Trading模块发布的订单创建事件
    # 触发BinanceClient下单
    # 数据格式: {user_id, symbol, side, order_type, quantity, price?, stopPrice?}
    INPUT_ORDER_CREATE = "trading.order.create"

    # Trading模块发布的订单取消事件
    # 触发BinanceClient取消订单
    # 数据格式: {user_id, symbol, order_id}
    INPUT_ORDER_CANCEL = "trading.order.cancel"

    # Trading模块发布的账户余额查询事件
    # 触发BinanceClient查询账户余额
    # 数据格式: {user_id, asset}
    INPUT_GET_ACCOUNT_BALANCE = "trading.get_account_balance"

    # ==================== 发布的事件（输出） ====================

    # 客户端连接成功事件
    # 当BinanceClient创建成功时发布
    # 数据格式: {user_id, timestamp}
    CLIENT_CONNECTED = "de.client.connected"

    # 客户端连接失败事件
    # 当BinanceClient创建失败时发布
    # 数据格式: {user_id, error_type, error_message}
    CLIENT_CONNECTION_FAILED = "de.client.connection_failed"

    # WebSocket连接成功事件
    # 当MarketWebSocket或UserDataWebSocket连接成功时发布
    # 数据格式: {user_id, connection_type, timestamp}
    # connection_type: "market" 或 "user_data"
    WEBSOCKET_CONNECTED = "de.websocket.connected"

    # WebSocket断开事件
    # 当WebSocket连接断开时发布
    # 数据格式: {user_id, connection_type, reason}
    WEBSOCKET_DISCONNECTED = "de.websocket.disconnected"

    # K线数据更新事件
    # 当MarketWebSocket接收到K线关闭消息时发布（只在is_closed=True时发布）
    # 包含完整的历史K线列表（包括最新关闭的K线）
    # 数据格式: {user_id, symbol, interval, klines: [{open, high, low, close, volume, timestamp, is_closed}, ...]}
    KLINE_UPDATE = "de.kline.update"

    # 历史K线获取成功事件
    # 当BinanceClient成功获取历史K线数据时发布
    # 数据格式: {user_id, symbol, interval, klines: [...]}
    HISTORICAL_KLINES_SUCCESS = "de.historical_klines.success"

    # 历史K线获取失败事件
    # 当BinanceClient获取历史K线失败时发布
    # 数据格式: {user_id, symbol, interval, error}
    HISTORICAL_KLINES_FAILED = "de.historical_klines.failed"

    # 订单提交成功事件
    # 当订单成功提交到币安时发布
    # 数据格式: {user_id, order_id, symbol, side, type, quantity, price}
    ORDER_SUBMITTED = "de.order.submitted"

    # 订单提交失败事件
    # 当订单提交失败时发布
    # 数据格式: {user_id, symbol, error, retry_count}
    ORDER_FAILED = "de.order.failed"

    # 订单取消成功事件
    # 当订单成功取消时发布
    # 数据格式: {user_id, order_id, symbol}
    ORDER_CANCELLED = "de.order.cancelled"

    # 订单成交事件
    # 当订单完全成交时发布（来自UserDataWebSocket）
    # 数据格式: {user_id, order_id, symbol, price, quantity, timestamp}
    ORDER_FILLED = "de.order.filled"

    # 订单状态更新事件
    # 当订单状态变化时发布（来自UserDataWebSocket）
    # 数据格式: {user_id, order_id, status, filled_quantity, remaining_quantity}
    ORDER_UPDATE = "de.order.update"

    # 账户余额查询成功事件
    # 当成功查询账户余额时发布
    # 数据格式: {user_id, asset, available_balance}
    ACCOUNT_BALANCE = "de.account.balance"

    # 持仓更新事件
    # 当持仓信息更新时发布（来自UserDataWebSocket）
    # 数据格式: {user_id, symbol, side, quantity, unrealized_pnl, entry_price}
    POSITION_UPDATE = "de.position.update"

    # 账户更新事件
    # 当账户信息更新时发布（来自UserDataWebSocket）
    # 数据格式: {user_id, total_equity, available_balance, margin_used}
    ACCOUNT_UPDATE = "de.account.update"

    # 用户数据流启动成功事件
    # 当UserDataWebSocket成功启动时发布
    # 数据格式: {user_id, listen_key}
    USER_STREAM_STARTED = "de.user_stream.started"
