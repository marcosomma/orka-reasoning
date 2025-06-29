"""
Unit tests for the tui_interface.py module.
Tests the TUI interface module imports and compatibility features.
"""


class TestTUIInterface:
    """Test suite for the TUI Interface module."""

    def test_module_imports(self):
        """Test that the module imports correctly."""
        # Import the module
        from orka import tui_interface

        # Check that the main class is available
        assert hasattr(tui_interface, "ModernTUIInterface")

        # Check __all__ export
        assert hasattr(tui_interface, "__all__")
        assert "ModernTUIInterface" in tui_interface.__all__

    def test_textual_availability_detection(self):
        """Test textual availability detection."""
        # Import the module to trigger textual availability check
        from orka import tui_interface

        # Check that TEXTUAL_AVAILABLE variable exists
        assert hasattr(tui_interface, "TEXTUAL_AVAILABLE")
        assert isinstance(tui_interface.TEXTUAL_AVAILABLE, bool)

    def test_orka_monitor_app_availability(self):
        """Test OrKaMonitorApp availability based on textual installation."""
        from orka import tui_interface

        # Test should work regardless of textual availability
        if tui_interface.TEXTUAL_AVAILABLE:
            # If textual is available, OrKaMonitorApp should be defined
            assert hasattr(tui_interface, "OrKaMonitorApp")
            assert "OrKaMonitorApp" in tui_interface.__all__
        else:
            # If textual is not available, module should still import successfully
            assert hasattr(tui_interface, "TEXTUAL_AVAILABLE")
            assert tui_interface.TEXTUAL_AVAILABLE is False

    def test_modern_tui_interface_import(self):
        """Test that ModernTUIInterface is properly imported."""
        from orka.tui_interface import ModernTUIInterface

        # Check that it's a class
        assert isinstance(ModernTUIInterface, type)

    def test_textual_app_import_attempt(self):
        """Test attempt to import OrKaTextualApp."""
        from orka import tui_interface

        # The import may succeed or fail depending on textual availability
        # We just check that the module handles it gracefully
        if hasattr(tui_interface, "OrKaTextualApp"):
            # If available, check it's a class or None
            assert tui_interface.OrKaTextualApp is None or isinstance(
                tui_interface.OrKaTextualApp,
                type,
            )

    def test_module_docstring(self):
        """Test that the module has proper documentation."""
        from orka import tui_interface

        # Check module docstring
        assert tui_interface.__doc__ is not None
        assert "OrKa Modern TUI Interface" in tui_interface.__doc__
        assert "Features:" in tui_interface.__doc__
