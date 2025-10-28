"""
DEEvents类单元测试

测试DE模块事件常量的完整性和命名规范，包括：
- 输入事件常量的存在性
- 输出事件常量的存在性
- 事件命名规范验证
- 事件主题字符串格式验证
"""

import pytest
from src.core.de.de_events import DEEvents


class TestDEEventsInputConstants:
    """测试DE模块订阅的输入事件常量"""
    
    def test_input_account_loaded_exists(self):
        """测试INPUT_ACCOUNT_LOADED常量存在"""
        assert hasattr(DEEvents, 'INPUT_ACCOUNT_LOADED')
        assert DEEvents.INPUT_ACCOUNT_LOADED == "pm.account.loaded"
    
    def test_input_subscribe_kline_exists(self):
        """测试INPUT_SUBSCRIBE_KLINE常量存在"""
        assert hasattr(DEEvents, 'INPUT_SUBSCRIBE_KLINE')
        assert DEEvents.INPUT_SUBSCRIBE_KLINE == "de.subscribe.kline"
    
    def test_input_get_historical_klines_exists(self):
        """测试INPUT_GET_HISTORICAL_KLINES常量存在"""
        assert hasattr(DEEvents, 'INPUT_GET_HISTORICAL_KLINES')
        assert DEEvents.INPUT_GET_HISTORICAL_KLINES == "de.get_historical_klines"
    
    def test_input_order_create_exists(self):
        """测试INPUT_ORDER_CREATE常量存在"""
        assert hasattr(DEEvents, 'INPUT_ORDER_CREATE')
        assert DEEvents.INPUT_ORDER_CREATE == "trading.order.create"
    
    def test_input_order_cancel_exists(self):
        """测试INPUT_ORDER_CANCEL常量存在"""
        assert hasattr(DEEvents, 'INPUT_ORDER_CANCEL')
        assert DEEvents.INPUT_ORDER_CANCEL == "trading.order.cancel"
    
    def test_input_get_account_balance_exists(self):
        """测试INPUT_GET_ACCOUNT_BALANCE常量存在"""
        assert hasattr(DEEvents, 'INPUT_GET_ACCOUNT_BALANCE')
        assert DEEvents.INPUT_GET_ACCOUNT_BALANCE == "trading.get_account_balance"


class TestDEEventsOutputConstants:
    """测试DE模块发布的输出事件常量"""
    
    def test_client_connected_exists(self):
        """测试CLIENT_CONNECTED常量存在"""
        assert hasattr(DEEvents, 'CLIENT_CONNECTED')
        assert DEEvents.CLIENT_CONNECTED == "de.client.connected"
    
    def test_client_connection_failed_exists(self):
        """测试CLIENT_CONNECTION_FAILED常量存在"""
        assert hasattr(DEEvents, 'CLIENT_CONNECTION_FAILED')
        assert DEEvents.CLIENT_CONNECTION_FAILED == "de.client.connection_failed"
    
    def test_websocket_connected_exists(self):
        """测试WEBSOCKET_CONNECTED常量存在"""
        assert hasattr(DEEvents, 'WEBSOCKET_CONNECTED')
        assert DEEvents.WEBSOCKET_CONNECTED == "de.websocket.connected"
    
    def test_websocket_disconnected_exists(self):
        """测试WEBSOCKET_DISCONNECTED常量存在"""
        assert hasattr(DEEvents, 'WEBSOCKET_DISCONNECTED')
        assert DEEvents.WEBSOCKET_DISCONNECTED == "de.websocket.disconnected"
    
    def test_kline_update_exists(self):
        """测试KLINE_UPDATE常量存在"""
        assert hasattr(DEEvents, 'KLINE_UPDATE')
        assert DEEvents.KLINE_UPDATE == "de.kline.update"
    
    def test_historical_klines_success_exists(self):
        """测试HISTORICAL_KLINES_SUCCESS常量存在"""
        assert hasattr(DEEvents, 'HISTORICAL_KLINES_SUCCESS')
        assert DEEvents.HISTORICAL_KLINES_SUCCESS == "de.historical_klines.success"
    
    def test_historical_klines_failed_exists(self):
        """测试HISTORICAL_KLINES_FAILED常量存在"""
        assert hasattr(DEEvents, 'HISTORICAL_KLINES_FAILED')
        assert DEEvents.HISTORICAL_KLINES_FAILED == "de.historical_klines.failed"
    
    def test_order_submitted_exists(self):
        """测试ORDER_SUBMITTED常量存在"""
        assert hasattr(DEEvents, 'ORDER_SUBMITTED')
        assert DEEvents.ORDER_SUBMITTED == "de.order.submitted"
    
    def test_order_failed_exists(self):
        """测试ORDER_FAILED常量存在"""
        assert hasattr(DEEvents, 'ORDER_FAILED')
        assert DEEvents.ORDER_FAILED == "de.order.failed"
    
    def test_order_cancelled_exists(self):
        """测试ORDER_CANCELLED常量存在"""
        assert hasattr(DEEvents, 'ORDER_CANCELLED')
        assert DEEvents.ORDER_CANCELLED == "de.order.cancelled"
    
    def test_order_filled_exists(self):
        """测试ORDER_FILLED常量存在"""
        assert hasattr(DEEvents, 'ORDER_FILLED')
        assert DEEvents.ORDER_FILLED == "de.order.filled"
    
    def test_order_update_exists(self):
        """测试ORDER_UPDATE常量存在"""
        assert hasattr(DEEvents, 'ORDER_UPDATE')
        assert DEEvents.ORDER_UPDATE == "de.order.update"
    
    def test_account_balance_exists(self):
        """测试ACCOUNT_BALANCE常量存在"""
        assert hasattr(DEEvents, 'ACCOUNT_BALANCE')
        assert DEEvents.ACCOUNT_BALANCE == "de.account.balance"
    
    def test_position_update_exists(self):
        """测试POSITION_UPDATE常量存在"""
        assert hasattr(DEEvents, 'POSITION_UPDATE')
        assert DEEvents.POSITION_UPDATE == "de.position.update"
    
    def test_account_update_exists(self):
        """测试ACCOUNT_UPDATE常量存在"""
        assert hasattr(DEEvents, 'ACCOUNT_UPDATE')
        assert DEEvents.ACCOUNT_UPDATE == "de.account.update"
    
    def test_user_stream_started_exists(self):
        """测试USER_STREAM_STARTED常量存在"""
        assert hasattr(DEEvents, 'USER_STREAM_STARTED')
        assert DEEvents.USER_STREAM_STARTED == "de.user_stream.started"


