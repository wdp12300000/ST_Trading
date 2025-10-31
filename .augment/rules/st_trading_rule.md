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

## DE 数据引擎模块需求文档

### 简介

DE（Data Engine）数据引擎是量化交易系统的核心数据层，负责管理币安永续合约的所有数据交互，包括 REST API 客户端管理、WebSocket 实时数据订阅、历史数据获取、订单执行和用户数据流管理。该模块采用事件驱动架构（EDA），通过发布/订阅模式与其他模块（PM、TA）进行通信。

### 术语表

- **DE_Module**：数据引擎模块，本需求文档描述的系统
- **DEManager**：DE模块管理器，单例模式，管理所有账户的客户端和连接
- **Binance_API**：币安永续合约官方 REST API
- **BinanceClient**：币安REST API客户端类，每个账户一个实例
- **WebSocket_Connection**：币安 WebSocket 实时数据连接
- **MarketWebSocket**：市场数据WebSocket连接，每个账户独立
- **UserDataWebSocket**：用户数据流WebSocket连接，每个账户独立
- **Event_Bus**：系统事件总线，用于模块间异步通信
- **PM_Module**：投资组合管理模块
- **TA_Module**：技术分析模块
- **Trading_Module**：交易执行模块
- **User_Data_Stream**：币安用户数据流，用于接收账户和订单更新
- **ListenKey**：币安用户数据流的认证密钥
- **Kline**：K线数据（蜡烛图数据）

- **Order_Type**：订单类型（市价单、限价单、止损单、止盈单等）
- **API_Key**：币安 API 访问密钥
- **API_Secret**：币安 API 访问密钥对应的密钥

### DE模块事件定义

DE模块通过事件总线与其他模块通信，以下是所有相关事件的定义：

#### 订阅的事件（输入）

| 事件主题 | 发布者 | 数据格式 | 说明 |
|---------|--------|---------|------|
| `pm.account.loaded` | PM模块 | `{user_id, name, api_key, api_secret, strategy, testnet}` | 账户加载完成，触发客户端创建 |
| `de.subscribe.kline` | 策略模块 | `{user_id, symbol, interval}` | 订阅K线数据流 |
| `de.get_historical_klines` | 策略模块/TA模块 | `{user_id, symbol, interval, limit}` | 获取历史K线数据 |
| `trading.order.create` | Trading模块 | `{user_id, symbol, side, order_type, quantity, price?, stopPrice?}` | 创建订单 |
| `trading.order.cancel` | Trading模块 | `{user_id, symbol, order_id}` | 取消订单 |
| `trading.get_account_balance` | Trading模块 | `{user_id, asset}` | 查询账户余额 |

#### 发布的事件（输出）

| 事件主题 | 触发时机 | 数据格式 | 说明 |
|---------|---------|---------|------|
| `de.client.connected` | 客户端创建成功 | `{user_id, testnet, timestamp}` | 客户端连接成功 |
| `de.client.connection_failed` | 客户端创建失败 | `{user_id, error_type, error_message}` | 客户端连接失败 |
| `de.websocket.connected` | WebSocket连接成功 | `{user_id, connection_type, timestamp}` | WebSocket连接成功 |
| `de.websocket.disconnected` | WebSocket断开 | `{user_id, connection_type, reason}` | WebSocket连接断开 |
| `de.kline.update` | 收到K线数据 | `{user_id, symbol, interval, kline: {open, high, low, close, volume, timestamp, is_closed}}` | K线数据更新 |
| `de.historical_klines.success` | 历史数据获取成功 | `{user_id, symbol, interval, klines: [...]}` | 历史K线获取成功 |
| `de.historical_klines.failed` | 历史数据获取失败 | `{user_id, symbol, interval, error}` | 历史K线获取失败 |
| `de.order.submitted` | 订单提交成功 | `{user_id, order_id, symbol, side, type, quantity, price}` | 订单提交成功 |
| `de.order.failed` | 订单提交失败 | `{user_id, symbol, error, retry_count}` | 订单提交失败 |
| `de.order.cancelled` | 订单取消成功 | `{user_id, order_id, symbol}` | 订单已取消 |
| `de.order.filled` | 订单成交 | `{user_id, order_id, symbol, price, quantity, timestamp}` | 订单已成交 |
| `de.order.update` | 订单状态变化 | `{user_id, order_id, status, filled_quantity, remaining_quantity}` | 订单状态更新 |
| `de.account.balance` | 账户余额查询成功 | `{user_id, asset, available_balance}` | 账户余额信息 |
| `de.position.update` | 持仓更新 | `{user_id, symbol, side, quantity, unrealized_pnl, entry_price}` | 持仓更新 |
| `de.account.update` | 账户更新 | `{user_id, total_equity, available_balance, margin_used}` | 账户更新 |
| `de.user_stream.started` | 用户数据流启动 | `{user_id, listen_key}` | 用户数据流启动成功 |

### 需求

#### 需求 1：币安客户端管理

**用户故事：** 作为系统管理员，我希望 DE 模块能够管理币安 API 客户端的生命周期，以便系统能够与币安交易所进行真实场景的实盘测试。

##### 验收标准

