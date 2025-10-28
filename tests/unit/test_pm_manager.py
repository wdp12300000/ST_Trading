"""
PMManager类单元测试

测试PMManager类的完整功能，包括：
- 单例模式
- 配置文件加载
- 配置验证
- PM实例创建和管理
- 失败账户记录
- 查询接口
- 系统关闭
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, call
from src.core.pm.pm_manager import PMManager
from src.core.pm.pm import PM
from src.core.pm.pm_events import PMEvents
from src.core.event import Event


class TestPMManagerSingleton:
    """测试PMManager的单例模式"""
    
    def teardown_method(self):
        """每个测试后重置单例"""
        PMManager.reset_instance()
    
    def test_get_instance_creates_singleton(self):
        """测试get_instance创建单例"""
        event_bus = Mock()
        
        manager1 = PMManager.get_instance(event_bus=event_bus)
        manager2 = PMManager.get_instance()
        
        assert manager1 is manager2
    
    def test_get_instance_requires_event_bus_on_first_call(self):
        """测试首次调用必须提供event_bus"""
        with pytest.raises(ValueError, match="首次调用必须提供event_bus"):
            PMManager.get_instance()
    
    def test_reset_instance(self):
        """测试重置单例"""
        event_bus = Mock()
        
        manager1 = PMManager.get_instance(event_bus=event_bus)
        PMManager.reset_instance()
        manager2 = PMManager.get_instance(event_bus=event_bus)
        
        assert manager1 is not manager2


class TestPMManagerConfigLoading:
    """测试PMManager的配置加载"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        
        # 创建临时配置文件
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "pm_config.json"
    
    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        # 清理临时文件
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()
    
    def _create_config_file(self, config_data):
        """创建配置文件的辅助方法"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    @pytest.mark.asyncio
    async def test_load_accounts_with_valid_config(self):
        """测试加载有效配置"""
        config_data = {
            "users": {
                "user_001": {
                    "name": "账户1",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1",
                    "testnet": True
                },
                "user_002": {
                    "name": "账户2",
                    "api_key": "key2",
                    "api_secret": "secret2",
                    "strategy": "strategy2"
                }
            }
        }
        self._create_config_file(config_data)
        
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        loaded_count = await manager.load_accounts()
        
        assert loaded_count == 2
        assert manager.get_pm_count() == 2
        assert "user_001" in manager.get_all_user_ids()
        assert "user_002" in manager.get_all_user_ids()
    
    def test_load_accounts_config_file_not_found(self):
        """测试配置文件不存在时抛出异常"""
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path="nonexistent.json")
        
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            asyncio.run(manager.load_accounts())
    
    def test_load_accounts_invalid_json(self):
        """测试JSON格式错误时抛出异常"""
        # 创建无效的JSON文件
        with open(self.config_path, 'w') as f:
            f.write("{ invalid json }")
        
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        
        with pytest.raises(ValueError, match="配置文件JSON格式错误"):
            asyncio.run(manager.load_accounts())
    
    @pytest.mark.asyncio
    async def test_load_accounts_missing_users_key(self):
        """测试配置文件缺少users键"""
        config_data = {"accounts": {}}  # 错误的键名
        self._create_config_file(config_data)
        
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        
        with pytest.raises(ValueError, match="配置文件缺少'users'字段"):
            await manager.load_accounts()


class TestPMManagerConfigValidation:
    """测试PMManager的配置验证"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "pm_config.json"
    
    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()
    
    def _create_config_file(self, config_data):
        """创建配置文件的辅助方法"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    @pytest.mark.asyncio
    async def test_load_accounts_skip_invalid_account(self):
        """测试跳过无效账户配置"""
        config_data = {
            "users": {
                "user_001": {
                    "name": "有效账户",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1"
                },
                "user_002": {
                    "name": "无效账户",
                    # 缺少api_key
                    "api_secret": "secret2",
                    "strategy": "strategy2"
                },
                "user_003": {
                    "name": "另一个有效账户",
                    "api_key": "key3",
                    "api_secret": "secret3",
                    "strategy": "strategy3"
                }
            }
        }
        self._create_config_file(config_data)
        
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        loaded_count = await manager.load_accounts()
        
        # 应该加载2个有效账户，跳过1个无效账户
        assert loaded_count == 2
        assert manager.get_pm_count() == 2
        assert manager.get_failed_count() == 1
        
        # 验证失败记录
        failed_accounts = manager.get_failed_accounts()
        assert "user_002" in failed_accounts
        assert "缺少必需字段" in failed_accounts["user_002"]


class TestPMManagerInstanceManagement:
    """测试PMManager的实例管理"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "pm_config.json"
        
        # 创建测试配置
        config_data = {
            "users": {
                "user_001": {
                    "name": "账户1",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1"
                },
                "user_002": {
                    "name": "账户2",
                    "api_key": "key2",
                    "api_secret": "secret2",
                    "strategy": "strategy2"
                }
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        self.manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
    
    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()
    
    @pytest.mark.asyncio
    async def test_get_pm_by_user_id(self):
        """测试根据user_id获取PM实例"""
        await self.manager.load_accounts()
        
        pm = self.manager.get_pm("user_001")
        
        assert pm is not None
        assert isinstance(pm, PM)
        assert pm.user_id == "user_001"
        assert pm.name == "账户1"
    
    @pytest.mark.asyncio
    async def test_get_pm_nonexistent_user(self):
        """测试获取不存在的用户返回None"""
        await self.manager.load_accounts()
        
        pm = self.manager.get_pm("user_999")
        
        assert pm is None
    
    @pytest.mark.asyncio
    async def test_get_all_user_ids(self):
        """测试获取所有用户ID列表"""
        await self.manager.load_accounts()
        
        user_ids = self.manager.get_all_user_ids()
        
        assert len(user_ids) == 2
        assert "user_001" in user_ids
        assert "user_002" in user_ids
    
    @pytest.mark.asyncio
    async def test_get_all_pms(self):
        """测试获取所有PM实例"""
        await self.manager.load_accounts()
        
        pms = self.manager.get_all_pms()
        
        assert len(pms) == 2
        assert "user_001" in pms
        assert "user_002" in pms
        assert isinstance(pms["user_001"], PM)
        assert isinstance(pms["user_002"], PM)


class TestPMManagerEvents:
    """测试PMManager的事件发布"""

    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "pm_config.json"

        # 创建测试配置
        config_data = {
            "users": {
                "user_001": {
                    "name": "账户1",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1"
                }
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        self.manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))

    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()

    @pytest.mark.asyncio
    async def test_load_accounts_publishes_manager_ready_event(self):
        """测试加载完成后发布pm.manager.ready事件"""
        await self.manager.load_accounts()

        # 查找manager.ready事件
        manager_ready_calls = [
            call for call in self.event_bus.publish.call_args_list
            if call[0][0].subject == PMEvents.MANAGER_READY
        ]

        assert len(manager_ready_calls) == 1
        event = manager_ready_calls[0][0][0]

        assert event.data["loaded_count"] == 1
        assert event.data["failed_count"] == 0
        assert "user_001" in event.data["user_ids"]

    @pytest.mark.asyncio
    async def test_load_accounts_publishes_load_failed_event(self):
        """测试加载失败时发布pm.load.failed事件"""
        # 创建包含无效账户的配置
        config_data = {
            "users": {
                "user_001": {
                    "name": "有效账户",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1"
                },
                "user_002": {
                    "name": "无效账户"
                    # 缺少必需字段
                }
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        await manager.load_accounts()

        # 查找load.failed事件
        load_failed_calls = [
            call for call in self.event_bus.publish.call_args_list
            if call[0][0].subject == PMEvents.LOAD_FAILED
        ]

        assert len(load_failed_calls) == 1
        event = load_failed_calls[0][0][0]

        assert event.data["user_id"] == "user_002"
        assert "error" in event.data


class TestPMManagerShutdown:
    """测试PMManager的关闭功能"""

    def setup_method(self):
        """每个测试前的准备工作"""
        self.event_bus = Mock()
        self.event_bus.publish = AsyncMock()
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "pm_config.json"

        # 创建测试配置
        config_data = {
            "users": {
                "user_001": {
                    "name": "账户1",
                    "api_key": "key1",
                    "api_secret": "secret1",
                    "strategy": "strategy1"
                },
                "user_002": {
                    "name": "账户2",
                    "api_key": "key2",
                    "api_secret": "secret2",
                    "strategy": "strategy2"
                }
            }
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        self.manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))

    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()

    @pytest.mark.asyncio
    async def test_shutdown_disables_all_accounts(self):
        """测试关闭时禁用所有账户"""
        await self.manager.load_accounts()

        # 验证账户初始状态为启用
        pm1 = self.manager.get_pm("user_001")
        pm2 = self.manager.get_pm("user_002")
        assert pm1.is_enabled is True
        assert pm2.is_enabled is True

        # 关闭管理器
        await self.manager.shutdown()

        # 验证所有账户被禁用
        assert pm1.is_enabled is False
        assert pm2.is_enabled is False

    @pytest.mark.asyncio
    async def test_shutdown_publishes_shutdown_event(self):
        """测试关闭时发布pm.manager.shutdown事件"""
        await self.manager.load_accounts()
        self.event_bus.publish.reset_mock()

        await self.manager.shutdown()

        # 查找shutdown事件（应该在所有disable事件之后）
        shutdown_calls = [
            call for call in self.event_bus.publish.call_args_list
            if call[0][0].subject == PMEvents.MANAGER_SHUTDOWN
        ]

        assert len(shutdown_calls) == 1
        event = shutdown_calls[0][0][0]

        assert event.data["pm_count"] == 2
        assert "message" in event.data

    @pytest.mark.asyncio
    async def test_shutdown_clears_pm_instances(self):
        """测试关闭后清空PM实例"""
        await self.manager.load_accounts()
        assert self.manager.get_pm_count() == 2

        await self.manager.shutdown()

        assert self.manager.get_pm_count() == 0
        assert len(self.manager.get_all_user_ids()) == 0

