# TA模块 (Technical Analysis)

## 📋 模块概述

TA模块负责管理技术指标实例，处理K线数据，计算技术指标并生成交易信号。采用事件驱动架构，与ST、DE模块通过EventBus进行通信。

## 🏗️ 架构设计

### 核心类

#### 1. BaseIndicator类（指标抽象基类）
- **职责**：定义技术指标的基础框架和接口
- **模式**：抽象基类，所有具体指标必须继承此类
- **核心方法**：
  - `calculate(klines)`: 计算指标并返回信号（抽象方法）
  - `initialize(historical_klines)`: 使用历史K线初始化指标
  - `is_ready()`: 检查指标是否已就绪

#### 2. TAManager类（指标管理器）
- **职责**：管理所有指标实例的生命周期和事件处理
- **模式**：单例模式，全局唯一实例
- **核心功能**：
  - 指标实例创建和存储
  - 历史K线数据请求和处理
  - 实时K线数据处理
  - 指标结果聚合和事件发布

#### 3. IndicatorFactory类（指标工厂）
- **职责**：创建指标实例
- **模式**：工厂模式
- **功能**：注册指标类、创建指标实例

#### 4. TAEvents类（事件常量）
- **职责**：定义TA模块所有事件主题常量
- **优势**：避免硬编码字符串，提供IDE自动补全

#### 5. IndicatorSignal枚举
- **职责**：定义指标信号类型
- **值**：LONG（多头）、SHORT（空头）、NONE（无信号）

## 📦 模块结构

```
src/core/ta/
├── __init__.py              # 模块导出
├── base_indicator.py        # BaseIndicator抽象基类
├── ta_manager.py            # TAManager管理器
├── indicator_factory.py     # IndicatorFactory工厂类
├── ta_events.py             # 事件常量定义
└── README.md                # 本文档
```

## 🔄 事件流程

### 指标订阅流程

```
1. ST模块发布st.indicator.subscribe事件
   ↓
2. TAManager接收事件
   ↓
3. 使用IndicatorFactory创建指标实例
   ↓
4. 存储指标实例到_indicators字典
   ↓
5. 向DE模块请求历史K线（de.get_historical_klines）
   ↓
6. 发布ta.indicator.created事件
```

### 历史K线初始化流程

```
1. DE模块发布de.historical_klines.success事件
   ↓
2. TAManager接收事件
   ↓
3. 遍历所有指标，找到匹配的指标（user_id, symbol, interval）
   ↓
4. 调用indicator.initialize(klines)
   ↓
5. 指标标记为已就绪（_is_ready = True）
```

### 实时K线处理流程

```
1. DE模块发布de.kline.update事件（K线关闭时）
   ↓
2. TAManager接收事件（包含完整的200根K线）
   ↓
3. 遍历所有指标，找到匹配的指标（user_id, symbol, interval）
   ↓
4. 检查指标是否已就绪（is_ready）
   ↓
5. 调用indicator.calculate(klines)
   ↓
6. 将结果添加到聚合器
   ↓
7. 检查该交易对的所有指标是否都已完成
   ↓
8. 如果都完成，发布ta.calculation.completed事件
```

### 指标聚合流程

```
1. 每个指标计算完成后，结果添加到聚合器
   ↓
2. 聚合键：{user_id}_{symbol}
   ↓
3. 等待该交易对的所有指标都计算完成
   ↓
4. 发布ta.calculation.completed事件
   ↓
5. 清空聚合器
```

## 📡 事件定义

### TA模块订阅的事件（输入）

| 事件主题 | 来源 | 触发时机 | 数据内容 |
|---------|------|---------|---------|
| `st.indicator.subscribe` | ST模块 | 策略订阅指标 | user_id, symbol, indicator_name, indicator_params, timeframe |
| `de.historical_klines.success` | DE模块 | 历史K线获取成功 | user_id, symbol, interval, klines |
| `de.historical_klines.failed` | DE模块 | 历史K线获取失败 | user_id, symbol, interval, error |
| `de.kline.update` | DE模块 | K线关闭时 | user_id, symbol, interval, klines |

### TA模块发布的事件（输出）

| 事件主题 | 触发时机 | 数据内容 |
|---------|---------|---------|
| `ta.indicator.created` | 指标实例创建成功 | user_id, symbol, indicator_name, indicator_id |
| `ta.indicator.create_failed` | 指标实例创建失败 | user_id, symbol, indicator_name, error |
| `ta.calculation.completed` | 所有指标计算完成 | user_id, symbol, timeframe, indicators |
| `de.get_historical_klines` | 请求历史K线 | user_id, symbol, interval, limit |

## 🔧 使用示例

### 初始化TA管理器

```python
from src.core.event.event_bus import EventBus
from src.core.ta.ta_manager import TAManager

# 获取EventBus实例
event_bus = EventBus.get_instance()

# 获取TAManager实例（单例）
ta_manager = TAManager.get_instance(event_bus=event_bus)
```

### 创建自定义指标

