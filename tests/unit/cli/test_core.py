import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from orka.cli.core import sanitize_for_console, deep_sanitize_result, run_cli_entrypoint

# Tests for sanitize_for_console
def test_sanitize_for_console_replaces_unicode():
    assert sanitize_for_console("hello\u2014world") == "hello--world"
    assert sanitize_for_console("it's a test") == "it's a test"
    assert sanitize_for_console("‘single quotes’") == "'single quotes'"
    assert sanitize_for_console("“double quotes”") == '"double quotes"'
    assert sanitize_for_console("ellipsis…") == "ellipsis..."

@patch('sys.stdout')
def test_sanitize_for_console_ascii_encoding(mock_stdout):
    # This will force the ascii replace logic
    mock_stdout.encoding = 'ascii'
    assert "???" in sanitize_for_console("你好世界")

# Tests for deep_sanitize_result
def test_deep_sanitize_result_simple():
    data = {
        "key1": "value\u20141",
        "key2": ["item1", "item\u2019s"],
        "key3": {"nested_key": "nested\u201cvalue\u201d"}
    }
    sanitized = deep_sanitize_result(data)
    assert sanitized["key1"] == "value--1"
    assert sanitized["key2"][1] == "item's"
    assert sanitized["key3"]["nested_key"] == 'nested"value"'

def test_deep_sanitize_result_nested():
    data = ("tuple", ["list_item\u2026", {"a": 1}])
    sanitized = deep_sanitize_result(data)
    assert sanitized[0] == "tuple"
    assert sanitized[1][0] == "list_item..."

# Tests for run_cli_entrypoint
@pytest.mark.asyncio
async def test_run_cli_entrypoint_success():
    with patch("orka.cli.core.Orchestrator") as mock_orchestrator:
        mock_orchestrator.return_value.run = AsyncMock(return_value={"result": "success"})
        
        result = await run_cli_entrypoint("config.yml", "input")
        
        mock_orchestrator.assert_called_once_with("config.yml")
        mock_orchestrator.return_value.run.assert_called_once_with("input")
        assert result == {"result": "success"}

@pytest.mark.asyncio
async def test_run_cli_entrypoint_log_to_file():
    with patch("orka.cli.core.Orchestrator") as mock_orchestrator, \
         patch("orka.cli.core.setup_logging") as mock_setup_logging, \
         patch("builtins.open") as mock_open:
        mock_orchestrator.return_value.run = AsyncMock(return_value="success string")
        
        await run_cli_entrypoint("config.yml", "input", log_to_file=True)
        
        mock_open.assert_called_once_with("orka_trace.log", "w")
        mock_open.return_value.__enter__.return_value.write.assert_called_once_with("success string")

@pytest.mark.asyncio
async def test_run_cli_entrypoint_returns_str():
    with patch("orka.cli.core.Orchestrator") as mock_orchestrator:
        mock_orchestrator.return_value.run = AsyncMock(return_value="just a string")
        result = await run_cli_entrypoint("config.yml", "input")
        assert result == "just a string"

@pytest.mark.asyncio
async def test_run_cli_entrypoint_returns_list():
    with patch("orka.cli.core.Orchestrator") as mock_orchestrator:
        mock_orchestrator.return_value.run = AsyncMock(return_value=[{"agent_id": "a", "event_type": "t", "timestamp": "ts", "payload": {}}])
        result = await run_cli_entrypoint("config.yml", "input")
        assert isinstance(result, list)
        assert result[0]["agent_id"] == "a"

@pytest.mark.asyncio
async def test_run_cli_entrypoint_sanitizes_other_return_types():
    with patch("orka.cli.core.Orchestrator") as mock_orchestrator:
        mock_orchestrator.return_value.run = AsyncMock(return_value=123) # not dict, list or str
        result = await run_cli_entrypoint("config.yml", "input")
        assert result == "123"


# Tests for run_cli return codes
from orka.cli.core import run_cli


class TestRunCliReturnCodes:
    """Test CLI exit code handling for various result types."""

    @pytest.mark.parametrize(
        "result,expected_code",
        [
            # Valid results should return 0 (success)
            ({"status": "success"}, 0),
            ("Hello world", 0),
            ("", 0),  # Empty string is valid
            ({}, 0),  # Empty dict is valid
            ([], 0),  # Empty list is valid
            (0, 0),  # Zero is valid (integer result)
            (False, 0),  # Boolean False is valid (explicit result)
            # Only None should return 1 (failure)
            (None, 1),
        ],
    )
    def test_exit_code_for_result_types(self, result, expected_code):
        """Verify CLI returns correct exit codes for various result types."""
        with patch("orka.cli.core.asyncio.run") as mock_run:
            mock_run.return_value = result
            exit_code = run_cli(["run", "fake.yml", "test input"])
            assert exit_code == expected_code, f"Expected {expected_code} for result {result!r}"

    def test_exit_code_for_successful_dict(self):
        """Test dict result returns success."""
        with patch("orka.cli.core.asyncio.run") as mock_run:
            mock_run.return_value = {"answer": "test"}
            exit_code = run_cli(["run", "fake.yml", "test"])
            assert exit_code == 0

    def test_exit_code_for_none_result(self):
        """Test None result returns failure."""
        with patch("orka.cli.core.asyncio.run") as mock_run:
            mock_run.return_value = None
            exit_code = run_cli(["run", "fake.yml", "test"])
            assert exit_code == 1
