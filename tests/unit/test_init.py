"""Unit tests for orka/__init__.py."""
import unittest
from unittest.mock import patch

# Mark all tests in this class as unit tests
import pytest
pytestmark = pytest.mark.unit


class TestInit(unittest.TestCase):
    """Test suite for the orka package's __init__.py."""

    def test_import_orka(self):
        """Test that the orka package can be imported without errors."""
        try:
            import orka
            self.assertIsNotNone(orka)
        except ImportError as e:
            self.fail(f"Failed to import orka package: {e}")

    @patch.dict('sys.modules', {'orka.agents': None, 'orka.nodes': None})
    def test_selective_imports(self):
        """Test that specific modules are imported correctly."""
        import orka
        # Check if some key modules are imported
        self.assertTrue(hasattr(orka, 'Orchestrator'))
        self.assertTrue(hasattr(orka, 'YAMLLoader'))
        self.assertTrue(hasattr(orka, 'ForkGroupManager'))
        self.assertTrue(hasattr(orka, 'RedisMemoryLogger'))

    def test_all_variable(self):
        """Test that the __all__ variable is defined."""
        import orka
        self.assertTrue(hasattr(orka, '__all__'))
        self.assertIsInstance(orka.__all__, list)


if __name__ == '__main__':
    unittest.main()
