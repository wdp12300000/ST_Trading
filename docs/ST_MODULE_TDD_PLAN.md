# ST 策略执行模块 TDD 开发计划

## 1. 模块概述

ST（Strategy Execution）模块负责：
- 加载策略配置
- 创建策略实例
- 处理指标信号生成交易决策
- 管理持仓状态（内存中，不持久化）
- 触发网格交易和反向建仓

## 2. 核心组件（最小化设计）

```
ST模块
├── st_events.py          # 事件常量定义
├── st_manager.py         # STManager 单例管理器
└── base_strategy.py      # BaseStrategy 抽象基类（内部用字典管理持仓）
```

**说明**：
- 不需要单独的 `PositionManager` 类
- 不需要单独的 `StrategyConfigLoader` 类
- 持仓状态用字典管理：`{symbol: PositionState}`

## 3. 事件定义

### 订阅的事件（输入）

| 事件主题 | 发布者 | 数据格式 | 说明 |
|---------|--------|---------|------|
| `pm.account.loaded` | PM模块 | `{user_id, strategy, ...}` | 触发策略加载 |
| `ta.indicator.signal` | TA模块 | `{user_id, symbol, signal_type, ...}` | signal_type为LONG/SHORT |
| `tr.position.opened` | TR模块 | `{user_id, symbol, side, entry_price, ...}` | 更新持仓为LONG/SHORT，可能触发网格 |
| `tr.position.closed` | TR模块 | `{user_id, symbol, ...}` | 更新持仓为NONE，可能触发反向建仓 |

### 发布的事件（输出）

| 事件主题 | 触发时机 | 数据格式 | 说明 |
|---------|---------|---------|------|
| `st.strategy.loaded` | 策略创建成功 | `{user_id, strategy, timeframe, trading_pairs}` | 策略加载成功 |
| `st.indicator.subscribe` | 策略创建后 | `{user_id, symbol, indicator_name, indicator_params}` | 请求TA订阅指标 |
| `st.signal.generated` | 生成交易信号 | `{user_id, symbol, side, action, quantity}` | action为OPEN/CLOSE |
| `st.grid.create` | 持仓开启后 | `{user_id, symbol, entry_price, grid_levels, grid_ratio, move_up, move_down}` | 创建网格交易 |

## 4. 持仓状态枚举

```python
from enum import Enum

class PositionState(Enum):
    NONE = "NONE"    # 无持仓
    LONG = "LONG"    # 多头持仓
    SHORT = "SHORT"  # 空头持仓
```

## 5. TDD 开发任务（红-绿-重构）

### 任务 1：事件常量定义

**文件**：`src/core/st/st_events.py`

**内容**：
```python
# 订阅的事件（输入）
ACCOUNT_LOADED = "pm.account.loaded"
INDICATOR_SIGNAL = "ta.indicator.signal"
POSITION_OPENED = "tr.position.opened"
POSITION_CLOSED = "tr.position.closed"

# 发布的事件（输出）
STRATEGY_LOADED = "st.strategy.loaded"
INDICATOR_SUBSCRIBE = "st.indicator.subscribe"
SIGNAL_GENERATED = "st.signal.generated"
GRID_CREATE = "st.grid.create"
```

---

### 任务 2：STManager 单例模式（TDD）

#### 测试 2.1：验证单例模式

**测试文件**：`tests/unit/test_st_manager.py`

**测试代码**：
```python
def test_st_manager_singleton():
    """测试 STManager 是单例"""
    event_bus = EventBus.get_instance()
    manager1 = STManager.get_instance(event_bus)
    manager2 = STManager.get_instance(event_bus)
    assert manager1 is manager2
```

**实现代码**：
```python
class STManager:
    _instance = None
    
    @classmethod
    def get_instance(cls, event_bus: EventBus) -> 'STManager':
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance
    
    def __init__(self, event_bus: EventBus):
        if STManager._instance is not None:
            raise RuntimeError("使用 get_instance() 获取单例")
        self._event_bus = event_bus
        self._strategies: Dict[str, BaseStrategy] = {}
```

