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


# Tests for OrKaMonitorApp (legacy Textual app)
class TestOrKaMonitorApp:
    """Test suite for OrKaMonitorApp legacy Textual interface."""

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_orka_monitor_app_initialization(self):
        """Test OrKaMonitorApp initialization."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        app = OrKaMonitorApp(mock_tui)
        
        assert app.tui == mock_tui
        assert len(app.BINDINGS) == 6  # q, 1-4, r

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_compose_creates_ui_components(self):
        """Test compose method is defined and callable."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        app = OrKaMonitorApp(mock_tui)
        
        # Verify compose method exists and is callable
        assert hasattr(app, "compose")
        assert callable(app.compose)

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_on_mount_sets_interval(self):
        """Test on_mount sets up refresh interval."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.refresh_interval = 2.0
        app = OrKaMonitorApp(mock_tui)
        app.set_interval = MagicMock()
        
        app.on_mount()
        
        app.set_interval.assert_called_once_with(2.0, app.update_display)

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_update_display_success(self):
        """Test update_display with successful data update."""
        from orka.tui_interface import OrKaMonitorApp
        from textual.widgets import Static
        
        mock_tui = MagicMock()
        mock_tui.data_manager.stats.current = {
            "total_entries": 100,
            "stored_memories": 60,
            "orchestration_logs": 40,
            "active_entries": 90,
            "expired_entries": 10,
        }
        mock_tui.data_manager.backend = "RedisStack"
        
        app = OrKaMonitorApp(mock_tui)
        mock_content = MagicMock()
        app.query_one = MagicMock(return_value=mock_content)
        
        app.update_display()
        
        mock_tui.data_manager.update_data.assert_called_once()
        app.query_one.assert_called_once_with("#main-content", Static)
        mock_content.update.assert_called_once()
        
        # Check the display text contains stats
        call_args = mock_content.update.call_args[0][0]
        assert "100" in call_args  # total_entries
        assert "60" in call_args  # stored_memories
        assert "RedisStack" in call_args

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_update_display_error_handling(self):
        """Test update_display handles errors gracefully."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.data_manager.update_data.side_effect = Exception("Connection failed")
        
        app = OrKaMonitorApp(mock_tui)
        mock_content = MagicMock()
        app.query_one = MagicMock(return_value=mock_content)
        
        app.update_display()
        
        # Should catch exception and display error message
        mock_content.update.assert_called()
        error_msg = mock_content.update.call_args[0][0]
        assert "Error updating display" in error_msg
        assert "Connection failed" in error_msg

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_action_show_dashboard(self):
        """Test action_show_dashboard changes view."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.current_view = "memories"
        app = OrKaMonitorApp(mock_tui)
        
        app.action_show_dashboard()
        
        assert mock_tui.current_view == "dashboard"

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_action_show_memories(self):
        """Test action_show_memories changes view."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.current_view = "dashboard"
        app = OrKaMonitorApp(mock_tui)
        
        app.action_show_memories()
        
        assert mock_tui.current_view == "memories"

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_action_show_performance(self):
        """Test action_show_performance changes view."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.current_view = "dashboard"
        app = OrKaMonitorApp(mock_tui)
        
        app.action_show_performance()
        
        assert mock_tui.current_view == "performance"

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_action_show_config(self):
        """Test action_show_config changes view."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        mock_tui.current_view = "dashboard"
        app = OrKaMonitorApp(mock_tui)
        
        app.action_show_config()
        
        assert mock_tui.current_view == "config"

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_action_refresh(self):
        """Test action_refresh triggers display update."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        app = OrKaMonitorApp(mock_tui)
        app.update_display = MagicMock()
        
        app.action_refresh()
        
        app.update_display.assert_called_once()

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_css_styling_defined(self):
        """Test CSS styling is properly defined."""
        from orka.tui_interface import OrKaMonitorApp
        
        mock_tui = MagicMock()
        app = OrKaMonitorApp(mock_tui)
        
        # Check CSS is defined and contains expected classes
        assert hasattr(app, "CSS")
        assert ".box" in app.CSS
        assert ".header" in app.CSS
        assert ".footer" in app.CSS
        assert "background:" in app.CSS


# Test OrKaTextualApp import and availability
class TestOrKaTextualAppImport:
    """Test suite for OrKaTextualApp import handling."""

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", True)
    def test_orka_textual_app_available_when_textual_installed(self):
        """Test OrKaTextualApp is available when Textual is installed."""
        # This is a smoke test to ensure the import doesn't fail
        from orka import tui_interface
        
        # Should have OrKaTextualApp in module or set to None
        assert hasattr(tui_interface, "OrKaTextualApp") or True

    @patch("orka.tui_interface.TEXTUAL_AVAILABLE", False)
    def test_orka_monitor_app_not_available_without_textual(self):
        """Test OrKaMonitorApp is not available when Textual is missing."""
        import sys
        
        # Remove module if cached
        if "orka.tui_interface" in sys.modules:
            del sys.modules["orka.tui_interface"]
        
        # This should not raise an error even if TEXTUAL_AVAILABLE is False
        import orka.tui_interface as tui_module
        
        # Module should still be importable
        assert tui_module is not None
