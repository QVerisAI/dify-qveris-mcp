from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from .common import jsonrpc_error
from .qveris_client import QVerisClient, QVerisError


SERVER_INFO = {"name": "qveris-mcp-gateway", "version": "0.1.0"}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "discover",
        "description": (
            "Discover QVeris capabilities from a natural-language query. This operation is free. "
            "Save search_id and select a tool_id from the response before inspecting or calling."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "description": "Capability-level query."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "session_id": {"type": "string", "description": "Stable QVeris task trace id."},
                "view": {"type": "string", "enum": ["routing", "full"]},
                "lang": {"type": "string", "enum": ["zh", "en"]},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "inspect",
        "description": (
            "Inspect current schemas, examples, quality signals, and cost signals for QVeris tool IDs. "
            "This operation is free."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 100,
                    "items": {"type": "string", "minLength": 1},
                },
                "search_id": {"type": "string"},
                "session_id": {"type": "string"},
                "view": {"type": "string", "enum": ["lean", "full"]},
            },
            "required": ["tool_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "probe",
        "description": (
            "Validate candidate parameters and obtain a pre-call quote without executing the "
            "capability or consuming credits."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "minLength": 1},
                "parameters": {
                    "type": "object",
                    "description": "Candidate parameters as a JSON object. Preferred for standard MCP clients.",
                },
                "parameters_json": {
                    "type": "string",
                    "description": (
                        "JSON-text fallback for clients that cannot render free-form object inputs. "
                        "Use instead of parameters. Example: {\"city\":\"Beijing\"}"
                    ),
                },
                "checks": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["schema", "quote", "coverage", "sample"]},
                    "default": ["schema", "quote"],
                },
                "live_budget": {"type": "string", "enum": ["none"], "default": "none"},
            },
            "required": ["tool_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "call",
        "description": (
            "Execute one QVeris capability. This operation can consume credits. Inspect and probe "
            "first, show the price to the user, and pass the exact selected tool schema."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_id": {"type": "string", "minLength": 1},
                "parameters": {
                    "type": "object",
                    "description": "Capability parameters as a JSON object. Preferred for standard MCP clients.",
                },
                "parameters_json": {
                    "type": "string",
                    "description": (
                        "JSON-text fallback for clients that cannot render free-form object inputs. "
                        "Use instead of parameters. Example: {\"city\":\"Beijing\"}"
                    ),
                },
                "search_id": {"type": "string"},
                "session_id": {"type": "string"},
                "model": {"type": "string", "maxLength": 128},
                "max_response_size": {"type": "integer", "minimum": -1},
                "respond_with": {
                    "type": "string",
                    "description": "full, summary, or fields:<JSONPath,...>",
                },
            },
            "required": ["tool_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "usage_history",
        "description": (
            "Audit final QVeris request status and charge outcome. Prefer execution_id or a compact "
            "summary instead of returning unrestricted history."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "event_type": {
                    "type": "string",
                    "enum": ["search", "search_by_ids", "tool_execute", "capabilities_query", "model_call"],
                },
                "kind": {"type": "string", "enum": ["discover", "call", "model"]},
                "success": {"type": "boolean"},
                "billable_success": {"type": "boolean"},
                "outcome": {"type": "string"},
                "reason_code": {"type": "string"},
                "has_execution_outcome": {"type": "boolean"},
                "charge_outcome": {
                    "type": "string",
                    "enum": ["charged", "included", "failed_not_charged", "failed_charged_review"],
                },
                "anomaly": {
                    "type": "string",
                    "enum": ["failed_charged_review", "missing_ledger_link", "missing_billing_snapshot"],
                },
                "search_id": {"type": "string"},
                "execution_id": {"type": "string"},
                "min_credits": {"type": "number", "minimum": 0},
                "max_credits": {"type": "number", "minimum": 0},
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 50000},
                "summary": {"type": "boolean"},
                "bucket": {"type": "string", "enum": ["hour", "day", "week"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "credits_ledger",
        "description": "Inspect final QVeris credit balance movements and reconcile a capability call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
                "entry_type": {"type": "string"},
                "scope": {"type": "string", "enum": ["account_history"]},
                "direction": {"type": "string", "enum": ["consume", "grant", "any"]},
                "min_credits": {"type": "number", "minimum": 0},
                "max_credits": {"type": "number", "minimum": 0},
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 500},
                "summary": {"type": "boolean"},
                "bucket": {"type": "string", "enum": ["hour", "day", "week"]},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "additionalProperties": False,
        },
    },
]