1. WHEN DE_Module 接收到 `pm.account.loaded` 事件，THE DE_Module SHALL 从事件数据中提取 user_id、api_key 和 api_secret
2. WHEN 提取参数成功，THE DE_Module SHALL 为该账户创建 BinanceClient 实例
3. THE BinanceClient SHALL 使用币安正式网API端点（https://fapi.binance.com），不使用测试网
4. WHEN BinanceClient 创建成功，THE DE_Module SHALL 发布 `de.client.connected` 事件，事件数据包含 user_id 和时间戳
5. WHEN BinanceClient 创建失败，THE DE_Module SHALL 发布 `de.client.connection_failed` 事件，事件数据包含 user_id、错误类型和错误消息
6. THE DE_Module SHALL 直接调用币安官方 REST API，不依赖币安官方以外的第三方封装库（如python-binance），但可以使用标准HTTP客户端库（如aiohttp、httpx）
7. THE DE_Module SHALL 维护 user_id 到 BinanceClient 实例的映射关系
8. THE DE_Module SHALL 支持同时管理多个账户的 BinanceClient 实例
9. WHEN DE_Module 需要断开 BinanceClient，THE DE_Module SHALL 关闭所有活跃的连接并释放相关资源

#### 需求 2：WebSocket K线数据订阅

**用户故事：** 作为交易策略开发者，我希望实时接收 K线数据更新，以便策略能够基于最新市场数据做出决策。

##### 验收标准

1. WHEN DE_Module 成功创建 BinanceClient 后，THE DE_Module SHALL 为该账户建立独立的 MarketWebSocket 连接到币安市场数据流
2. WHEN MarketWebSocket 连接成功，THE DE_Module SHALL 发布 `de.websocket.connected` 事件，事件数据包含 user_id、connection_type（market）和时间戳
3. WHEN DE_Module 接收到 `de.subscribe.kline` 事件，THE DE_Module SHALL 从事件数据中提取 user_id、symbol（交易对）和 interval（时间周期）参数
4. WHEN 提取参数成功，THE DE_Module SHALL 通过该账户的 MarketWebSocket 订阅指定交易对和时间周期的 K线数据流
5. WHEN MarketWebSocket 接收到新的 Kline 数据，THE DE_Module SHALL 直接发布 `de.kline.update` 事件，事件数据包含 user_id、symbol、interval 和完整的 K线信息（open、high、low、close、volume、timestamp、is_closed）
6. THE DE_Module SHALL NOT 在内存中缓存 K线数据，以避免断线数据不齐等复杂问题
7. WHEN MarketWebSocket 断开，THE DE_Module SHALL 发布 `de.websocket.disconnected` 事件并立即尝试重新建立连接
8. WHEN MarketWebSocket 重连成功，THE DE_Module SHALL 恢复之前的所有订阅配置
9. THE DE_Module SHALL 支持每个账户同时订阅多个交易对和时间周期的 K线数据流
10. THE DE_Module SHALL 确保不同账户的 MarketWebSocket 连接相互独立

#### 需求 3：历史K线数据获取

**用户故事：** 作为技术分析模块，我需要获取历史 K线数据，以便计算技术指标和回测策略。

##### 验收标准

1. WHEN DE_Module 接收到 `de.get_historical_klines` 事件，THE DE_Module SHALL 从事件数据中提取 user_id、symbol（交易对）、interval（时间周期）和 limit（K线数量）参数
2. WHEN DE_Module 提取参数成功，THE DE_Module SHALL 使用对应账户的 BinanceClient 通过 REST API 请求指定数量的最新历史 Kline 数据
3. WHEN 历史 Kline 数据获取成功，THE DE_Module SHALL 发布 `de.historical_klines.success` 事件，事件数据包含 user_id、symbol、interval 和所有 K线记录
4. WHEN 历史 Kline 数据获取失败，THE DE_Module SHALL 发布 `de.historical_klines.failed` 事件，事件数据包含 user_id、symbol、interval 和错误信息
5. THE DE_Module SHALL 每次请求时从币安服务器重新获取历史数据，不使用本地缓存

#### 需求 4：订单执行管理

**用户故事：** 作为交易执行模块，我需要提交和管理订单，以便执行交易策略的买卖决策。

##### 验收标准

1. THE DE_Module SHALL 订阅 `trading.order.create` 事件以接收来自 Trading 模块的下单请求
2. WHEN DE_Module 接收到 `trading.order.create` 事件，THE DE_Module SHALL 从事件数据中提取 user_id、symbol、side（BUY/SELL）、order_type、quantity 和可选的 price、stopPrice 参数
3. THE DE_Module SHALL 支持所有币安永续合约 Order_Type（MARKET、LIMIT、STOP、TAKE_PROFIT、STOP_MARKET、TAKE_PROFIT_MARKET）
4. WHEN 提取参数成功，THE DE_Module SHALL 使用对应账户的 BinanceClient 通过 REST API 提交订单到币安交易所
5. WHEN 订单提交成功，THE DE_Module SHALL 发布 `de.order.submitted` 事件，事件数据包含 user_id、order_id、symbol、side、type、quantity 和 price
6. WHEN 订单提交失败，THE DE_Module SHALL 自动重试提交订单最多 3 次
7. WHEN 订单重试 3 次后仍然失败，THE DE_Module SHALL 发布 `de.order.failed` 事件，事件数据包含 user_id、symbol、error 和 retry_count
8. THE DE_Module SHALL 订阅 `trading.order.cancel` 事件以接收撤单请求
9. WHEN DE_Module 接收到 `trading.order.cancel` 事件，THE DE_Module SHALL 从事件数据中提取 user_id、symbol 和 order_id 参数
10. WHEN 订单撤销成功，THE DE_Module SHALL 发布 `de.order.cancelled` 事件，事件数据包含 user_id、order_id 和 symbol

