from collections.abc import Mapping

from dify_plugin import Endpoint
from werkzeug import Request, Response

from .common import empty_response


class QVerisMCPOptionsEndpoint(Endpoint):
    def _invoke(self, request: Request, values: Mapping, settings: Mapping) -> Response:
        return empty_response(204, headers={"Access-Control-Max-Age": "86400"})
