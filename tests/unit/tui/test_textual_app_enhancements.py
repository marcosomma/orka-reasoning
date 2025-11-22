"""
Unit tests for OrKaTextualApp enhancements (themes, vim navigation, export).
"""

import json
import pytest
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
from pathlib import Path
from datetime import datetime

from orka.tui.textual_app import OrKaTextualApp
from orka.tui.theme_vintage import VINTAGE
from orka.tui.theme_dark import DARK


class TestThemeRegistration:
    """Test suite for custom theme registration."""
    
    def test_initialization_registers_themes(self):
        """Test app initializes and registers custom themes."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        # Verify custom themes are registered
        assert VINTAGE.name == "orka-vintage"
        assert DARK.name == "orka-dark"
        
        # Verify themes have correct colors
        assert VINTAGE.primary == "#00ff00"  # Green CRT
        assert DARK.primary == "#58a6ff"  # Cyan accent
    
    def test_vintage_theme_properties(self):
        """Test vintage theme has correct retro CRT colors."""
        assert VINTAGE.name == "orka-vintage"
        assert VINTAGE.background == "#000000"  # Pure black
        assert VINTAGE.foreground == "#aaffaa"  # Light green
        assert VINTAGE.primary == "#00ff00"  # Bright green
        assert VINTAGE.error == "#ff3333"  # Red
    
    def test_dark_theme_properties(self):
        """Test dark theme has correct modern colors."""
        assert DARK.name == "orka-dark"
        assert DARK.background == "#0d1117"  # Dark gray
        assert DARK.foreground == "#c9d1d9"  # Light gray
        assert DARK.primary == "#58a6ff"  # Cyan
        assert DARK.success == "#3fb950"  # Green


class TestVimNavigation:
    """Test suite for Vim-style navigation."""
    
    @patch.object(OrKaTextualApp, 'focused', new_callable=lambda: MagicMock())
    def test_vim_down_action(self, mock_focused):
        """Test j key triggers down navigation."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        # Mock focused widget with cursor_down action
        mock_widget = MagicMock()
        mock_widget.action_cursor_down = MagicMock()
        mock_focused.return_value = mock_widget
        
        with patch.object(app, 'focused', mock_widget):
            app.action_vim_down()
        
        mock_widget.action_cursor_down.assert_called_once()
    
    @patch.object(OrKaTextualApp, 'focused', new_callable=lambda: MagicMock())
    def test_vim_up_action(self, mock_focused):
        """Test k key triggers up navigation."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        mock_widget = MagicMock()
        mock_widget.action_cursor_up = MagicMock()
        mock_focused.return_value = mock_widget
        
        with patch.object(app, 'focused', mock_widget):
            app.action_vim_up()
        
        mock_widget.action_cursor_up.assert_called_once()
    
    @patch.object(OrKaTextualApp, 'focused', new_callable=lambda: MagicMock())
    def test_vim_top_action(self, mock_focused):
        """Test g key triggers jump to top."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        mock_widget = MagicMock()
        mock_widget.action_scroll_home = MagicMock()
        mock_focused.return_value = mock_widget
        
        with patch.object(app, 'focused', mock_widget):
            app.action_vim_top()
        
        mock_widget.action_scroll_home.assert_called_once()
    
    @patch.object(OrKaTextualApp, 'focused', new_callable=lambda: MagicMock())
    def test_vim_bottom_action(self, mock_focused):
        """Test G key triggers jump to bottom."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        mock_widget = MagicMock()
        mock_widget.action_scroll_end = MagicMock()
        mock_focused.return_value = mock_widget
        
        with patch.object(app, 'focused', mock_widget):
            app.action_vim_bottom()
        
        mock_widget.action_scroll_end.assert_called_once()
    
    def test_vim_navigation_no_focused_widget(self):
        """Test vim navigation when no widget is focused."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        with patch.object(type(app), 'focused', new_callable=PropertyMock, return_value=None):
            # Should not raise exception
            app.action_vim_down()
            app.action_vim_up()
            app.action_vim_top()
            app.action_vim_bottom()
    
    def test_vim_navigation_widget_without_action(self):
        """Test vim navigation when widget doesn't support action."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        # Widget without navigation actions
        mock_widget = MagicMock(spec=[])
        
        with patch.object(type(app), 'focused', new_callable=PropertyMock, return_value=mock_widget):
            # Should not raise exception
            app.action_vim_down()
            app.action_vim_up()
            app.action_vim_top()
            app.action_vim_bottom()


class TestExportFunctionality:
    """Test suite for export functionality."""
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.tui.textual_app.Path")
    def test_export_memory_with_table_widget(self, mock_path, mock_file):
        """Test exporting memories from table widget."""
        mock_data_manager = MagicMock()
        mock_data_manager.memory_data = []
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen with memory table
        mock_screen = MagicMock()
        mock_table = MagicMock()
        mock_table.current_memories = [
            {"key": "mem1", "content": "content1"},
            {"key": "mem2", "content": "content2"}
        ]
        
        mock_screen.query_one = MagicMock(return_value=mock_table)
        
        # Mock Path
        mock_path.cwd.return_value = Path("/test")
        
        with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
            app.action_export_memory()
        
        # Should call json.dump with memories
        mock_file.assert_called_once()
        app.notify.assert_called()
        notification = app.notify.call_args[0][0]
        assert "Exported 2 memories" in notification
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("orka.tui.textual_app.Path")
    def test_export_memory_fallback_all_data(self, mock_path, mock_file):
        """Test export falls back to all data when no table."""
        mock_data_manager = MagicMock()
        mock_data_manager.memory_data = [
            {"entry": 1},
            {"entry": 2},
            {"entry": 3}
        ]
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen without table widget
        mock_screen = MagicMock()
        mock_screen.query_one = MagicMock(side_effect=Exception("No table"))
        
        mock_path.cwd.return_value = Path("/test")
        
        with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
            app.action_export_memory()
        
        # Should export all data
        mock_file.assert_called_once()
        app.notify.assert_called()
        notification = app.notify.call_args[0][0]
        assert "Exported 3 entries" in notification
    
    def test_export_memory_no_data(self):
        """Test export when no data available."""
        mock_data_manager = MagicMock()
        mock_data_manager.memory_data = []
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen without table
        mock_screen = MagicMock()
        mock_screen.query_one = MagicMock(side_effect=Exception("No table"))
        
        with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
            app.action_export_memory()
        
        # Should notify no data
        app.notify.assert_called()
        notification = app.notify.call_args[0][0]
        assert "No data" in notification or "no data" in notification.lower()
    
    def test_export_memory_no_table_widget_no_memories(self):
        """Test export when table has no memories."""
        mock_data_manager = MagicMock()
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen with empty table
        mock_screen = MagicMock()
        mock_table = MagicMock()
        mock_table.current_memories = []
        mock_screen.query_one = MagicMock(return_value=mock_table)
        
        with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
            app.action_export_memory()
        
        # Should notify no memories
        app.notify.assert_called()
        notification = app.notify.call_args[0][0]
        assert "No memories" in notification or "no memories" in notification.lower()
    
    def test_export_memory_screen_without_query(self):
        """Test export on screen without query_one method."""
        mock_data_manager = MagicMock()
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen without query_one
        mock_screen = MagicMock(spec=[])
        
        with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
            app.action_export_memory()
        
        # Should notify not available
        app.notify.assert_called()
        notification = app.notify.call_args[0][0]
        assert "not available" in notification.lower()


class TestHelpScreen:
    """Test suite for help screen functionality."""
    
    def test_help_screen_action(self):
        """Test help screen is shown."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        app.push_screen = MagicMock()
        
        app.action_show_help()
        
        app.push_screen.assert_called_once_with("help")