#### 需求 5：订单状态更新

**用户故事：** 作为风险管理模块，我需要实时了解订单状态变化，以便监控交易执行情况和管理风险敞口。

##### 验收标准

1. WHEN UserDataWebSocket 接收到订单成交通知，THE DE_Module SHALL 发布 `de.order.filled` 事件，事件数据包含 user_id、order_id、symbol、price、quantity 和 timestamp
2. WHEN UserDataWebSocket 接收到订单状态变化通知，THE DE_Module SHALL 发布 `de.order.update` 事件，事件数据包含 user_id、order_id、status、filled_quantity 和 remaining_quantity
3. THE DE_Module SHALL 通过 UserDataWebSocket 实时接收所有订单状态更新，无人为延迟
4. THE DE_Module SHALL 确保订单更新事件包含足够的信息供其他模块使用，无需额外查询

#### 需求 6：账户信息管理

**用户故事：** 作为投资组合管理模块，我需要查询账户余额和持仓信息，以便进行资金管理和仓位控制。

##### 验收标准

1. THE DE_Module SHALL 订阅 `trading.get_account_balance` 事件以接收来自 Trading 模块的账户余额查询请求
2. WHEN DE_Module 接收到 `trading.get_account_balance` 事件，THE DE_Module SHALL 从事件数据中提取 user_id 和 asset（保证金资产类型，如 USDT 或 USDC）
3. WHEN 提取参数成功，THE DE_Module SHALL 使用对应账户的 BinanceClient 通过 REST API 查询指定资产的可用保证金余额
4. WHEN 账户余额查询成功，THE DE_Module SHALL 发布 `de.account.balance` 事件，事件数据包含 user_id、asset 和 available_balance
5. WHEN UserDataWebSocket 接收到持仓更新通知，THE DE_Module SHALL 发布 `de.position.update` 事件，事件数据包含 user_id、symbol、side、quantity、unrealized_pnl 和 entry_price
6. WHEN UserDataWebSocket 接收到账户更新通知，THE DE_Module SHALL 发布 `de.account.update` 事件，事件数据包含 user_id、total_equity、available_balance 和 margin_used

#### 需求 7：用户数据流管理

**用户故事：** 作为系统运维人员，我需要确保用户数据流持续有效，以便系统能够实时接收账户和订单更新。

##### 验收标准

1. WHEN DE_Module 成功创建 BinanceClient 后，THE DE_Module SHALL 自动启动该账户的用户数据流
2. WHEN 启动用户数据流时，THE DE_Module SHALL 使用 BinanceClient 通过 REST API 创建 ListenKey
3. WHEN ListenKey 创建成功，THE DE_Module SHALL 建立 UserDataWebSocket 连接到用户数据流端点
4. WHEN UserDataWebSocket 连接成功，THE DE_Module SHALL 发布 `de.user_stream.started` 事件，事件数据包含 user_id 和 listen_key
5. THE DE_Module SHALL 每 30 分钟通过 BinanceClient 发送 keepalive 请求以延长 ListenKey 有效期
6. WHEN UserDataWebSocket 断开，THE DE_Module SHALL 发布 `de.websocket.disconnected` 事件并立即重新建立连接
7. WHEN UserDataWebSocket 重连时，THE DE_Module SHALL 重新创建 ListenKey 并建立新的连接
8. THE DE_Module SHALL 确保 UserDataWebSocket 实时推送币安的账户和订单更新，无人为延迟

#### 需求 8：错误处理和恢复

**用户故事：** 作为系统可靠性工程师，我需要系统能够处理各种异常情况并自动恢复，以确保交易系统的稳定运行。

##### 验收标准

1. WHEN BinanceClient 的 REST API 请求返回网络错误，THE DE_Module SHALL 记录 ERROR 级别日志并发布相应的失败事件
2. WHEN WebSocket 接收到无效数据格式，THE DE_Module SHALL 记录 WARNING 级别日志并继续处理后续数据
3. WHEN DE_Module 检测到 API_Key 或 API_Secret 无效，THE DE_Module SHALL 发布 `de.client.connection_failed` 事件，事件数据包含 user_id 和认证失败信息
4. WHEN 订单执行遇到余额不足错误，THE DE_Module SHALL 发布 `de.order.failed` 事件，事件数据明确标识余额不足原因
5. WHEN WebSocket 连接失败超过 5 次，THE DE_Module SHALL 记录 CRITICAL 级别日志并发布告警事件
6. THE DE_Module SHALL 为所有异常情况提供清晰的错误消息，包含 user_id、错误类型、错误代码和可读的中文错误描述
7. THE DE_Module SHALL 确保单个账户的错误不影响其他账户的正常运行

#### 需求 9：事件驱动集成

**用户故事：** 作为系统架构师，我需要 DE 模块通过事件总线与其他模块解耦通信，以便系统具有良好的可扩展性和可维护性。

##### 验收标准

