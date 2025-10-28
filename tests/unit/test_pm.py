"""
PM类单元测试

测试PM类的完整功能，包括：
- 初始化和配置验证
- 属性访问（只读属性）
- 启用/禁用功能
- 事件发布
- 配置获取
"""

import pytest
from unittest.mock import Mock, AsyncMock, call
from src.core.pm.pm import PM
from src.core.pm.pm_events import PMEvents
from src.core.event import Event


class TestPMInitialization:
    """测试PM类的初始化"""
    
    def test_pm_init_with_valid_config(self):
        """测试使用有效配置初始化PM实例"""
        event_bus = Mock()
        config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy",
            "testnet": True
        }
        
        pm = PM(user_id="user_001", config=config, event_bus=event_bus)
        
        assert pm.user_id == "user_001"
        assert pm.name == "测试账户"
        assert pm.strategy == "test_strategy"
        assert pm.is_testnet is True
        assert pm.is_enabled is True  # 默认启用
    
    def test_pm_init_without_testnet(self):
        """测试配置中不包含testnet字段时使用默认值False"""
        event_bus = Mock()
        config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy"
        }
        
        pm = PM(user_id="user_001", config=config, event_bus=event_bus)
        
        assert pm.is_testnet is False
    
    def test_pm_init_missing_required_field(self):
        """测试缺少必需字段时抛出异常"""
        event_bus = Mock()
        
        # 缺少name
        config = {
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy"
        }
        
        with pytest.raises(ValueError, match="缺少必需字段: name"):
            PM(user_id="user_001", config=config, event_bus=event_bus)
    
    def test_pm_init_empty_required_field(self):
        """测试必需字段为空字符串时抛出异常"""
        event_bus = Mock()
        config = {
            "name": "",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy"
        }
        
        with pytest.raises(ValueError, match="字段不能为空: name"):
            PM(user_id="user_001", config=config, event_bus=event_bus)
    
    def test_pm_init_invalid_testnet_type(self):
        """测试testnet字段类型错误时抛出异常"""
        event_bus = Mock()
        config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy",
            "testnet": "true"  # 应该是布尔类型
        }
        
        with pytest.raises(ValueError, match="testnet字段必须是布尔类型"):
            PM(user_id="user_001", config=config, event_bus=event_bus)
    
    @pytest.mark.asyncio
    async def test_pm_init_publishes_account_loaded_event(self):
        """测试初始化时发布pm.account.loaded事件"""
        event_bus = Mock()
        event_bus.publish = AsyncMock()

        config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy",
            "testnet": True
        }

        pm = PM(user_id="user_001", config=config, event_bus=event_bus)

        # 等待异步事件发布（如果有事件循环会自动发布）
        if pm._init_event_task:
            await pm._init_event_task
        else:
            # 没有事件循环时手动触发
            await pm.ensure_init_event_published()

        # 验证事件发布
        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]

        assert published_event.subject == PMEvents.ACCOUNT_LOADED
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["name"] == "测试账户"
        assert published_event.data["api_key"] == "test_api_key"
        assert published_event.data["api_secret"] == "test_api_secret"
        assert published_event.data["strategy"] == "test_strategy"
        assert published_event.data["testnet"] is True


class TestPMProperties:
    """测试PM类的属性访问"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy",
            "testnet": True
        }
        self.pm = PM(user_id="user_001", config=self.config, event_bus=self.event_bus)
    
    def test_user_id_property_readonly(self):
        """测试user_id属性为只读"""
        assert self.pm.user_id == "user_001"
        
        with pytest.raises(AttributeError):
            self.pm.user_id = "user_002"
    
    def test_name_property_readonly(self):
        """测试name属性为只读"""
        assert self.pm.name == "测试账户"
        
        with pytest.raises(AttributeError):
            self.pm.name = "新账户"
    
    def test_strategy_property_readonly(self):
        """测试strategy属性为只读"""
        assert self.pm.strategy == "test_strategy"
        
        with pytest.raises(AttributeError):
            self.pm.strategy = "new_strategy"
    
    def test_is_testnet_property_readonly(self):
        """测试is_testnet属性为只读"""
        assert self.pm.is_testnet is True
        
        with pytest.raises(AttributeError):
            self.pm.is_testnet = False
    
    def test_is_enabled_property_readonly(self):
        """测试is_enabled属性为只读"""
        assert self.pm.is_enabled is True
        
        with pytest.raises(AttributeError):
            self.pm.is_enabled = False


class TestPMCredentials:
    """测试PM类的凭证获取"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy"
        }
        self.pm = PM(user_id="user_001", config=self.config, event_bus=self.event_bus)
    
    def test_get_api_credentials(self):
        """测试获取API凭证"""
        api_key, api_secret = self.pm.get_api_credentials()
        
        assert api_key == "test_api_key"
        assert api_secret == "test_api_secret"
    
    def test_get_config_without_sensitive_info(self):
        """测试获取配置信息（不含敏感信息）"""
        config = self.pm.get_config()
        
        assert config["user_id"] == "user_001"
        assert config["name"] == "测试账户"
        assert config["strategy"] == "test_strategy"
        assert config["testnet"] is False
        assert config["enabled"] is True
        assert "api_key" not in config
        assert "api_secret" not in config
    
    def test_get_full_config_with_sensitive_info(self):
        """测试获取完整配置信息（含敏感信息）"""
        config = self.pm.get_full_config()
        
        assert config["user_id"] == "user_001"
        assert config["name"] == "测试账户"
        assert config["api_key"] == "test_api_key"
        assert config["api_secret"] == "test_api_secret"
        assert config["strategy"] == "test_strategy"
        assert config["testnet"] is False
        assert config["enabled"] is True


class TestPMEnableDisable:
    """测试PM类的启用/禁用功能"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        self.config = {
            "name": "测试账户",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret",
            "strategy": "test_strategy"
        }
        self.pm = PM(user_id="user_001", config=self.config, event_bus=self.event_bus)
    
    @pytest.mark.asyncio
    async def test_disable_account(self):
        """测试禁用账户"""
        # 清除初始化时的事件调用
        self.event_bus.publish.reset_mock()
        
        await self.pm.disable()
        
        assert self.pm.is_enabled is False
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
        published_event = self.event_bus.publish.call_args[0][0]
        
        assert published_event.subject == PMEvents.ACCOUNT_DISABLED
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["name"] == "测试账户"
        assert published_event.data["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_enable_account(self):
        """测试启用账户"""
        # 先禁用
        await self.pm.disable()
        self.event_bus.publish.reset_mock()
        
        await self.pm.enable()
        
        assert self.pm.is_enabled is True
        
        # 验证事件发布
        self.event_bus.publish.assert_called_once()
        published_event = self.event_bus.publish.call_args[0][0]
        
        assert published_event.subject == PMEvents.ACCOUNT_ENABLED
        assert published_event.data["user_id"] == "user_001"
        assert published_event.data["name"] == "测试账户"
        assert published_event.data["enabled"] is True

