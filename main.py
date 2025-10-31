"""
ST_Trading 量化交易系统主程序

系统启动入口，负责：
- 初始化事件总线和事件存储
- 加载PM模块并初始化所有账户
- 初始化DE模块（数据引擎）
- 初始化ST模块（策略执行）
- 初始化TA模块（技术分析）
- 注册技术指标
- 启动WebSocket连接
- 订阅关键事件
- 优雅关闭系统

使用方式：
    python main.py
"""

import asyncio
import signal
import sys
from pathlib import Path

from src.core.event import Event, EventBus, SQLiteEventStore
from src.core.pm.pm_manager import PMManager
from src.core.pm.pm_events import PMEvents
from src.core.de.de_manager import DEManager
from src.core.de.de_events import DEEvents
from src.core.st.st_manager import STManager
from src.core.st.st_events import STEvents
from src.core.ta.ta_manager import TAManager
from src.core.ta.ta_events import TAEvents
from src.core.ta.indicator_factory import IndicatorFactory
from src.indicators.ma_stop_indicator import MAStopIndicator
from src.utils.logger import get_logger

logger = get_logger()


class STTradingSystem:
    """
    ST_Trading 量化交易系统主类

    职责：
    - 管理系统生命周期
    - 初始化各个模块
    - 处理系统关闭信号
    """

    def __init__(self):
        """初始化系统"""
        self.event_bus: EventBus = None
        self.event_store: SQLiteEventStore = None
        self.pm_manager: PMManager = None
        self.de_manager: DEManager = None
        self.st_manager: STManager = None
        self.ta_manager: TAManager = None
        self.running = False

        logger.info("=" * 80)
        logger.info("ST_Trading 量化交易系统启动中...")
        logger.info("=" * 80)
    
    async def initialize(self):
        """
        初始化系统各个模块

        初始化顺序：
        1. 事件存储（EventStore）
        2. 事件总线（EventBus）
        3. 订阅关键事件
        4. 注册技术指标
        5. PM管理器（PMManager）
        6. DE管理器（DEManager）
        7. ST管理器（STManager）
        8. TA管理器（TAManager）
        9. 加载账户配置
        10. 启动WebSocket连接
        """
        try:
            # 1. 初始化事件存储
            logger.info("=" * 80)
            logger.info("步骤 1/10: 初始化事件存储...")
            db_path = Path("data/events.db")
            self.event_store = SQLiteEventStore(db_path=str(db_path))
            logger.info(f"✅ 事件存储初始化完成: {db_path}")

            # 2. 初始化事件总线
            logger.info("=" * 80)
            logger.info("步骤 2/10: 初始化事件总线...")
            self.event_bus = EventBus.get_instance(event_store=self.event_store)
            logger.info("✅ 事件总线初始化完成")

            # 3. 订阅关键事件
            logger.info("=" * 80)
            logger.info("步骤 3/10: 订阅系统事件...")
            self._subscribe_events()
            logger.info("✅ 事件订阅完成")

            # 4. 注册技术指标
            logger.info("=" * 80)
            logger.info("步骤 4/10: 注册技术指标...")
            self._register_indicators()
            logger.info("✅ 技术指标注册完成")

            # 5. 初始化PM管理器
            logger.info("=" * 80)
            logger.info("步骤 5/10: 初始化PM管理器...")
            config_path = Path("config/pm_config.json")
            self.pm_manager = PMManager.get_instance(
                event_bus=self.event_bus,
                config_path=str(config_path)
            )
            logger.info("✅ PM管理器初始化完成")

            # 6. 初始化DE管理器
            logger.info("=" * 80)
            logger.info("步骤 6/10: 初始化DE管理器...")
            self.de_manager = DEManager.get_instance(event_bus=self.event_bus)
            logger.info("✅ DE管理器初始化完成")

            # 7. 初始化ST管理器
            logger.info("=" * 80)
            logger.info("步骤 7/10: 初始化ST管理器...")
            self.st_manager = STManager.get_instance(event_bus=self.event_bus)
            logger.info("✅ ST管理器初始化完成")

            # 8. 初始化TA管理器
            logger.info("=" * 80)
            logger.info("步骤 8/10: 初始化TA管理器...")
            self.ta_manager = TAManager.get_instance(event_bus=self.event_bus)
            logger.info("✅ TA管理器初始化完成")

            # 9. 加载所有账户
            logger.info("=" * 80)
            logger.info("步骤 9/10: 加载账户配置...")
            loaded_count = await self.pm_manager.load_accounts()
            logger.info(f"✅ 账户加载完成: 成功={loaded_count}, 失败={self.pm_manager.get_failed_count()}")

            # 显示加载的账户信息
            self._display_loaded_accounts()

            # 10. 启动WebSocket连接
            logger.info("=" * 80)
            logger.info("步骤 10/10: 启动WebSocket连接...")
            await self._start_websockets()
            logger.info("✅ WebSocket连接启动完成")

            self.running = True
            logger.info("=" * 80)
            logger.info("🎉 系统初始化完成，准备就绪！")
            logger.info("=" * 80)
            logger.info("")
            logger.info("📝 提示：")
            logger.info("  - 所有模块已初始化完成")
            logger.info("  - 事件驱动架构已就绪")
            logger.info("  - 策略已加载并订阅指标")
            logger.info("  - WebSocket已连接，等待实时K线数据...")
            logger.info("  - 系统将自动计算指标并生成交易信号")
            logger.info("")

        except Exception as e:
            logger.critical(f"❌ 系统初始化失败: {e}", exc_info=True)
            raise
    
    def _subscribe_events(self):
        """订阅关键系统事件"""
        # 订阅PM模块事件
        self.event_bus.subscribe(PMEvents.ACCOUNT_LOADED, self._on_account_loaded)
        self.event_bus.subscribe(PMEvents.MANAGER_READY, self._on_manager_ready)
        self.event_bus.subscribe(PMEvents.LOAD_FAILED, self._on_load_failed)

        # 订阅ST模块事件
        self.event_bus.subscribe(STEvents.STRATEGY_LOADED, self._on_strategy_loaded)
        self.event_bus.subscribe(STEvents.SIGNAL_GENERATED, self._on_signal_generated)

        # 订阅TA模块事件
        self.event_bus.subscribe(TAEvents.INDICATOR_CREATED, self._on_indicator_created)
        self.event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, self._on_calculation_completed)

        # 订阅DE模块事件
        self.event_bus.subscribe(DEEvents.KLINE_UPDATE, self._on_kline_update)

        logger.debug("已订阅所有模块事件")

    def _register_indicators(self):
        """注册所有技术指标"""
        # 注册MA Stop指标
        IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)

        registered = IndicatorFactory.get_registered_indicators()
        logger.info(f"已注册指标: {registered}")

    async def _start_websockets(self):
        """启动所有账户的WebSocket连接"""
        user_ids = self.pm_manager.get_all_user_ids()

        for user_id in user_ids:
            pm = self.pm_manager.get_pm(user_id)
            if not pm:
                continue

            # 获取策略配置
            strategy = self.st_manager.get_strategy(user_id)
            if not strategy:
                logger.warning(f"用户 {user_id} 没有加载策略，跳过WebSocket启动")
                continue

            # 获取交易对列表
            trading_pairs = strategy.get_trading_pairs()
            symbols = [pair["symbol"] for pair in trading_pairs]

            # 获取时间周期
            timeframe = strategy.get_timeframe()

            logger.info(f"启动WebSocket: user_id={user_id}, symbols={symbols}, timeframe={timeframe}")

            # 启动市场数据WebSocket（K线订阅）
            await self.de_manager.start_market_websocket(
                user_id=user_id,
                symbols=symbols,
                interval=timeframe
            )

            logger.info(f"✅ WebSocket启动成功: user_id={user_id}")
    
    async def _on_account_loaded(self, event: Event):
        """处理账户加载成功事件"""
        user_id = event.data.get("user_id")
        name = event.data.get("name")
        strategy = event.data.get("strategy")
        testnet = event.data.get("testnet", False)

        logger.info(f"📦 账户加载成功: {name} (user_id={user_id}, strategy={strategy}, testnet={testnet})")

    async def _on_manager_ready(self, event: Event):
        """处理PM管理器就绪事件"""
        loaded_count = event.data.get("loaded_count")
        failed_count = event.data.get("failed_count")

        logger.info(f"✅ PM管理器就绪: 成功加载 {loaded_count} 个账户, {failed_count} 个失败")

    async def _on_load_failed(self, event: Event):
        """处理账户加载失败事件"""
        user_id = event.data.get("user_id")
        error = event.data.get("error")

        logger.warning(f"⚠️ 账户加载失败: user_id={user_id}, error={error}")

    async def _on_strategy_loaded(self, event: Event):
        """处理策略加载成功事件"""
        user_id = event.data.get("user_id")
        strategy_name = event.data.get("strategy_name")
        trading_pairs = event.data.get("trading_pairs", [])

        logger.info(f"📈 策略加载成功: user_id={user_id}, strategy={strategy_name}, pairs={len(trading_pairs)}")

    async def _on_signal_generated(self, event: Event):
        """处理信号生成事件"""
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        signal = event.data.get("signal")
        action = event.data.get("action")

        logger.info(f"🎯 信号生成: user_id={user_id}, symbol={symbol}, signal={signal}, action={action}")

    async def _on_indicator_created(self, event: Event):
        """处理指标创建成功事件"""
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        indicator_name = event.data.get("indicator_name")
        indicator_id = event.data.get("indicator_id")

        logger.info(f"📊 指标创建成功: {indicator_id}")

    async def _on_calculation_completed(self, event: Event):
        """处理指标计算完成事件"""
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        timeframe = event.data.get("timeframe")
        indicators = event.data.get("indicators", {})

        # 提取信号
        signals = {name: data.get("signal") for name, data in indicators.items()}

        logger.info(f"📊 指标计算完成: user_id={user_id}, symbol={symbol}, timeframe={timeframe}, signals={signals}")

    async def _on_kline_update(self, event: Event):
        """处理K线更新事件"""
        user_id = event.data.get("user_id")
        symbol = event.data.get("symbol")
        interval = event.data.get("interval")
        klines = event.data.get("klines", [])

        if klines:
            latest_kline = klines[-1]
            logger.debug(
                f"📈 K线更新: user_id={user_id}, symbol={symbol}, interval={interval}, "
                f"close={latest_kline.get('close')}, is_closed={latest_kline.get('is_closed')}"
            )
    
    def _display_loaded_accounts(self):
        """显示已加载的账户信息"""
        if not self.pm_manager:
            return

        user_ids = self.pm_manager.get_all_user_ids()
        if not user_ids:
            logger.warning("⚠️ 没有成功加载任何账户")
            return

        logger.info("-" * 80)
        logger.info(f"📋 已加载账户列表 (共 {len(user_ids)} 个):")
        for user_id in user_ids:
            pm = self.pm_manager.get_pm(user_id)
            if pm:
                logger.info(f"  - {pm.name} (user_id={user_id}, strategy={pm.strategy}, testnet={pm.is_testnet})")
        logger.info("-" * 80)
    
    async def run(self):
        """
        运行系统主循环

        系统运行中，所有模块通过事件驱动自动工作：
        - DE模块：接收WebSocket数据，发布K线更新事件
        - TA模块：接收K线更新，计算指标，发布计算完成事件
        - ST模块：接收指标计算结果，生成交易信号
        - TR模块：接收交易信号，执行订单（待开发）
        """
        logger.info("=" * 80)
        logger.info("🚀 系统运行中...")
        logger.info("📡 WebSocket连接已建立，等待实时数据...")
        logger.info("💡 按 Ctrl+C 停止系统")
        logger.info("=" * 80)

        try:
            # 显示系统状态
            self._display_system_status()

            # 主循环：保持系统运行，等待事件
            while self.running:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("收到取消信号，准备关闭系统...")

    def _display_system_status(self):
        """显示系统状态"""
        logger.info("-" * 80)
        logger.info("📊 系统状态:")

        # PM模块状态
        user_ids = self.pm_manager.get_all_user_ids()
        logger.info(f"  PM模块: {len(user_ids)} 个账户")

        # ST模块状态
        for user_id in user_ids:
            strategy = self.st_manager.get_strategy(user_id)
            if strategy:
                trading_pairs = strategy.get_trading_pairs()
                logger.info(f"  ST模块 ({user_id}): {len(trading_pairs)} 个交易对")

        # TA模块状态
        indicator_count = len(self.ta_manager._indicators)
        logger.info(f"  TA模块: {indicator_count} 个指标实例")

        # 已注册指标
        registered = IndicatorFactory.get_registered_indicators()
        logger.info(f"  已注册指标: {registered}")

        logger.info("-" * 80)
    
    async def shutdown(self):
        """
        优雅关闭系统

        关闭顺序：
        1. 停止主循环
        2. 关闭WebSocket连接
        3. 关闭DE管理器
        4. 关闭ST管理器
        5. 关闭TA管理器
        6. 关闭PM管理器
        7. 关闭事件存储
        """
        logger.info("=" * 80)
        logger.info("🛑 系统关闭中...")
        logger.info("=" * 80)

        self.running = False

        try:
            # 1. 停止WebSocket连接
            if self.de_manager:
                logger.info("停止WebSocket连接...")
                await self.de_manager.stop_all_websockets()
                logger.info("✅ WebSocket连接已停止")

            # 2. 关闭DE管理器
            if self.de_manager:
                logger.info("关闭DE管理器...")
                await self.de_manager.shutdown()
                logger.info("✅ DE管理器已关闭")

            # 3. 关闭ST管理器
            if self.st_manager:
                logger.info("关闭ST管理器...")
                # ST管理器目前没有特殊关闭逻辑
                logger.info("✅ ST管理器已关闭")

            # 4. 关闭TA管理器
            if self.ta_manager:
                logger.info("关闭TA管理器...")
                # TA管理器目前没有特殊关闭逻辑
                logger.info("✅ TA管理器已关闭")

            # 5. 关闭PM管理器
            if self.pm_manager:
                logger.info("关闭PM管理器...")
                await self.pm_manager.shutdown()
                logger.info("✅ PM管理器已关闭")

            # 6. 关闭事件存储
            if self.event_store:
                logger.info("关闭事件存储...")
                self.event_store.close()
                logger.info("✅ 事件存储已关闭")

            logger.info("=" * 80)
            logger.info("✅ 系统已安全关闭")
            logger.info("=" * 80)

        except Exception as e:
            logger.error(f"❌ 系统关闭时发生错误: {e}", exc_info=True)


async def main():
    """主函数"""
    system = STTradingSystem()
    
    # 设置信号处理器
    def signal_handler(sig, frame):
        """处理 Ctrl+C 信号"""
        logger.info("收到中断信号 (Ctrl+C)")
        asyncio.create_task(system.shutdown())
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # 初始化系统
        await system.initialize()
        
        # 运行系统
        await system.run()
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
    except Exception as e:
        logger.critical(f"系统运行时发生严重错误: {e}", exc_info=True)
    finally:
        # 确保系统被关闭
        await system.shutdown()


if __name__ == "__main__":
    """程序入口"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.critical(f"程序异常退出: {e}", exc_info=True)
        sys.exit(1)