1. THE DE_Module SHALL 通过 Event_Bus 订阅 `pm.account.loaded` 事件以接收来自 PM_Module 的账户加载通知
2. THE DE_Module SHALL 通过 Event_Bus 订阅 `de.subscribe.kline` 事件以接收 K线订阅请求
3. THE DE_Module SHALL 通过 Event_Bus 订阅 `de.get_historical_klines` 事件以接收历史数据请求
4. THE DE_Module SHALL 通过 Event_Bus 订阅 `trading.order.create` 事件以接收来自 Trading_Module 的下单请求
5. THE DE_Module SHALL 通过 Event_Bus 订阅 `trading.order.cancel` 事件以接收撤单请求
6. THE DE_Module SHALL 通过 Event_Bus 订阅 `trading.get_account_balance` 事件以接收账户余额查询请求
7. THE DE_Module SHALL 通过 Event_Bus 发布所有输出事件（连接状态、数据更新、订单状态、账户更新）
8. THE DE_Module SHALL 使用面向对象设计，将所有功能封装在类方法中
9. THE DE_Module SHALL 使用单例模式实现 DEManager 类，确保全局唯一实例
10. THE DE_Module SHALL 遵循 YAGNI 原则，仅实现当前需要的功能，不进行过早优化

#### 需求 10：API密钥管理

**用户故事：** 作为系统架构师，我需要确保 API 密钥的安全管理和正确使用，以便在真实市场环境中进行实盘测试（通过控制交易数额降低风险）。

##### 验收标准

1. THE DE_Module SHALL NOT 维护独立的配置文件存储 API 密钥
2. THE DE_Module SHALL 从 PM_Module 发布的 `pm.account.loaded` 事件中获取 api_key 和 api_secret
3. THE DE_Module SHALL 将接收到的 api_key 和 api_secret 传递给 BinanceClient，连接到币安正式网进行真实场景测试
4. THE DE_Module SHALL 确保 API 密钥仅在内存中存储，不写入日志或持久化存储
5. THE DE_Module SHALL 在日志中记录 API 操作时，仅记录 user_id，不记录 api_key 或 api_secret
6. THE DE_Module SHALL 支持同时管理多个账户的不同 API 密钥，确保密钥不会混淆
7. THE DE_Module SHALL 通过 PM_Module 配置的交易数额限制来控制风险，而不是使用测试网

#### 需求 11：日志记录

**用户故事：** 作为系统管理员，我希望 DE 模块能够记录详细的操作日志，以便排查问题和监控系统状态。

##### 验收标准

1. THE DE_Module SHALL 在创建 BinanceClient 时记录 INFO 级别日志，包含 user_id 和 testnet 标志
2. THE DE_Module SHALL 在 WebSocket 连接建立时记录 INFO 级别日志，包含 user_id 和连接类型（market/user_data）
3. THE DE_Module SHALL 在 WebSocket 断开时记录 WARNING 级别日志，包含 user_id、连接类型和断开原因
4. THE DE_Module SHALL 在订单提交时记录 INFO 级别日志，包含 user_id、symbol、side 和 order_type
5. THE DE_Module SHALL 在订单成交时记录 INFO 级别日志，包含 user_id、order_id 和成交价格
6. THE DE_Module SHALL 在 API 请求失败时记录 ERROR 级别日志，包含 user_id、请求类型和错误详情
7. THE DE_Module SHALL 在 WebSocket 重连时记录 INFO 级别日志，包含 user_id、连接类型和重连次数
8. THE DE_Module SHALL 在所有日志中包含文件名和行号，遵循项目日志规范
9. THE DE_Module SHALL 使用 Loguru 记录所有日志，日志语言为中文

#### 需求 12：多账户管理

**用户故事：** 作为系统架构师，我需要 DE 模块能够同时管理多个交易账户，以便支持多账户交易策略。

##### 验收标准

1. THE DE_Module SHALL 使用单例模式实现 DEManager 类，作为全局唯一的 DE 模块管理器
2. THE DE_Module SHALL 为每个账户创建独立的 BinanceClient 实例
3. THE DE_Module SHALL 维护 user_id 到 BinanceClient 实例的映射关系
4. THE DE_Module SHALL 为每个账户建立独立的 MarketWebSocket 连接
5. THE DE_Module SHALL 为每个账户建立独立的 UserDataWebSocket 连接
6. THE DE_Module SHALL 确保不同账户的操作相互隔离，一个账户的错误不影响其他账户
7. THE DE_Module SHALL 提供方法查询所有已创建客户端的 user_id 列表
8. THE DE_Module SHALL 提供方法根据 user_id 获取对应的 BinanceClient 实例
9. WHEN 系统关闭时，THE DE_Module SHALL 优雅关闭所有账户的 WebSocket 连接和 BinanceClient


## ST 策略执行模块需求文档

### 简介

ST（Strategy Execution）模块是量化交易系统的策略执行核心模块,负责加载策略配置、管理策略实例、处理指标信号、生成交易信号、获取持仓状态以及对入场及出场订单成交事件作出反应。该模块采用事件驱动架构(EDA),通过事件总线与其他模块(PM、TA、TR)进行解耦通信。

### 术语表

