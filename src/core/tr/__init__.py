"""
TR (Trade Execution) 模块

交易执行模块，负责：
- 订单执行：接收ST模块的交易信号并执行订单
- 持仓管理：跟踪每个交易对的持仓状态
- 网格交易：创建和管理网格订单
- 资金管理：计算仓位大小和资金分配
- 订单持久化：记录所有订单和交易任务

主要组件：
- TRManager: TR模块管理器（单例）
- TradingTask: 交易任务类，管理单个交易对的所有订单
- OrderManager: 订单管理器，负责订单提交和状态跟踪
- CapitalManager: 资金管理器，负责资金分配和仓位计算
- GridManager: 网格管理器，负责网格订单创建和管理
- GridCalculator: 网格计算器，负责网格价格和数量计算

使用方式：
    from src.core.tr.tr_manager import TRManager
    from src.core.event.event_bus import EventBus
    
    # 创建事件总线
    event_bus = EventBus()
    
    # 获取TR管理器实例
    tr_manager = TRManager.get_instance(event_bus=event_bus)
    
    # 启动TR管理器
    await tr_manager.start()
"""

from src.core.tr.tr_manager import TRManager
from src.core.tr.tr_events import TREvents

__all__ = ["TRManager", "TREvents"]

