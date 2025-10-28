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

## PM 模块需求文档

### 简介

PM（Portfolio Manager）模块是量化交易系统的账户管理层，负责从配置文件加载多个币安账户信息，验证配置有效性，并通过事件总线通知其他模块。该模块采用面向对象设计和事件驱动架构（EDA），每个账户由独立的 PM 实例对象管理，实现多实例化的账户管理模式。

### 术语表

- **PM（Portfolio Manager）**: 账户管理类，每个实例负责管理一个交易账户
- **PM 管理器（PM Manager）**: 负责加载配置文件并创建多个 PM 实例的管理类
- **事件总线（Event Bus）**: 系统中用于发布/订阅事件的消息传递机制
- **账户配置（Account Configuration）**: 包含 API 密钥、策略名称等信息的账户设置
- **用户 ID（User ID）**: 唯一标识一个账户的字符串，如 "user_001"
- **策略（Strategy）**: 交易策略的名称标识符
- **测试网（Testnet）**: 币安提供的测试环境，用于模拟交易
- **PM 实例（PM Instance）**: 一个 PM 类的实例对象，管理单个账户

### 需求

#### 需求 1：加载账户配置文件

**用户故事：** 作为系统管理员，我希望 PM 管理器能够从配置文件加载多个账户信息，以便系统能够为每个账户创建独立的 PM 实例。

##### 验收标准

1. WHEN 系统启动时，THE PM 管理器 SHALL 从 `config/pm_config.json` 文件读取账户配置
2. THE PM 管理器 SHALL 解析 JSON 格式的配置文件并提取所有账户信息
3. IF 配置文件不存在，THEN THE PM 管理器 SHALL 记录错误日志并抛出配置文件缺失异常
4. IF 配置文件格式无效，THEN THE PM 管理器 SHALL 记录错误日志并抛出 JSON 解析异常

#### 需求 2：验证账户配置

**用户故事：** 作为系统管理员，我希望 PM 管理器能够验证每个账户配置的有效性，以便及早发现配置错误。

##### 验收标准

1. THE PM 管理器 SHALL 验证每个账户配置包含必需字段：`name`、`api_key`、`api_secret`、`strategy`
2. THE PM 管理器 SHALL 验证 `name` 字段为非空字符串
3. THE PM 管理器 SHALL 验证 `api_key` 字段为非空字符串
4. THE PM 管理器 SHALL 验证 `api_secret` 字段为非空字符串
5. THE PM 管理器 SHALL 验证 `strategy` 字段为非空字符串
6. WHERE `testnet` 字段存在，THE PM 管理器 SHALL 验证其为布尔类型
7. WHERE `testnet` 字段不存在，THE PM 管理器 SHALL 使用默认值 false

#### 需求 3：处理配置错误

**用户故事：** 作为系统管理员，我希望当某个账户配置无效时，系统能够跳过该账户并继续加载其他账户，以便部分配置错误不影响整个系统运行。

##### 验收标准

1. IF 某个账户配置验证失败，THEN THE PM 管理器 SHALL 记录该账户的错误信息
2. IF 某个账户配置验证失败，THEN THE PM 管理器 SHALL 跳过该账户并继续处理下一个账户
3. THE PM 管理器 SHALL 在日志中明确标识哪个用户 ID 的配置加载失败
4. THE PM 管理器 SHALL 记录配置失败的具体原因（如缺少字段、类型错误等）
5. WHEN 所有账户处理完成后，THE PM 管理器 SHALL 返回成功创建的 PM 实例数量

#### 需求 4：创建 PM 实例

**用户故事：** 作为开发者，我希望为每个有效的账户配置创建独立的 PM 实例，以便每个账户由独立对象管理。

##### 验收标准

