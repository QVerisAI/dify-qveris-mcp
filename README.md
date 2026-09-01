# QVeris MCP Gateway for Dify

QVeris MCP Gateway is a Dify Extension plugin that exposes six QVeris operations through a Dify-hosted Streamable HTTP MCP endpoint. Install the plugin, create an endpoint, and connect any compatible MCP client to the generated Dify URL.

> This gateway is for teams that want a workspace-owned Dify endpoint. If you only need direct QVeris access, use the hosted endpoint at `https://mcp.qveris.ai/mcp`.

[Chinese documentation](readme/README_zh_Hans.md)

## Available tools

| Tool | QVeris API | Cost behavior |
| --- | --- | --- |
| `discover` | `POST /search` | Free |
| `inspect` | `POST /tools/by-ids` | Free |
| `probe` | `POST /tools/probe` | Free; validates inputs and returns a quote |
| `call` | `POST /tools/execute` | May consume credits |
| `usage_history` | `GET /auth/usage/history/v2` | Free audit query |
| `credits_ledger` | `GET /auth/credits/ledger` | Free balance query |

Use the safe sequence `discover -> inspect -> probe -> call`. Show the selected capability's pricing information before calling it, then use `usage_history` or `credits_ledger` for final settlement details.

### Form-based MCP clients

`probe` and `call` accept capability parameters in either of two forms:

- `parameters`: the standard free-form JSON object, preferred for normal MCP clients.
- `parameters_json`: a JSON-encoded string fallback for clients whose forms cannot render a free-form object input, including some Coze plugin debugger versions.

Provide exactly one form. The gateway validates `parameters_json`, converts it to the canonical `parameters` object, and never forwards the compatibility field to QVeris.

## Requirements

- Dify 1.3.0 or later
- A QVeris API key from [QVeris API Keys](https://qveris.ai/account?page=api-keys)
- A strong, user-generated endpoint bearer token
- Outbound HTTPS access to `qveris.ai`

## Configure the extension

1. Install the `.difypkg` in Dify.
2. Create a QVeris MCP Gateway endpoint.
3. Enter the QVeris API key. The gateway sends it only to `https://qveris.ai/api/v1` in the `Authorization` header.
4. Create and enter a strong endpoint bearer token. This is separate from the QVeris API key.
5. Copy the generated endpoint URL ending in `/mcp`.

Example MCP client configuration:

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

The server negotiates MCP protocol versions `2025-06-18`, `2025-03-26`, and `2024-11-05`. It supports `initialize`, `notifications/initialized`, `ping`, `tools/list`, and `tools/call`. Session termination is available through `DELETE /mcp` with `Mcp-Session-Id`. SSE is not supported; clients must use Streamable HTTP POST.

## Security and network behavior

- The endpoint bearer token protects the Dify-generated URL.
- The QVeris API key is never returned to MCP clients or written to application logs.
- Outbound requests use a fixed `https://qveris.ai/api/v1` base URL, reject redirects, time out quickly, and cap responses at 2 MiB.
- The plugin does not execute local commands or access Dify host files.
- QVeris capabilities can process financial, medical, location, personal, or other sensitive inputs depending on the selected tool. Review the tool schema and provider before calling it.
- Some calls are billable. Probe and surface the quote before a paid call.

See [PRIVACY.md](PRIVACY.md) and [QVeris Privacy](https://qveris.ai/privacy).

## Local development

Python 3.12 is required.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/python -m pytest
```

On macOS or Linux, activate the virtual environment with the platform-specific command. For remote Dify debugging, copy `.env.example` to `.env`, enter the Dify debug credentials, and run:

```bash
python -m main
```

Package with the current Dify plugin CLI:

```bash
dify-plugin plugin package ./dify-qveris-mcp
```

The expected package name for Marketplace submission is `qveris-mcp-0.1.0.difypkg`.

## Marketplace submission

Submit exactly one package file to the official `langgenius/dify-plugins` repository at:

```text
qverisai/qveris-mcp/qveris-mcp-0.1.0.difypkg
```

Use an English PR title such as `feat: add QVeris MCP Gateway 0.1.0`, select **New plugin** and **High risk**, and disclose that the plugin is a broad capability gateway that can process sensitive queries and make billable calls.

## Support

- Source: <https://github.com/QVerisAI/dify-qveris-mcp>
- QVeris: <https://qveris.ai>
- Contact: <contact@qveris.ai>
