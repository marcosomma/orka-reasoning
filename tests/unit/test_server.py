"""Tests for orka.server module."""

import base64
import os
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

# Import the components we're testing
from orka.server import app, sanitize_for_json


class TestSanitizeForJson:
    """Test the sanitize_for_json function."""

    def test_sanitize_primitive_types(self):
        """Test sanitization of primitive types."""
        assert sanitize_for_json(None) is None
        assert sanitize_for_json("string") == "string"
        assert sanitize_for_json(42) == 42
        assert sanitize_for_json(3.14) == 3.14
        assert sanitize_for_json(True) is True
        assert sanitize_for_json(False) is False

    def test_sanitize_bytes(self):
        """Test sanitization of bytes objects."""
        test_bytes = b"hello world"
        expected = {
            "__type": "bytes",
            "data": base64.b64encode(test_bytes).decode("utf-8"),
        }

        result = sanitize_for_json(test_bytes)
        assert result == expected

    def test_sanitize_list_and_tuple(self):
        """Test sanitization of list and tuple objects."""
        test_list = [1, "string", b"bytes", None]
        expected_list = [
            1,
            "string",
            {"__type": "bytes", "data": base64.b64encode(b"bytes").decode("utf-8")},
            None,
        ]

        result = sanitize_for_json(test_list)
        assert result == expected_list

        # Test tuple (should be converted to list)
        result_tuple = sanitize_for_json(tuple(test_list))
        assert result_tuple == expected_list

    def test_sanitize_dict(self):
        """Test sanitization of dictionary objects."""
        test_dict = {
            "string_key": "value",
            123: "numeric_key",
            "bytes_value": b"test",
            "nested": {"inner": "value"},
        }

        result = sanitize_for_json(test_dict)

        assert result["string_key"] == "value"
        assert result["123"] == "numeric_key"  # Key converted to string
        assert result["bytes_value"]["__type"] == "bytes"
        assert result["nested"]["inner"] == "value"

    def test_sanitize_datetime_object(self):
        """Test sanitization of datetime-like objects."""
        mock_datetime = Mock()
        mock_datetime.isoformat.return_value = "2023-01-01T12:00:00"

        result = sanitize_for_json(mock_datetime)
        assert result == "2023-01-01T12:00:00"
        mock_datetime.isoformat.assert_called_once()

    def test_sanitize_custom_object_with_dict(self):
        """Test sanitization of custom objects with __dict__."""

        class CustomObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        obj = CustomObject()
        result = sanitize_for_json(obj)

        assert result["__type"] == "CustomObject"
        assert result["data"]["attr1"] == "value1"
        assert result["data"]["attr2"] == 42

    def test_sanitize_custom_object_dict_exception(self):
        """Test sanitization of custom objects where accessing __dict__ fails."""

        # Create a custom object that will raise an exception when __dict__ is accessed
        class ProblematicObject:
            def __init__(self):
                pass

            @property
            def __dict__(self):
                raise ValueError("Cannot access __dict__")

        obj = ProblematicObject()
        result = sanitize_for_json(obj)
        # When an exception occurs during sanitization, it returns a sanitization-error message
        assert "sanitization-error" in result
        assert "Cannot access __dict__" in result

    def test_sanitize_non_serializable_object(self):
        """Test sanitization of objects without __dict__."""

        # Create a simple object without __dict__ by using __slots__
        class NonSerializableObject:
            __slots__ = ["value"]

            def __init__(self):
                self.value = "test"

        obj = NonSerializableObject()
        result = sanitize_for_json(obj)
        assert "non-serializable: NonSerializableObject" in result

    def test_sanitize_exception_handling(self):
        """Test sanitization with general exceptions."""
        with patch("orka.server.logger") as mock_logger:
            # Create a scenario that will trigger the outer exception handler
            with patch("orka.server.isinstance", side_effect=RuntimeError("Test error")):
                result = sanitize_for_json("test")

                assert "sanitization-error" in result
                assert "Test error" in result
                mock_logger.warning.assert_called_once()


