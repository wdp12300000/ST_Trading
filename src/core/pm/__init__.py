"""
PM（Portfolio Manager）模块

负责账户管理，包括：
- PM类：单个账户管理
- PMManager类：多账户管理器（单例模式）
- PMEvents：事件主题常量
"""

from src.core.pm.pm_events import PMEvents
from src.core.pm.pm import PM
from src.core.pm.pm_manager import PMManager

__all__ = ["PMEvents", "PM", "PMManager"]

