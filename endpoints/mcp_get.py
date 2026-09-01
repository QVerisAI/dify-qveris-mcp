from collections.abc import Mapping

from dify_plugin import Endpoint
from werkzeug import Request, Response

from .common import authenticate_endpoint, json_response, jsonrpc_error, require_session


class QVerisMCPGetEndpoint(Endpoint):
    def _invoke(self, request: Request, values: Mapping, settings: Mapping) -> Response:
        auth_error = authenticate_endpoint(request, settings)
        if auth_error:
            return auth_error
        _, session_error = require_session(request, self.session.storage)
        if session_error:
            return session_error
        return json_response(
            jsonrpc_error(None, -32004, "SSE streams are not supported; use Streamable HTTP POST"),
            status=405,
            headers={"Allow": "POST, DELETE, OPTIONS"},
        )