def initialize_result(request_id: Any, protocol_version: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "Use discover, inspect, and probe before call. The call tool may consume QVeris credits."
            ),
        },
    }


def handle_message(message: Any, client: QVerisClient) -> dict[str, Any] | None:
    if not isinstance(message, Mapping):
        return jsonrpc_error(None, -32600, "Invalid Request")

    request_id = message.get("id")
    if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
        return jsonrpc_error(request_id, -32600, "Invalid Request")

    method = message["method"]
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        return _handle_tool_call(request_id, message.get("params"), client)
    if method == "initialize":
        return jsonrpc_error(request_id, -32600, "initialize must start a new MCP session")
    return jsonrpc_error(request_id, -32601, f"Method not found: {method}")


def _handle_tool_call(request_id: Any, params: Any, client: QVerisClient) -> dict[str, Any]:
    if not isinstance(params, Mapping):
        return jsonrpc_error(request_id, -32602, "Invalid tools/call parameters")
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, Mapping):
        return jsonrpc_error(request_id, -32602, "Tool name and object arguments are required")

    handlers: dict[str, Callable[[Mapping[str, Any]], Any]] = {
        "discover": client.discover,
        "inspect": client.inspect,
        "probe": client.probe,
        "call": client.call,
        "usage_history": client.usage_history,
        "credits_ledger": client.credits_ledger,
    }
    handler = handlers.get(name)
    if handler is None:
        return _tool_result({"error": f"Unknown tool: {name}"}, is_error=True, request_id=request_id)

    validation_error = _validate_required_arguments(name, arguments)
    if validation_error:
        return _tool_result({"error": validation_error}, is_error=True, request_id=request_id)

    try:
        result = handler(arguments)
        business_error = isinstance(result, Mapping) and bool(result.get("error_message"))
        return _tool_result(result, is_error=business_error, request_id=request_id)
    except QVerisError as exc:
        return _tool_result(exc.as_dict(), is_error=True, request_id=request_id)
    except Exception:
        return _tool_result(
            {"error": "Unexpected gateway error; no request credentials were logged"},
            is_error=True,
            request_id=request_id,
        )


def _validate_required_arguments(name: str, arguments: Mapping[str, Any]) -> str | None:
    required: dict[str, tuple[str, ...]] = {
        "discover": ("query",),
        "inspect": ("tool_ids",),
        "probe": ("tool_id",),
        "call": ("tool_id",),
    }
    missing = [key for key in required.get(name, ()) if key not in arguments]
    if missing:
        return f"Missing required parameters: {', '.join(missing)}"
    if name == "discover" and not isinstance(arguments.get("query"), str):
        return "query must be a string"
    if name == "inspect":
        tool_ids = arguments.get("tool_ids")
        if not isinstance(tool_ids, list) or not tool_ids:
            return "tool_ids must be a non-empty array"
    if name in {"probe", "call"}:
        has_object = "parameters" in arguments
        has_json = "parameters_json" in arguments
        if not has_object and not has_json:
            return "Missing required parameters: parameters or parameters_json"
        if has_object and has_json:
            return "Provide exactly one of parameters or parameters_json"
        if has_object and not isinstance(arguments.get("parameters"), Mapping):
            return "parameters must be an object"
        if has_json:
            encoded = arguments.get("parameters_json")
            if not isinstance(encoded, str) or not encoded.strip():
                return "parameters_json must be a non-empty JSON string"
            try:
                decoded = json.loads(encoded)
            except json.JSONDecodeError:
                return "parameters_json must contain valid JSON"
            if not isinstance(decoded, Mapping):
                return "parameters_json must encode a JSON object"
    return None


def _tool_result(payload: Any, *, is_error: bool, request_id: Any) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, indent=2)}],
            "isError": is_error,
        },
    }
