# PM模块 (Portfolio Manager)

## 📋 模块概述

PM模块负责管理多个交易账户，为每个账户提供独立的配置管理和状态控制。采用事件驱动架构，与系统其他模块通过EventBus进行通信。

## 🏗️ 架构设计

### 核心类

#### 1. PM类（单账户管理）
- **职责**：管理单个交易账户的配置和状态
- **实例化**：每个交易账户对应一个PM实例
- **生命周期**：随Python对象自动回收，无需手动关闭

#### 2. PMManager类（多账户管理器）
- **职责**：管理所有PM实例的生命周期
- **模式**：单例模式，全局唯一实例
- **功能**：配置加载、验证、实例创建、系统关闭

#### 3. PMEvents类（事件常量）
- **职责**：定义PM模块所有事件主题常量
- **优势**：避免硬编码字符串，提供IDE自动补全

## 📦 模块结构

```
src/core/pm/
├── __init__.py          # 模块导出
├── pm.py                # PM类实现
├── pm_manager.py        # PMManager类实现
├── pm_events.py         # 事件常量定义
└── README.md            # 本文档
```

## 🔄 事件流程

### 系统启动流程

```
1. 创建PMManager实例
   ↓
2. 调用load_accounts()加载配置
   ↓
3. 读取config/pm_config.json
   ↓
4. 验证每个账户配置
   ├─ 成功 → 创建PM实例 → 发布pm.account.loaded
   └─ 失败 → 记录错误 → 发布pm.load.failed
   ↓
5. 所有账户处理完成
   ↓
6. 发布pm.manager.ready
```

### 系统关闭流程

```
1. 调用PMManager.shutdown()
   ↓
2. 禁用所有PM实例
   ├─ 调用pm.disable() → 发布pm.account.disabled
   ↓
3. 清空PM实例映射
   ↓
4. 发布pm.manager.shutdown
```

## 📡 事件定义

### PM实例事件

| 事件主题 | 触发时机 | 数据内容 |
|---------|---------|---------|
| `pm.account.loaded` | PM实例初始化完成 | user_id, name, api_key, api_secret, strategy, testnet |
| `pm.account.enabled` | 账户被启用 | user_id, name, enabled=true |
| `pm.account.disabled` | 账户被禁用 | user_id, name, enabled=false |

### PMManager事件

| 事件主题 | 触发时机 | 数据内容 |
|---------|---------|---------|
| `pm.manager.ready` | 所有账户加载完成 | loaded_count, failed_count, user_ids |
| `pm.manager.shutdown` | 管理器关闭完成 | pm_count, message |
| `pm.load.failed` | 账户加载失败（警告） | user_id, error |

## 🔧 使用示例

### 初始化PM管理器

```python
from src.core.event_bus import EventBus
from src.core.pm import PMManager

# 获取EventBus实例
event_bus = EventBus.get_instance()

# 获取PMManager实例（单例）
pm_manager = PMManager.get_instance(
    event_bus=event_bus,
    config_path="config/pm_config.json"
)

# 加载所有账户
loaded_count = await pm_manager.load_accounts()
print(f"成功加载 {loaded_count} 个账户")
```

### 获取PM实例

```python
# 通过user_id获取PM实例
pm = pm_manager.get_pm("user_001")

# 获取账户信息
print(f"账户名称: {pm.name}")
print(f"策略: {pm.strategy}")
print(f"测试网: {pm.is_testnet}")
print(f"启用状态: {pm.is_enabled}")

# 获取API凭证
api_key, api_secret = pm.get_api_credentials()

# 获取完整配置（含敏感信息）
full_config = pm.get_full_config()
```

### 启用/禁用账户

```python
# 禁用账户
await pm.disable()

# 启用账户
await pm.enable()
```

### 订阅PM事件

