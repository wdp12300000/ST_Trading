# DE (Data Engine) 模块

## 概述

DE（Data Engine）模块是ST_Trading量化交易系统的数据引擎，负责与币安期货交易所的API交互，提供市场数据订阅、订单执行、账户查询等核心功能。

## 主要功能

### 1. 币安API客户端 (BinanceClient)
- ✅ REST API调用（HMAC SHA256签名认证）
- ✅ 历史K线数据查询
- ✅ 账户余额查询
- ✅ 订单创建和取消
- ✅ ListenKey管理（用户数据流）
- ✅ 自动重试机制（订单失败时最多重试3次）

### 2. 市场数据WebSocket (MarketWebSocket)
- ✅ K线数据实时订阅
- ✅ 多交易对同时订阅
- ✅ 自动断线重连
- ✅ 事件驱动的数据推送

### 3. 用户数据流WebSocket (UserDataWebSocket)
- ✅ 订单更新实时推送
- ✅ 账户余额更新推送
- ✅ 持仓信息更新推送
- ✅ ListenKey自动续期（每30分钟）
- ✅ 自动断线重连

### 4. DE管理器 (DEManager)
- ✅ 单例模式管理
- ✅ 多账户支持（每个账户独立的BinanceClient）
- ✅ 事件驱动架构集成
- ✅ 自动响应PM模块的账户加载事件
- ✅ 订单执行事件处理
- ✅ 账户余额查询事件处理

## 架构设计

### 事件驱动架构

DE模块完全基于事件驱动架构，通过EventBus与其他模块通信：

#### 输入事件（订阅）
- `pm.account.loaded` - PM模块发布的账户加载事件
- `trading.order.create` - Trading模块发布的订单创建事件
- `trading.order.cancel` - Trading模块发布的订单取消事件
- `trading.get_account_balance` - Trading模块发布的余额查询事件

#### 输出事件（发布）
- `de.client.connected` - 客户端连接成功
- `de.kline.update` - K线数据更新
- `de.order.submitted` - 订单提交成功
- `de.order.cancelled` - 订单取消成功
- `de.order.failed` - 订单操作失败
- `de.order.update` - 订单状态更新（来自WebSocket）
- `de.account.balance` - 账户余额查询结果
- `de.account.update` - 账户信息更新（来自WebSocket）
- `de.position.update` - 持仓信息更新（来自WebSocket）

### 模块结构

```
src/core/de/
├── __init__.py              # 模块初始化
├── de_events.py             # 事件常量定义（22个事件）
├── binance_client.py        # 币安REST API客户端（161行）
├── de_manager.py            # DE管理器单例（133行）
├── market_websocket.py      # 市场数据WebSocket（114行）
├── user_data_websocket.py   # 用户数据流WebSocket（163行）
└── README.md                # 本文档
```

## 使用示例

### 1. 初始化DE管理器

```python
from src.core.event import EventBus
from src.core.de.de_manager import DEManager

# 获取EventBus实例
event_bus = EventBus.get_instance()

# 获取DEManager实例（单例）
de_manager = DEManager.get_instance(event_bus=event_bus)
```

### 2. 账户加载流程

当PM模块加载账户时，会自动触发DE模块创建对应的BinanceClient：

```python
# PM模块发布账户加载事件
await event_bus.publish(Event(
    subject="pm.account.loaded",
    data={
        "user_id": "user_001",
        "api_key": "your_api_key",
        "api_secret": "your_api_secret",
        "testnet": False
    }
))

# DE模块自动创建BinanceClient并发布de.client.connected事件
```

### 3. 订单执行流程

```python
# Trading模块发布订单创建事件
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

# DE模块自动执行订单并发布de.order.submitted或de.order.failed事件
```

### 4. 账户余额查询

```python
# Trading模块发布余额查询事件
await event_bus.publish(Event(
    subject="trading.get_account_balance",
    data={
        "user_id": "user_001",
        "asset": "USDT"
    }
))

# DE模块查询余额并发布de.account.balance事件
```

## API配置

### 币安期货API
- **生产环境**: `https://fapi.binance.com`
- **WebSocket**: `wss://fstream.binance.com`
- **认证方式**: HMAC SHA256签名

### 安全性
- ✅ API密钥仅存储在内存中
- ✅ 所有API调用都使用HMAC SHA256签名
- ✅ 日志中不记录敏感信息（API密钥、密钥等）
- ✅ 支持小额交易进行风险控制

## 错误处理

### 订单重试机制
- 5xx错误（服务器错误）：自动重试最多3次
- 4xx错误（客户端错误）：直接抛出异常，不重试
- 每次重试都生成新的时间戳和签名

### WebSocket重连
- 连接断开时自动重连
- K线订阅在重连后自动恢复
- ListenKey过期时自动重新创建

### 事件发布
- 所有错误都会发布对应的失败事件
- 关键操作失败时记录ERROR级别日志
- 不允许静默失败

## 测试

### 单元测试
```bash
# 运行所有DE模块单元测试
pytest tests/unit/test_de_*.py -v

# 运行特定测试
pytest tests/unit/test_binance_client.py -v
pytest tests/unit/test_de_manager.py -v
pytest tests/unit/test_market_websocket.py -v
pytest tests/unit/test_user_data_websocket.py -v
```

### 集成测试
```bash
# 运行DE模块集成测试
pytest tests/integration/test_de_integration.py -v
```

### 测试覆盖率
```bash
# 生成覆盖率报告
pytest --cov=src/core/de --cov-report=html --cov-report=term tests/
```

**当前测试覆盖率**: 79%
- BinanceClient: 79%
- DEManager: 90%
- MarketWebSocket: 69%
- UserDataWebSocket: 75%
- DEEvents: 100%

## 日志

DE模块使用Loguru进行日志记录，日志级别：
- `DEBUG`: 详细的调试信息（事件处理、API调用）
- `INFO`: 一般信息（客户端创建、订单提交成功）
- `WARNING`: 警告信息（资产未找到）
- `ERROR`: 错误信息（订单失败、API错误）
- `CRITICAL`: 严重错误（模块崩溃、连接断开）

日志格式包含文件名和行号，便于快速定位问题。

## 依赖

- `aiohttp 3.13.1` - 异步HTTP客户端
- `websockets 15.0.1` - WebSocket客户端
- `loguru` - 日志记录
- `src.core.event` - 事件总线
- `src.core.pm.pm_events` - PM模块事件

## 开发规范

### 代码风格
- 遵循Google Style规范
- 使用中文注释和日志
- 类型提示（Type Hints）
- 异步函数使用`async/await`

### 测试驱动开发（TDD）
- 先编写测试（红）
- 再实现功能（绿）
- 最后重构优化（重构）

### 错误处理
- 所有外部API调用必须有异常处理
- 关键操作失败时必须发布告警事件
- 不允许静默失败，所有错误必须记录日志

## 未来计划

- [ ] 支持更多订单类型（止损单、止盈单）
- [ ] 实现订单簿数据订阅
- [ ] 添加成交数据订阅
- [ ] 支持现货交易API
- [ ] 性能优化（连接池、批量请求）

## 许可证

本项目为私有项目，未经授权不得使用。
