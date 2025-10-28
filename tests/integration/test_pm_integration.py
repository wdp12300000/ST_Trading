"""
PM模块集成测试

测试PM模块与EventBus的完整交互，包括：
- PM实例与EventBus的事件发布
- PMManager与EventBus的事件发布
- 完整的账户加载流程
- 事件订阅和处理
- 系统关闭流程
"""

import pytest
import json
import tempfile
import asyncio
from pathlib import Path
from src.core.event import EventBus
from src.core.event import SQLiteEventStore
from src.core.pm.pm import PM
from src.core.pm.pm_manager import PMManager
from src.core.pm.pm_events import PMEvents


class TestPMEventBusIntegration:
    """测试PM类与EventBus的集成"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_events.db"
        
        # 创建EventBus和EventStore
        self.event_store = SQLiteEventStore(db_path=str(self.db_path))
        self.event_bus = EventBus.get_instance(event_store=self.event_store)
        
        # 用于收集事件的列表
        self.received_events = []
    
    def teardown_method(self):
        """每个测试后的清理工作"""
        # EventBus是单例，不需要重置
        self.event_store.close()
        if self.db_path.exists():
            self.db_path.unlink()
        Path(self.temp_dir).rmdir()
    
    async def event_collector(self, event):
        """事件收集器"""
        self.received_events.append(event)
    
    @pytest.mark.asyncio
    async def test_pm_publishes_account_loaded_event(self):
        """测试PM实例发布账户加载事件到EventBus"""
        # 订阅事件
        self.event_bus.subscribe(PMEvents.ACCOUNT_LOADED, self.event_collector)

        # 创建PM实例
        config = {
            "name": "测试账户",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "strategy": "test_strategy",
            "testnet": True
        }

        pm = PM(user_id="user_001", config=config, event_bus=self.event_bus)

        # 等待事件处理（PM初始化时会自动发布事件）
        await asyncio.sleep(0.1)

        # 验证事件（PM初始化时自动发布一次）
        assert len(self.received_events) == 1
        event = self.received_events[0]
        assert event.subject == PMEvents.ACCOUNT_LOADED
        assert event.data["user_id"] == "user_001"
        assert event.data["name"] == "测试账户"
        assert event.data["api_key"] == "test_key"
        assert event.data["testnet"] is True
    
    @pytest.mark.asyncio
    async def test_pm_enable_disable_events(self):
        """测试PM启用/禁用事件"""
        # 订阅所有PM事件
        self.event_bus.subscribe("pm.*", self.event_collector)

        config = {
            "name": "测试账户",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "strategy": "test_strategy"
        }

        pm = PM(user_id="user_001", config=config, event_bus=self.event_bus)

        # 等待初始化事件
        await asyncio.sleep(0.1)

        # 清空已收集的事件（包括初始化事件）
        self.received_events.clear()

        # 禁用账户
        await pm.disable()
        await asyncio.sleep(0.1)

        # 验证禁用事件
        disable_events = [e for e in self.received_events if e.subject == PMEvents.ACCOUNT_DISABLED]
        assert len(disable_events) == 1
        assert disable_events[0].data["enabled"] is False

        # 启用账户
        await pm.enable()
        await asyncio.sleep(0.1)

        # 验证启用事件
        enable_events = [e for e in self.received_events if e.subject == PMEvents.ACCOUNT_ENABLED]
        assert len(enable_events) == 1
        assert enable_events[0].data["enabled"] is True


class TestPMManagerEventBusIntegration:
    """测试PMManager与EventBus的集成"""
    
    def setup_method(self):
        """每个测试前的准备工作"""
        # 创建临时目录和文件
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_events.db"
        self.config_path = Path(self.temp_dir) / "pm_config.json"
        
        # 创建EventBus和EventStore
        self.event_store = SQLiteEventStore(db_path=str(self.db_path))
        self.event_bus = EventBus.get_instance(event_store=self.event_store)
        
        # 用于收集事件的列表
        self.received_events = []
    
    def teardown_method(self):
        """每个测试后的清理工作"""
        PMManager.reset_instance()
        # EventBus是单例，不需要重置
        self.event_store.close()
        if self.db_path.exists():
            self.db_path.unlink()
        if self.config_path.exists():
            self.config_path.unlink()
        Path(self.temp_dir).rmdir()
    
    async def event_collector(self, event):
        """事件收集器"""
        self.received_events.append(event)
    
    def _create_config_file(self, config_data):
        """创建配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    @pytest.mark.asyncio
    async def test_pm_manager_complete_workflow(self):
        """测试PMManager完整工作流程"""
        # 订阅所有PM事件
        self.event_bus.subscribe("pm.*", self.event_collector)
        
        # 创建配置文件
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
        
        # 创建PMManager并加载账户
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        loaded_count = await manager.load_accounts()
        
        # 等待事件处理
        await asyncio.sleep(0.1)
        
        # 验证加载结果
        assert loaded_count == 2
        assert manager.get_pm_count() == 2

        # 验证事件
        # 每个PM实例初始化时会自动发布一次account.loaded事件
        # 所以2个账户会有2次account.loaded事件 + 1个manager.ready事件
        account_loaded_events = [e for e in self.received_events if e.subject == PMEvents.ACCOUNT_LOADED]
        manager_ready_events = [e for e in self.received_events if e.subject == PMEvents.MANAGER_READY]

        assert len(account_loaded_events) == 2
        assert len(manager_ready_events) == 1

        # 验证manager.ready事件数据
        ready_event = manager_ready_events[0]
        assert ready_event.data["loaded_count"] == 2
        assert ready_event.data["failed_count"] == 0
        assert "user_001" in ready_event.data["user_ids"]
        assert "user_002" in ready_event.data["user_ids"]
    
    @pytest.mark.asyncio
    async def test_pm_manager_with_failed_accounts(self):
        """测试PMManager处理失败账户"""
        # 订阅所有PM事件
        self.event_bus.subscribe("pm.*", self.event_collector)
        
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
        
        # 加载账户
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        loaded_count = await manager.load_accounts()
        
        await asyncio.sleep(0.1)
        
        # 验证加载结果
        assert loaded_count == 2
        assert manager.get_failed_count() == 1
        
        # 验证事件
        account_loaded_events = [e for e in self.received_events if e.subject == PMEvents.ACCOUNT_LOADED]
        load_failed_events = [e for e in self.received_events if e.subject == PMEvents.LOAD_FAILED]
        manager_ready_events = [e for e in self.received_events if e.subject == PMEvents.MANAGER_READY]
        
        assert len(account_loaded_events) == 2
        assert len(load_failed_events) == 1
        assert len(manager_ready_events) == 1
        
        # 验证失败事件
        failed_event = load_failed_events[0]
        assert failed_event.data["user_id"] == "user_002"
        assert "error" in failed_event.data
    
    @pytest.mark.asyncio
    async def test_pm_manager_shutdown_workflow(self):
        """测试PMManager关闭流程"""
        # 订阅所有PM事件
        self.event_bus.subscribe("pm.*", self.event_collector)
        
        # 创建配置并加载
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
        self._create_config_file(config_data)
        
        manager = PMManager.get_instance(event_bus=self.event_bus, config_path=str(self.config_path))
        await manager.load_accounts()
        
        # 清空事件
        self.received_events.clear()
        
        # 关闭管理器
        await manager.shutdown()
        await asyncio.sleep(0.1)
        
        # 验证关闭事件
        # 应该有: 2个account.disabled + 1个manager.shutdown
        disabled_events = [e for e in self.received_events if e.subject == PMEvents.ACCOUNT_DISABLED]
        shutdown_events = [e for e in self.received_events if e.subject == PMEvents.MANAGER_SHUTDOWN]
        
        assert len(disabled_events) == 2
        assert len(shutdown_events) == 1
        
        # 验证shutdown事件数据
        shutdown_event = shutdown_events[0]
        assert shutdown_event.data["pm_count"] == 2
        assert "message" in shutdown_event.data
        
        # 验证PM实例已清空
        assert manager.get_pm_count() == 0

