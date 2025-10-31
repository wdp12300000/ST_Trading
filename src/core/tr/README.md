# TR (Trade Execution) 模块

## 📌 模块概述

TR（Trade Execution）是量化交易系统的**交易执行层**，负责订单执行、持仓管理、网格交易、资金管理和订单持久化。

## 🎯 核心功能

### 1. 订单执行
- 接收ST模块的交易信号
- 提交市价单、限价单、POST_ONLY订单
- 跟踪订单状态和成交情况

### 2. 持仓管理
- 跟踪每个交易对的持仓状态（NONE/LONG/SHORT）
- 记录入场价格、持仓数量
- 发布持仓开启/关闭事件

### 3. 网格交易
- 支持三种交易模式：无网格、普通网格、特殊网格
- 自动创建和管理网格订单
- 支持网格移动（move_up/move_down）
- 网格订单配对管理

### 4. 资金管理
- 获取账户可用保证金
- 按交易对数量分配保证金
- 计算仓位大小（考虑杠杆）
- 订单精度处理

### 5. 利润计算
- 单个订单利润计算
- 网格订单配对利润计算
- 交易任务总盈亏统计

### 6. 订单持久化
- SQLite数据库存储
- 交易任务记录
- 订单历史查询

## 🏗️ 架构设计

### 核心类

```
TRManager (单例)
├── CapitalManager (资金管理)
├── OrderManager (订单管理)
├── GridManager (网格管理)
│   └── GridCalculator (网格计算)
└── TradingTask (交易任务)
    ├── 持仓状态管理
    ├── 订单记录
    └── 利润计算
```

### 三种交易模式

#### 1. 无网格模式 (`grid_trading.enabled = false`)
```
ST入场信号 → TR提交市价单 → 成交后发布 tr.position.opened
ST出场信号 → TR提交市价单 → 成交后发布 tr.position.closed
```

#### 2. 普通网格模式 (`grid_type = "normal", ratio = 1`)
```
ST入场信号 → TR直接创建网格交易 → 网格入场订单成交 → 发布 tr.position.opened
使用100%保证金 × 杠杆倍数
```

#### 3. 特殊网格模式 (`grid_type = "abnormal", ratio < 1`)
```
ST入场信号 → TR用ratio%保证金建仓 → 成交后发布 tr.position.opened
ST发布 st.grid.create → TR用剩余保证金创建网格
入场订单：ratio% × 杠杆，网格订单：(1-ratio)% × 杠杆
```

## 📡 事件交互

### 订阅的事件（输入）

| 事件主题 | 发布者 | 数据格式 | 说明 |
|---------|--------|---------|------|
| `pm.account.loaded` | PM模块 | `{user_id, api_key, api_secret, ...}` | 账户加载完成，初始化资金管理 |
| `st.signal.generated` | ST模块 | `{user_id, symbol, side, action}` | 交易信号，执行订单 |
| `st.grid.create` | ST模块 | `{user_id, symbol, entry_price, upper_price, lower_price, grid_levels, ...}` | 创建网格交易 |
| `de.order.filled` | DE模块 | `{user_id, order_id, symbol, price, quantity}` | 订单成交，更新持仓 |
| `de.order.update` | DE模块 | `{user_id, order_id, status, ...}` | 订单状态更新 |

### 发布的事件（输出）

| 事件主题 | 触发时机 | 数据格式 | 说明 |
|---------|---------|---------|------|
| `tr.position.opened` | 入场订单成交 | `{user_id, symbol, side, quantity, entry_price}` | 持仓开启 |
| `tr.position.closed` | 平仓完成 | `{user_id, symbol, side, exit_price, pnl}` | 持仓关闭 |
| `trading.order.create` | 提交订单 | `{user_id, symbol, side, order_type, quantity, price}` | 创建订单 |
| `trading.order.cancel` | 撤销订单 | `{user_id, symbol, order_id}` | 取消订单 |

## 💰 资金管理

### 保证金分配
```python
可用保证金 = 账户余额 × 0.95  # 保留5%作为缓冲
每个交易对保证金 = 可用保证金 ÷ 交易对数量
```

