"""
PM（Portfolio Manager）类

负责管理单个交易账户，包括：
- 存储和管理账户配置信息
- 管理账户的启用/禁用状态
- 提供账户信息的访问接口
- 发布账户状态变更事件

使用方式：
    from src.core.pm.pm import PM
    from src.core.event_bus import EventBus
    
    bus = EventBus.get_instance()
    config = {
        "name": "测试账户",
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "strategy": "ma_stop_st",
        "testnet": True
    }
    
    pm = PM(user_id="user_001", config=config, event_bus=bus)
    
    # 获取API凭证
    api_key, api_secret = pm.get_api_credentials()
    
    # 禁用账户
    await pm.disable()
"""

import asyncio
from typing import Dict, Any, Tuple
from src.core.event import Event, EventBus
from src.core.pm.pm_events import PMEvents
from src.utils.logger import logger


class PM:
    """
    账户管理类，每个实例管理一个交易账户
    
    职责：
    - 存储和管理单个账户的配置信息
    - 管理账户的启用/禁用状态
    - 提供账户信息的访问接口
    - 发布账户状态变更事件
    
    设计原则：
    - 面向对象：所有属性私有化，通过属性和方法访问
    - 不可变性：关键属性（user_id, name等）为只读
    - 事件驱动：状态变更通过事件通知其他模块
    
    Attributes:
        _user_id: 用户ID（私有，只读）
        _name: 账户名称（私有，只读）
        _api_key: API密钥（私有）
        _api_secret: API密钥（私有）
        _strategy: 策略名称（私有，只读）
        _testnet: 是否测试网（私有，只读）
        _enabled: 启用状态（私有）
        _event_bus: 事件总线（私有）
    """
    
    def __init__(self, user_id: str, config: Dict[str, Any], event_bus: EventBus):
        """
        初始化PM实例
        
        Args:
            user_id: 用户ID
            config: 账户配置字典，必需字段：name, api_key, api_secret, strategy
                   可选字段：testnet (默认False)
            event_bus: 事件总线实例
        
        Raises:
            ValueError: 配置验证失败
        
        实现细节：
            1. 验证配置有效性
            2. 初始化所有私有属性
            3. 默认启用状态为True
            4. 异步发布 pm.account.loaded 事件
        """
        # 验证配置
        self._validate_config(config)
        
        # 初始化私有属性
        self._user_id = user_id
        self._name = config["name"]
        self._api_key = config["api_key"]
        self._api_secret = config["api_secret"]
        self._strategy = config["strategy"]
        self._testnet = config.get("testnet", False)
        self._enabled = True
        self._event_bus = event_bus
        
        # 记录日志
        logger.info(f"PM实例初始化: user_id={user_id}, name={self._name}, "
                   f"strategy={self._strategy}, testnet={self._testnet}")

        # 标记是否已发布初始化事件
        self._init_event_published = False

        # 尝试异步发布账户加载事件（如果有事件循环）
        try:
            self._init_event_task = asyncio.create_task(self._publish_account_loaded())
        except RuntimeError:
            # 没有运行中的事件循环，延迟发布
            self._init_event_task = None
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """
        验证账户配置（私有方法）
        
        Args:
            config: 账户配置字典
        
        Raises:
            ValueError: 配置验证失败
        
        验证规则：
            - name: 必需，非空字符串
            - api_key: 必需，非空字符串
            - api_secret: 必需，非空字符串
            - strategy: 必需，非空字符串
            - testnet: 可选，布尔类型
        """
        required_fields = ["name", "api_key", "api_secret", "strategy"]
        
        # 检查必需字段
        for field in required_fields:
            if field not in config:
                raise ValueError(f"缺少必需字段: {field}")
            
            if not isinstance(config[field], str):
                raise ValueError(f"字段必须是字符串类型: {field}")
            
            if not config[field].strip():
                raise ValueError(f"字段不能为空: {field}")
        
        # 检查testnet字段类型
        if "testnet" in config and not isinstance(config["testnet"], bool):
            raise ValueError("testnet字段必须是布尔类型")
    
    async def _publish_account_loaded(self) -> None:
        """
        发布账户加载事件（私有方法）

        实现细节：
            - 创建 pm.account.loaded 事件
            - 包含完整的账户信息（含API密钥）
            - 异步发布到事件总线
        """
        if self._init_event_published:
            return

        event = Event(
            subject=PMEvents.ACCOUNT_LOADED,
            data={
                "user_id": self._user_id,
                "name": self._name,
                "api_key": self._api_key,
                "api_secret": self._api_secret,
                "strategy": self._strategy,
                "testnet": self._testnet
            },
            source="PM"
        )

        await self._event_bus.publish(event)
        self._init_event_published = True
        logger.info(f"发布账户加载事件: user_id={self._user_id}")

    async def ensure_init_event_published(self) -> None:
        """
        确保初始化事件已发布（公共方法）

        如果初始化时没有事件循环，可以在有事件循环时调用此方法发布事件

        使用方式：
            pm = PM(...)  # 可能没有事件循环
            await pm.ensure_init_event_published()  # 在有事件循环时调用
        """
        if not self._init_event_published:
            await self._publish_account_loaded()
    
    # ==================== 只读属性 ====================
    
    @property
    def user_id(self) -> str:
        """获取用户ID（只读属性）"""
        return self._user_id
    
    @property
    def name(self) -> str:
        """获取账户名称（只读属性）"""
        return self._name
    
    @property
    def strategy(self) -> str:
        """获取策略名称（只读属性）"""
        return self._strategy
    
    @property
    def is_testnet(self) -> bool:
        """是否为测试网（只读属性）"""
        return self._testnet
    
    @property
    def is_enabled(self) -> bool:
        """获取启用状态（只读属性）"""
        return self._enabled
    
    # ==================== 公共方法 ====================
    
    def get_api_credentials(self) -> Tuple[str, str]:
        """
        获取API凭证
        
        Returns:
            (api_key, api_secret) 元组
        
        使用方式：
            api_key, api_secret = pm.get_api_credentials()
        """
        return (self._api_key, self._api_secret)
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取配置信息（不含敏感信息）
        
        Returns:
            配置字典（不包含api_key和api_secret）
        
        使用方式：
            config = pm.get_config()
            print(config["name"])
        """
        return {
            "user_id": self._user_id,
            "name": self._name,
            "strategy": self._strategy,
            "testnet": self._testnet,
            "enabled": self._enabled
        }
    
    def get_full_config(self) -> Dict[str, Any]:
        """
        获取完整配置信息（含敏感信息）
        
        Returns:
            完整配置字典（包含api_key和api_secret）
        
        注意：
            此方法返回敏感信息，请谨慎使用
        
        使用方式：
            config = pm.get_full_config()
            api_key = config["api_key"]
        """
        return {
            "user_id": self._user_id,
            "name": self._name,
            "api_key": self._api_key,
            "api_secret": self._api_secret,
            "strategy": self._strategy,
            "testnet": self._testnet,
            "enabled": self._enabled
        }
    
    async def enable(self) -> None:
        """
        启用账户
        
        实现细节：
            1. 设置 _enabled = True
            2. 发布 pm.account.enabled 事件
            3. 记录日志
        
        使用方式：
            await pm.enable()
        """
        self._enabled = True
        
        event = Event(
            subject=PMEvents.ACCOUNT_ENABLED,
            data={
                "user_id": self._user_id,
                "name": self._name,
                "enabled": True
            },
            source="PM"
        )
        
        await self._event_bus.publish(event)
        logger.info(f"账户已启用: user_id={self._user_id}")
    
    async def disable(self, persist: bool = True) -> None:
        """
        禁用账户

        参数：
            persist: 是否持久化事件（默认True，在系统关闭时可设为False）

        实现细节：
            1. 设置 _enabled = False
            2. 发布 pm.account.disabled 事件
            3. 记录日志

        使用方式：
            await pm.disable()
            await pm.disable(persist=False)  # 系统关闭时
        """
        self._enabled = False

        event = Event(
            subject=PMEvents.ACCOUNT_DISABLED,
            data={
                "user_id": self._user_id,
                "name": self._name,
                "enabled": False
            },
            source="PM"
        )

        await self._event_bus.publish(event, persist=persist)
        logger.info(f"账户已禁用: user_id={self._user_id}")
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"PM(user_id={self._user_id}, name={self._name}, enabled={self._enabled})"

