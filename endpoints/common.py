from __future__ import annotations

import hmac
import json
import re
import uuid
from collections.abc import Mapping
from typing import Any

from werkzeug import Request, Response


SESSION_PREFIX = "qveris-mcp-session:"
SESSION_PATTERN = re.compile(r"^qv_[a-f0-9]{32}$")
PROTOCOL_HEADER = "MCP-Protocol-Version"
SESSION_HEADER = "Mcp-Session-Id"
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": (
            "Authorization, Content-Type, Accept, Mcp-Session-Id, "
            "MCP-Protocol-Version, Last-Event-ID"
        ),
        "Access-Control-Expose-Headers": "Mcp-Session-Id, MCP-Protocol-Version",
    }


def json_response(
    payload: Any,
    status: int = 200,
    *,
    headers: Mapping[str, str] | None = None,
) -> Response:
    response_headers = cors_headers()
    if headers:
        response_headers.update(headers)
    return Response(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        status=status,
        content_type="application/json",
        headers=response_headers,
    )


def empty_response(status: int, *, headers: Mapping[str, str] | None = None) -> Response:
    response_headers = cors_headers()
    if headers:
        response_headers.update(headers)
    return Response("", status=status, headers=response_headers)


def jsonrpc_error(request_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def authenticate_endpoint(request: Request, settings: Mapping[str, Any]) -> Response | None:
    configured = str(settings.get("endpoint_bearer_token") or "")
    authorization = request.headers.get("Authorization", "")
    scheme, separator, supplied = authorization.partition(" ")
    valid = (
        bool(configured)
        and bool(separator)
        and scheme.lower() == "bearer"
        and hmac.compare_digest(supplied.strip(), configured)
    )
    if valid:
        return None
    return json_response(
        jsonrpc_error(None, -32001, "Unauthorized: invalid or missing endpoint bearer token"),
        status=401,
        headers={"WWW-Authenticate": "Bearer"},
    )


def choose_protocol_version(requested: Any) -> str:
    if isinstance(requested, str) and requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return SUPPORTED_PROTOCOL_VERSIONS[0]


def create_session(storage: Any) -> str:
    session_id = f"qv_{uuid.uuid4().hex}"
    storage.set(f"{SESSION_PREFIX}{session_id}", b"active")
    return session_id


def session_id_from_request(request: Request) -> str:
    return request.headers.get(SESSION_HEADER, "").strip()


def session_exists(storage: Any, session_id: str) -> bool:
    if not SESSION_PATTERN.fullmatch(session_id):
        return False
    return storage.get(f"{SESSION_PREFIX}{session_id}") is not None


def require_session(request: Request, storage: Any) -> tuple[str | None, Response | None]:
    session_id = session_id_from_request(request)
    if not session_id:
        return None, json_response(
            jsonrpc_error(None, -32002, "Missing Mcp-Session-Id header"), status=400
        )
    if not session_exists(storage, session_id):
        return None, json_response(
            jsonrpc_error(None, -32003, "Unknown or expired MCP session"), status=404
        )
    return session_id, None


def delete_session(storage: Any, session_id: str) -> None:
    storage.delete(f"{SESSION_PREFIX}{session_id}")
