from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dify_plugin import Endpoint
from werkzeug import Request, Response

from .common import (
    PROTOCOL_HEADER,
    SESSION_HEADER,
    authenticate_endpoint,
    choose_protocol_version,
    create_session,
    empty_response,
    json_response,
    jsonrpc_error,
    require_session,
)
from .mcp import handle_message, initialize_result
from .qveris_client import QVerisClient


class QVerisMCPPostEndpoint(Endpoint):
    def _invoke(self, request: Request, values: Mapping, settings: Mapping) -> Response:
        auth_error = authenticate_endpoint(request, settings)
        if auth_error:
            return auth_error

        if not request.is_json:
            return json_response(
                jsonrpc_error(None, -32700, "Content-Type must be application/json"), status=415
            )
        try:
            payload: Any = request.get_json(silent=False)
        except Exception:
            return json_response(jsonrpc_error(None, -32700, "Parse error"), status=400)

        if isinstance(payload, list):
            if not payload:
                return json_response(jsonrpc_error(None, -32600, "Invalid Request"), status=400)
            if any(isinstance(item, Mapping) and item.get("method") == "initialize" for item in payload):
                return json_response(
                    jsonrpc_error(None, -32600, "initialize is not allowed in a JSON-RPC batch"),
                    status=400,
                )
            _, session_error = require_session(request, self.session.storage)
            if session_error:
                return session_error
            client = QVerisClient(str(settings.get("qveris_api_key") or ""))
            responses = [response for item in payload if (response := handle_message(item, client))]
            if not responses:
                return empty_response(202)
            return json_response(responses, headers=_protocol_headers(request))

        if not isinstance(payload, Mapping):
            return json_response(jsonrpc_error(None, -32600, "Invalid Request"), status=400)

        if payload.get("method") == "initialize":
            params = payload.get("params") if isinstance(payload.get("params"), Mapping) else {}
            protocol_version = choose_protocol_version(params.get("protocolVersion"))
            session_id = create_session(self.session.storage)
            return json_response(
                initialize_result(payload.get("id"), protocol_version),
                headers={SESSION_HEADER: session_id, PROTOCOL_HEADER: protocol_version},
            )

        _, session_error = require_session(request, self.session.storage)
        if session_error:
            return session_error
        client = QVerisClient(str(settings.get("qveris_api_key") or ""))
        response = handle_message(payload, client)
        if response is None:
            return empty_response(202, headers=_protocol_headers(request))
        return json_response(response, headers=_protocol_headers(request))


def _protocol_headers(request: Request) -> dict[str, str]:
    requested = request.headers.get(PROTOCOL_HEADER)
    return {PROTOCOL_HEADER: choose_protocol_version(requested)}