### 仓位计算
```python
# 无网格模式
仓位大小 = 交易对保证金 × 杠杆倍数 ÷ 入场价格

# 普通网格模式 (ratio = 1)
网格总资金 = 交易对保证金 × 杠杆倍数
每个网格订单资金 = 网格总资金 ÷ 网格层数

# 特殊网格模式 (ratio = 0.5)
入场订单资金 = 交易对保证金 × 0.5 × 杠杆倍数
网格订单资金 = 交易对保证金 × 0.5 × 杠杆倍数
每个网格订单资金 = 网格订单资金 ÷ 网格层数
```

## 📊 网格交易

### 网格计算
```python
价格间隔 = (upper_price - lower_price) / grid_levels

# 示例：
# upper_price = 1.05, lower_price = 0.95, grid_levels = 10
# 价格间隔 = (1.05 - 0.95) / 10 = 0.01
# 网格价格：0.95, 0.96, 0.97, ..., 1.04, 1.05
```

### 网格移动
- `move_up = true`: 价格突破上边界时，整体向上移动网格
- `move_down = true`: 价格突破下边界时，整体向下移动网格

### 网格订单配对
- 每个买单对应一个卖单
- 用于计算网格利润
- 配对成交后计算差价利润

## 💵 利润计算

### 单个订单利润
```python
# 多头订单
利润 = (出场价格 - 入场价格) × 数量 - 手续费

# 空头订单
利润 = (入场价格 - 出场价格) × 数量 - 手续费

# 手续费
手续费 = 入场价格 × 数量 × 入场费率 + 出场价格 × 数量 × 出场费率
```

### 网格订单配对利润
```python
# 买单价格 = 0.95, 卖单价格 = 0.96, 数量 = 100
利润 = (0.96 - 0.95) × 100 - 手续费
```

### 交易任务总盈亏
```python
总盈亏 = Σ(所有订单利润) + Σ(所有网格配对利润)
```

## 🗄️ 数据持久化

### 数据库表结构

#### trading_tasks 表
- task_id: 任务ID
- user_id: 用户ID
- symbol: 交易对
- side: 方向（LONG/SHORT）
- entry_price: 入场价格
- exit_price: 出场价格
- quantity: 数量
- pnl: 盈亏
- status: 状态（OPEN/CLOSED）
- created_at: 创建时间
- closed_at: 关闭时间

#### orders 表
- order_id: 订单ID
- task_id: 所属任务ID
- user_id: 用户ID
- symbol: 交易对
- side: 方向（BUY/SELL）
- order_type: 订单类型
- price: 价格
- quantity: 数量
- filled_quantity: 成交数量
- status: 状态
- is_grid_order: 是否网格订单
- grid_pair_id: 网格配对ID
- created_at: 创建时间
- filled_at: 成交时间

## 🔧 使用示例

### 初始化TR模块
```python
from src.core.tr.tr_manager import TRManager
from src.core.event.event_bus import EventBus

# 创建事件总线
event_bus = EventBus()

# 获取TR管理器实例
tr_manager = TRManager.get_instance(event_bus=event_bus)

# 启动TR管理器
await tr_manager.start()
```

### 查询交易任务
```python
# 获取用户的所有交易任务
tasks = tr_manager.get_user_tasks("user_001")

# 获取指定交易对的任务
task = tr_manager.get_task("user_001", "XRPUSDC")

# 查询任务盈亏
pnl = task.calculate_pnl()
```

## 📝 开发规范

### 日志记录
- 所有日志使用中文
- 包含文件名和行号
- 使用Loguru记录日志

### 错误处理
- 所有外部API调用必须有异常处理
- 关键操作失败时发布告警事件
- 不允许静默失败

### 测试要求
- 核心模块必须有单元测试
- 事件流转必须有集成测试
- 测试覆盖率 ≥ 80%

## 🚀 开发进度

- [x] 第一阶段：基础架构与事件定义
- [ ] 第二阶段：资金管理与订单执行
- [ ] 第三阶段：持仓管理与交易模式
- [ ] 第四阶段：网格交易实现
- [ ] 第五阶段：利润计算与订单持久化
- [ ] 第六阶段：测试与集成