- **ST 模块**: Strategy Execution 模块,策略执行模块
- **PM 模块**: Portfolio Management 模块,账户管理模块
- **TA 模块**: Technical Analysis 模块,技术分析/指标模块
- **TR 模块**: Trading 模块,交易执行模块
- **事件总线**: 系统中用于发布/订阅事件的消息中间件
- **策略实例**: 根据策略配置及具体策略文件创建的具体策略对象
- **指标信号**: TA 模块计算并发布的技术指标数据和信号
- **交易信号**: ST 模块根据策略逻辑生成的买入/卖出信号
- **持仓状态**: 策略中每个交易对的当前持仓信息
- **网格交易**: 在特定价格区间内设置多个买卖订单的交易策略
- **入场订单**: 开仓订单,建立新的持仓
- **出场订单**: 平仓订单,关闭现有持仓
- **STManager**: ST模块管理器,单例模式,管理所有策略实例
- **BaseStrategy**: 策略抽象基类,定义策略的通用接口
- **PositionManager**: 持仓状态管理器,管理每个交易对的持仓状态

### ST模块事件定义

ST模块通过事件总线与其他模块通信,以下是所有相关事件的定义:

#### 订阅的事件(输入)

| 事件主题 | 发布者 | 数据格式 | 说明 |
|---------|--------|---------|------|
| `pm.account.loaded` | PM模块 | `{user_id, name, api_key, api_secret, strategy, testnet}` | 账户加载完成,触发策略加载 |
| `ta.indicator.signal` | TA模块 | `{user_id, symbol, indicator_name, signal_type, signal_data}` | 指标信号更新,signal_type为LONG/SHORT |
| `tr.position.opened` | TR模块 | `{user_id, symbol, side, quantity, entry_price}` | 持仓开启,更新持仓状态为LONG/SHORT,可能触发网格交易 |
| `tr.position.closed` | TR模块 | `{user_id, symbol, side, exit_price, pnl}` | 持仓关闭,更新持仓状态为NONE,可能触发反向建仓 |

#### 发布的事件(输出)

| 事件主题 | 触发时机 | 数据格式 | 说明 |
|---------|---------|---------|------|
| `st.strategy.loaded` | 策略实例创建成功 | `{user_id, strategy, timeframe, trading_pairs}` | 策略加载成功 |
| `st.indicator.subscribe` | 策略实例创建后 | `{user_id, symbol, indicator_name, indicator_params}` | 请求TA模块订阅指标 |
| `st.signal.generated` | 生成交易信号 | `{user_id, symbol, side, action, quantity}` | 交易信号生成,action为OPEN/CLOSE |
| `st.grid.create` | 持仓开启后(如配置开启) | `{user_id, symbol, entry_price, grid_levels, grid_ratio, move_up, move_down}` | 创建网格交易 |

### 需求

#### 需求 1: 策略配置加载

**用户故事:** 作为系统管理员,我希望 ST 模块能够自动加载用户的策略配置文件,以便为每个用户创建独立的策略实例。

##### 验收标准

1. WHEN ST 模块接收到 `pm.account.loaded` 事件,THE ST 模块 SHALL 从事件数据中提取 user_id 和 strategy 字段
2. THE ST 模块 SHALL 根据路径规则 `config/strategies/{user_id}/{strategy}.json` 加载策略配置文件
3. IF 配置文件不存在,THEN THE ST 模块 SHALL 记录 ERROR 级别日志并跳过该用户的策略加载
4. IF 配置文件格式无效,THEN THE ST 模块 SHALL 记录 ERROR 级别日志并跳过该用户的策略加载
5. THE ST 模块 SHALL 验证配置文件包含必需字段: timeframe, leverage, position_side, margin_mode, margin_type, trading_pairs
6. THE ST 模块 SHALL 验证 trading_pairs 数组非空,且每个交易对包含 symbol 和 indicator_params 字段
7. WHERE grid_trading 字段存在,THE ST 模块 SHALL 验证其包含 enabled, ratio, grid_levels 等必需字段
8. WHERE reverse 字段不存在,THE ST 模块 SHALL 使用默认值 false

#### 需求 2: 策略实例创建

**用户故事:** 作为量化交易员,我希望系统能够根据我的配置创建策略实例,以便执行我定义的交易逻辑。

##### 验收标准

1. WHEN 策略配置验证成功,THE ST 模块 SHALL 根据 strategy 名称创建对应的策略实例
2. THE ST 模块 SHALL 为每个用户维护独立的策略实例
3. THE ST 模块 SHALL 将 user_id、配置信息和事件总线传递给策略实例
4. WHEN 策略实例创建成功,THE ST 模块 SHALL 发布 `st.strategy.loaded` 事件
5. THE `st.strategy.loaded` 事件 SHALL 包含 user_id, strategy, timeframe, trading_pairs 信息
6. THE ST 模块 SHALL 为策略配置中的每个交易对创建独立的持仓状态管理对象
7. THE ST 模块 SHALL 维护 user_id 到策略实例的映射关系

#### 需求 3: 指标订阅与信号处理

**用户故事:** 作为策略开发者,我希望策略能够接收 TA 模块的指标更新,以便根据技术指标生成交易决策。

##### 验收标准

