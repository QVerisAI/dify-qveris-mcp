import json
from unittest.mock import Mock, patch

import pytest

from endpoints.qveris_client import QVerisClient, QVerisError


def response(status, payload, headers=None):
    raw = json.dumps(payload).encode()
    result = Mock()
    result.status_code = status
    result.headers = {"Content-Length": str(len(raw)), **(headers or {})}
    result.iter_content.return_value = [raw]
    return result


@patch("endpoints.qveris_client.requests.request")
def test_call_sends_key_only_in_authorization_header_and_encodes_tool_id(request):
    request.return_value = response(200, {"success": True})
    client = QVerisClient("secret-key")

    result = client.call({"tool_id": "provider/tool", "parameters": {"city": "Shanghai"}})

    assert result == {"success": True}
    _, url = request.call_args.args
    kwargs = request.call_args.kwargs
    assert url.endswith("/tools/execute?tool_id=provider%2Ftool")
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
    assert kwargs["json"] == {"parameters": {"city": "Shanghai"}}
    assert "secret-key" not in json.dumps(kwargs["json"])
    assert kwargs["allow_redirects"] is False


@patch("endpoints.qveris_client.requests.request")
def test_call_decodes_json_text_fallback_before_upstream_request(request):
    request.return_value = response(200, {"success": True})
    client = QVerisClient("secret-key")

    client.call(
        {
            "tool_id": "provider/tool",
            "parameters_json": '{"city":"Beijing","units":"metric"}',
            "search_id": "search-123",
        }
    )

    assert request.call_args.kwargs["json"] == {
        "parameters": {"city": "Beijing", "units": "metric"},
        "search_id": "search-123",
    }


@patch("endpoints.qveris_client.requests.request")
def test_probe_decodes_empty_json_object_fallback(request):
    request.return_value = response(200, {"schema": {"valid": True}})

    QVerisClient("secret-key").probe(
        {"tool_id": "provider/tool", "parameters_json": "{}"}
    )

    assert request.call_args.kwargs["json"] == {"parameters": {}}


@pytest.mark.parametrize("encoded", ["not-json", "[]", "null"])
def test_call_rejects_invalid_json_text_fallback_without_network(encoded):
    with patch("endpoints.qveris_client.requests.request") as request:
        with pytest.raises(QVerisError, match="parameters_json"):
            QVerisClient("secret-key").call(
                {"tool_id": "provider/tool", "parameters_json": encoded}
            )
        request.assert_not_called()


@patch("endpoints.qveris_client.requests.request")
def test_boolean_query_values_are_lowercase(request):
    request.return_value = response(200, {"data": {"items": []}})
    QVerisClient("secret-key").usage_history({"summary": True, "success": False})
    assert request.call_args.args[1].endswith("summary=true&success=false")


@patch("endpoints.qveris_client.requests.request")
def test_rate_limit_becomes_safe_tool_error(request):
    request.return_value = response(429, {"message": "too many requests"})
    with pytest.raises(QVerisError, match="rate limit") as error:
        QVerisClient("secret-key").discover({"query": "weather"})
    assert error.value.status == 429


@patch("endpoints.qveris_client.requests.request")
def test_redirect_is_rejected(request):
    request.return_value = response(302, {})
    with pytest.raises(QVerisError, match="redirect"):
        QVerisClient("secret-key").discover({"query": "weather"})
