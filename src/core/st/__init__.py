"""
ST (Strategy Execution) 策略执行模块

该模块负责：
1. 加载和管理策略配置
2. 创建和管理策略实例
3. 处理指标信号并生成交易决策
4. 管理持仓状态（内存中）
5. 触发网格交易和反向建仓

主要组件：
- STManager: 策略管理器（单例模式）
- BaseStrategy: 策略抽象基类
- STEvents: 事件常量定义
"""

from src.core.st.st_events import STEvents
from src.core.st.st_manager import STManager
from src.core.st.base_strategy import BaseStrategy, PositionState

__all__ = [
    'STManager',
    'BaseStrategy',
    'PositionState',
    'STEvents',
]