1. WHEN 策略实例创建成功,THE ST 模块 SHALL 为每个交易对发布 `st.indicator.subscribe` 事件
2. THE `st.indicator.subscribe` 事件 SHALL 包含 user_id, symbol, indicator_name, indicator_params 信息
3. THE ST 模块 SHALL 订阅 `ta.indicator.signal` 事件以接收 TA 模块的指标信号
4. WHEN 接收到 `ta.indicator.signal` 事件,THE ST 模块 SHALL 验证 user_id 和 symbol 匹配当前策略
5. THE ST 模块 SHALL 从 `ta.indicator.signal` 事件中提取指标信号类型(多头/空头)
6. THE ST 模块 SHALL 将指标信号传递给对应的策略实例进行处理

#### 需求 4: 交易信号生成

**用户故事:** 作为量化交易员,我希望策略能够根据指标信号自动生成交易信号,以便系统执行交易操作。

##### 验收标准

1. WHEN 策略实例接收到指标信号,THE 策略实例 SHALL 查询当前交易对的持仓状态
2. IF 当前无持仓且指标信号为多头,THEN THE 策略实例 SHALL 生成开多仓交易信号
3. IF 当前无持仓且指标信号为空头,THEN THE 策略实例 SHALL 生成开空仓交易信号
4. IF 当前持有多头且指标信号为空头,THEN THE 策略实例 SHALL 生成平多仓交易信号
5. IF 当前持有空头且指标信号为多头,THEN THE 策略实例 SHALL 生成平空仓交易信号
6. WHEN 生成交易信号,THE 策略实例 SHALL 根据账户余额、杠杆和风险参数计算仓位大小
7. WHEN 生成交易信号,THE 策略实例 SHALL 发布 `st.signal.generated` 事件
8. THE `st.signal.generated` 事件 SHALL 包含 user_id, symbol, side(BUY/SELL), action(OPEN/CLOSE), quantity, price 信息

#### 需求 5: 持仓状态管理

**用户故事:** 作为系统管理员,我希望 ST 模块能够准确跟踪每个策略的持仓状态,以便正确处理交易信号是没有持仓的建仓订单还是已有持仓的离场订单。

##### 验收标准

1. THE ST 模块 SHALL 为每个交易对维护持仓状态(NONE/LONG/SHORT)
2. THE ST 模块 SHALL 订阅 `tr.position.opened` 事件以更新持仓状态为开仓
3. THE ST 模块 SHALL 订阅 `tr.position.closed` 事件以更新持仓状态为平仓
4. THE ST 模块 SHALL NOT 订阅 `de.order.filled` 事件更新持仓状态(避免挂单撤销未完成的问题)
5. THE ST 模块 SHALL NOT 订阅 `de.position.update` 事件更新持仓状态(避免挂单撤销未完成的问题)
6. WHEN 持仓状态变化,THE ST 模块 SHALL 记录 INFO 级别日志
7. THE ST 模块 SHALL 提供方法查询指定交易对的当前持仓状态
8. THE ST 模块 SHALL NOT 持久化持仓状态,仅在内存中管理

#### 需求 6: 网格交易支持

**用户故事:** 作为量化交易员,我希望在入场订单成交后如果策略配置中开启了网格交易后能够触发发布网格交易信息的事件供TR交易模块使用。

##### 验收标准

1. THE ST 模块 SHALL 订阅 `tr.position.opened` 事件以监听持仓开启
2. WHEN 接收到 `tr.position.opened` 事件,THE 策略实例 SHALL 读取实例属性 `self._config["grid_trading"]["enabled"]`
3. IF 实例属性 grid_trading.enabled 为 true,THEN THE 策略实例 SHALL 发布 `st.grid.create` 事件
4. THE `st.grid.create` 事件 SHALL 包含 user_id, symbol, entry_price, grid_levels, grid_ratio 信息
5. THE `st.grid.create` 事件 SHALL 包含 move_up, move_down 配置信息
6. THE `st.grid.create` 事件 SHALL 包含网格止损止盈参数(如果配置中存在)
7. THE ST 模块 SHALL 在持仓开启后发布网格事件,因为策略实例已加载配置无需重复读取文件

#### 需求 7: 订单成交事件处理

**用户故事:** 作为系统管理员,我希望 ST 模块能够正确处理订单成交事件,以便更新持仓状态和触发后续操作，入场订单成交后有可能触发网格交易，出场订单成交后可能触发反向建仓操作。

##### 验收标准

1. THE ST 模块 SHALL 订阅 `de.order.filled` 事件以监听所有订单成交
2. WHEN 接收到入场订单成交事件,THE ST 模块 SHALL 检查是否需要触发网格交易
3. WHEN 接收到出场订单成交事件,THE ST 模块 SHALL 检查是否需要触发反向建仓
4. THE ST 模块 SHALL 订阅 `tr.position.closed` 事件以确认平仓操作完全完成(包括挂单撤销)
5. IF 策略配置中 reverse 为 true 且平仓完成,THEN THE ST 模块 SHALL 立即生成反向开仓信号
6. IF 平多仓完成且 reverse 为 true,THEN THE ST 模块 SHALL 生成开空仓信号
7. IF 平空仓完成且 reverse 为 true,THEN THE ST 模块 SHALL 生成开多仓信号
8. THE ST 模块 SHALL 记录所有订单成交事件的处理日志

#### 需求 8: 错误处理与日志记录

**用户故事:** 作为系统管理员,我希望 ST 模块能够妥善处理异常情况并记录详细日志,以便排查问题和监控系统运行。