```python
async def on_account_loaded(event):
    print(f"账户加载: {event.data['name']}")

async def on_manager_ready(event):
    print(f"管理器就绪: {event.data['loaded_count']} 个账户")

# 订阅事件
event_bus.subscribe(PMEvents.ACCOUNT_LOADED, on_account_loaded)
event_bus.subscribe(PMEvents.MANAGER_READY, on_manager_ready)
```

### 系统关闭

```python
# 关闭PM管理器
await pm_manager.shutdown()
```

## ⚙️ 配置文件格式

`config/pm_config.json`:

```json
{
  "users": {
    "user_001": {
      "name": "主账户",
      "api_key": "your_api_key",
      "api_secret": "your_api_secret",
      "strategy": "ma_stop_st",
      "testnet": false
    },
    "user_002": {
      "name": "测试账户",
      "api_key": "test_api_key",
      "api_secret": "test_api_secret",
      "strategy": "test_strategy",
      "testnet": true
    }
  }
}
```

### 配置字段说明

| 字段 | 类型 | 必需 | 说明 |
|-----|------|------|------|
| `name` | string | ✅ | 账户名称 |
| `api_key` | string | ✅ | Binance API密钥 |
| `api_secret` | string | ✅ | Binance API密钥 |
| `strategy` | string | ✅ | 使用的策略名称 |
| `testnet` | boolean | ❌ | 是否使用测试网（默认false） |

## 🔒 安全设计

1. **API密钥保护**
   - API密钥只在PM实例内部保存
   - 通过`get_api_credentials()`方法获取
   - 事件中传递完整凭证（供其他模块使用）

2. **配置验证**
   - 加载时验证所有必需字段
   - 验证失败不影响其他账户
   - 发布告警事件通知失败

3. **错误隔离**
   - 单个账户失败不影响其他账户
   - 所有错误都记录日志
   - 关键操作发布告警事件

## 📊 测试覆盖

### 测试统计
- **总测试数**: 38个
- **单元测试**: 33个（PM类16个 + PMManager类17个）
- **集成测试**: 5个
- **测试覆盖率**: 89%

### 测试文件
- `tests/unit/test_pm.py` - PM类单元测试
- `tests/unit/test_pm_manager.py` - PMManager类单元测试
- `tests/integration/test_pm_integration.py` - PM模块集成测试

### 运行测试

```bash
# 运行所有PM模块测试
pytest tests/unit/test_pm.py tests/unit/test_pm_manager.py tests/integration/test_pm_integration.py -v

# 生成覆盖率报告
pytest --cov=src/core/pm --cov-report=html tests/unit/test_pm.py tests/unit/test_pm_manager.py tests/integration/test_pm_integration.py
```

## 🎯 设计原则

### 面向对象设计
- ✅ 充分使用类方法和属性
- ✅ 封装内部实现细节
- ✅ 提供清晰的公共接口

### SOLID原则
- ✅ **单一职责**：PM管理单账户，PMManager管理多实例
- ✅ **开闭原则**：对扩展开放，对修改关闭
- ✅ **依赖倒置**：依赖EventBus抽象，不依赖具体实现

### 其他原则
- ✅ **YAGNI**：只实现当前需要的功能
- ✅ **DRY**：避免重复代码
- ✅ **TDD**：测试驱动开发，先写测试再写代码

## 📝 日志规范

所有日志遵循项目统一规范：
- 使用Loguru记录日志
- 包含文件名和行号
- 使用中文描述
- 分级记录：DEBUG、INFO、WARNING、ERROR、CRITICAL

## 🔗 依赖关系

```
PM模块
  ├─ 依赖: EventBus（事件总线）
  ├─ 依赖: Event（事件对象）
  └─ 被依赖: 策略模块、交易模块、风控模块等
```

## 📅 版本历史

- **v1.0.0** (2025-10-27)
  - ✅ PM类实现（单账户管理）
  - ✅ PMManager类实现（多账户管理）
  - ✅ 事件驱动架构
  - ✅ 完整的单元测试和集成测试
  - ✅ 89%测试覆盖率

