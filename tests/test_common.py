from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

from endpoints.common import (
    authenticate_endpoint,
    choose_protocol_version,
    create_session,
    delete_session,
    session_exists,
)


class MemoryStorage:
    def __init__(self):
        self.values = {}

    def set(self, key, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)


def make_request(authorization=None):
    headers = {} if authorization is None else {"Authorization": authorization}
    return Request(EnvironBuilder(path="/mcp", headers=headers).get_environ())


def test_endpoint_bearer_token_uses_exact_match():
    settings = {"endpoint_bearer_token": "correct-token"}
    assert authenticate_endpoint(make_request("Bearer correct-token"), settings) is None
    assert authenticate_endpoint(make_request("Bearer wrong-token"), settings).status_code == 401
    assert authenticate_endpoint(make_request(), settings).status_code == 401


def test_session_lifecycle():
    storage = MemoryStorage()
    session_id = create_session(storage)
    assert session_id.startswith("qv_")
    assert session_exists(storage, session_id)
    delete_session(storage, session_id)
    assert not session_exists(storage, session_id)


def test_protocol_negotiation_prefers_supported_client_version():
    assert choose_protocol_version("2024-11-05") == "2024-11-05"
    assert choose_protocol_version("unknown") == "2025-06-18"
