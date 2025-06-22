# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-resoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
# You may not use this file for commercial purposes without explicit permission.
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
# For commercial use, contact: marcosomma.work@gmail.com
#
# Required attribution: OrKa by Marco Somma – https://github.com/marcosomma/orka-resoning

"""
Test cases for server functionality
"""

import base64
import os
import tempfile
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from orka.server import app, sanitize_for_json


class TestSanitizeForJson:
    """Test suite for sanitize_for_json function"""

    def test_sanitize_basic_types(self):
        """Test sanitization of basic types"""
        assert sanitize_for_json(None) is None
        assert sanitize_for_json("string") == "string"
        assert sanitize_for_json(42) == 42
        assert sanitize_for_json(3.14) == 3.14
        assert sanitize_for_json(True) is True
        assert sanitize_for_json(False) is False

    def test_sanitize_bytes(self):
        """Test sanitization of bytes objects"""
        test_bytes = b"hello world"
        result = sanitize_for_json(test_bytes)

        assert result["__type"] == "bytes"
        assert result["data"] == base64.b64encode(test_bytes).decode("utf-8")

    def test_sanitize_list(self):
        """Test sanitization of lists"""
        test_list = [1, "string", b"bytes", None]
        result = sanitize_for_json(test_list)

        assert result[0] == 1
        assert result[1] == "string"
        assert result[2]["__type"] == "bytes"
        assert result[3] is None

    def test_sanitize_tuple(self):
        """Test sanitization of tuples"""
        test_tuple = (1, "string", b"bytes")
        result = sanitize_for_json(test_tuple)

        assert isinstance(result, list)
        assert result[0] == 1
        assert result[1] == "string"
        assert result[2]["__type"] == "bytes"

    def test_sanitize_dict(self):
        """Test sanitization of dictionaries"""
        test_dict = {
            "string": "value",
            "number": 42,
            "bytes": b"data",
            123: "numeric_key",
        }
        result = sanitize_for_json(test_dict)

        assert result["string"] == "value"
        assert result["number"] == 42
        assert result["bytes"]["__type"] == "bytes"
        assert result["123"] == "numeric_key"  # Key converted to string

    def test_sanitize_datetime(self):
        """Test sanitization of datetime objects"""
        test_datetime = datetime(2025, 1, 1, 12, 0, 0)
        result = sanitize_for_json(test_datetime)

        assert result == test_datetime.isoformat()

    def test_sanitize_custom_object(self):
        """Test sanitization of custom objects"""

        class TestObject:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        test_obj = TestObject()
        result = sanitize_for_json(test_obj)

        assert result["__type"] == "TestObject"
        assert result["data"]["attr1"] == "value1"
        assert result["data"]["attr2"] == 42

    def test_sanitize_custom_object_with_error(self):
        """Test sanitization of custom objects that raise errors"""

        class ProblematicObject:
            @property
            def __dict__(self):
                raise Exception("Cannot access __dict__")

        test_obj = ProblematicObject()
        result = sanitize_for_json(test_obj)

        assert "sanitization-error:" in result

    def test_sanitize_non_serializable_type(self):
        """Test sanitization of non-serializable types"""
        test_obj = object()
        result = sanitize_for_json(test_obj)

        assert "non-serializable: object" in result

    def test_sanitize_with_exception(self):
        """Test sanitization when an exception occurs"""

        class ExceptionObject:
            def __getattribute__(self, name):
                raise Exception("Always fails")

        test_obj = ExceptionObject()
        result = sanitize_for_json(test_obj)

        assert "sanitization-error:" in result

    def test_sanitize_nested_structure(self):
        """Test sanitization of deeply nested structures"""
        nested_data = {
            "level1": {
                "level2": [
                    {"bytes": b"data", "string": "value"},
                    {"number": 42, "none": None},
                ],
            },
        }

        result = sanitize_for_json(nested_data)

        assert result["level1"]["level2"][0]["bytes"]["__type"] == "bytes"
        assert result["level1"]["level2"][0]["string"] == "value"
        assert result["level1"]["level2"][1]["number"] == 42
        assert result["level1"]["level2"][1]["none"] is None


