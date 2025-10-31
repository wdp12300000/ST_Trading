"""
TRManager单元测试

测试TRManager类的基本功能。
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.core.tr.tr_manager import TRManager
from src.core.event.event_bus import EventBus
from src.core.event.event import Event
from src.core.tr.tr_events import TREvents


class TestTRManagerCreation:
    """测试TRManager的创建"""
    
    def setup_method(self):
        """每个测试方法前重置单例"""
        TRManager.reset_instance()
    
    def teardown_method(self):
        """每个测试方法后重置单例"""
        TRManager.reset_instance()
    
    def test_create_instance_with_event_bus(self):
        """测试使用event_bus创建实例"""
        event_bus = Mock(spec=EventBus)
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        
        assert tr_manager is not None
        assert isinstance(tr_manager, TRManager)
        assert tr_manager._event_bus == event_bus
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        event_bus = Mock(spec=EventBus)
        tr_manager1 = TRManager.get_instance(event_bus=event_bus)
        tr_manager2 = TRManager.get_instance()
        
        assert tr_manager1 is tr_manager2
    
    def test_get_instance_without_event_bus_raises_error(self):
        """测试首次调用get_instance时未提供event_bus会抛出异常"""
        with pytest.raises(ValueError, match="首次调用get_instance"):
            TRManager.get_instance()
    
    def test_direct_instantiation_raises_error(self):
        """测试直接实例化会抛出异常"""
        event_bus = Mock(spec=EventBus)
        TRManager.get_instance(event_bus=event_bus)
        
        with pytest.raises(RuntimeError, match="单例类"):
            TRManager(event_bus)
    
    def test_initial_state(self):
        """测试初始状态"""
        event_bus = Mock(spec=EventBus)
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        
        assert tr_manager._is_started is False
        assert len(tr_manager._tasks) == 0
        assert len(tr_manager._user_configs) == 0


class TestTRManagerStart:
    """测试TRManager的启动"""
    
    def setup_method(self):
        """每个测试方法前重置单例"""
        TRManager.reset_instance()
    
    def teardown_method(self):
        """每个测试方法后重置单例"""
        TRManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_start_subscribes_events(self):
        """测试启动时订阅事件"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        
        # 验证订阅了所有必要的事件
        assert event_bus.subscribe.call_count >= 7  # 至少订阅7个事件
        assert tr_manager._is_started is True
    
    @pytest.mark.asyncio
    async def test_start_publishes_manager_started_event(self):
        """测试启动时发布manager_started事件"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        
        # 验证发布了启动事件
        event_bus.publish.assert_called()
        call_args = event_bus.publish.call_args[0][0]
        assert call_args.subject == TREvents.MANAGER_STARTED
    
    @pytest.mark.asyncio
    async def test_start_twice_raises_error(self):
        """测试重复启动会抛出异常"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        
        with pytest.raises(RuntimeError, match="已经启动"):
            await tr_manager.start()


class TestTRManagerEventHandlers:
    """测试TRManager的事件处理器"""
    
    def setup_method(self):
        """每个测试方法前重置单例"""
        TRManager.reset_instance()
    
    def teardown_method(self):
        """每个测试方法后重置单例"""
        TRManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_on_account_loaded(self):
        """测试处理账户加载事件"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        
        # 创建账户加载事件
        event = Event(
            subject=TREvents.INPUT_ACCOUNT_LOADED,
            data={"user_id": "user_001", "api_key": "test_key"},
            source="pm"
        )
        
        # 调用事件处理器
        await tr_manager._on_account_loaded(event)
        
        # 验证日志记录（通过不抛出异常来验证）
        assert True
    
    @pytest.mark.asyncio
    async def test_on_signal_generated(self):
        """测试处理交易信号事件"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        
        # 创建交易信号事件
        event = Event(
            subject=TREvents.INPUT_SIGNAL_GENERATED,
            data={"user_id": "user_001", "symbol": "XRPUSDC", "side": "LONG", "action": "OPEN"},
            source="st"
        )
        
        # 调用事件处理器
        await tr_manager._on_signal_generated(event)
        
        # 验证日志记录
        assert True


class TestTRManagerShutdown:
    """测试TRManager的关闭"""
    
    def setup_method(self):
        """每个测试方法前重置单例"""
        TRManager.reset_instance()
    
    def teardown_method(self):
        """每个测试方法后重置单例"""
        TRManager.reset_instance()
    
    @pytest.mark.asyncio
    async def test_shutdown_publishes_event(self):
        """测试关闭时发布shutdown事件"""
        event_bus = Mock(spec=EventBus)
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        await tr_manager.start()
        await tr_manager.shutdown()
        
        # 验证发布了关闭事件
        calls = event_bus.publish.call_args_list
        shutdown_event = None
        for call in calls:
            event = call[0][0]
            if event.subject == TREvents.MANAGER_SHUTDOWN:
                shutdown_event = event
                break
        
        assert shutdown_event is not None
        assert tr_manager._is_started is False
    
    @pytest.mark.asyncio
    async def test_shutdown_without_start(self):
        """测试未启动时关闭不会抛出异常"""
        event_bus = Mock(spec=EventBus)
        tr_manager = TRManager.get_instance(event_bus=event_bus)
        
        # 不应该抛出异常
        await tr_manager.shutdown()
        assert tr_manager._is_started is False