1. WHEN 账户配置验证成功时，THE PM 管理器 SHALL 创建一个新的 PM 实例
2. THE PM 管理器 SHALL 将用户 ID 传递给 PM 实例
3. THE PM 管理器 SHALL 将账户配置信息传递给 PM 实例
4. THE PM 实例 SHALL 存储其管理的账户的用户 ID
5. THE PM 实例 SHALL 存储其管理的账户的配置信息
6. THE PM 管理器 SHALL 维护用户 ID 到 PM 实例的映射关系

#### 需求 5：发布账户加载事件

**用户故事：** 作为系统开发者，我希望 PM 实例在初始化成功后发布事件，以便其他模块能够响应并初始化相应功能。

##### 验收标准

1. WHEN PM 实例创建成功时，THE PM 实例 SHALL 通过事件总线发布 `pm.account.loaded` 事件
2. THE PM 实例 SHALL 在事件数据中包含用户 ID
3. THE PM 实例 SHALL 在事件数据中包含账户名称
4. THE PM 实例 SHALL 在事件数据中包含策略名称
5. THE PM 实例 SHALL 在事件数据中包含测试网标志
6. THE PM 实例 SHALL 在事件数据中包含 API 密钥信息（用于后续模块使用）

#### 需求 6：提供账户查询接口

**用户故事：** 作为开发者，我希望能够查询已创建的 PM 实例和账户信息，以便在系统运行时获取账户配置。

##### 验收标准

1. THE PM 管理器 SHALL 提供方法获取所有已创建 PM 实例的用户 ID 列表
2. THE PM 管理器 SHALL 提供方法根据用户 ID 获取对应的 PM 实例
3. THE PM 管理器 SHALL 提供方法获取已创建 PM 实例的总数
4. THE PM 实例 SHALL 提供方法获取其管理的账户配置信息
5. IF 查询不存在的用户 ID，THEN THE PM 管理器 SHALL 返回 None 或空值

#### 需求 7：提供账户启用/禁用功能

**用户故事：** 作为系统管理员，我希望能够在运行时启用或禁用特定账户，以便灵活控制哪些账户参与交易。

##### 验收标准

1. THE PM 实例 SHALL 提供方法禁用其管理的账户
2. THE PM 实例 SHALL 提供方法启用其管理的账户
3. WHEN 账户被禁用时，THE PM 实例 SHALL 通过事件总线发布 `pm.account.disabled` 事件
4. WHEN 账户被启用时，THE PM 实例 SHALL 通过事件总线发布 `pm.account.enabled` 事件
5. THE PM 实例 SHALL 维护其账户的启用/禁用状态
6. THE PM 实例 SHALL 提供方法查询其账户的当前状态（启用或禁用）

#### 需求 8：管理加载失败记录

**用户故事：** 作为系统管理员，我希望能够查询哪些账户加载失败及失败原因，以便排查配置问题。

##### 验收标准

1. THE PM 管理器 SHALL 维护加载失败账户的记录
2. THE PM 管理器 SHALL 为每个失败账户存储用户 ID 和错误信息
3. THE PM 管理器 SHALL 提供方法获取所有加载失败账户的用户 ID 列表
4. THE PM 管理器 SHALL 提供方法查询特定用户 ID 的失败原因

#### 需求 9：日志记录

**用户故事：** 作为系统管理员，我希望 PM 模块能够记录详细的操作日志，以便排查问题和监控系统状态。

##### 验收标准

1. THE PM 管理器 SHALL 在开始加载配置时记录信息级别日志
2. THE PM 管理器 SHALL 在每个 PM 实例创建成功时记录信息级别日志
3. THE PM 管理器 SHALL 在账户配置验证失败时记录错误级别日志
4. THE PM 管理器 SHALL 在配置文件读取失败时记录错误级别日志
5. THE PM 管理器 SHALL 在完成所有账户加载后记录汇总信息（成功数量、失败数量）
6. THE PM 实例 SHALL 在初始化时记录信息级别日志
7. THE PM 实例 SHALL 在状态变更时记录信息级别日志
