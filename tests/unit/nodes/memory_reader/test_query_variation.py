# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for QueryVariationMixin."""

import pytest

from orka.nodes.memory_reader.query_variation import QueryVariationMixin


class ConcreteQueryVariation(QueryVariationMixin):
    """Concrete implementation for testing."""

    pass


class TestQueryVariationMixin:
    """Tests for QueryVariationMixin."""

    @pytest.fixture
    def generator(self):
        return ConcreteQueryVariation()

    def test_generate_query_variations_single_word(self, generator):
        """Test variations for single word query."""
        variations = generator._generate_query_variations("python")

        assert "python" in variations
        assert "about python" in variations
        assert len(variations) >= 3

    def test_generate_query_variations_two_words(self, generator):
        """Test variations for two word query."""
        variations = generator._generate_query_variations("machine learning")

        assert "machine learning" in variations
        assert "learning machine" in variations  # Reversed

    def test_generate_query_variations_multi_word(self, generator):
        """Test variations for multi-word query."""
        variations = generator._generate_query_variations("natural language processing basics")

        assert "natural language processing basics" in variations
        # Should include first and last word variation
        assert any("natural" in v and "basics" in v for v in variations)

    def test_generate_query_variations_empty(self, generator):
        """Test variations for empty query."""
        variations = generator._generate_query_variations("")
        assert variations == []

    def test_generate_query_variations_short(self, generator):
        """Test variations for very short query."""
        variations = generator._generate_query_variations("a")
        assert variations == []

    def test_generate_query_variations_unique(self, generator):
        """Test that variations are unique."""
        variations = generator._generate_query_variations("hello world")
        assert len(variations) == len(set(variations))

    def test_generate_enhanced_query_variations(self, generator):
        """Test enhanced variations with context."""
        query = "python programming"
        context = [{"content": "Django framework tutorial"}]

        variations = generator._generate_enhanced_query_variations(query, context)

        assert query in variations
        # Should include context-enhanced variations
        assert len(variations) > 1

    def test_generate_enhanced_query_variations_no_context(self, generator):
        """Test enhanced variations without context."""
        query = "python"
        variations = generator._generate_enhanced_query_variations(query, [])

        assert query in variations

    def test_generate_enhanced_query_variations_limit(self, generator):
        """Test that variations are limited to 8."""
        query = "test query"
        context = [
            {"content": "word1 word2 word3 word4 word5"},
            {"content": "word6 word7 word8 word9 word10"},
        ]

        variations = generator._generate_enhanced_query_variations(query, context)

        assert len(variations) <= 8