class TestScreenInitialization:
    """Test suite for screen initialization with new features."""
    
    def test_help_screen_installed(self):
        """Test help screen is in screens dict."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        # Trigger mount
        with patch.object(app, 'install_screen'):
            with patch.object(app, 'push_screen'):
                with patch.object(app, 'set_interval'):
                    app.on_mount()
        
        assert "help" in app.screens
    
    def test_all_screens_created(self):
        """Test all screens are created on mount."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        with patch.object(app, 'install_screen'):
            with patch.object(app, 'push_screen'):
                with patch.object(app, 'set_interval'):
                    app.on_mount()
        
        expected_screens = ["dashboard", "short_memory", "long_memory", 
                          "memory_logs", "health", "help"]
        
        for screen_name in expected_screens:
            assert screen_name in app.screens


class TestBindings:
    """Test suite for keybinding configuration."""
    
    def test_new_bindings_present(self):
        """Test new keybindings are registered."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        binding_keys = [binding.key for binding in app.BINDINGS]
        
        # Check new bindings
        assert "?" in binding_keys  # Help
        assert "e" in binding_keys  # Export
        assert "ctrl+p" in binding_keys  # Command palette (for theme switching)
        assert "j" in binding_keys  # Vim down
        assert "k" in binding_keys  # Vim up
        assert "g" in binding_keys  # Vim top
        assert "G" in binding_keys  # Vim bottom
    
    def test_vim_bindings_not_shown_in_footer(self):
        """Test vim bindings are hidden from footer."""
        mock_data_manager = MagicMock()
        app = OrKaTextualApp(mock_data_manager)
        
        # Find vim bindings
        vim_bindings = [b for b in app.BINDINGS if b.key in ["j", "k", "g", "G"]]
        
        # Should not be shown
        for binding in vim_bindings:
            assert binding.show is False


class TestIntegration:
    """Integration tests for multiple features working together."""
    
    def test_export_workflow(self):
        """Test exporting data works correctly."""
        mock_data_manager = MagicMock()
        mock_data_manager.memory_data = [{"test": "data"}]
        
        app = OrKaTextualApp(mock_data_manager)
        app.notify = MagicMock()
        
        # Mock screen for export
        mock_screen = MagicMock()
        mock_screen.query_one = MagicMock(side_effect=Exception("No table"))
        
        with patch("builtins.open", mock_open()):
            with patch("orka.tui.textual_app.Path"):
                with patch.object(type(app), 'screen', new_callable=PropertyMock, return_value=mock_screen):
                    app.action_export_memory()
        
        # Verify export was attempted
        assert app.notify.call_count >= 1
