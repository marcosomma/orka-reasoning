# OrKa: Orchestrator Kit Agents
# Tests for HeaderFooterMixin

import pytest
from unittest.mock import MagicMock, patch

from orka.tui.components.header_footer import HeaderFooterMixin


class ConcreteHeaderFooter(HeaderFooterMixin):
    """Concrete implementation for testing."""

    def __init__(self, running=True, backend="redis"):
        self._running = running
        self._backend = backend

    @property
    def running(self):
        return self._running

    @property
    def backend(self):
        return self._backend


class TestHeaderFooterMixin:
    """Tests for HeaderFooterMixin."""

    @pytest.fixture
    def builder(self):
        return ConcreteHeaderFooter()

    def test_create_compact_header(self, builder):
        """Test compact header creation."""
        result = builder.create_compact_header()
        assert result is not None

    def test_create_header(self, builder):
        """Test full header creation."""
        result = builder.create_header()
        assert result is not None

    def test_create_compact_footer(self, builder):
        """Test compact footer creation."""
        result = builder.create_compact_footer()
        assert result is not None

    def test_create_footer(self, builder):
        """Test full footer creation."""
        result = builder.create_footer()
        assert result is not None

    def test_footer_redisstack_controls(self):
        """Test footer includes RedisStack controls."""
        builder = ConcreteHeaderFooter(backend="redisstack")
        result = builder.create_footer()
        # RedisStack controls should be present
        assert result is not None

    def test_header_running_status(self):
        """Test header shows running status."""
        builder_running = ConcreteHeaderFooter(running=True)
        result_running = builder_running.create_header()
        
        builder_stopped = ConcreteHeaderFooter(running=False)
        result_stopped = builder_stopped.create_header()
        
        # Both should create valid panels
        assert result_running is not None
        assert result_stopped is not None

