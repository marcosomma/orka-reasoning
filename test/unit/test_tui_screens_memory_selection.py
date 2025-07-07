"""
Tests for TUI screen memory selection functionality.
"""

from unittest.mock import Mock, patch

import pytest

# First check if textual is available
try:
    import textual

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


# Only run these tests if textual is available
@pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="Textual not available")
class TestMemorySelection:
    """Test memory selection behavior in TUI screens."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_data_manager = Mock()
        self.mock_data_manager._get_content.return_value = "Test content"
        self.mock_data_manager._format_metadata_for_display.return_value = "[cyan]key:[/cyan] value"
        self.mock_data_manager._get_key.return_value = "test_memory_key_123"
        self.mock_data_manager._get_memory_type.return_value = "short_term"
        self.mock_data_manager._get_importance_score.return_value = 0.8
        self.mock_data_manager._get_node_id.return_value = "test_node"

        # Mock textual components
        self.textual_mocks = {
            "textual.app": Mock(),
            "textual.containers": Mock(),
            "textual.screen": Mock(),
            "textual.widgets": Mock(),
        }

    def test_short_memory_screen_memory_selection(self):
        """Test memory selection in ShortMemoryScreen."""
        # Mock textual imports
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            # Create screen with mocked dependencies
            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify content widget was updated
                mock_content_widget.update.assert_called_once()

                # Verify the update call contained expected sections
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "📄 CONTENT:" in update_call_args
                assert "📋 METADATA:" in update_call_args
                assert "🏷️ SYSTEM INFO:" in update_call_args

    def test_memory_deselection(self):
        """Test memory deselection shows placeholder."""
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create deselection message
                mock_message = Mock()
                mock_message.memory_data = None

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify placeholder text was set
                mock_content_widget.update.assert_called_once_with(
                    "[dim]Select a row to view memory content and metadata[/dim]",
                )

    def test_memory_selection_error_handling(self):
        """Test error handling in memory selection."""
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query to raise exception
                screen.query_one = Mock(side_effect=Exception("Widget not found"))

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test"}

                # Call should not raise exception
                try:
                    screen.on_memory_table_widget_memory_selected(mock_message)
                except Exception:
                    pytest.fail("Memory selection should handle errors gracefully")

    def test_memory_selection_with_data_manager_error(self):
        """Test memory selection when DataManager methods fail."""
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Make DataManager method raise exception
                self.mock_data_manager._get_content.side_effect = Exception("Data error")

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test"}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify error message was displayed
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "[red]Error loading content:" in update_call_args

    def test_long_memory_screen_similarity(self):
        """Test LongMemoryScreen has similar behavior to ShortMemoryScreen."""
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import LongMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = LongMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify content widget was updated with expected sections
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "📄 CONTENT:" in update_call_args
                assert "📋 METADATA:" in update_call_args
                assert "🏷️ SYSTEM INFO:" in update_call_args

    def test_logs_screen_shows_log_type(self):
        """Test MemoryLogsScreen shows log type instead of memory type."""
        self.mock_data_manager._get_log_type.return_value = "orchestration"

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import MemoryLogsScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = MemoryLogsScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify log type is shown instead of memory type
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "[cyan]Log Type:[/cyan] orchestration" in update_call_args

    def test_memory_selection_with_long_content(self):
        """Test memory selection with long content shows full content (scrollable)."""
        # Create very long content
        long_content = "A" * 500
        self.mock_data_manager._get_content.return_value = long_content

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": long_content, "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify full content is displayed (no truncation)
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                # Check that the full content is present and available for scrolling
                assert long_content in update_call_args
                # Check that truncation ellipsis is NOT present (removed truncation)
                assert "[dim]...[/dim]" not in update_call_args

    def test_memory_selection_with_empty_content(self):
        """Test memory selection with empty content shows placeholder."""
        self.mock_data_manager._get_content.return_value = ""

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify empty content placeholder is shown
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "[dim]No content[/dim]" in update_call_args

    def test_memory_selection_with_none_content(self):
        """Test memory selection with None content shows placeholder."""
        self.mock_data_manager._get_content.return_value = None

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": None, "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify None content placeholder is shown
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "[dim]No content[/dim]" in update_call_args

    def test_memory_selection_with_long_key(self):
        """Test memory selection with long key gets truncated."""
        long_key = "very_long_memory_key_" + "x" * 100
        self.mock_data_manager._get_key.return_value = long_key

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify key was truncated to last 20 characters
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                expected_key = long_key[-20:]
                assert f"...{expected_key}" in update_call_args

    def test_logs_screen_deselection(self):
        """Test MemoryLogsScreen deselection shows appropriate placeholder."""
        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import MemoryLogsScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = MemoryLogsScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create deselection message
                mock_message = Mock()
                mock_message.memory_data = None

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify appropriate placeholder text was set
                mock_content_widget.update.assert_called_once_with(
                    "[dim]Select a row to view entry details and metadata[/dim]",
                )

    def test_system_info_formatting(self):
        """Test system info section formatting."""
        self.mock_data_manager._get_memory_type.return_value = "long_term"
        self.mock_data_manager._get_importance_score.return_value = 0.95
        self.mock_data_manager._get_node_id.return_value = "node_abc123"

        with patch.dict("sys.modules", self.textual_mocks):
            from orka.tui.textual_screens import ShortMemoryScreen

            with patch("orka.tui.textual_screens.Static") as mock_static:
                screen = ShortMemoryScreen(self.mock_data_manager)

                # Mock the widget query
                mock_content_widget = Mock()
                screen.query_one = Mock(return_value=mock_content_widget)

                # Create memory selection message
                mock_message = Mock()
                mock_message.memory_data = {"content": "test", "metadata": {"key": "value"}}

                # Call the selection handler
                screen.on_memory_table_widget_memory_selected(mock_message)

                # Verify system info formatting
                mock_content_widget.update.assert_called_once()
                update_call_args = mock_content_widget.update.call_args[0][0]
                assert "[cyan]Type:[/cyan] long_term" in update_call_args
                assert "[cyan]Node ID:[/cyan] node_abc123" in update_call_args
                assert "[cyan]Importance:[/cyan] 0.95" in update_call_args


# Test that we can at least test the basic functionality when textual is not available
class TestWithoutTextual:
    """Test basic functionality when textual is not available."""

    def test_textual_availability(self):
        """Test that we can detect textual availability."""
        # This test will always pass but documents the textual availability
        assert isinstance(TEXTUAL_AVAILABLE, bool)

    def test_can_import_data_manager(self):
        """Test that DataManager can be imported even without textual."""
        from orka.tui.data_manager import DataManager

        data_manager = DataManager()
        assert data_manager is not None
