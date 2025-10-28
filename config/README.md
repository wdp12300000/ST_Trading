# 配置文件说明

## 账户配置

### 创建配置文件

1. 复制示例配置文件：
```bash
cp config/pm_config.json.example config/pm_config.json
```

2. 编辑 `config/pm_config.json`，填入您的币安API密钥：
```json
{
  "users": {
    "user_001": {
      "name": "您的账户名称",
      "api_key": "您的币安API Key",
      "api_secret": "您的币安API Secret",
      "strategy": "ma_stop_st",
      "testnet": false
    }
  }
}
```

### 配置说明

- `name`: 账户名称（用于标识）
- `api_key`: 币安API密钥
- `api_secret`: 币安API密钥密码
- `strategy`: 使用的策略名称
- `testnet`: 是否使用测试网（true=测试网，false=生产环境）

### 安全提示

⚠️ **重要：** `pm_config.json` 包含敏感信息，已被添加到 `.gitignore`，不会被提交到Git仓库。

- ✅ 请勿将 `pm_config.json` 提交到版本控制
- ✅ 请勿分享您的API密钥
- ✅ 定期更换API密钥
- ✅ 为API密钥设置IP白名单
- ✅ 为API密钥设置最小权限（仅需要的权限）

### 获取币安API密钥

1. 登录币安账户
2. 进入 **API管理** 页面
3. 创建新的API密钥
4. 设置权限（建议仅开启必要权限）：
   - ✅ 读取信息
   - ✅ 现货和杠杆交易
   - ✅ 合约交易
   - ❌ 提现（不建议开启）
5. 设置IP白名单（推荐）
6. 保存API Key和Secret

### 测试网配置

如果您想使用币安测试网进行测试：

1. 访问 [币安期货测试网](https://testnet.binancefuture.com/)
2. 使用GitHub账号登录
3. 获取测试网API密钥
4. 在配置中设置 `"testnet": true`

### 文件结构

```
config/
├── .gitkeep                    # 保持目录存在
├── README.md                   # 本说明文件
├── pm_config.json.example      # 配置文件示例（可提交）
└── pm_config.json              # 实际配置文件（不提交，包含敏感信息）
```