##### 验收标准

1. WHEN 策略配置文件加载失败,THE ST 模块 SHALL 记录 ERROR 级别日志并继续处理其他用户
2. WHEN 策略实例创建失败,THE ST 模块 SHALL 记录 ERROR 级别日志并发布 `st.strategy.load_failed` 事件
3. WHEN 指标信号处理异常,THE ST 模块 SHALL 记录 ERROR 级别日志并继续运行
4. WHEN 交易信号生成失败,THE ST 模块 SHALL 记录 ERROR 级别日志并发布 `st.signal.failed` 事件
5. THE ST 模块 SHALL 确保单个策略实例的错误不影响其他策略实例
6. THE ST 模块 SHALL 在所有日志中包含 user_id 和 symbol 信息以便追踪
7. THE ST 模块 SHALL 在策略加载时记录 INFO 级别日志
8. THE ST 模块 SHALL 在交易信号生成时记录 INFO 级别日志
9. THE ST 模块 SHALL 在持仓状态变化时记录 INFO 级别日志
10. THE ST 模块 SHALL 使用 Loguru 记录所有日志,日志语言为中文

#### 需求 9: 多策略隔离

**用户故事:** 作为量化交易员,我希望能够同时运行多个策略实例,并且它们之间互不干扰。

##### 验收标准

1. THE ST 模块 SHALL 使用单例模式实现 STManager 类,作为全局唯一的策略管理器
2. THE ST 模块 SHALL 为每个用户创建独立的策略实例
3. THE ST 模块 SHALL 维护 user_id 到策略实例的映射关系
4. THE ST 模块 SHALL 确保不同用户的策略实例相互隔离,一个策略的错误不影响其他策略
5. THE ST 模块 SHALL 为每个策略实例维护独立的持仓状态管理器
6. THE ST 模块 SHALL 提供方法查询所有已创建策略实例的 user_id 列表
7. THE ST 模块 SHALL 提供方法根据 user_id 获取对应的策略实例
8. WHEN 系统关闭时,THE ST 模块 SHALL 优雅关闭所有策略实例并发布 `st.manager.shutdown` 事件

## TA 指标模块需求文档

### 简介

TA（Technical Analysis）指标模块是币安永续合约量化交易系统的技术分析层，负责管理技术指标实例、计算技术指标、生成指标信号。该模块采用事件驱动架构（EDA），通过事件总线与 ST（策略）模块和 DE（数据引擎）模块进行交互。

### 术语表

- **TA 模块**：Technical Analysis 模块，技术分析模块
- **ST 模块**：Strategy 模块，策略模块
- **DE 模块**：Data Engine 模块，数据引擎模块
- **事件总线**：Event Bus，用于模块间通信的发布/订阅机制
- **指标实例**：Indicator Instance，根据特定参数配置创建的技术指标对象
- **K线数据**：Kline Data，包含开盘价、最高价、最低价、收盘价、成交量等的时间序列数据
- **指标信号**：Indicator Signal，指标计算后产生的市场趋势判断（多头、空头、空）
- **交易对**：Trading Pair，如 BTCUSDT、ETHUSDT 等币安永续合约交易对
- **指标配置**：Indicator Configuration，包含指标类型、参数、交易对等信息的配置数据

### 需求

#### 需求 1：指标实例管理

**用户故事：** 作为系统开发者，我希望 TA 模块能够管理多个指标实例，以便为不同账号和交易对提供独立的技术分析服务

##### 验收标准

1. THE TA 模块 SHALL 提供创建指标实例的接口
2. THE TA 模块 SHALL 存储所有已创建的指标实例
3. THE TA 模块 SHALL 提供通过唯一标识符获取指标实例的接口
4. THE TA 模块 SHALL 支持同时管理至少 10 个指标实例
5. WHEN 创建指标实例时，THE TA 模块 SHALL 为每个实例分配唯一标识符

#### 需求 2：策略配置订阅

**用户故事：** 作为系统开发者，我希望 TA 模块能够订阅策略加载事件，以便根据策略配置动态创建所需的指标实例

##### 验收标准

1. THE TA 模块 SHALL 订阅 ST 模块发布的策略加载事件
2. WHEN 接收到策略加载事件时，THE TA 模块 SHALL 解析事件中的指标配置信息
3. WHEN 接收到策略加载事件时，THE TA 模块 SHALL 根据指标配置创建对应的指标实例
4. THE 指标配置 SHALL 包含指标类型、参数、交易对和时间周期信息

#### 需求 3：历史K线数据请求

**用户故事：** 作为系统开发者，我希望 TA 模块能够向 DE 模块请求历史K线数据，以便初始化指标计算所需的数据

##### 验收标准

1. WHEN 创建新指标实例时，THE TA 模块 SHALL 向 DE 模块发布历史K线数据请求事件
2. THE 历史K线数据请求事件 SHALL 包含交易对、时间周期和数据数量信息
3. THE TA 模块 SHALL 订阅 DE 模块发布的历史K线数据响应事件
4. WHEN 接收到历史K线数据响应事件时，THE TA 模块 SHALL 将数据传递给对应的指标实例

#### 需求 4：实时K线数据处理

**用户故事：** 作为系统开发者，我希望 TA 模块能够处理实时K线数据更新，以便持续计算最新的技术指标值

##### 验收标准

