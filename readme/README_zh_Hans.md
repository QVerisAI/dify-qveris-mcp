# 适用于 Dify 的 QVeris MCP 网关

QVeris MCP Gateway 是一个 Dify Extension 插件。安装后，它会生成一个由当前 Dify 工作区托管的 Streamable HTTP MCP Endpoint，并对外提供六项 QVeris 能力：`discover`、`inspect`、`probe`、`call`、`usage_history` 和 `credits_ledger`。

如果只需要直接连接 QVeris，无需二次托管，可使用官方 Hosted MCP：`https://mcp.qveris.ai/mcp`。

## 配置

1. 在 Dify 中安装 `.difypkg`。
2. 创建 QVeris MCP Gateway Endpoint。
3. 填入从 [QVeris 账户](https://qveris.ai/account?page=api-keys)创建的 API Key。
4. 自行生成一个高强度 Endpoint Bearer Token。该令牌与 QVeris API Key 不同，供 MCP 客户端访问 Dify Endpoint 时使用。
5. 复制 Dify 生成的、以 `/mcp` 结尾的地址。

客户端配置示例：

```json
{
  "mcpServers": {
    "qveris": {
      "type": "http",
      "url": "https://your-dify-host/e/generated-id/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_ENDPOINT_TOKEN"
      }
    }
  }
}
```

## 推荐调用顺序

```text
discover -> inspect -> probe -> call -> usage_history / credits_ledger
```

- `discover`：按自然语言查找能力，免费。
- `inspect`：读取当前参数结构、质量和价格信号，免费。
- `probe`：校验参数并获得调用前报价，不执行能力、不消耗积分。
- `call`：执行选定能力，可能消耗积分。
- `usage_history`：查询最终请求状态和扣费结果。
- `credits_ledger`：核对最终积分余额变动。

在 `call` 前应向用户展示能力与价格信息，并使用 Inspect 返回的当前 schema 构造参数。

## 扣子等表单式 MCP 客户端

`probe` 和 `call` 支持两种互斥的能力参数传法：

- `parameters`：标准的自由 JSON 对象，普通 MCP 客户端应优先使用。
- `parameters_json`：JSON 文本兼容入口，适用于无法在表单中渲染自由对象输入框的扣子插件调试器等客户端。

网关会校验并把 `parameters_json` 转换为标准 `parameters` 对象，不会把兼容字段传给 QVeris。每次调用只能填写其中一种。

## 安全限制

- 插件只向固定地址 `https://qveris.ai/api/v1` 发起 HTTPS 请求，并拒绝跳转。
- API Key 仅放入发送给 QVeris 的 Authorization 请求头，不返回给 MCP 客户端，也不写入日志。
- Endpoint Bearer Token 用于保护 Dify 生成的 MCP 地址。
- 插件不执行本地命令，不读取 Dify 宿主文件。
- 不同 QVeris 能力可能处理金融、医疗、位置、个人信息等敏感数据，请在调用前检查具体能力与服务商。
- 上游请求采用短超时，响应上限为 2 MiB。

服务器支持 `2025-06-18`、`2025-03-26` 和 `2024-11-05` 三个 MCP 协议版本。当前不提供 SSE，客户端应使用 Streamable HTTP POST。

更多信息参见 [隐私说明](../PRIVACY.md) 和 [QVeris 隐私政策](https://qveris.ai/privacy)。
