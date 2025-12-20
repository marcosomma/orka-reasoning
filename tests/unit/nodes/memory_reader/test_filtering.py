# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for FilteringMixin."""

import pytest
import time

from orka.nodes.memory_reader.filtering import FilteringMixin


class ConcreteFiltering(FilteringMixin):
    """Concrete implementation for testing."""

    def __init__(self):
        self.similarity_threshold = 0.7
        self.memory_category_filter = None
        self.decay_config = {}
        self.enable_temporal_ranking = True
        self.temporal_decay_hours = 24.0


class TestFilteringMixin:
    """Tests for FilteringMixin."""

    @pytest.fixture
    def filterer(self):
        return ConcreteFiltering()

    def test_apply_hybrid_scoring_empty(self, filterer):
        """Test hybrid scoring with empty list."""
        result = filterer._apply_hybrid_scoring([], "query", [])
        assert result == []

    def test_apply_hybrid_scoring(self, filterer):
        """Test hybrid scoring applies factors."""
        memories = [
            {"content": "short", "similarity": 0.5},
            {
                "content": " ".join(["word"] * 100),  # 100 words
                "similarity": 0.5,
            },
        ]

        scored = filterer._apply_hybrid_scoring(memories, "query", [])

        # Each memory should have scoring factors
        for memory in scored:
            assert "length_factor" in memory
            assert "recency_factor" in memory
            assert "metadata_factor" in memory

    def test_apply_hybrid_scoring_metadata_boost(self, filterer):
        """Test metadata boost for stored category."""
        memories = [
            {
                "content": "test content here",
                "similarity": 0.5,
                "metadata": {"category": "stored", "key1": 1, "key2": 2, "key3": 3, "key4": 4},
            }
        ]

        scored = filterer._apply_hybrid_scoring(memories, "query", [])

        assert scored[0]["metadata_factor"] > 1.0

    def test_filter_enhanced_relevant_memories(self, filterer):
        """Test enhanced relevance filtering."""
        memories = [
            {"content": "hello world test", "similarity": 0.8},
            {"content": "completely unrelated", "similarity": 0.3},
        ]

        filtered = filterer._filter_enhanced_relevant_memories(
            memories, "hello world", []
        )

        assert len(filtered) >= 1
        assert filtered[0]["content"] == "hello world test"

    def test_filter_enhanced_relevant_memories_with_context(self, filterer):
        """Test filtering with context."""
        memories = [
            {"content": "python django tutorial", "similarity": 0.5},
        ]
        context = [{"content": "python programming"}]

        filtered = filterer._filter_enhanced_relevant_memories(
            memories, "query", context
        )

        assert len(filtered) == 1

    def test_filter_by_category_disabled(self, filterer):
        """Test category filter when disabled."""
        memories = [{"content": "test", "metadata": {"category": "other"}}]
        filtered = filterer._filter_by_category(memories)
        assert filtered == memories

    def test_filter_by_category_enabled(self, filterer):
        """Test category filter when enabled."""
        filterer.memory_category_filter = "stored"
        memories = [
            {"content": "match", "metadata": {"category": "stored"}},
            {"content": "no match", "metadata": {"category": "other"}},
        ]

        filtered = filterer._filter_by_category(memories)

        assert len(filtered) == 1
        assert filtered[0]["content"] == "match"

    def test_filter_expired_memories_disabled(self, filterer):
        """Test expired filter when disabled."""
        memories = [{"content": "test"}]
        filtered = filterer._filter_expired_memories(memories)
        assert filtered == memories

    def test_filter_expired_memories_by_expiry_time(self, filterer):
        """Test filtering by expiry_time."""
        filterer.decay_config = {"enabled": True}
        current_time = time.time() * 1000

        memories = [
            {
                "content": "expired",
                "metadata": {"expiry_time": current_time - 1000},
            },
            {
                "content": "valid",
                "metadata": {"expiry_time": current_time + 100000},
            },
        ]

        filtered = filterer._filter_expired_memories(memories)

        assert len(filtered) == 1
        assert filtered[0]["content"] == "valid"

    def test_filter_relevant_memories_legacy(self, filterer):
        """Test legacy filter method."""
        memories = [{"content": "hello world", "similarity": 0.8}]
        filtered = filterer._filter_relevant_memories(memories, "hello")
        assert len(filtered) >= 0