1. THE TA 模块 SHALL 订阅 DE 模块发布的实时K线更新事件
2. WHEN 接收到实时K线更新事件时，THE TA 模块 SHALL 识别对应的指标实例
3. WHEN 接收到实时K线更新事件时，THE TA 模块 SHALL 将新K线数据传递给对应的指标实例进行计算
4. THE TA 模块 SHALL 支持同时处理多个交易对的实时K线更新

#### 需求 5：技术指标计算

**用户故事：** 作为系统开发者，我希望指标实例能够基于K线数据计算技术指标，以便生成技术分析结果

##### 验收标准

1. THE 指标实例 SHALL 接收K线数据作为输入
2. WHEN 接收到新K线数据时，THE 指标实例 SHALL 执行指标计算逻辑
3. THE 指标实例 SHALL 支持使用第三方技术指标库进行基础指标计算
4. THE 指标实例 SHALL 支持自定义指标计算逻辑
5. THE 指标实例 SHALL 在计算完成后生成指标结果数据

#### 需求 6：指标信号生成

**用户故事：** 作为系统开发者，我希望指标实例能够根据计算结果生成指标信号，以便为策略模块提供市场趋势判断

##### 验收标准

1. WHEN 指标计算完成时，THE 指标实例 SHALL 根据计算结果判断市场趋势
2. THE 指标实例 SHALL 生成多头、空头或空三种指标信号之一
3. THE 指标结果数据 SHALL 包含指标信号和其他计算结果信息
4. THE 指标结果数据 SHALL 包含交易对、时间周期和时间戳信息

#### 需求 7：指标更新事件发布

**用户故事：** 作为系统开发者，我希望 TA 模块能够发布指标计算完成事件，以便 ST 模块能够接收最新的技术分析结果

##### 验收标准

1. WHEN 指标实例完成计算时，THE TA 模块 SHALL 发布指标计算完成事件
2. THE 指标计算完成事件 SHALL 包含指标实例标识符
3. THE 指标计算完成事件 SHALL 包含指标结果数据
4. THE 指标计算完成事件 SHALL 通过事件总线发送给订阅者

#### 需求 8：面向对象设计

**用户故事：** 作为系统开发者，我希望 TA 模块采用面向对象设计，以便提高代码的可维护性和可扩展性

##### 验收标准

1. THE TA 模块 SHALL 使用类封装指标管理功能
2. THE 指标实例 SHALL 使用类封装指标计算逻辑
3. THE TA 模块 SHALL 将相关方法和功能集成在对应的类中
4. THE TA 模块 SHALL 充分利用继承、封装和多态等面向对象特性

#### 需求 9：事件驱动架构

**用户故事：** 作为系统开发者，我希望 TA 模块采用事件驱动架构，以便实现模块间的松耦合通信

##### 验收标准

1. THE TA 模块 SHALL 通过事件总线与其他模块通信
2. THE TA 模块 SHALL 使用发布/订阅模式处理事件
3. THE TA 模块 SHALL 订阅所需的外部事件
4. THE TA 模块 SHALL 发布指标计算完成事件供其他模块订阅

## TR 模块设计完整介绍

### 📌 TR 模块概述

**TR（Trade Execution）** 是量化交易系统的**交易执行层**，负责：

✅ **订阅交易信号** - 从 ST 模块接收交易信号（ENTRY/EXIT/GRID）
✅ **执行订单** - 向de模块提交市价单、限价单、止损止盈单
✅ **管理订单状态** - 跟踪订单的完整生命周期，发布订单成功成交等
✅ **管理持仓状态** - 跟踪每个交易对的持仓信息，在入场订单成交后发布持该交易对持仓开启事件，在出场订单成交后发布该交易对持仓关闭事件。
✅ **WebSocket 监控** - 实时监控订单成交状态
✅ **网格交易** - 根据st模块发布的网格事件启动网格交易，并管理维护网格订单
✅ **资金管理** - 计算入场数量、精度处理、最小名义价值检查（如果开启网格会有网格资金占比）
✅ **订单持久化** - 针对每个交易任务设置一个实例对象，记录他的所有订单，并计算订单获利，有些订单是趋势主仓订单+网格交易这种混合策略，需要设计如何计算订单利润和亏损，直接从币安获取可能不准确，需要根据入场和出场价和手续费自己计算。

### TR模块的一些细节
- 资金管理：在初始化tr模块时通过de获取账户可用保证金余额（可能是usdc或者usdt根据）st的margin_type属性决定。获取后可用保证金*0.95/策略配置中交易对总个数，作为每个交易对象平均分到的保证金数量。
- 交易模式分为普通交易和网格交易量大类型，根据策略中属性，分三种情况如果策略未开启网格交易选项，就按照st生成的入场和出场交易信号进行交易；如果开启了网格而且"grid_type": "normal","ratio": 1,就是普通网格交易资金比例为1说明交易的资金是所有分到这个交易对的可用保证金，直接根据st的入场信号和网格信息开启网格交易就行；最后一种是"grid_type": "abnormal","ratio": 0.5,说明为特殊网格交易这类交易需要由st入场信号完成入场交易后st再向tr发送网格交易信息。其中ratio说明交易的资金是50%分到这个交易对的可用保证金。这三种交易模式怎么识别和触发怎么设计需要详细讨论










