import base64
import json
import os
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

from fastapi import Request
from fastapi.responses import JSONResponse

from orka.server import app, sanitize_for_json, run_execution, api_health, health_basic
from orka.orchestrator import Orchestrator

class CustomObject:
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return isinstance(other, CustomObject) and self.value == other.value

    def __repr__(self):
        return f"CustomObject(value={self.value})"

class NonSerializableObject:
    __slots__ = ()
    def __init__(self):
        pass

    def __repr__(self):
        return "<NonSerializableObject>"

class TestSanitizeForJson:
    def test_primitive_types(self):
        assert sanitize_for_json("hello") == "hello"
        assert sanitize_for_json(123) == 123
        assert sanitize_for_json(123.45) == 123.45
        assert sanitize_for_json(True) is True
        assert sanitize_for_json(None) is None

    def test_bytes_object(self):
        data = b"test bytes"
        expected = {"__type": "bytes", "data": base64.b64encode(data).decode("utf-8")}
        assert sanitize_for_json(data) == expected

    def test_list_and_tuple(self):
        data = [1, "two", b"three"]
        expected = [1, "two", {"__type": "bytes", "data": base64.b64encode(b"three").decode("utf-8")}]
        assert sanitize_for_json(data) == expected

        data = (1, "two", b"three")
        expected = [1, "two", {"__type": "bytes", "data": base64.b64encode(b"three").decode("utf-8")}]
        assert sanitize_for_json(data) == expected

    def test_dictionary(self):
        data = {"key1": 1, "key2": b"value2"}
        expected = {"key1": 1, "key2": {"__type": "bytes", "data": base64.b64encode(b"value2").decode("utf-8")}} 
        assert sanitize_for_json(data) == expected

    def test_datetime_object(self):
        dt = datetime(2023, 1, 1, 10, 30, 0)
        assert sanitize_for_json(dt) == "2023-01-01T10:30:00"

    def test_custom_object_with_dict(self):
        obj = CustomObject("custom_value")
        expected = {"__type": "CustomObject", "data": {"value": "custom_value"}}
        assert sanitize_for_json(obj) == expected

    def test_custom_object_without_dict(self):
        class NoDictObject:
            __slots__ = ('value',)
            def __init__(self, value):
                self.value = value
        obj = NoDictObject("slot_value")
        assert sanitize_for_json(obj) == f"<non-serializable: {type(obj).__name__}>"

    def test_custom_object_dict_conversion_failure(self):
        class FailingDictObject:
            @property
            def __dict__(self):
                raise Exception("Dict access failed")
        obj = FailingDictObject()
        assert sanitize_for_json(obj) == "<sanitization-error: Dict access failed>"

    def test_non_serializable_object(self):
        obj = NonSerializableObject()
        assert sanitize_for_json(obj) == f"<non-serializable: {type(obj).__name__}>"

    @patch("orka.server.logger")
    def test_sanitization_error_logging(self, mock_logger):
        class ErrorObject:
            @property
            def __dict__(self):
                raise Exception("Error during dict access")
        obj = ErrorObject()
        result = sanitize_for_json(obj)
        assert result == "<sanitization-error: Error during dict access>"
        mock_logger.warning.assert_called_once()
        assert "Failed to sanitize object for JSON: Error during dict access" in mock_logger.warning.call_args[0][0]


