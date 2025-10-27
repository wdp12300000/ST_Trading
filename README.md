# ST_Trading - 事件驱动量化交易系统

基于事件驱动架构（EDA）的加密货币量化交易系统，专注于币安永续合约交易。

[![Tests](https://img.shields.io/badge/tests-99%20passed-brightgreen)](https://github.com/wdp12300000/ST_Trading)
[![Coverage](https://img.shields.io/badge/coverage-97%25-brightgreen)](https://github.com/wdp12300000/ST_Trading)
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
- ✅ **高测试覆盖率**：97% 测试覆盖率，99 个测试全部通过

## 🏗️ 架构设计

### 核心模块

```
ST_Trading/
├── src/
│   ├── core/                    # 核心模块
│   │   ├── event.py            # 事件数据类
│   │   ├── abstract_event_store.py  # 事件存储抽象接口
│   │   ├── event_store.py      # SQLite 事件存储实现
│   │   └── event_bus.py        # 事件总线
│   └── utils/
│       └── logger.py           # 日志模块
├── tests/
│   ├── unit/                   # 单元测试（76个）
│   └── integration/            # 集成测试（23个）
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

### 1. Event（事件类）

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

### 2. EventBus（事件总线）

```python
from src.core.event_bus import EventBus

bus = EventBus.get_instance()

# 订阅事件
bus.subscribe("order.created", handler)
bus.subscribe("order.*", handler)  # 通配符订阅

# 发布事件
await bus.publish(event)
```

### 3. EventStore（事件存储）

```python
from src.core.event_store import SQLiteEventStore

store = SQLiteEventStore(db_path="data/events.db")
store.insert_event(event)
events = store.query_recent_events(limit=100)
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html tests/
```

### 测试统计

- **总测试数：99 个** ✅
- **单元测试：76 个**
- **集成测试：23 个**
- **测试覆盖率：97%**

详细报告：[TEST_COVERAGE_REPORT.md](docs/TEST_COVERAGE_REPORT.md)

## 📖 文档

- [测试覆盖率报告](docs/TEST_COVERAGE_REPORT.md)
- [API 文档](docs/) (待完善)

## 🛠️ 技术栈

- **Python 3.12.4**
- **SQLite3** - 事件持久化
- **Loguru** - 日志管理
- **pytest** - 测试框架
- **pytest-asyncio** - 异步测试
- **pytest-cov** - 覆盖率统计

## 📊 开发进度

- [x] 阶段1 - 环境准备
  - [x] 项目初始化和 Git 配置
  - [x] 安装依赖
  - [x] 配置日志模块
- [x] 阶段2 - TDD 开发
  - [x] Event 类（100% 覆盖率）
  - [x] EventStore 类（100% 覆盖率）
  - [x] EventBus 类（97% 覆盖率）
- [x] 阶段3 - 集成测试
  - [x] 事件发布与持久化
  - [x] 异步处理与错误隔离
  - [x] 通配符订阅混合场景
- [x] 阶段4 - 验证和提交
  - [x] 测试覆盖率报告（97%）
  - [x] 代码提交到 GitHub
- [ ] 阶段5 - 业务模块开发
  - [ ] 数据管理模块
  - [ ] 策略引擎
  - [ ] 风险管理
  - [ ] 订单执行

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

- GitHub: [wdp12300000/ST_Trading](https://github.com/wdp12300000/ST_Trading)

---

**开发时间：** 2025-10-27
**版本：** v0.1.0 - 事件驱动模块
**状态：** ✅ 开发完成，测试通过

