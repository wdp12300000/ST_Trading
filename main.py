"""
ST_Trading 量化交易系统主程序

系统启动入口，负责：
- 初始化事件总线和事件存储
- 加载PM模块并初始化所有账户
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
        self.running = False
        
        logger.info("=" * 60)
        logger.info("ST_Trading 量化交易系统启动中...")
        logger.info("=" * 60)
    
    async def initialize(self):
        """
        初始化系统各个模块
        
        初始化顺序：
        1. 事件存储（EventStore）
        2. 事件总线（EventBus）
        3. PM管理器（PMManager）
        4. 订阅关键事件
        """
        try:
            # 1. 初始化事件存储
            logger.info("初始化事件存储...")
            db_path = Path("data/events.db")
            self.event_store = SQLiteEventStore(db_path=str(db_path))
            logger.info(f"事件存储初始化完成: {db_path}")
            
            # 2. 初始化事件总线
            logger.info("初始化事件总线...")
            self.event_bus = EventBus.get_instance(event_store=self.event_store)
            logger.info("事件总线初始化完成")
            
            # 3. 订阅关键事件
            logger.info("订阅系统事件...")
            self._subscribe_events()
            logger.info("事件订阅完成")
            
            # 4. 初始化PM管理器
            logger.info("初始化PM管理器...")
            config_path = Path("config/pm_config.json")
            self.pm_manager = PMManager.get_instance(
                event_bus=self.event_bus,
                config_path=str(config_path)
            )
            logger.info("PM管理器初始化完成")
            
            # 5. 加载所有账户
            logger.info("加载账户配置...")
            loaded_count = await self.pm_manager.load_accounts()
            logger.info(f"账户加载完成: 成功={loaded_count}, 失败={self.pm_manager.get_failed_count()}")
            
            # 6. 显示加载的账户信息
            self._display_loaded_accounts()
            
            self.running = True
            logger.info("=" * 60)
            logger.info("系统初始化完成，准备就绪")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.critical(f"系统初始化失败: {e}", exc_info=True)
            raise
    
    def _subscribe_events(self):
        """订阅关键系统事件"""
        # 订阅PM模块事件
        self.event_bus.subscribe(PMEvents.ACCOUNT_LOADED, self._on_account_loaded)
        self.event_bus.subscribe(PMEvents.MANAGER_READY, self._on_manager_ready)
        self.event_bus.subscribe(PMEvents.LOAD_FAILED, self._on_load_failed)
        
        logger.debug("已订阅PM模块事件")
    
    async def _on_account_loaded(self, event: Event):
        """处理账户加载成功事件"""
        user_id = event.data.get("user_id")
        name = event.data.get("name")
        strategy = event.data.get("strategy")
        testnet = event.data.get("testnet", False)
        
        logger.info(f"账户加载成功: {name} (user_id={user_id}, strategy={strategy}, testnet={testnet})")
    
    async def _on_manager_ready(self, event: Event):
        """处理PM管理器就绪事件"""
        loaded_count = event.data.get("loaded_count")
        failed_count = event.data.get("failed_count")
        
        logger.info(f"PM管理器就绪: 成功加载 {loaded_count} 个账户, {failed_count} 个失败")
    
    async def _on_load_failed(self, event: Event):
        """处理账户加载失败事件"""
        user_id = event.data.get("user_id")
        error = event.data.get("error")
        
        logger.warning(f"账户加载失败: user_id={user_id}, error={error}")
    
    def _display_loaded_accounts(self):
        """显示已加载的账户信息"""
        if not self.pm_manager:
            return
        
        user_ids = self.pm_manager.get_all_user_ids()
        if not user_ids:
            logger.warning("没有成功加载任何账户")
            return
        
        logger.info("-" * 60)
        logger.info(f"已加载账户列表 (共 {len(user_ids)} 个):")
        for user_id in user_ids:
            pm = self.pm_manager.get_pm(user_id)
            if pm:
                logger.info(f"  - {pm.name} (user_id={user_id}, strategy={pm.strategy}, testnet={pm.is_testnet})")
        logger.info("-" * 60)
    
    async def run(self):
        """
        运行系统主循环
        
        目前只是保持系统运行，等待事件
        后续会添加策略执行、交易逻辑等
        """
        logger.info("系统运行中...")
        logger.info("按 Ctrl+C 停止系统")
        
        try:
            while self.running:
                # 主循环：等待事件和信号
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("收到取消信号，准备关闭系统...")
    
    async def shutdown(self):
        """
        优雅关闭系统
        
        关闭顺序：
        1. 停止主循环
        2. 关闭PM管理器
        3. 关闭事件存储
        """
        logger.info("=" * 60)
        logger.info("系统关闭中...")
        logger.info("=" * 60)
        
        self.running = False
        
        try:
            # 1. 关闭PM管理器
            if self.pm_manager:
                logger.info("关闭PM管理器...")
                await self.pm_manager.shutdown()
                logger.info("PM管理器已关闭")
            
            # 2. 关闭事件存储
            if self.event_store:
                logger.info("关闭事件存储...")
                self.event_store.close()
                logger.info("事件存储已关闭")
            
            logger.info("=" * 60)
            logger.info("系统已安全关闭")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"系统关闭时发生错误: {e}", exc_info=True)


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

