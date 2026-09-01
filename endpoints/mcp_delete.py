from collections.abc import Mapping

from dify_plugin import Endpoint
from werkzeug import Request, Response

from .common import (
    authenticate_endpoint,
    delete_session,
    empty_response,
    require_session,
)


class QVerisMCPDeleteEndpoint(Endpoint):
    def _invoke(self, request: Request, values: Mapping, settings: Mapping) -> Response:
        auth_error = authenticate_endpoint(request, settings)
        if auth_error:
            return auth_error
        session_id, session_error = require_session(request, self.session.storage)
        if session_error:
            return session_error
        delete_session(self.session.storage, session_id)
        return empty_response(204)
