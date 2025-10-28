"""
PMManager（PM管理器）类

负责管理多个PM实例，包括：
- 从配置文件加载账户信息
- 验证账户配置有效性
- 创建和管理多个PM实例
- 提供PM实例的查询接口
- 记录加载失败的账户
- 系统关闭时的清理工作

使用方式：
    from src.core.pm.pm_manager import PMManager
    from src.core.event_bus import EventBus

    bus = EventBus.get_instance()
    manager = PMManager.get_instance(event_bus=bus)

    # 加载所有账户
    loaded_count = await manager.load_accounts()

    # 获取PM实例
    pm = manager.get_pm("user_001")

    # 系统关闭
    await manager.shutdown()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.core.event import Event, EventBus
from src.core.pm.pm import PM
from src.core.pm.pm_events import PMEvents
from src.utils.logger import logger


class PMManager:
    """
    PM管理器，负责加载配置并管理多个PM实例（单例模式）

    职责：
    - 从配置文件加载账户信息
    - 验证账户配置有效性
    - 创建和管理多个PM实例
    - 提供PM实例的查询接口
    - 记录加载失败的账户
    - 系统关闭时的清理工作

    设计原则：
    - 单例模式：全局唯一的PM管理器
    - 面向对象：所有功能封装在类方法中
    - 错误隔离：单个账户加载失败不影响其他账户
    - 事件驱动：通过事件通知其他模块

    Attributes:
        _instance: 单例实例（类属性）
        _pm_instances: 用户ID到PM实例的映射（私有）
        _failed_accounts: 加载失败的账户记录（私有）
        _event_bus: 事件总线（私有）
        _config_path: 配置文件路径（私有）
    """

    _instance = None  # 单例实例

    def __init__(self, event_bus: EventBus, config_path: str = "config/pm_config.json"):
        """
        私有构造函数（通过get_instance调用）

        Args:
            event_bus: 事件总线实例
            config_path: 配置文件路径
        """
        self._event_bus = event_bus
        self._config_path = config_path
        self._pm_instances: Dict[str, PM] = {}
        self._failed_accounts: Dict[str, str] = {}

        logger.info(f"PMManager初始化: config_path={config_path}")

    @classmethod
    def get_instance(cls, event_bus: EventBus = None,
                     config_path: str = "config/pm_config.json") -> "PMManager":
        """
        获取PMManager单例实例

        Args:
            event_bus: 事件总线实例（首次调用必需）
            config_path: 配置文件路径

        Returns:
            PMManager单例实例

        Raises:
            ValueError: 首次调用时未提供event_bus

        实现细节：
            - 首次调用时创建实例
            - 后续调用返回已有实例
            - 首次调用必须提供event_bus
        """
        if cls._instance is None:
            if event_bus is None:
                raise ValueError("首次调用必须提供event_bus")
            cls._instance = cls(event_bus=event_bus, config_path=config_path)
            logger.info("PMManager单例实例已创建")

        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例（仅用于测试）

        警告：
            此方法仅用于测试，生产环境不应调用
        """
        cls._instance = None
        logger.debug("PMManager单例实例已重置")

    async def load_accounts(self) -> int:
        """
        从配置文件加载所有账户

        Returns:
            成功加载的账户数量

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置文件格式错误

        实现细节：
            1. 读取配置文件
            2. 遍历所有账户配置
            3. 验证每个账户配置
            4. 创建PM实例或记录失败
            5. 发布 pm.manager.ready 事件
            6. 返回成功数量

        异常处理：
            - 配置文件不存在：记录错误并抛出异常
            - JSON格式错误：记录错误并抛出异常
            - 单个账户验证失败：记录错误并继续
        """
        logger.info(f"开始加载账户配置: {self._config_path}")

        # 1. 读取配置文件
        config_path = Path(self._config_path)
        if not config_path.exists():
            error_msg = f"配置文件不存在: {self._config_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            error_msg = f"配置文件JSON格式错误: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 2. 验证配置结构
        if "users" not in config_data:
            error_msg = "配置文件缺少'users'字段"
            logger.error(error_msg)
            raise ValueError(error_msg)

        users = config_data["users"]
        logger.info(f"配置文件中共有 {len(users)} 个账户")

        # 3. 遍历所有账户配置
        loaded_count = 0
        for user_id, user_config in users.items():
            try:
                # 验证配置
                if not self._validate_account_config(user_id, user_config):
                    # 验证失败，发布失败事件
                    error_msg = self._failed_accounts.get(user_id, "配置验证失败")
                    await self._publish_load_failed_event(user_id, error_msg)
                    continue

                # 创建PM实例（初始化时会自动发布account.loaded事件）
                pm = PM(user_id=user_id, config=user_config, event_bus=self._event_bus)

                # 保存PM实例
                self._pm_instances[user_id] = pm
                loaded_count += 1

                logger.info(f"账户加载成功: user_id={user_id}, name={user_config.get('name')}")

            except Exception as e:
                # 记录失败
                error_msg = str(e)
                self._failed_accounts[user_id] = error_msg
                logger.error(f"账户加载失败: user_id={user_id}, error={error_msg}")

                # 发布加载失败事件
                await self._publish_load_failed_event(user_id, error_msg)

        # 4. 发布管理器就绪事件
        await self._publish_manager_ready_event(loaded_count)

        logger.info(f"账户加载完成: 成功={loaded_count}, 失败={len(self._failed_accounts)}")
        return loaded_count

    def _validate_account_config(self, user_id: str, config: Dict[str, Any]) -> bool:
        """
        验证账户配置（私有方法）

        Args:
            user_id: 用户ID
            config: 账户配置

        Returns:
            验证是否通过

        验证规则：
            - name: 必需，非空字符串
            - api_key: 必需，非空字符串
            - api_secret: 必需，非空字符串
            - strategy: 必需，非空字符串
            - testnet: 可选，布尔类型，默认False

        实现细节：
            - 验证失败时记录到_failed_accounts
            - 返回False表示验证失败
        """
        required_fields = ["name", "api_key", "api_secret", "strategy"]

        # 检查必需字段
        for field in required_fields:
            if field not in config:
                error_msg = f"缺少必需字段: {field}"
                self._failed_accounts[user_id] = error_msg
                logger.warning(f"账户配置验证失败: user_id={user_id}, {error_msg}")
                return False

            if not isinstance(config[field], str):
                error_msg = f"字段必须是字符串类型: {field}"
                self._failed_accounts[user_id] = error_msg
                logger.warning(f"账户配置验证失败: user_id={user_id}, {error_msg}")
                return False

            if not config[field].strip():
                error_msg = f"字段不能为空: {field}"
                self._failed_accounts[user_id] = error_msg
                logger.warning(f"账户配置验证失败: user_id={user_id}, {error_msg}")
                return False

        # 检查testnet字段类型
        if "testnet" in config and not isinstance(config["testnet"], bool):
            error_msg = "testnet字段必须是布尔类型"
            self._failed_accounts[user_id] = error_msg
            logger.warning(f"账户配置验证失败: user_id={user_id}, {error_msg}")
            return False

        return True

    async def _publish_load_failed_event(self, user_id: str, error: str) -> None:
        """
        发布账户加载失败事件（私有方法）

        Args:
            user_id: 用户ID
            error: 错误信息
        """
        event = Event(
            subject=PMEvents.LOAD_FAILED,
            data={
                "user_id": user_id,
                "error": error
            },
            source="PMManager"
        )

        await self._event_bus.publish(event)

    async def _publish_manager_ready_event(self, loaded_count: int) -> None:
        """
        发布管理器就绪事件（私有方法）

        Args:
            loaded_count: 成功加载的账户数量
        """
        event = Event(
            subject=PMEvents.MANAGER_READY,
            data={
                "loaded_count": loaded_count,
                "failed_count": len(self._failed_accounts),
                "user_ids": list(self._pm_instances.keys())
            },
            source="PMManager"
        )

        await self._event_bus.publish(event)
        logger.info(f"PM管理器就绪: loaded={loaded_count}, failed={len(self._failed_accounts)}")

    # ==================== 查询接口 ====================

    def get_pm(self, user_id: str) -> Optional[PM]:
        """
        根据用户ID获取PM实例

        Args:
            user_id: 用户ID

        Returns:
            PM实例，不存在返回None

        使用方式：
            pm = manager.get_pm("user_001")
            if pm:
                api_key, api_secret = pm.get_api_credentials()
        """
        return self._pm_instances.get(user_id)

    def get_all_user_ids(self) -> List[str]:
        """
        获取所有已加载账户的用户ID列表

        Returns:
            用户ID列表

        使用方式：
            user_ids = manager.get_all_user_ids()
            for user_id in user_ids:
                pm = manager.get_pm(user_id)
        """
        return list(self._pm_instances.keys())

    def get_all_pms(self) -> Dict[str, PM]:
        """
        获取所有PM实例

        Returns:
            用户ID到PM实例的映射字典

        使用方式：
            pms = manager.get_all_pms()
            for user_id, pm in pms.items():
                print(f"{user_id}: {pm.name}")
        """
        return self._pm_instances.copy()

    def get_pm_count(self) -> int:
        """
        获取已加载的PM实例数量

        Returns:
            PM实例数量
        """
        return len(self._pm_instances)

    def get_failed_accounts(self) -> Dict[str, str]:
        """
        获取加载失败的账户记录

        Returns:
            用户ID到错误信息的映射字典

        使用方式：
            failed = manager.get_failed_accounts()
            for user_id, error in failed.items():
                print(f"{user_id} 加载失败: {error}")
        """
        return self._failed_accounts.copy()

    def get_failed_count(self) -> int:
        """
        获取加载失败的账户数量

        Returns:
            失败账户数量
        """
        return len(self._failed_accounts)

    # ==================== 系统关闭 ====================

    async def shutdown(self) -> None:
        """
        关闭PM管理器，清理所有资源

        实现细节：
            1. 禁用所有PM实例
            2. 发布 pm.manager.shutdown 事件
            3. 清空PM实例映射
            4. 记录日志

        使用方式：
            await manager.shutdown()
        """
        logger.info(f"开始关闭PM管理器: pm_count={len(self._pm_instances)}")

        # 1. 禁用所有PM实例（不持久化事件，避免数据库已关闭）
        for user_id, pm in self._pm_instances.items():
            if pm.is_enabled:
                await pm.disable(persist=False)
                logger.debug(f"账户已禁用: user_id={user_id}")

        # 2. 发布关闭事件（不持久化，避免数据库已关闭的错误）
        event = Event(
            subject=PMEvents.MANAGER_SHUTDOWN,
            data={
                "pm_count": len(self._pm_instances),
                "message": "PM管理器已关闭"
            },
            source="PMManager"
        )

        await self._event_bus.publish(event, persist=False)

        # 3. 清空PM实例
        pm_count = len(self._pm_instances)
        self._pm_instances.clear()

        logger.info(f"PM管理器已关闭: 已清理 {pm_count} 个PM实例")

    def __repr__(self) -> str:
        """字符串表示"""
        return f"PMManager(loaded={self.get_pm_count()}, failed={self.get_failed_count()})"