**重构**：优化代码结构

---

#### 测试 2.2：验证订阅 pm.account.loaded 事件

**测试代码**：
```python
async def test_subscribe_account_loaded():
    """测试 STManager 订阅 pm.account.loaded 事件"""
    event_bus = EventBus.get_instance()
    manager = STManager.get_instance(event_bus)
    
    # 验证订阅了事件
    assert ACCOUNT_LOADED in event_bus._subscribers
```

**实现代码**：
```python
def __init__(self, event_bus: EventBus):
    # ...
    self._event_bus.subscribe(ACCOUNT_LOADED, self._handle_account_loaded)

async def _handle_account_loaded(self, event: Event):
    """处理账户加载事件"""
    pass  # 先空实现
```

---

#### 测试 2.3：验证加载策略配置文件

**测试代码**：
```python
async def test_load_strategy_config():
    """测试加载策略配置文件"""
    manager = STManager.get_instance(event_bus)
    config = await manager._load_config("user_001", "ma_stop_st")
    
    assert config is not None
    assert "timeframe" in config
    assert "leverage" in config
    assert "trading_pairs" in config
```

**实现代码**：
```python
async def _load_config(self, user_id: str, strategy: str) -> Dict:
    """加载策略配置文件"""
    config_path = f"config/strategies/{user_id}/{strategy}.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        logger.info(f"[st_manager.py:{lineno()}] 加载策略配置成功: {user_id}/{strategy}")
        return config
    except FileNotFoundError:
        logger.error(f"[st_manager.py:{lineno()}] 配置文件不存在: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"[st_manager.py:{lineno()}] 配置文件格式错误: {e}")
        return None
```

---

#### 测试 2.4：验证配置验证

**测试代码**：
```python
def test_validate_config_success():
    """测试配置验证成功"""
    config = {
        "timeframe": "15m",
        "leverage": 4,
        "position_side": "BOTH",
        "margin_mode": "CROSS",
        "margin_type": "USDC",
        "trading_pairs": [{"symbol": "XRPUSDC", "indicator_params": {}}]
    }
    assert STManager._validate_config(config) is True

def test_validate_config_missing_field():
    """测试配置缺少必需字段"""
    config = {"timeframe": "15m"}
    assert STManager._validate_config(config) is False
```

**实现代码**：
```python
@staticmethod
def _validate_config(config: Dict) -> bool:
    """验证配置文件"""
    required_fields = ["timeframe", "leverage", "position_side", 
                      "margin_mode", "margin_type", "trading_pairs"]
    
    for field in required_fields:
        if field not in config:
            logger.error(f"[st_manager.py:{lineno()}] 配置缺少必需字段: {field}")
            return False
    
    if not isinstance(config["trading_pairs"], list) or len(config["trading_pairs"]) == 0:
        logger.error(f"[st_manager.py:{lineno()}] trading_pairs 必须是非空数组")
        return False
    
    return True
```

---

### 任务 3：BaseStrategy 基础框架（TDD）

#### 测试 3.1：验证策略实例创建

**测试文件**：`tests/unit/test_base_strategy.py`

**测试代码**：
```python
def test_create_strategy_instance():
    """测试创建策略实例"""
    config = {...}  # 配置
    strategy = MaStopStrategy("user_001", config, event_bus)
    
    assert strategy._user_id == "user_001"
    assert strategy._config == config
```

**实现代码**：
```python
class BaseStrategy(ABC):
    def __init__(self, user_id: str, config: Dict, event_bus: EventBus):
        self._user_id = user_id
        self._config = config
        self._event_bus = event_bus
        self._positions: Dict[str, PositionState] = {}
```

---

#### 测试 3.2：验证持仓状态初始化

**测试代码**：
```python
def test_position_initialization():
    """测试持仓状态初始化为 NONE"""
    config = {"trading_pairs": [{"symbol": "XRPUSDC"}, {"symbol": "BTCUSDC"}]}
    strategy = MaStopStrategy("user_001", config, event_bus)
    
    assert strategy.get_position("XRPUSDC") == PositionState.NONE
    assert strategy.get_position("BTCUSDC") == PositionState.NONE
```

