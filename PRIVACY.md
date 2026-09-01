# Privacy Policy for QVeris MCP Gateway

Last updated: September 1, 2026

## Scope

QVeris MCP Gateway is a Dify Extension maintained by QVerisAI. It receives MCP requests from clients, converts tool calls into requests to the fixed QVeris API origin at `https://qveris.ai/api/v1`, and returns the API response to the requesting MCP client.

## Data processed

Depending on the selected QVeris capability, the plugin may process natural-language queries, capability identifiers, capability parameters, model identifiers, session and search identifiers, execution identifiers, usage records, billing records, and data returned by third-party capability providers. Parameters may contain personal, financial, medical, location, or other sensitive information when a user chooses a capability that requires it.

## Credentials

The Dify endpoint bearer token is used only to authenticate MCP clients. The QVeris API key is sent only to the fixed QVeris API origin in an HTTPS `Authorization` header. The plugin does not return either credential to MCP clients and does not intentionally log credentials or complete request headers.

## Storage and retention

The plugin stores only opaque MCP session identifiers in Dify plugin storage so that it can validate and terminate sessions. It does not intentionally persist MCP tool arguments or QVeris responses in plugin storage. Endpoint settings and their retention are controlled by the Dify workspace where the plugin is installed.

QVeris may retain queries, execution data, usage audit records, and billing records as described in the [QVeris Privacy Policy](https://qveris.ai/privacy). Individual third-party capability providers may process and retain submitted parameters under their own terms and privacy policies. Retention can therefore vary by selected capability and provider.

## Third parties and international transfer

Tool requests are sent to QVeris. QVeris may route a call to the third-party provider associated with the capability selected by the user. Data may be processed in jurisdictions different from the user or Dify workspace.

## Deletion and user choices

Users can terminate an MCP session with `DELETE /mcp`, remove the Dify endpoint, uninstall the plugin, rotate or revoke the endpoint bearer token, and revoke the QVeris API key. For deletion or privacy requests concerning data held by QVeris, contact `contact@qveris.ai`. Requests concerning a third-party capability provider must be directed to that provider when applicable.

## Security

The gateway uses HTTPS, a fixed QVeris API origin, endpoint bearer authentication, short upstream timeouts, redirect rejection, and a response-size limit. No network service can be guaranteed completely secure; users should avoid sending unnecessary sensitive data and should grant access only to trusted MCP clients.

## Contact

Privacy questions: `contact@qveris.ai`
