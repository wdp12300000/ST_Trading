"""
TA (Technical Analysis) 技术分析模块

该模块负责：
1. 管理技术指标实例
2. 处理历史K线数据请求
3. 处理实时K线数据更新
4. 计算技术指标
5. 生成指标信号
6. 聚合同一交易对的多个指标结果
7. 发布指标计算完成事件

主要组件：
- TAManager: 指标管理器（单例模式）
- BaseIndicator: 指标抽象基类
- TAEvents: 事件常量定义

设计原则：
- 面向对象设计：充分使用类方法
- 开闭原则：对扩展开放，对修改关闭
- 依赖倒置原则：依赖抽象而非具体实现
- 事件驱动架构：通过事件总线与其他模块通信
"""

from src.core.ta.ta_events import TAEvents

__all__ = [
    'TAEvents',
]