class TestDEEventsNamingConvention:
    """测试事件命名规范"""
    
    def test_output_events_start_with_de_prefix(self):
        """测试所有输出事件（除了输入事件）都以'de.'开头"""
        # 获取所有非输入事件的常量
        output_events = [
            DEEvents.CLIENT_CONNECTED,
            DEEvents.CLIENT_CONNECTION_FAILED,
            DEEvents.WEBSOCKET_CONNECTED,
            DEEvents.WEBSOCKET_DISCONNECTED,
            DEEvents.KLINE_UPDATE,
            DEEvents.HISTORICAL_KLINES_SUCCESS,
            DEEvents.HISTORICAL_KLINES_FAILED,
            DEEvents.ORDER_SUBMITTED,
            DEEvents.ORDER_FAILED,
            DEEvents.ORDER_CANCELLED,
            DEEvents.ORDER_FILLED,
            DEEvents.ORDER_UPDATE,
            DEEvents.ACCOUNT_BALANCE,
            DEEvents.POSITION_UPDATE,
            DEEvents.ACCOUNT_UPDATE,
            DEEvents.USER_STREAM_STARTED,
        ]
        
        for event in output_events:
            assert event.startswith("de."), f"输出事件 {event} 应该以 'de.' 开头"
    
    def test_event_format_follows_module_object_action_pattern(self):
        """测试事件主题遵循'模块.对象.动作'格式"""
        # 测试几个典型的事件格式
        assert DEEvents.CLIENT_CONNECTED.count('.') == 2  # de.client.connected
        assert DEEvents.ORDER_SUBMITTED.count('.') == 2   # de.order.submitted
        assert DEEvents.KLINE_UPDATE.count('.') == 2      # de.kline.update
    
    def test_no_duplicate_event_values(self):
        """测试没有重复的事件主题值"""
        # 获取所有事件常量的值
        event_values = []
        for attr_name in dir(DEEvents):
            if not attr_name.startswith('_'):  # 排除私有属性
                attr_value = getattr(DEEvents, attr_name)
                if isinstance(attr_value, str):
                    event_values.append(attr_value)
        
        # 检查是否有重复
        assert len(event_values) == len(set(event_values)), "存在重复的事件主题值"
    
    def test_all_event_constants_are_strings(self):
        """测试所有事件常量都是字符串类型"""
        for attr_name in dir(DEEvents):
            if not attr_name.startswith('_'):  # 排除私有属性
                attr_value = getattr(DEEvents, attr_name)
                if not callable(attr_value):  # 排除方法
                    assert isinstance(attr_value, str), f"{attr_name} 应该是字符串类型"


class TestDEEventsCount:
    """测试事件常量数量"""
    
    def test_input_events_count(self):
        """测试输入事件数量为6个"""
        input_events = [
            attr for attr in dir(DEEvents) 
            if attr.startswith('INPUT_')
        ]
        assert len(input_events) == 6, f"应该有6个输入事件，实际有{len(input_events)}个"
    
    def test_output_events_count(self):
        """测试输出事件数量为16个"""
        # 获取所有非INPUT_开头的公共常量
        all_attrs = [
            attr for attr in dir(DEEvents)
            if not attr.startswith('_') and not attr.startswith('INPUT_')
        ]
        # 排除可能的方法
        output_events = [
            attr for attr in all_attrs
            if not callable(getattr(DEEvents, attr))
        ]
        assert len(output_events) == 16, f"应该有16个输出事件，实际有{len(output_events)}个"

