"""
Comprehensive tests for CLI core module to improve coverage.
"""

from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from orka.cli.core import run_cli_entrypoint


class TestRunCliEntrypoint:
    """Test the run_cli_entrypoint function."""

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_basic(self, mock_orchestrator_class):
        """Test basic run_cli_entrypoint functionality."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"agent1": "result1"})
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test
        result = await run_cli_entrypoint("config.yml", "test input")

        # Assertions
        assert result == {"agent1": "result1"}
        mock_orchestrator_class.assert_called_once_with("config.yml")
        mock_orchestrator.run.assert_called_once_with("test input")

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_dict_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with dict result and logging."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(
            return_value={
                "agent1": "result1",
                "agent2": "result2",
                "agent3": {"nested": "data"},
            },
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == {
                "agent1": "result1",
                "agent2": "result2",
                "agent3": {"nested": "data"},
            }

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_list_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with list result and logging."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(
            return_value=[
                {"agent_id": "agent1", "payload": {"data": "value1"}},
                {"agent_id": "agent2", "payload": {"data": "value2"}},
                {"payload": {"data": "value3"}},  # Missing agent_id
            ],
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == str([
                {"agent_id": "agent1", "payload": {"data": "value1"}},
                {"agent_id": "agent2", "payload": {"data": "value2"}},
                {"payload": {"data": "value3"}},  # Missing agent_id
            ])

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_string_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with string result and logging."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value="Simple string result")
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == "Simple string result"

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_other_result_type(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with other result types and logging."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value=42)  # Integer result
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == "42"

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_log_to_file_true(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with log_to_file=True."""
        # Setup mock
        mock_orchestrator = Mock()
        test_result = {"agent1": "result1", "agent2": "result2"}
        mock_orchestrator.run = AsyncMock(return_value=test_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("orka.cli.core.logger") as mock_logger:
                # Test
                result = await run_cli_entrypoint("config.yml", "test input", log_to_file=True)

                # Assertions
                assert result == test_result

                # Check file was opened and written to
                mock_file.assert_any_call("orka_trace.log", "w")
                mock_file().write.assert_called_once_with(str(test_result))

                # Logger should not be called when log_to_file=True
                mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_log_to_file_false_default(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with default log_to_file=False."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"agent1": "result1"})
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("builtins.open", mock_open()) as mock_file:
            with patch("orka.cli.core.logger") as mock_logger:
                # Test (log_to_file defaults to False)
                result = await run_cli_entrypoint("config.yml", "test input")

                # Assertions
                assert result == {"agent1": "result1"}

                # File should not be opened for trace log
                for call in mock_file.call_args_list:
                    assert call[0][0] != "orka_trace.log"

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_complex_config_path(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with complex config path."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"result": "success"})
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test with complex path
        complex_path = "/path/to/configs/complex_workflow.yml"
        result = await run_cli_entrypoint(complex_path, "complex input")

        # Assertions
        assert result == {"result": "success"}
        mock_orchestrator_class.assert_called_once_with(complex_path)
        mock_orchestrator.run.assert_called_once_with("complex input")

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_with_complex_input(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with complex input text."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"processed": "data"})
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test with complex input
        complex_input = (
            "This is a very long input text with multiple sentences. "
            "It contains various punctuation marks! And questions? "
            "It also has numbers like 123 and special characters @#$%."
        )

        result = await run_cli_entrypoint("config.yml", complex_input)

        # Assertions
        assert result == {"processed": "data"}
        mock_orchestrator.run.assert_called_once_with(complex_input)

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_empty_dict_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with empty dict result."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={})
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == {}
            # No logging calls should be made for empty dict
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_empty_list_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with empty list result."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value=[])
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == []
            # No logging calls should be made for empty list
            mock_logger.info.assert_not_called()

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_list_with_missing_payload(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with list result containing events without payload."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(
            return_value=[
                {"agent_id": "agent1"},  # Missing payload
                {"agent_id": "agent2", "payload": None},  # None payload
            ],
        )
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == str([
                {"agent_id": "agent1"},  # Missing payload
                {"agent_id": "agent2", "payload": None},  # None payload
            ])

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_orchestrator_exception(self, mock_orchestrator_class):
        """Test run_cli_entrypoint when orchestrator raises exception."""
        # Setup mock to raise exception
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(side_effect=Exception("Orchestrator error"))
        mock_orchestrator_class.return_value = mock_orchestrator

        # Test that exception is propagated
        with pytest.raises(Exception, match="Orchestrator error"):
            await run_cli_entrypoint("config.yml", "test input")

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_file_write_exception(self, mock_orchestrator_class):
        """Test run_cli_entrypoint when file writing fails."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value={"result": "data"})
        mock_orchestrator_class.return_value = mock_orchestrator

        # Mock open to raise exception
        with patch("builtins.open", side_effect=OSError("File write error")):
            # Test that exception is propagated
            with pytest.raises(IOError, match="File write error"):
                await run_cli_entrypoint("config.yml", "test input", log_to_file=True)

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_none_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with None result."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value=None)
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == "None"

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_boolean_result(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with boolean result."""
        # Setup mock
        mock_orchestrator = Mock()
        mock_orchestrator.run = AsyncMock(return_value=True)
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("orka.cli.core.logger") as mock_logger:
            # Test
            result = await run_cli_entrypoint("config.yml", "test input")

            # Assertions
            assert result == "True"

    @pytest.mark.asyncio
    @patch("orka.cli.core.Orchestrator")
    async def test_run_cli_entrypoint_all_parameters(self, mock_orchestrator_class):
        """Test run_cli_entrypoint with all parameters specified."""
        # Setup mock
        mock_orchestrator = Mock()
        test_result = {"comprehensive": "test"}
        mock_orchestrator.run = AsyncMock(return_value=test_result)
        mock_orchestrator_class.return_value = mock_orchestrator

        with patch("builtins.open", mock_open()) as mock_file:
            # Test with all parameters
            result = await run_cli_entrypoint(
                config_path="comprehensive_config.yml",
                input_text="comprehensive input text",
                log_to_file=True,
            )

            # Assertions
            assert result == test_result
            mock_orchestrator_class.assert_called_once_with("comprehensive_config.yml")
            mock_orchestrator.run.assert_called_once_with("comprehensive input text")
            mock_file.assert_any_call("orka_trace.log", "w")
            mock_file().write.assert_called_once_with(str(test_result))


class TestModuleImports:
    """Test module-level imports and dependencies."""

    def test_imports_available(self):
        """Test that all required imports are available."""
        from orka.cli.core import logger, run_cli_entrypoint
        from orka.cli.types import Event

        # Check that imports are successful
        assert callable(run_cli_entrypoint)
        assert logger is not None
        assert Event is not None

    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        from orka.cli.core import logger

        assert logger.name == "orka.cli.core"
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
