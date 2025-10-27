# ST_Trading - 加密货币量化交易系统

基于 Python 的加密货币量化交易系统，采用事件驱动架构（EDA），专注于币安永续合约交易。

## 技术栈

- Python 3.12+
- Flask
- SQLite3
- Loguru（日志工具）
- 币安官方 API

## 项目结构

```
ST_Trading/
├── src/              # 源代码
│   ├── core/         # 核心模块（事件驱动、EventBus等）
│   └── utils/        # 工具模块
├── tests/            # 测试代码
│   ├── unit/         # 单元测试
│   └── integration/  # 集成测试
├── logs/             # 日志文件
├── data/             # 数据库文件
├── config/           # 配置文件
└── venv/             # 虚拟环境
```

## 设计原则

- 面向对象设计，充分使用类方法
- 遵守开闭原则（Open-Closed Principle）
- 遵守依赖倒置原则（Dependency Inversion Principle）
- TDD 测试驱动开发
- YAGNI 原则（You Aren't Gonna Need It）

## 开发进度

- [x] 项目初始化
- [ ] 事件驱动模块（EDA）
- [ ] 数据管理模块
- [ ] 策略引擎
- [ ] 风险管理
- [ ] 订单执行

## 许可证

MIT License