**实现代码**：
```python
def __init__(self, user_id: str, config: Dict, event_bus: EventBus):
    # ...
    # 初始化所有交易对的持仓状态为 NONE
    for pair in config["trading_pairs"]:
        self._positions[pair["symbol"]] = PositionState.NONE

def get_position(self, symbol: str) -> PositionState:
    """获取持仓状态"""
    return self._positions.get(symbol, PositionState.NONE)
```

---

#### 测试 3.3：验证发布 st.strategy.loaded 事件

**测试代码**：
```python
async def test_publish_strategy_loaded():
    """测试策略创建后发布 st.strategy.loaded 事件"""
    event_published = False
    
    async def handler(event: Event):
        nonlocal event_published
        event_published = True
        assert event.data["user_id"] == "user_001"
        assert event.data["strategy"] == "ma_stop_st"
    
    event_bus.subscribe(STRATEGY_LOADED, handler)
    strategy = MaStopStrategy("user_001", config, event_bus)
    await strategy._publish_strategy_loaded()
    
    await asyncio.sleep(0.1)
    assert event_published is True
```

**实现代码**：
```python
async def _publish_strategy_loaded(self):
    """发布策略加载成功事件"""
    await self._event_bus.publish(Event(
        subject=STRATEGY_LOADED,
        data={
            "user_id": self._user_id,
            "strategy": self._config.get("strategy_name"),
            "timeframe": self._config["timeframe"],
            "trading_pairs": [p["symbol"] for p in self._config["trading_pairs"]]
        },
        source="st"
    ))
    logger.info(f"[base_strategy.py:{lineno()}] 策略加载成功: {self._user_id}")
```

---

#### 测试 3.4：验证发布 st.indicator.subscribe 事件

**测试代码**：
```python
async def test_publish_indicator_subscribe():
    """测试为每个交易对发布 st.indicator.subscribe 事件"""
    events = []
    
    async def handler(event: Event):
        events.append(event.data)
    
    event_bus.subscribe(INDICATOR_SUBSCRIBE, handler)
    strategy = MaStopStrategy("user_001", config, event_bus)
    await strategy._publish_indicator_subscriptions()
    
    await asyncio.sleep(0.1)
    assert len(events) == 2  # 假设有2个交易对
    assert events[0]["symbol"] == "XRPUSDC"
```

**实现代码**：
```python
async def _publish_indicator_subscriptions(self):
    """为每个交易对发布指标订阅事件"""
    for pair in self._config["trading_pairs"]:
        for indicator_name, params in pair["indicator_params"].items():
            await self._event_bus.publish(Event(
                subject=INDICATOR_SUBSCRIBE,
                data={
                    "user_id": self._user_id,
                    "symbol": pair["symbol"],
                    "indicator_name": indicator_name,
                    "indicator_params": params
                },
                source="st"
            ))
            logger.info(f"[base_strategy.py:{lineno()}] 发布指标订阅: {pair['symbol']}/{indicator_name}")
```

---

### 任务 4-7：继续按 TDD 流程实现

- 任务 4：指标信号处理
- 任务 5：持仓状态管理
- 任务 6：网格交易
- 任务 7：反向建仓
- 任务 8：集成测试

## 6. 开发原则

1. **严格遵守 TDD**：先写测试，再写代码，红-绿-重构
2. **YAGNI**：只实现讨论中明确需要的功能
3. **不过早优化**：最小可行实现
4. **面向对象**：充分使用类方法
5. **开闭原则**：对扩展开放，对修改关闭
6. **依赖倒置**：依赖抽象而非具体实现

## 7. 下一步

请确认以上 TDD 开发计划，我将开始执行：
1. 创建 `src/core/st/st_events.py`
2. 编写第一个测试：`test_st_manager_singleton`
3. 实现最小代码使测试通过
4. 重构
5. 继续下一个测试...

