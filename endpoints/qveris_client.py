from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import requests


BASE_URL = "https://qveris.ai/api/v1"
CONNECT_TIMEOUT_SECONDS = 2
READ_TIMEOUT_SECONDS = 5
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class QVerisError(Exception):
    def __init__(self, message: str, *, status: int | None = None, details: Any = None):
        super().__init__(message)
        self.status = status
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"error": str(self)}
        if self.status is not None:
            result["status"] = self.status
        if self.details is not None:
            result["details"] = self.details
        return result


class QVerisClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise QVerisError("QVeris API key is not configured")
        self._api_key = api_key

    def discover(self, arguments: Mapping[str, Any]) -> Any:
        return self._request("POST", "/search", body=dict(arguments))

    def inspect(self, arguments: Mapping[str, Any]) -> Any:
        return self._request("POST", "/tools/by-ids", body=dict(arguments))

    def probe(self, arguments: Mapping[str, Any]) -> Any:
        tool_id = _required_string(arguments, "tool_id")
        body = _parameter_body(arguments)
        return self._request("POST", "/tools/probe", query={"tool_id": tool_id}, body=body)

    def call(self, arguments: Mapping[str, Any]) -> Any:
        tool_id = _required_string(arguments, "tool_id")
        body = _parameter_body(arguments)
        return self._request("POST", "/tools/execute", query={"tool_id": tool_id}, body=body)

    def usage_history(self, arguments: Mapping[str, Any]) -> Any:
        return self._request("GET", "/auth/usage/history/v2", query=dict(arguments))

    def credits_ledger(self, arguments: Mapping[str, Any]) -> Any:
        return self._request("GET", "/auth/credits/ledger", query=dict(arguments))

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        normalized_query = _normalize_query(query or {})
        url = f"{BASE_URL}{path}"
        if normalized_query:
            url = f"{url}?{urlencode(normalized_query)}"

        try:
            response = requests.request(
                method,
                url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "qveris-dify-mcp/0.1.0",
                },
                json=body if method == "POST" else None,
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                allow_redirects=False,
                stream=True,
            )
        except requests.Timeout as exc:
            raise QVerisError("QVeris request timed out") from exc
        except requests.RequestException as exc:
            raise QVerisError("QVeris is temporarily unreachable") from exc

        raw = _read_limited(response)
        parsed = _parse_json(raw)

        if 300 <= response.status_code < 400:
            raise QVerisError("QVeris returned an unexpected redirect", status=response.status_code)
        if response.status_code >= 400:
            message = _error_message(response.status_code, parsed)
            raise QVerisError(message, status=response.status_code, details=parsed)
        if parsed is None:
            raise QVerisError("QVeris returned an invalid JSON response", status=response.status_code)
        return parsed


def _required_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise QVerisError(f"Missing or invalid required parameter: {key}")
    return value


def _parameter_body(arguments: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        key: value
        for key, value in arguments.items()
        if key not in {"tool_id", "parameters_json"}
    }
    has_object = "parameters" in arguments
    has_json = "parameters_json" in arguments
    if not has_object and not has_json:
        raise QVerisError("Missing required parameter: parameters or parameters_json")
    if has_object and has_json:
        raise QVerisError("Provide exactly one of parameters or parameters_json")
    if has_object:
        if not isinstance(arguments.get("parameters"), Mapping):
            raise QVerisError("parameters must be an object")
        body["parameters"] = dict(arguments["parameters"])
        return body

    encoded = arguments.get("parameters_json")
    if not isinstance(encoded, str) or not encoded.strip():
        raise QVerisError("parameters_json must be a non-empty JSON string")
    try:
        decoded = json.loads(encoded)
    except json.JSONDecodeError as exc:
        raise QVerisError("parameters_json must contain valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise QVerisError("parameters_json must encode a JSON object")
    body["parameters"] = dict(decoded)
    return body


def _normalize_query(query: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, bool):
            result[key] = "true" if value else "false"
        else:
            result[key] = value
    return result


def _read_limited(response: requests.Response) -> bytes:
    content_length = response.headers.get("Content-Length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_RESPONSE_BYTES:
        response.close()
        raise QVerisError("QVeris response exceeded the 2 MiB gateway limit", status=502)

    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=65536):
        if not chunk:
            continue
        size += len(chunk)
        if size > MAX_RESPONSE_BYTES:
            response.close()
            raise QVerisError("QVeris response exceeded the 2 MiB gateway limit", status=502)
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_json(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _error_message(status: int, details: Any) -> str:
    if status == 401:
        return "QVeris rejected the API key"
    if status == 402:
        return "QVeris account has insufficient credits"
    if status == 429:
        return "QVeris rate limit exceeded; retry later"
    if isinstance(details, Mapping):
        candidate = details.get("message") or details.get("error") or details.get("error_message")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return f"QVeris request failed with HTTP {status}"
