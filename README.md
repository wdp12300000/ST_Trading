# ST_Trading - 事件驱动量化交易系统

基于事件驱动架构（EDA）的加密货币量化交易系统，专注于币安永续合约交易。

[![Tests](https://img.shields.io/badge/tests-520%20passed-brightgreen)](https://github.com/wdp12300000/ST_Trading)
[![Coverage](https://img.shields.io/badge/coverage-86%25-brightgreen)](https://github.com/wdp12300000/ST_Trading)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

## 📋 项目概述

ST_Trading 是一个使用 Python 开发的量化交易系统，采用事件驱动架构设计，提供高性能、高可靠性的交易能力。

### 核心特性

- ✅ **事件驱动架构**：基于发布/订阅模式的松耦合设计
- ✅ **异步处理**：并发执行事件处理器，提高系统吞吐量
- ✅ **错误隔离**：单个处理器失败不影响其他处理器
- ✅ **事件持久化**：SQLite3 持久化事件历史，支持查询和审计
- ✅ **通配符订阅**：灵活的事件路由机制
- ✅ **依赖注入**：可测试、可扩展的设计
- ✅ **高测试覆盖率**：86% 测试覆盖率，520 个测试全部通过
- ✅ **多账户管理**：支持多个交易账户独立运行
- ✅ **币安API集成**：完整的币安期货REST API和WebSocket支持
- ✅ **实时数据流**：K线数据、订单更新、账户更新实时推送
- ✅ **策略执行引擎**：支持多策略并行、网格交易、反向建仓
- ✅ **技术指标分析**：支持自定义指标、指标聚合、信号生成
- ✅ **交易执行模块**：订单管理、持仓管理、网格交易、资金管理、利润计算

## 🏗️ 架构设计

### 核心模块

```
ST_Trading/
├── src/
│   ├── core/                    # 核心模块
│   │   ├── event/              # 事件驱动架构（EDA）
│   │   │   ├── event.py        # 事件数据类
│   │   │   ├── abstract_event_store.py  # 事件存储抽象接口
│   │   │   ├── event_store.py  # SQLite 事件存储实现
│   │   │   └── event_bus.py    # 事件总线
│   │   ├── pm/                 # 账户管理模块（PM）
│   │   │   ├── pm.py           # 单账户管理类
│   │   │   ├── pm_manager.py   # 多账户管理器（单例）
│   │   │   ├── pm_events.py    # PM模块事件常量
│   │   │   └── README.md       # PM模块文档
│   │   ├── de/                 # 数据引擎模块（DE）
│   │   │   ├── binance_client.py      # 币安REST API客户端
│   │   │   ├── de_manager.py          # DE管理器（单例）
│   │   │   ├── market_websocket.py    # 市场数据WebSocket
│   │   │   ├── user_data_websocket.py # 用户数据流WebSocket
│   │   │   ├── de_events.py           # DE模块事件常量
│   │   │   └── README.md              # DE模块文档
│   │   ├── st/                 # 策略执行模块（ST）
│   │   │   ├── st_manager.py          # ST管理器（单例）
│   │   │   ├── base_strategy.py       # 策略抽象基类
│   │   │   └── st_events.py           # ST模块事件常量
│   │   ├── ta/                 # 技术分析模块（TA）
│   │   │   ├── ta_manager.py          # TA管理器（单例）
│   │   │   ├── base_indicator.py      # 指标抽象基类
│   │   │   ├── indicator_factory.py   # 指标工厂类
│   │   │   ├── ta_events.py           # TA模块事件常量
│   │   │   └── README.md              # TA模块文档
│   │   └── tr/                 # 交易执行模块（TR）
│   │       ├── tr_manager.py          # TR管理器（单例）
│   │       ├── trading_task.py        # 交易任务管理
│   │       ├── order_manager.py       # 订单管理器
│   │       ├── capital_manager.py     # 资金管理器
│   │       ├── precision_handler.py   # 精度处理器
│   │       ├── grid_calculator.py     # 网格计算器
│   │       ├── grid_manager.py        # 网格管理器
│   │       ├── profit_calculator.py   # 利润计算器
│   │       ├── tr_database.py         # 数据库持久化
│   │       └── tr_events.py           # TR模块事件常量
│   └── utils/
│       └── logger.py           # 日志模块
├── tests/
│   ├── unit/                   # 单元测试（466个）
│   └── integration/            # 集成测试（54个）
├── logs/                       # 日志文件
├── data/                       # 数据文件
├── docs/                       # 文档
└── htmlcov/                    # 测试覆盖率报告
```

### 设计原则

- **SOLID 原则**：单一职责、开闭原则、依赖倒置
- **TDD 开发**：测试驱动开发，红-绿-重构循环
- **YAGNI 原则**：只做当前需要的事情，不过早优化

## 🚀 快速开始

### 环境要求

- Python 3.12.4+
- 虚拟环境（venv）

### 安装

```bash
# 克隆项目
git clone https://github.com/wdp12300000/ST_Trading.git
cd ST_Trading

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
```

### 基本使用

```python
import asyncio
from src.core.event import Event
from src.core.event_bus import EventBus
from src.core.event_store import SQLiteEventStore

# 初始化事件总线和存储
store = SQLiteEventStore(db_path="data/events.db")
bus = EventBus.get_instance(event_store=store)

# 定义事件处理器
async def order_handler(event):
    print(f"收到订单事件: {event.data}")

# 订阅事件
bus.subscribe("order.created", order_handler)

# 发布事件
async def main():
    event = Event(
        subject="order.created",
        data={"order_id": "12345", "symbol": "BTC/USDT", "price": 50000.0}
    )
    await bus.publish(event)

asyncio.run(main())
```

## 📚 核心组件

### 1. EDA（事件驱动架构）模块

事件驱动架构是系统的核心基础，提供发布/订阅机制和事件持久化。

#### Event（事件类）

```python
from src.core.event import Event

# 创建事件
event = Event(
    subject="order.created",
    data={"order_id": "12345"},
    source="order_manager"
)

# 序列化/反序列化
event_dict = event.to_dict()
event = Event.from_dict(event_dict)
```

#### EventBus（事件总线）

```python
from src.core.event_bus import EventBus

bus = EventBus.get_instance()

# 订阅事件
bus.subscribe("order.created", handler)
bus.subscribe("order.*", handler)  # 通配符订阅

# 发布事件
await bus.publish(event)
```

#### EventStore（事件存储）

```python
from src.core.event_store import SQLiteEventStore

store = SQLiteEventStore(db_path="data/events.db")
store.insert_event(event)
events = store.query_recent_events(limit=100)
```

**测试覆盖率**: 97% | **测试数**: 99个

---

### 2. PM（账户管理）模块

PM模块负责管理多个交易账户，提供账户配置加载、验证和事件发布功能。

#### 主要功能
- ✅ 多账户管理（PMManager单例）
- ✅ 账户配置加载和验证
- ✅ 账户信息事件发布
- ✅ 风险参数管理

#### 使用示例

```python
from src.core.pm.pm_manager import PMManager
from src.core.event import EventBus

# 获取PMManager实例
event_bus = EventBus.get_instance()
pm_manager = PMManager.get_instance(event_bus=event_bus)

# 加载账户配置
await pm_manager.load_account_from_file("config/account_user_001.json")

# 查询账户
pm = pm_manager.get_pm("user_001")
```

**测试覆盖率**: 89% | **测试数**: 33个 | **详细文档**: [src/core/pm/README.md](src/core/pm/README.md)

---

### 3. DE（数据引擎）模块

DE模块负责与币安期货交易所的API交互，提供市场数据订阅、订单执行、账户查询等功能。

#### 主要功能
- ✅ 币安REST API客户端（HMAC SHA256签名）
- ✅ 市场数据WebSocket（K线实时订阅）
- ✅ 用户数据流WebSocket（订单/账户/持仓更新）
- ✅ 订单执行（创建、取消、重试）
- ✅ 账户余额查询
- ✅ 多账户支持

#### 使用示例

```python
from src.core.de.de_manager import DEManager
from src.core.event import Event, EventBus

# 获取DEManager实例
event_bus = EventBus.get_instance()
de_manager = DEManager.get_instance(event_bus=event_bus)

# 发布订单创建事件
await event_bus.publish(Event(
    subject="trading.order.create",
    data={
        "user_id": "user_001",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "LIMIT",
        "quantity": 0.001,
        "price": 50000.0
    }
))
```

**测试覆盖率**: 79% | **测试数**: 113个 | **详细文档**: [src/core/de/README.md](src/core/de/README.md)

---

### 4. ST（策略执行）模块

ST模块负责策略执行、信号生成、持仓管理、网格交易和反向建仓等功能。

#### 主要功能
- ✅ 策略管理（STManager单例）
- ✅ 多用户策略隔离
- ✅ 持仓状态管理（NONE/LONG/SHORT）
- ✅ 指标信号处理（多指标支持）
- ✅ 网格交易（自动创建网格）
- ✅ 反向建仓（平仓后反向开仓）
- ✅ 策略配置加载和验证

#### 使用示例

```python
from src.core.st.st_manager import STManager
from src.core.st.base_strategy import BaseStrategy
from src.core.event import Event, EventBus

# 获取STManager实例
event_bus = EventBus.get_instance()
st_manager = STManager.get_instance(event_bus=event_bus)

# 发布指标计算完成事件
await event_bus.publish(Event(
    subject="ta.calculation.completed",
    data={
        "user_id": "user_001",
        "symbol": "XRPUSDC",
        "timeframe": "15m",
        "indicators": {
            "ma_stop_ta": {"signal": "LONG", "data": {}},
            "rsi_ta": {"signal": "LONG", "data": {}}
        }
    }
))
```

#### 事件流程

```
PM模块 → st.strategy.loaded → ST模块
TA模块 → ta.calculation.completed → ST模块 → st.signal.generated → TR模块
TR模块 → tr.position.opened → ST模块 → st.grid.create → Grid模块
TR模块 → tr.position.closed → ST模块 → st.signal.generated → TR模块
```

**测试覆盖率**: 92% | **测试数**: 43个

---

### 5. TA（技术分析）模块

TA模块负责管理技术指标实例，处理K线数据，计算技术指标并生成交易信号。

#### 主要功能
- ✅ 指标实例管理（TAManager单例）
- ✅ 指标订阅和创建
- ✅ 历史K线数据请求和处理
- ✅ 实时K线数据处理
- ✅ 指标结果聚合和事件发布
- ✅ 自定义指标支持（BaseIndicator抽象基类）
- ✅ 指标工厂模式（IndicatorFactory）

#### 使用示例

```python
from src.core.ta.ta_manager import TAManager
from src.core.ta.base_indicator import BaseIndicator, IndicatorSignal
from src.core.ta.indicator_factory import IndicatorFactory
from src.core.event import Event, EventBus

# 获取TAManager实例
event_bus = EventBus.get_instance()
ta_manager = TAManager.get_instance(event_bus=event_bus)

# 创建自定义指标
class MAStopIndicator(BaseIndicator):
    async def calculate(self, klines):
        # 计算移动平均线
        closes = [float(k["close"]) for k in klines]
        ma_value = sum(closes[-20:]) / 20

        # 判断信号
        if closes[-1] > ma_value:
            return {"signal": IndicatorSignal.LONG.value, "data": {"ma": ma_value}}
        else:
            return {"signal": IndicatorSignal.SHORT.value, "data": {"ma": ma_value}}

# 注册指标
IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)

# 订阅指标（ST模块发布）
await event_bus.publish(Event(
    subject="st.indicator.subscribe",
    data={
        "user_id": "user_001",
        "symbol": "XRPUSDC",
        "indicator_name": "ma_stop_ta",
        "indicator_params": {"period": 20},
        "timeframe": "15m"
    }
))
```

#### 事件流程

```
ST模块 → st.indicator.subscribe → TA模块
TA模块 → de.get_historical_klines → DE模块
DE模块 → de.historical_klines.success → TA模块（初始化指标）
DE模块 → de.kline.update → TA模块（实时计算）
TA模块 → ta.calculation.completed → ST模块
```

#### 设计原则

- **无K线缓存**：每次计算都使用DE模块提供的完整历史K线
- **指标聚合**：等待同一交易对的所有指标完成后统一发布事件
- **只处理关闭的K线**：只在K线关闭时计算指标
- **指标就绪状态**：只处理已初始化的指标

**测试覆盖率**: 90% | **测试数**: 54个 | **详细文档**: [src/core/ta/README.md](src/core/ta/README.md)

---

### 6. TR（交易执行）模块

TR模块负责订单执行、持仓管理、网格交易、资金管理和利润计算等核心交易功能。

#### 主要功能
- ✅ 订单管理（市价单、限价单、POST_ONLY订单）
- ✅ 持仓状态管理（未持仓/已持仓）
- ✅ 三种交易模式（无网格、普通网格、特殊网格）
- ✅ 资金管理（保证金分配、仓位计算）
- ✅ 网格交易（网格创建、配对管理、网格移动）
- ✅ 精度处理（价格/数量精度、最小名义价值验证）
- ✅ 利润计算（订单利润、网格配对利润、总盈亏统计）
- ✅ 数据持久化（异步SQLite存储）

#### 使用示例

```python
from src.core.tr.tr_manager import TRManager
from src.core.event import Event, EventBus

# 获取TRManager实例
event_bus = EventBus.get_instance()
tr_manager = TRManager.get_instance(event_bus=event_bus)

# 启动TR管理器
await tr_manager.start()

# 发布账户加载事件（来自PM模块）
await event_bus.publish(Event(
    subject="pm.account.loaded",
    data={
        "user_id": "user_001",
        "balance": 10000.0,
        "leverage": 10
    }
))

# 发布交易信号事件（来自ST模块）
await event_bus.publish(Event(
    subject="st.signal.generated",
    data={
        "user_id": "user_001",
        "symbol": "BTCUSDT",
        "signal": "LONG",
        "strategy_id": "ma_stop_st",
        "grid_trading": {
            "enabled": True,
            "grid_type": "normal",
            "ratio": 1.0,
            "grid_levels": 10
        }
    }
))
```

#### 三种交易模式

**1. 无网格模式** (`grid_trading.enabled = false`)
- 直接使用市价单入场/出场
- 适合趋势跟踪策略

**2. 普通网格模式** (`grid_type = "normal", ratio = 1`)
- 收到入场信号后直接创建网格
- 使用100%保证金创建网格订单
- 适合震荡行情

**3. 特殊网格模式** (`grid_type = "abnormal", ratio < 1`)
- 先使用ratio%保证金建仓
- 等待ST模块发送网格信息后创建网格
- 使用剩余保证金创建网格订单
- 适合需要先确认趋势再布局网格的策略

#### 资金管理公式

```python
# 可用保证金 = 账户余额 × 0.95（安全系数）
available_margin = balance * 0.95

# 每个交易对的保证金 = 可用保证金 ÷ 交易对数量
margin_per_symbol = available_margin / num_symbols

# 仓位大小 = 保证金 × 杠杆 ÷ 入场价格
position_size = margin * leverage / entry_price

# 网格仓位大小 = 总仓位 ÷ 网格层数
grid_position_size = total_position / grid_levels
```

#### 网格交易

```python
# 网格价格间隔 = (上边价格 - 下边价格) / 网格层数
price_interval = (upper_price - lower_price) / grid_levels

# 网格配对利润 = (卖价 - 买价) × 数量 - 手续费
profit = (sell_price - buy_price) * quantity - fees
```

#### 事件流程

```
PM模块 → pm.account.loaded → TR模块（加载账户信息）
ST模块 → st.signal.generated → TR模块（处理交易信号）
TR模块 → trading.order.create → DE模块（提交订单）
DE模块 → de.order.filled → TR模块（订单成交）
TR模块 → tr.position.opened → ST模块（持仓开启）
ST模块 → st.grid.create → TR模块（创建网格）
TR模块 → tr.position.closed → ST模块（持仓关闭）
```

#### 核心组件

**TRManager** - TR模块管理器
- 单例模式，协调所有子模块
- 管理所有交易任务（TradingTask）
- 订阅PM、ST、DE模块的事件

**TradingTask** - 交易任务管理
- 管理单个交易对的交易任务
- 持仓状态管理
- 交易模式识别

**CapitalManager** - 资金管理器
- 保证金计算（安全系数0.95）
- 仓位大小计算
- 网格仓位分配

**OrderManager** - 订单管理器
- 订单提交（市价单、限价单、POST_ONLY）
- 订单撤销

**PrecisionHandler** - 精度处理器
- 价格/数量精度处理（向下取整）
- 最小名义价值验证

**GridCalculator** - 网格计算器
- 网格价格计算
- 网格订单计算

**GridManager** - 网格管理器
- 网格订单创建
- 网格配对管理
- 配对利润计算

**ProfitCalculator** - 利润计算器
- 单个订单利润计算
- 网格配对利润计算
- 总盈亏统计（胜率、ROI）

**TRDatabase** - 数据库持久化
- 异步SQLite操作（aiosqlite）
- 交易任务持久化
- 订单记录持久化

**测试覆盖率**: 83% | **测试数**: 165个

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html tests/
```

### 测试统计

- **总测试数：520 个** ✅
- **单元测试：466 个**
- **集成测试：54 个**
- **整体测试覆盖率：86%**

#### 各模块覆盖率
- EDA模块：97%（99个测试）
- PM模块：89%（33个测试）
- DE模块：79%（113个测试）
- ST模块：92%（43个测试）
- TA模块：90%（54个测试）
- TR模块：83%（165个测试）

详细报告：[TEST_COVERAGE_REPORT.md](docs/TEST_COVERAGE_REPORT.md)

## 📖 文档

- [测试覆盖率报告](docs/TEST_COVERAGE_REPORT.md)
- [API 文档](docs/) (待完善)

## 🛠️ 技术栈

- **Python 3.12.4**
- **SQLite3** - 事件持久化
- **Loguru** - 日志管理
- **aiohttp 3.13.1** - 异步HTTP客户端
- **websockets 15.0.1** - WebSocket客户端
- **pytest** - 测试框架
- **pytest-asyncio** - 异步测试
- **pytest-cov** - 覆盖率统计

## 📊 开发进度

### 已完成模块

- [x] **EDA（事件驱动架构）模块** - 97% 覆盖率
  - [x] Event 类（100% 覆盖率）
  - [x] EventStore 类（100% 覆盖率）
  - [x] EventBus 类（97% 覆盖率）
  - [x] 集成测试（事件发布、异步处理、通配符订阅）

- [x] **PM（账户管理）模块** - 89% 覆盖率
  - [x] PM 单账户管理类
  - [x] PMManager 多账户管理器（单例）
  - [x] 账户配置加载和验证
  - [x] 事件发布机制
  - [x] 集成测试

- [x] **DE（数据引擎）模块** - 79% 覆盖率
  - [x] BinanceClient REST API客户端
  - [x] DEManager 管理器（单例）
  - [x] MarketWebSocket 市场数据流
  - [x] UserDataWebSocket 用户数据流
  - [x] 订单执行功能
  - [x] 账户余额查询
  - [x] 集成测试

- [x] **ST（策略执行）模块** - 92% 覆盖率
  - [x] STManager 管理器（单例）
  - [x] BaseStrategy 策略抽象基类
  - [x] 持仓状态管理（NONE/LONG/SHORT）
  - [x] 指标信号处理（多指标支持）
  - [x] 网格交易功能
  - [x] 反向建仓功能
  - [x] 策略配置加载和验证
  - [x] 单元测试（36个）
  - [x] 集成测试（7个）

- [x] **TA（技术分析）模块** - 90% 覆盖率
  - [x] TAManager 管理器（单例）
  - [x] BaseIndicator 指标抽象基类
  - [x] IndicatorFactory 指标工厂
  - [x] 指标订阅和创建
  - [x] 历史K线数据处理
  - [x] 实时K线数据处理
  - [x] 指标结果聚合
  - [x] 事件发布机制
  - [x] 单元测试（46个）
  - [x] 集成测试（8个）

- [x] **TR（交易执行）模块** - 83% 覆盖率
  - [x] TRManager 管理器（单例）
  - [x] TradingTask 交易任务管理
  - [x] OrderManager 订单管理器
  - [x] CapitalManager 资金管理器
  - [x] PrecisionHandler 精度处理器
  - [x] GridCalculator 网格计算器
  - [x] GridManager 网格管理器
  - [x] ProfitCalculator 利润计算器
  - [x] TRDatabase 数据库持久化
  - [x] 三种交易模式（无网格/普通网格/特殊网格）
  - [x] 网格交易功能（创建、配对、移动）
  - [x] 利润计算和统计
  - [x] 单元测试（165个）
  - [x] 集成测试框架

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- GitHub: [wdp12300000/ST_Trading](https://github.com/wdp12300000/ST_Trading)

---

**开发时间：** 2025-10-27 ~ 2025-10-31
**版本：** v0.6.0 - EDA + PM + DE + ST + TA + TR 模块
**状态：** ✅ 核心模块开发完成，520个测试全部通过

### 版本历史
- **v0.1.0** (2025-10-27) - EDA事件驱动架构模块
- **v0.2.0** (2025-10-28) - PM账户管理模块
- **v0.3.0** (2025-10-28) - DE数据引擎模块
- **v0.4.0** (2025-10-29) - ST策略执行模块
- **v0.5.0** (2025-10-30) - TA技术分析模块
- **v0.6.0** (2025-10-31) - TR交易执行模块