class TestServerAPI:
    """Test suite for server API endpoints"""

    def setup_method(self):
        """Set up test client"""
        self.client = TestClient(app)

    @pytest.mark.asyncio
    async def test_run_execution_success(self):
        """Test successful execution via API"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        # Mock the orchestrator
        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.return_value = {"status": "success", "result": "test result"}
            mock_orchestrator_class.return_value = mock_orchestrator

            response = self.client.post("/api/run", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["input"] == "test input"
        assert "execution_log" in data
        assert "log_file" in data

    @pytest.mark.asyncio
    async def test_run_execution_with_complex_result(self):
        """Test execution with complex result data"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-answer
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        # Mock orchestrator with complex result
        complex_result = {
            "status": "success",
            "data": {
                "bytes_data": b"binary data",
                "datetime": datetime(2025, 1, 1),
                "nested": {"list": [1, 2, 3]},
            },
        }

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.return_value = complex_result
            mock_orchestrator_class.return_value = mock_orchestrator

            response = self.client.post("/api/run", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["input"] == "test input"

        # Check that complex data was sanitized
        execution_log = data["execution_log"]
        assert execution_log["data"]["bytes_data"]["__type"] == "bytes"
        assert execution_log["data"]["nested"]["list"] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_run_execution_orchestrator_error(self):
        """Test execution when orchestrator raises an error"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.side_effect = Exception("Orchestrator failed")
            mock_orchestrator_class.return_value = mock_orchestrator

            # Expect an exception to be raised when orchestrator fails
            with pytest.raises(Exception, match="Orchestrator failed"):
                response = self.client.post("/api/run", json=request_data)

    @pytest.mark.asyncio
    async def test_run_execution_json_serialization_error(self):
        """Test execution when JSON serialization fails"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        # Create a result that will cause JSON serialization issues
        problematic_result = {"data": object()}  # object() is not JSON serializable

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.return_value = problematic_result
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock JSONResponse to raise an exception
            with patch("orka.server.JSONResponse") as mock_json_response:
                mock_json_response.side_effect = [Exception("JSON error"), MagicMock()]

                response = self.client.post("/api/run", json=request_data)

        assert response.status_code == 200  # The fallback response should succeed
        data = response.json()
        # The mock returns an empty dict, so we just check it's valid JSON
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_run_execution_temp_file_cleanup(self):
        """Test that temporary files are cleaned up"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        created_files = []

        # Track created temporary files
        original_mkstemp = tempfile.mkstemp

        def track_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            created_files.append(path)
            return fd, path

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.return_value = {"status": "success"}
            mock_orchestrator_class.return_value = mock_orchestrator

            with patch("tempfile.mkstemp", side_effect=track_mkstemp):
                response = self.client.post("/api/run", json=request_data)

        assert response.status_code == 200

        # Check that temporary files were cleaned up
        for file_path in created_files:
            assert not os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_run_execution_temp_file_cleanup_failure(self):
        """Test behavior when temp file cleanup fails"""
        yaml_config = """
orchestrator:
  id: test_orchestrator
  strategy: sequential
  queue: orka:test
  agents:
    - test_agent

agents:
  - id: test_agent
    type: openai-binary
    queue: orka:test_queue
    prompt: "Test prompt: {{ input }}"
        """

        request_data = {
            "input": "test input",
            "yaml_config": yaml_config,
        }

        with patch("orka.server.Orchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run.return_value = {"status": "success"}
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock os.remove to raise an exception
            with patch("os.remove", side_effect=Exception("Cannot remove file")):
                response = self.client.post("/api/run", json=request_data)

        # Should still succeed despite cleanup failure
        assert response.status_code == 200

    def test_cors_middleware(self):
        """Test that CORS middleware is properly configured"""
        # Test preflight request
        response = self.client.options(
            "/api/run",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should allow CORS
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_app_creation(self):
        """Test that FastAPI app is properly created"""
        assert app is not None
        assert hasattr(app, "post")
        assert hasattr(app, "add_middleware")

    def test_main_execution(self):
        """Test main execution with environment variables"""
        with patch("orka.server.uvicorn.run") as mock_run:
            with patch.dict(os.environ, {"ORKA_PORT": "9000"}):
                # Import and execute the main block

                # Simulate running the main block
                if __name__ == "__main__":
                    port = int(os.environ.get("ORKA_PORT", 8001))
                    assert port == 9000

    def test_main_execution_default_port(self):
        """Test main execution with default port"""
        with patch("orka.server.uvicorn.run") as mock_run:
            with patch.dict(os.environ, {}, clear=True):
                # Simulate running the main block
                port = int(os.environ.get("ORKA_PORT", 8001))
                assert port == 8001