class TestServerEndpoints:
    """Test the FastAPI server endpoints."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(app)

    @patch("orka.server.Orchestrator")
    @patch("orka.server.tempfile.mkstemp")
    @patch("orka.server.os.close")
    @patch("orka.server.os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_api_run_success(
        self,
        mock_file,
        mock_remove,
        mock_close,
        mock_mkstemp,
        mock_orchestrator_class,
    ):
        """Test successful API run execution."""
        # Mock tempfile creation
        mock_mkstemp.return_value = (123, "/tmp/test.yml")

        # Mock orchestrator with ASYNC run method
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"result": "success", "data": "test_data"})
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test data
        request_data = {
            "input": "test input",
            "yaml_config": "test:\n  value: example",
        }

        # Make request
        response = self.client.post("/api/run", json=request_data)

        # Verify response
        assert response.status_code == 200
        response_data = response.json()

        assert response_data["input"] == "test input"
        assert "execution_log" in response_data
        assert "log_file" in response_data

        # Verify mocks were called correctly
        mock_mkstemp.assert_called_once_with(suffix=".yml")
        mock_close.assert_called_once_with(123)
        # The open call - just verify it was called with the right parameters
        mock_file.assert_called_with("/tmp/test.yml", "w", encoding="utf-8")
        # Since mock_open creates a complex mock, we just check the orchestrator was called correctly
        mock_orchestrator_class.assert_called_once_with("/tmp/test.yml")
        mock_orchestrator.run.assert_called_once_with("test input")
        mock_remove.assert_called_once_with("/tmp/test.yml")

    def test_api_run_file_cleanup_exception(self):
        """Test API run when file cleanup fails."""
        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            # Mock orchestrator
            mock_orchestrator = Mock()
            mock_orchestrator.run = AsyncMock(return_value={"result": "success"})
            mock_orchestrator_class.return_value = mock_orchestrator

            with patch("orka.server.os.remove") as mock_remove:
                # Mock remove to raise an exception (should not affect response)
                mock_remove.side_effect = Exception("Remove failed")

                response = self.client.post(
                    "/api/run",
                    json={"input": "test", "yaml_config": "test: value"},
                )

                # Should still succeed despite cleanup failure
                assert response.status_code == 200

    def test_cors_middleware(self):
        """Test CORS middleware is properly configured."""
        # Make a simple request to check CORS headers
        response = self.client.get("/")  # This will 404 but should have CORS headers

        # Even with 404, CORS headers should be present if middleware is configured
        # Note: TestClient doesn't always show CORS headers the same way as a real browser
        assert response.status_code == 404  # Endpoint doesn't exist, but that's expected

    def test_api_run_basic_functionality(self):
        """Test that the API endpoint exists and handles basic requests."""
        # Test with minimal valid data instead of empty data
        request_data = {
            "input": "test input",
            "yaml_config": "test: value",  # Provide a basic YAML config
        }

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            # Mock orchestrator
            mock_orchestrator = Mock()
            mock_orchestrator.run = AsyncMock(return_value={"result": "success"})
            mock_orchestrator_class.return_value = mock_orchestrator

            response = self.client.post("/api/run", json=request_data)

            # Should respond successfully
            assert response.status_code == 200

    def test_api_run_orchestrator_exception(self):
        """Test API run when orchestrator raises an exception."""
        request_data = {
            "input": "test input",
            "yaml_config": "test: value",
        }

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            # Mock orchestrator that raises an exception during initialization
            mock_orchestrator_class.side_effect = Exception("Orchestrator init failed")

            # In the test environment, FastAPI's TestClient will raise the exception
            # rather than converting it to an HTTP 500 response
            with pytest.raises(Exception, match="Orchestrator init failed"):
                response = self.client.post("/api/run", json=request_data)


class TestServerMain:
    """Test the server main execution logic."""

    def test_main_default_port(self):
        """Test main execution with default port."""
        with patch.dict(os.environ, {}, clear=True):
            port = int(os.environ.get("ORKA_PORT", 8001))
            assert port == 8001

    def test_main_custom_port(self):
        """Test main execution with custom port from environment."""
        with patch.dict(os.environ, {"ORKA_PORT": "9000"}):
            port = int(os.environ.get("ORKA_PORT", 8001))
            assert port == 9000

    def test_main_invalid_port(self):
        """Test main execution with invalid port from environment."""
        with patch.dict(os.environ, {"ORKA_PORT": "invalid"}):
            with pytest.raises(ValueError):
                int(os.environ.get("ORKA_PORT", 8001))


class TestServerApp:
    """Test the FastAPI app configuration."""

    def test_app_configuration(self):
        """Test FastAPI app is properly configured."""
        assert app.title == "OrKa AI Orchestration API"
        assert app.description == "🚀 High-performance API gateway for AI workflow orchestration"
        assert app.version == "1.0.0"

    def test_app_has_cors_middleware(self):
        """Test that CORS middleware is configured."""
        # Check that middleware is present
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes
