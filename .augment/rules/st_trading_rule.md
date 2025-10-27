---
type: "manual"
---

#  ！！！重点注意任何设计和编码动作请详细查看并遵照User Guidelines中的规则设定
## 项目概述
这是一个基于 Python 的加密货币量化交易系统，采用事件驱动架构（EDA），专注于币安永续合约交易。
##技术栈
- python
- flask
- SQLite3
- 使用loguru作为日志工具
- 币安官方api

## 其中的一些设计原则
- 使用面向对象设计，充分使用类方法
- 遵守开闭原则 (Open-Closed Principle)，定义: 软件实体应该对扩展开放,对修改关闭。
- 遵守依赖倒置原则 (Dependency Inversion Principle)，定义: 高层模块不应该依赖低层模块,两者都应该依赖抽象。
- 遵守TDD测试驱动开发原则（详细可参考User Guidelines）
- 严格遵守不要过早优化，只做当前需要的事情
- 严格遵守YAGNI原则（You Aren't Gonna Need It）
- 就算是补充遗漏的功能或需求时也要按照TDD测试驱动的规范

## 事件驱动模块（EDA）
### 核心特性
| 特性 | 说明 | 实现方式 |
|------|------|--------|
| **发布/订阅模式** | 模块间通过事件进行解耦通信
| **异步处理** | 所有事件处理都是异步的 
| **通配符订阅** | 支持 `pm.*` 等模式订阅 | fnmatch 模式匹配 |
| **错误隔离** | 一个处理器失败不影响其他 
| **单例模式** | 全局唯一事件总线实例 
| **事件历史** | 数据持久化，记录最近 1000 条事件 
| **数据验证** | 自动验证事件数据有效性 | Event.__post_init__ |

### Event 类结构
    ```python
    @dataclass
    class Event:
        subject: str              # 事件主题（必需）
        data: Dict[str, Any]      # 事件数据（必需）
        event_id: str             # 事件ID（自动生成UUID）
        timestamp: datetime       # 时间戳（自动生成）
        source: Optional[str]     # 事件源模块
    ```

### 术语表

- **EventBus**: 事件总线,负责事件的发布、订阅和分发的核心组件
- **Event**: 事件对象,包含主题、数据、ID、时间戳等信息
- **Publisher**: 发布者,发布事件到事件总线的模块
- **Subscriber**: 订阅者,订阅并处理特定主题事件的模块
- **Subject**: 事件主题,用于标识事件类型的字符串常量
- **Handler**: 处理器,订阅者注册的异步回调函数
- **SQLite3**: 用于事件持久化的轻量级数据库
- **Wildcard Pattern**: 通配符模式,如 `pm.*` 用于批量订阅事件

### 需求 1

**用户故事:** 作为系统开发者,我希望模块之间通过事件进行通信,以便实现松耦合的系统架构

#### 验收标准

1. THE EventBus SHALL 提供发布方法以允许任何模块发布事件
2. THE EventBus SHALL 提供订阅方法以允许任何模块订阅特定主题的事件
3. WHEN 模块发布事件时, THE EventBus SHALL 将事件分发给所有订阅该主题的处理器
4. THE EventBus SHALL 使用事件主题常量而非硬编码字符串进行事件标识
5. THE EventBus SHALL 实现单例模式以确保全局唯一实例

### 需求 2

**用户故事:** 作为系统开发者,我希望事件处理是异步的,以便不阻塞主线程和提高系统性能

#### 验收标准

1. THE EventBus SHALL 异步执行所有事件处理器
2. WHEN 事件被发布时, THE EventBus SHALL 立即返回而不等待处理器完成
3. THE EventBus SHALL 支持异步处理器函数的注册
4. THE EventBus SHALL 使用 asyncio 实现异步事件分发

### 需求 3

**用户故事:** 作为系统开发者,我希望支持通配符订阅,以便批量订阅相关事件

#### 验收标准

1. THE EventBus SHALL 支持使用通配符模式订阅事件
2. WHEN 订阅者使用模式如 `pm.*` 时, THE EventBus SHALL 匹配所有以 `pm.` 开头的事件主题
3. THE EventBus SHALL 使用 fnmatch 模式匹配实现通配符功能
4. THE EventBus SHALL 同时支持精确主题订阅和通配符模式订阅

### 需求 4

**用户故事:** 作为系统开发者,我希望事件处理器的错误被隔离,以便一个处理器失败不影响其他处理器

#### 验收标准

1. WHEN 事件处理器抛出异常时, THE EventBus SHALL 捕获该异常
2. THE EventBus SHALL 记录处理器异常信息到日志
3. THE EventBus SHALL 继续执行其他订阅该事件的处理器
4. THE EventBus SHALL 确保单个处理器失败不影响事件总线的正常运行

### 需求 5

**用户故事:** 作为系统开发者,我希望事件被持久化存储,以便进行历史查询和系统审计

#### 验收标准

1. THE EventBus SHALL 使用 SQLite3 数据库持久化所有事件
2. WHEN 事件被发布时, THE EventBus SHALL 将事件信息存储到数据库
3. THE EventBus SHALL 保留最近 1000 条事件记录
4. THE EventBus SHALL 提供查询历史事件的方法
5. THE EventBus SHALL 存储事件的主题、数据、ID、时间戳和来源信息

### 需求 6

**用户故事:** 作为系统开发者,我希望事件数据在创建时被验证,以便确保数据完整性和有效性

#### 验收标准

1. THE Event SHALL 在初始化时自动验证必需字段
2. THE Event SHALL 要求 subject 和 data 字段为必需参数
3. WHEN Event 被创建时, THE Event SHALL 自动生成唯一的 event_id
4. WHEN Event 被创建时, THE Event SHALL 自动生成当前时间戳
5. THE Event SHALL 使用 dataclass 实现数据验证

### 需求 7

**用户故事:** 作为系统开发者,我希望使用面向对象设计,以便代码结构清晰且易于维护

#### 验收标准

1. THE EventBus SHALL 使用类方法实现所有核心功能
2. THE Event SHALL 使用 dataclass 定义数据结构
3. THE EventBus SHALL 封装事件订阅、发布和持久化逻辑
4. THE EventBus SHALL 提供清晰的公共接口方法