class TestRunExecution:
    @pytest.fixture
    def mock_orchestrator_instance(self):
        mock_orch = AsyncMock(spec=Orchestrator)
        mock_orch.run.return_value = [{"agent": "output"}]
        return mock_orch

    @pytest.fixture
    def mock_request(self):
        request = MagicMock(spec=Request)
        request.json = AsyncMock(return_value={
            "input": "test input",
            "yaml_config": """orchestrator:
  id: test_orch
agents:
  - id: agent1
    type: dummy"""
        })
        return request

    @pytest.mark.asyncio
    @patch("orka.server.Orchestrator")
    @patch("tempfile.mkstemp", return_value=(123, "/tmp/test_config.yml"))
    @patch("os.close", MagicMock())
    @patch("os.remove", MagicMock())
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.server.logger")
    async def test_run_execution_success(self, mock_logger, mock_open, mock_mkstemp, MockOrchestrator, mock_request, mock_orchestrator_instance):
        MockOrchestrator.return_value = mock_orchestrator_instance

        response = await run_execution(mock_request)

        mock_request.json.assert_awaited_once()
        mock_mkstemp.assert_called_once_with(suffix=".yml")
        # mock_close is not a mock object, so we can't assert called on it
        mock_open.assert_called_once_with("/tmp/test_config.yml", "w", encoding="utf-8")
        mock_open().write.assert_called_once()
        MockOrchestrator.assert_called_once_with("/tmp/test_config.yml")
        mock_orchestrator_instance.run.assert_awaited_once_with("test input", return_logs=True)
        # mock_remove is not a mock object, so we can't assert called on it

        assert isinstance(response, JSONResponse)
        content = json.loads(response.body)
        assert content["input"] == "test input"
        assert content["execution_log"] == [{"agent": "output"}]
        assert content["log_file"] == [{"agent": "output"}]
        assert response.status_code == 200
        mock_logger.info.assert_called()

    @pytest.mark.asyncio
    @patch("orka.server.Orchestrator")
    @patch("tempfile.mkstemp", return_value=(123, "/tmp/test_config.yml"))
    @patch("os.close", MagicMock())
    @patch("os.remove", MagicMock())
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.server.logger")
    async def test_run_execution_orchestrator_instantiation_failure(self, mock_logger, mock_open, mock_mkstemp, MockOrchestrator, mock_request):
        MockOrchestrator.side_effect = Exception("Orchestrator init failed")

        response = await run_execution(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = json.loads(response.body)
        assert "error" in content
        assert "Orchestrator init failed" in content["error"]
        mock_logger.error.assert_called_once()
        assert "Error creating JSONResponse: Orchestrator init failed" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    @patch("orka.server.Orchestrator")
    @patch("tempfile.mkstemp", return_value=(123, "/tmp/test_config.yml"))
    @patch("os.close", MagicMock())
    @patch("os.remove", MagicMock())
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.server.logger")
    async def test_run_execution_orchestrator_run_failure(self, mock_logger, mock_open, mock_mkstemp, MockOrchestrator, mock_request, mock_orchestrator_instance):
        MockOrchestrator.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.run.side_effect = Exception("Orchestrator run failed")

        response = await run_execution(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = json.loads(response.body)
        assert "error" in content
        assert "Orchestrator run failed" in content["error"]
        mock_logger.error.assert_called_once()
        assert "Error creating JSONResponse: Orchestrator run failed" in mock_logger.error.call_args[0][0]

    @pytest.mark.asyncio
    @patch("orka.server.Orchestrator")
    @patch("tempfile.mkstemp", return_value=(123, "/tmp/test_config.yml"))
    @patch("os.close", MagicMock())
    @patch("orka.server.os.remove")
    @patch("orka.server.os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.server.logger")
    async def test_run_execution_os_remove_failure(self, mock_logger, mock_open, mock_exists, mock_os_remove, mock_mkstemp, MockOrchestrator, mock_request, mock_orchestrator_instance):
        MockOrchestrator.return_value = mock_orchestrator_instance
        mock_os_remove.side_effect = Exception("OS remove failed")

        response = await run_execution(mock_request)

        mock_os_remove.assert_called_once_with("/tmp/test_config.yml")
        mock_logger.warning.assert_any_call("Warning: Failed to remove temporary file /tmp/test_config.yml: OS remove failed")

        assert isinstance(response, JSONResponse)
        content = json.loads(response.body)
        assert content["input"] == "test input"
        assert content["execution_log"] == [{"agent": "output"}]
        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch("orka.server.Orchestrator")
    @patch("tempfile.mkstemp", return_value=(123, "/tmp/test_config.yml"))
    @patch("os.close", MagicMock())
    @patch("os.remove", MagicMock())
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.server.logger")
    @patch("orka.server.sanitize_for_json", side_effect=Exception("Sanitization failed"))
    async def test_run_execution_json_response_creation_failure(self, mock_sanitize_for_json, mock_logger, mock_open, mock_mkstemp, MockOrchestrator, mock_request, mock_orchestrator_instance):
        MockOrchestrator.return_value = mock_orchestrator_instance

        response = await run_execution(mock_request)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        content = json.loads(response.body)
        assert "error" in content
        assert "Sanitization failed" in content["error"]
        mock_logger.error.assert_called_once()
        assert "Error creating JSONResponse: Sanitization failed" in mock_logger.error.call_args[0][0]

@patch("uvicorn.run")
@patch("sys.exit")
def test_server_startup_with_env_port(mock_exit, mock_run):
    with patch.dict("os.environ", {"ORKA_PORT": "8002"}):
        from orka import server
        server.main()
    mock_run.assert_called_once_with(app, host="0.0.0.0", port=8002)

@patch("uvicorn.run")
@patch("sys.exit")
def test_server_startup_default_port(mock_exit, mock_run):
    with patch.dict("os.environ", {}):
        from orka import server
        server.main()
    mock_run.assert_called_once_with(app, host="0.0.0.0", port=8001)


class DummyRedisClient:
    async def ping(self):
        return True

    async def set(self, key, value, ex=None):  # noqa: ARG002 - test stub
        return True

    async def get(self, key):  # noqa: ARG002 - test stub
        return b"ok"

    async def execute_command(self, *args, **kwargs):  # noqa: D401, ARG002
        # Simulate RedisSearch available
        return [b"orka_enhanced_memory"]

    async def close(self):
        return None


class DummyRedisModule:
    def from_url(self, *args, **kwargs):  # noqa: D401, ARG002
        return DummyRedisClient()


@pytest.mark.asyncio
async def test_api_health_without_redis_module(monkeypatch):
    # Simulate missing redis.asyncio module
    import orka.server as srv

    monkeypatch.setattr(srv, "aioredis", None, raising=False)

    response = await api_health()
    assert isinstance(response, JSONResponse)
    body = json.loads(response.body)
    assert body["status"] in {"critical", "degraded", "healthy"}
    # Without redis module we expect not connected and critical status or degraded
    assert body["memory"]["connected"] is False
    assert response.status_code in (200, 503)


@pytest.mark.asyncio
async def test_api_health_with_redis_ok(monkeypatch):
    import orka.server as srv

    monkeypatch.setattr(srv, "aioredis", DummyRedisModule(), raising=False)

    response = await api_health()
    assert isinstance(response, JSONResponse)
    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["status"] == "healthy"
    assert body["memory"]["connected"] is True
    assert body["memory"]["search_module"] is True
    assert "orka_enhanced_memory" in body["memory"].get("index_list", [])


@pytest.mark.asyncio
async def test_health_basic_status_codes(monkeypatch):
    # Critical path: make ping fail
    class FailingClient(DummyRedisClient):
        async def ping(self):
            raise RuntimeError("no connection")

    class FailingModule(DummyRedisModule):
        def from_url(self, *args, **kwargs):  # noqa: ARG002
            return FailingClient()

    import orka.server as srv
    monkeypatch.setattr(srv, "aioredis", FailingModule(), raising=False)

    resp = await health_basic()
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 503
    body = json.loads(resp.body)
    assert body["status"] == "critical"
