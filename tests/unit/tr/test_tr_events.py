"""
TR模块事件常量测试

测试TR模块的事件常量定义是否正确。
"""

import pytest
from src.core.tr.tr_events import TREvents


class TestTREvents:
    """测试TR模块事件常量"""
    
    def test_input_events_defined(self):
        """测试输入事件常量是否定义"""
        # 验证所有输入事件常量都已定义
        assert hasattr(TREvents, 'INPUT_ACCOUNT_LOADED')
        assert hasattr(TREvents, 'INPUT_SIGNAL_GENERATED')
        assert hasattr(TREvents, 'INPUT_GRID_CREATE')
        assert hasattr(TREvents, 'INPUT_ORDER_FILLED')
        assert hasattr(TREvents, 'INPUT_ORDER_UPDATE')
        assert hasattr(TREvents, 'INPUT_ORDER_SUBMITTED')
        assert hasattr(TREvents, 'INPUT_ORDER_FAILED')
        assert hasattr(TREvents, 'INPUT_ORDER_CANCELLED')
        assert hasattr(TREvents, 'INPUT_ACCOUNT_BALANCE')
    
    def test_output_events_defined(self):
        """测试输出事件常量是否定义"""
        # 验证所有输出事件常量都已定义
        assert hasattr(TREvents, 'POSITION_OPENED')
        assert hasattr(TREvents, 'POSITION_CLOSED')
        assert hasattr(TREvents, 'ORDER_CREATE')
        assert hasattr(TREvents, 'ORDER_CANCEL')
        assert hasattr(TREvents, 'ACCOUNT_BALANCE_REQUEST')
        assert hasattr(TREvents, 'MANAGER_STARTED')
        assert hasattr(TREvents, 'MANAGER_SHUTDOWN')
        assert hasattr(TREvents, 'GRID_CREATED')
        assert hasattr(TREvents, 'GRID_MOVED')
        assert hasattr(TREvents, 'TASK_CREATED')
        assert hasattr(TREvents, 'TASK_COMPLETED')
    
    def test_event_naming_convention(self):
        """测试事件命名规范"""
        # 输入事件应该以其他模块名开头
        assert TREvents.INPUT_ACCOUNT_LOADED.startswith("pm.")
        assert TREvents.INPUT_SIGNAL_GENERATED.startswith("st.")
        assert TREvents.INPUT_GRID_CREATE.startswith("st.")
        assert TREvents.INPUT_ORDER_FILLED.startswith("de.")
        
        # 输出事件应该以tr.或trading.开头
        assert TREvents.POSITION_OPENED.startswith("tr.")
        assert TREvents.POSITION_CLOSED.startswith("tr.")
        assert TREvents.ORDER_CREATE.startswith("trading.")
        assert TREvents.ORDER_CANCEL.startswith("trading.")
    
    def test_event_values_are_strings(self):
        """测试事件常量值都是字符串"""
        assert isinstance(TREvents.INPUT_ACCOUNT_LOADED, str)
        assert isinstance(TREvents.POSITION_OPENED, str)
        assert isinstance(TREvents.ORDER_CREATE, str)
    
    def test_event_values_not_empty(self):
        """测试事件常量值不为空"""
        assert len(TREvents.INPUT_ACCOUNT_LOADED) > 0
        assert len(TREvents.POSITION_OPENED) > 0
        assert len(TREvents.ORDER_CREATE) > 0

