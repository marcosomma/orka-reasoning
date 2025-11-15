import pytest
from unittest.mock import MagicMock, patch

from orka.tui_interface import ModernTUIInterface

class MockArgs:
    def __init__(self, **kwargs):
        self.backend = kwargs.get('backend', 'redisstack')
        self.json = kwargs.get('json', False)
        self.interval = kwargs.get('interval', 2.0)
        self.use_rich = kwargs.get('use_rich', False)
        self.fallback = kwargs.get('fallback', False)

    def __getattr__(self, name):
        return self.__dict__.get(name)

@patch("orka.tui.interface.RICH_AVAILABLE", True)
def test_modern_tui_interface_initialization():
    tui = ModernTUIInterface()
    assert tui.console is not None
    assert not tui.running
    assert tui.current_view == "dashboard"

@patch("orka.tui.interface.RICH_AVAILABLE", True)
@patch("orka.tui.interface.TEXTUAL_AVAILABLE", True)
@patch("orka.tui.interface.ModernTUIInterface._run_textual_interface")
def test_run_defaults_to_textual(mock_run_textual):
    args = MockArgs()
    tui = ModernTUIInterface()
    tui.data_manager.init_memory_logger = MagicMock()
    tui.run(args)
    tui.data_manager.init_memory_logger.assert_called_once_with(args)
    mock_run_textual.assert_called_once_with(args)

@patch("orka.tui.interface.RICH_AVAILABLE", True)
@patch("orka.tui.interface.TEXTUAL_AVAILABLE", False)
@patch("orka.tui.interface.ModernTUIInterface._run_rich_interface")
def test_run_falls_back_to_rich_when_textual_unavailable(mock_run_rich, capsys):
    args = MockArgs()
    tui = ModernTUIInterface()
    tui.data_manager.init_memory_logger = MagicMock()
    tui.run(args)
    tui.data_manager.init_memory_logger.assert_called_once_with(args)
    captured = capsys.readouterr()
    assert "Textual not available" in captured.out

@patch("orka.tui.interface.RICH_AVAILABLE", True)
@patch("orka.tui.interface.TEXTUAL_AVAILABLE", True)
@patch("orka.tui.interface.ModernTUIInterface._run_rich_interface")
def test_run_uses_rich_when_flagged(mock_run_rich, capsys):
    args = MockArgs(use_rich=True)
    tui = ModernTUIInterface()
    tui.data_manager.init_memory_logger = MagicMock()
    tui.run(args)
    tui.data_manager.init_memory_logger.assert_called_once_with(args)
    captured = capsys.readouterr()
    assert "Using Rich fallback interface" in captured.out

@patch("orka.tui.interface.RICH_AVAILABLE", False)
@patch("orka.tui.fallback.FallbackInterface.run_basic_fallback")
def test_run_falls_back_to_basic_when_rich_unavailable(mock_run_basic, caplog):
    args = MockArgs()
    tui = ModernTUIInterface()
    tui.run(args)
    assert "Modern TUI requires 'rich' library" in caplog.text
    mock_run_basic.assert_called_once_with(args)

@patch("orka.tui.interface.signal.signal")
def test_signal_handler(mock_signal_call):
    tui = ModernTUIInterface()
    tui.running = True
    tui._signal_handler(None, None)
    assert not tui.running

@patch("orka.tui.interface.RICH_AVAILABLE", True)
@patch("orka.tui.interface.Live")
@patch("orka.tui.interface.time.sleep", side_effect=KeyboardInterrupt)
def test_run_rich_interface_main_loop(mock_sleep, mock_live):
    args = MockArgs()
    tui = ModernTUIInterface()
    tui.running = True
    tui.data_manager = MagicMock()
    tui.layouts = MagicMock()
    live_context = mock_live.return_value.__enter__.return_value
    tui._run_rich_interface(args)
    tui.data_manager.update_data.assert_called_once()
    tui.layouts.get_view.assert_called_with("dashboard")
    live_context.update.assert_called()
    mock_sleep.assert_called_once()

@patch("orka.tui.interface.TEXTUAL_AVAILABLE", True)
@patch("orka.tui.textual_app.OrKaTextualApp")
def test_run_textual_interface(mock_app):
    args = MockArgs()
    tui = ModernTUIInterface()
    tui.data_manager = MagicMock()
    tui._run_textual_interface(args)
    mock_app.assert_called_once_with(tui.data_manager)
    mock_app.return_value.run.assert_called_once()
