from endpoints.mcp import TOOLS, handle_message, initialize_result


class FakeClient:
    def discover(self, arguments):
        return {"search_id": "srch_test", "query": arguments["query"], "results": []}

    def inspect(self, arguments):
        return {"results": arguments["tool_ids"]}

    def probe(self, arguments):
        return {"schema": {"valid": True}, "tool_id": arguments["tool_id"]}

    def call(self, arguments):
        return {"success": True, "execution_id": "exec_test"}

    def usage_history(self, arguments):
        return {"filters": dict(arguments)}

    def credits_ledger(self, arguments):
        return {"filters": dict(arguments)}


def test_tool_catalog_contains_documented_six_tools():
    assert [tool["name"] for tool in TOOLS] == [
        "discover",
        "inspect",
        "probe",
        "call",
        "usage_history",
        "credits_ledger",
    ]


def test_probe_and_call_offer_json_text_fallback_for_form_clients():
    by_name = {tool["name"]: tool for tool in TOOLS}
    for name in ("probe", "call"):
        schema = by_name[name]["inputSchema"]
        assert schema["properties"]["parameters"]["type"] == "object"
        assert schema["properties"]["parameters_json"]["type"] == "string"
        assert "parameters" not in schema["required"]
        assert "parameters_json" not in schema["required"]


def test_initialize_result_exposes_protocol_and_tools_capability():
    result = initialize_result(1, "2025-06-18")
    assert result["id"] == 1
    assert result["result"]["protocolVersion"] == "2025-06-18"
    assert result["result"]["capabilities"]["tools"] == {"listChanged": False}


def test_tools_list_returns_catalog():
    response = handle_message(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, FakeClient()
    )
    assert response["result"]["tools"] == TOOLS


def test_discover_tool_call_returns_text_content():
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "discover", "arguments": {"query": "weather"}},
        },
        FakeClient(),
    )
    assert response["result"]["isError"] is False
    assert "srch_test" in response["result"]["content"][0]["text"]


def test_call_rejects_missing_parameters_without_upstream_request():
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "call", "arguments": {"tool_id": "tool.test"}},
        },
        FakeClient(),
    )
    assert response["result"]["isError"] is True
    assert "parameters" in response["result"]["content"][0]["text"]


def test_call_accepts_json_text_fallback():
    class RecordingClient(FakeClient):
        def call(self, arguments):
            self.arguments = dict(arguments)
            return {"success": True, "execution_id": "exec_json"}

    client = RecordingClient()
    response = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "call",
                "arguments": {
                    "tool_id": "tool.test",
                    "parameters_json": '{"city":"Beijing"}',
                },
            },
        },
        client,
    )
    assert response["result"]["isError"] is False
    assert client.arguments["parameters_json"] == '{"city":"Beijing"}'


def test_call_rejects_invalid_or_ambiguous_json_fallback():
    for arguments, expected in (
        ({"tool_id": "tool.test", "parameters_json": "not-json"}, "valid JSON"),
        (
            {"tool_id": "tool.test", "parameters": {}, "parameters_json": "{}"},
            "exactly one",
        ),
        ({"tool_id": "tool.test", "parameters_json": "[]"}, "JSON object"),
    ):
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 6,
                "method": "tools/call",
                "params": {"name": "call", "arguments": arguments},
            },
            FakeClient(),
        )
        assert response["result"]["isError"] is True
        assert expected in response["result"]["content"][0]["text"]


def test_notifications_do_not_return_jsonrpc_response():
    assert (
        handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
            FakeClient(),
        )
        is None
    )
