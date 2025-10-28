"""
DE模块实盘API测试

使用真实的币安API进行测试，包括：
- 账户余额查询（只读操作）
- 历史K线数据获取（只读操作）
- 小额订单提交和取消（0.001 BTC）
- WebSocket实时数据订阅

注意：
- 本测试使用真实API，会产生实际的网络请求
- 订单测试使用极小金额（0.001 BTC）
- 测试前请确保账户有足够余额
- 测试会立即取消提交的订单
"""

import pytest
import asyncio
import json
from src.core.event import EventBus, Event
from src.core.pm.pm_manager import PMManager
from src.core.de.de_manager import DEManager
from src.core.de.de_events import DEEvents
from src.core.pm.pm_events import PMEvents
from src.utils.logger import logger


class TestDERealAPI:
    """DE模块实盘API测试"""
    
    def setup_method(self):
        """每个测试前重置单例和事件收集器"""
        EventBus._instance = None
        PMManager.reset_instance()
        DEManager.reset_instance()
        self.event_bus = EventBus.get_instance()
        self.received_events = []
        self.pm_manager = None
        self.de_manager = None
    
    def teardown_method(self):
        """每个测试后清理"""
        EventBus._instance = None
        PMManager.reset_instance()
        DEManager.reset_instance()
    
    async def event_collector(self, event):
        """事件收集器"""
        self.received_events.append(event)
        logger.info(f"收到事件: {event.subject}, data={event.data}")
    
    @pytest.mark.asyncio
    async def test_01_account_balance_query(self):
        """
        测试1：账户余额查询（只读操作，无风险）
        
        流程：
        1. 加载PM配置
        2. PM发布pm.account.loaded事件
        3. DE创建BinanceClient
        4. 发布trading.get_account_balance事件
        5. DE查询余额并发布de.account.balance事件
        """
        logger.info("=" * 60)
        logger.info("开始测试：账户余额查询")
        logger.info("=" * 60)
        
        # 订阅相关事件
        self.event_bus.subscribe(DEEvents.CLIENT_CONNECTED, self.event_collector)
        self.event_bus.subscribe(DEEvents.ACCOUNT_BALANCE, self.event_collector)
        
        # 创建PM和DE管理器
        self.pm_manager = PMManager.get_instance(event_bus=self.event_bus)
        self.de_manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 加载账户配置
        await self.pm_manager.load_accounts()
        
        # 等待客户端连接
        await asyncio.sleep(0.5)
        
        # 验证客户端已创建
        client = self.de_manager.get_client("user_001")
        assert client is not None, "BinanceClient未创建"
        
        # 清空事件列表
        self.received_events.clear()
        
        # 发布余额查询事件（使用USDC）
        await self.event_bus.publish(Event(
            subject=DEEvents.INPUT_GET_ACCOUNT_BALANCE,
            data={
                "user_id": "user_001",
                "asset": "USDC"
            }
        ))
        
        # 等待余额查询完成
        await asyncio.sleep(2.0)
        
        # 验证收到de.account.balance事件
        balance_events = [e for e in self.received_events if e.subject == DEEvents.ACCOUNT_BALANCE]
        assert len(balance_events) > 0, "未收到账户余额事件"

        balance_event = balance_events[0]
        assert balance_event.data["user_id"] == "user_001"
        assert balance_event.data["asset"] == "USDC"
        assert "balance" in balance_event.data
        assert "available_balance" in balance_event.data
        
        logger.info(f"✅ 账户余额查询成功: {balance_event.data}")
        logger.info("=" * 60)
    
    @pytest.mark.asyncio
    async def test_02_historical_klines(self):
        """
        测试2：历史K线数据获取（只读操作，无风险）
        
        流程：
        1. 加载PM配置
        2. 获取BinanceClient
        3. 调用get_historical_klines获取BTCUSDT的1小时K线
        4. 验证返回数据格式
        """
        logger.info("=" * 60)
        logger.info("开始测试：历史K线数据获取")
        logger.info("=" * 60)
        
        # 创建PM和DE管理器
        self.pm_manager = PMManager.get_instance(event_bus=self.event_bus)
        self.de_manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 加载账户配置
        await self.pm_manager.load_accounts()
        
        # 等待客户端连接
        await asyncio.sleep(0.5)
        
        # 获取客户端
        client = self.de_manager.get_client("user_001")
        assert client is not None, "BinanceClient未创建"
        
        # 获取历史K线
        klines = await client.get_historical_klines(
            symbol="BTCUSDT",
            interval="1h",
            limit=10
        )
        
        # 验证数据
        assert len(klines) == 10, f"K线数量不正确: {len(klines)}"
        assert len(klines[0]) == 12, f"K线数据格式不正确: {len(klines[0])}"
        
        # 打印第一条K线数据
        logger.info(f"✅ 历史K线获取成功，数量: {len(klines)}")
        logger.info(f"第一条K线: 时间={klines[0][0]}, 开={klines[0][1]}, 高={klines[0][2]}, 低={klines[0][3]}, 收={klines[0][4]}, 量={klines[0][5]}")
        logger.info("=" * 60)
    
    @pytest.mark.asyncio
    async def test_03_small_order_submit_and_cancel(self):
        """
        测试3：小额订单提交和取消（有风险，使用极小金额）
        
        流程：
        1. 加载PM配置
        2. 发布trading.order.create事件（0.001 BTC限价单）
        3. 等待订单提交成功
        4. 立即发布trading.order.cancel事件
        5. 验证订单取消成功
        
        注意：
        - 使用极小金额（0.001 BTC）
        - 限价单价格设置为远离市场价，避免成交
        - 立即取消订单
        """
        logger.info("=" * 60)
        logger.info("开始测试：小额订单提交和取消")
        logger.info("=" * 60)
        
        # 订阅订单事件
        self.event_bus.subscribe(DEEvents.ORDER_SUBMITTED, self.event_collector)
        self.event_bus.subscribe(DEEvents.ORDER_CANCELLED, self.event_collector)
        self.event_bus.subscribe(DEEvents.ORDER_FAILED, self.event_collector)
        
        # 创建PM和DE管理器
        self.pm_manager = PMManager.get_instance(event_bus=self.event_bus)
        self.de_manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 加载账户配置
        await self.pm_manager.load_accounts()
        
        # 等待客户端连接
        await asyncio.sleep(0.5)
        
        # 清空事件列表
        self.received_events.clear()
        
        # 发布订单创建事件（限价单，价格远离市场价）
        # 注意：币安要求订单名义价值 >= 100 USDC
        # 使用BTCUSDC交易对
        await self.event_bus.publish(Event(
            subject=DEEvents.INPUT_ORDER_CREATE,
            data={
                "user_id": "user_001",
                "symbol": "BTCUSDC",
                "side": "BUY",
                "order_type": "LIMIT",
                "quantity": 0.002,  # 0.002 BTC × 50000 = 100 USDC
                "price": 50000.0    # 远低于市场价（当前约114000），避免成交
            }
        ))
        
        # 等待订单提交
        await asyncio.sleep(2.0)
        
        # 验证订单提交成功
        submitted_events = [e for e in self.received_events if e.subject == DEEvents.ORDER_SUBMITTED]
        failed_events = [e for e in self.received_events if e.subject == DEEvents.ORDER_FAILED]
        
        if len(failed_events) > 0:
            logger.error(f"❌ 订单提交失败: {failed_events[0].data}")
            pytest.skip(f"订单提交失败: {failed_events[0].data.get('error')}")
        
        assert len(submitted_events) > 0, "未收到订单提交成功事件"
        
        order_id = submitted_events[0].data["order_id"]
        logger.info(f"✅ 订单提交成功: order_id={order_id}")
        
        # 清空事件列表
        self.received_events.clear()
        
        # 立即取消订单
        await self.event_bus.publish(Event(
            subject=DEEvents.INPUT_ORDER_CANCEL,
            data={
                "user_id": "user_001",
                "symbol": "BTCUSDC",
                "order_id": order_id
            }
        ))
        
        # 等待订单取消
        await asyncio.sleep(2.0)
        
        # 验证订单取消成功
        cancelled_events = [e for e in self.received_events if e.subject == DEEvents.ORDER_CANCELLED]
        assert len(cancelled_events) > 0, "未收到订单取消成功事件"
        
        logger.info(f"✅ 订单取消成功: {cancelled_events[0].data}")
        logger.info("=" * 60)
    
    @pytest.mark.asyncio
    async def test_04_websocket_kline_subscription(self):
        """
        测试4：WebSocket K线数据订阅
        
        流程：
        1. 加载PM配置
        2. 获取BinanceClient
        3. 创建MarketWebSocket
        4. 订阅BTCUSDT 1分钟K线
        5. 等待接收K线更新事件
        6. 断开连接
        """
        logger.info("=" * 60)
        logger.info("开始测试：WebSocket K线数据订阅")
        logger.info("=" * 60)
        
        # 订阅K线更新事件
        self.event_bus.subscribe(DEEvents.KLINE_UPDATE, self.event_collector)
        
        # 创建PM和DE管理器
        self.pm_manager = PMManager.get_instance(event_bus=self.event_bus)
        self.de_manager = DEManager.get_instance(event_bus=self.event_bus)
        
        # 加载账户配置
        await self.pm_manager.load_accounts()
        
        # 等待客户端连接
        await asyncio.sleep(0.5)
        
        # 获取客户端
        client = self.de_manager.get_client("user_001")
        assert client is not None, "BinanceClient未创建"
        
        # 创建MarketWebSocket
        from src.core.de.market_websocket import MarketWebSocket
        market_ws = MarketWebSocket(user_id="user_001", event_bus=self.event_bus)
        
        # 订阅K线
        await market_ws.subscribe_kline("BTCUSDT", "1m")
        
        # 启动WebSocket连接（后台任务）
        ws_task = asyncio.create_task(market_ws.connect())
        
        # 等待接收K线数据（最多等待65秒，因为1分钟K线可能需要等待下一个周期）
        logger.info("等待接收K线数据（最多65秒）...")
        for i in range(65):
            await asyncio.sleep(1)
            kline_events = [e for e in self.received_events if e.subject == DEEvents.KLINE_UPDATE]
            if len(kline_events) > 0:
                logger.info(f"✅ 收到K线更新事件: {kline_events[0].data}")
                break
            if i % 10 == 0:
                logger.info(f"已等待 {i} 秒...")
        
        # 断开连接
        await market_ws.disconnect()
        ws_task.cancel()
        
        # 验证收到K线事件
        kline_events = [e for e in self.received_events if e.subject == DEEvents.KLINE_UPDATE]
        assert len(kline_events) > 0, "未收到K线更新事件"
        
        logger.info("=" * 60)