```python
from src.core.ta.base_indicator import BaseIndicator, IndicatorSignal
from src.core.ta.indicator_factory import IndicatorFactory
from typing import Dict, Any, List

class MAStopIndicator(BaseIndicator):
    """MA Stop指标实现"""
    
    def __init__(self, user_id: str, symbol: str, interval: str, 
                 indicator_name: str, params: Dict[str, Any], event_bus):
        super().__init__(user_id, symbol, interval, indicator_name, params, event_bus)
        
        # 设置指标所需的最小K线数量
        self.period = params.get("period", 20)
        self._min_klines_required = self.period * 2
    
    async def calculate(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算MA Stop指标
        
        Args:
            klines: 完整的历史K线列表（200根）
        
        Returns:
            指标计算结果，包含signal和data
        """
        # 提取收盘价
        closes = [float(k["close"]) for k in klines]
        
        # 计算移动平均线
        ma_value = sum(closes[-self.period:]) / self.period
        
        # 判断信号
        latest_close = closes[-1]
        if latest_close > ma_value:
            signal = IndicatorSignal.LONG
        elif latest_close < ma_value:
            signal = IndicatorSignal.SHORT
        else:
            signal = IndicatorSignal.NONE
        
        return {
            "signal": signal.value,
            "data": {
                "ma_value": ma_value,
                "close": latest_close
            }
        }

# 注册指标到工厂
IndicatorFactory.register_indicator("ma_stop_ta", MAStopIndicator)
```

### 订阅指标（ST模块）

```python
from src.core.event.event import Event
from src.core.st.st_events import STEvents

# 发布指标订阅事件
subscribe_event = Event(
    subject=STEvents.INDICATOR_SUBSCRIBE,
    data={
        "user_id": "user_001",
        "symbol": "XRPUSDC",
        "indicator_name": "ma_stop_ta",
        "indicator_params": {"period": 20},
        "timeframe": "15m"
    },
    source="st"
)

await event_bus.publish(subscribe_event)
```

### 接收指标计算结果（ST模块）

```python
from src.core.ta.ta_events import TAEvents

async def handle_calculation_completed(event: Event):
    """处理指标计算完成事件"""
    user_id = event.data.get("user_id")
    symbol = event.data.get("symbol")
    timeframe = event.data.get("timeframe")
    indicators = event.data.get("indicators")
    
    # indicators格式：
    # {
    #     "ma_stop_ta": {
    #         "signal": "LONG",
    #         "data": {"ma_value": 1.05, "close": 1.10}
    #     },
    #     "rsi_ta": {
    #         "signal": "SHORT",
    #         "data": {"rsi": 70}
    #     }
    # }
    
    print(f"收到指标计算结果: {user_id}, {symbol}, {timeframe}")
    for indicator_name, result in indicators.items():
        print(f"  {indicator_name}: {result['signal']}")

# 订阅事件
event_bus.subscribe(TAEvents.CALCULATION_COMPLETED, handle_calculation_completed)
```

## 🎯 设计原则

### 1. 无K线缓存
- **原则**：TA模块不缓存K线数据
- **原因**：避免数据不一致，减少内存占用
- **实现**：每次计算都使用DE模块提供的完整历史K线列表

### 2. 指标聚合
- **原则**：等待同一交易对的所有指标计算完成后统一发布事件
- **聚合键**：`{user_id}_{symbol}`
- **好处**：减少事件数量，方便ST模块统一处理

### 3. 指标就绪状态
- **原则**：只处理已就绪的指标（`is_ready=True`）
- **实现**：指标初始化完成后才标记为就绪
- **好处**：避免未初始化的指标参与计算

### 4. 只处理关闭的K线
- **原则**：只在K线关闭时计算指标
- **实现**：DE模块只在`is_closed=True`时发布事件
- **好处**：避免频繁计算，确保数据完整性

## 📊 数据格式

### K线数据格式

```python
{
    "open": "1.0",
    "high": "1.1",
    "low": "0.9",
    "close": "1.05",
    "volume": "1000",
    "timestamp": 1499040000000,
    "is_closed": True
}
```

### 指标计算结果格式

```python
{
    "signal": "LONG",  # 或 "SHORT", "NONE"
    "data": {
        # 指标相关数据（由具体指标定义）
        "ma_value": 1.05,
        "close": 1.10
    }
}
```

## 🧪 测试

### 单元测试

```bash
# 运行TA模块单元测试
pytest tests/unit/ta/ -v

# 运行特定测试文件
pytest tests/unit/ta/test_ta_manager.py -v

# 运行特定测试类
pytest tests/unit/ta/test_ta_manager.py::TestTAManagerSingleton -v
```

### 集成测试

```bash
# 运行TA模块集成测试
pytest tests/integration/ta/ -v
```

## 📝 注意事项

1. **指标ID格式**：`{user_id}_{symbol}_{interval}_{indicator_name}`
   - 例如：`user_001_XRPUSDC_15m_ma_stop_ta`

2. **最小K线数量**：每个指标需要设置`_min_klines_required`
   - 默认值：200根K线
   - 建议：根据指标计算需求设置合理的值

3. **指标注册**：使用前必须先注册到IndicatorFactory
   ```python
   IndicatorFactory.register_indicator("indicator_name", IndicatorClass)
   ```

4. **事件数据完整性**：`de.kline.update`事件包含完整的历史K线列表
   - 不是单根K线，而是200根K线的列表

5. **聚合器清理**：指标计算完成后自动清空聚合器
   - 避免内存泄漏

## 🔗 相关模块

- **ST模块**：策略执行模块，订阅指标并接收计算结果
- **DE模块**：数据引擎模块，提供历史K线和实时K线数据
- **EventBus**：事件总线，负责模块间通信

