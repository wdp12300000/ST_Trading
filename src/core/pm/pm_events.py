"""
PM模块事件主题常量

定义PM模块发布的所有事件主题，避免硬编码字符串。
遵循事件命名规范：模块.对象.动作

使用方式：
    from src.core.pm.pm_events import PMEvents
    
    event = Event(
        subject=PMEvents.ACCOUNT_LOADED,
        data={"user_id": "user_001", ...}
    )
"""


class PMEvents:
    """
    PM模块事件主题常量类
    
    所有PM相关的事件主题都定义在这里，确保：
    - 避免硬编码字符串
    - 统一事件命名规范
    - 便于维护和查找
    """
    
    # 账户加载成功事件
    # 当PM实例创建成功时发布
    # 数据: user_id, name, api_key, api_secret, strategy, testnet
    ACCOUNT_LOADED = "pm.account.loaded"
    
    # 账户启用事件
    # 当账户被启用时发布
    # 数据: user_id, name, enabled=True
    ACCOUNT_ENABLED = "pm.account.enabled"
    
    # 账户禁用事件
    # 当账户被禁用时发布
    # 数据: user_id, name, enabled=False
    ACCOUNT_DISABLED = "pm.account.disabled"
    
    # PM管理器就绪事件
    # 当所有账户加载完成时发布
    # 数据: loaded_count, failed_count, user_ids
    MANAGER_READY = "pm.manager.ready"
    
    # PM管理器关闭事件
    # 当系统关闭时发布
    # 数据: pm_count, message
    MANAGER_SHUTDOWN = "pm.manager.shutdown"
    
    # 账户加载失败事件（警告级别）
    # 当某个账户配置验证失败时发布
    # 数据: user_id, error
    LOAD_FAILED = "pm.load.failed"

