# OrKa: Orchestrator Kit Agents
# Copyright © 2025 Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning

"""Tests for memory_reader utility functions."""

import pytest
import numpy as np

from orka.nodes.memory_reader.utils import calculate_overlap, cosine_similarity


class TestCalculateOverlap:
    """Tests for calculate_overlap function."""

    def test_overlap_identical(self):
        """Test overlap with identical strings."""
        score = calculate_overlap("hello world", "hello world")
        assert score == 2.0  # Perfect match gets 2x boost

    def test_overlap_partial(self):
        """Test overlap with partial match."""
        score = calculate_overlap("hello world", "hello there friend")
        assert 0 < score < 1.0  # Partial match

    def test_overlap_no_match(self):
        """Test overlap with no matching words."""
        score = calculate_overlap("hello world", "foo bar baz")
        assert score == 0.0

    def test_overlap_empty_first(self):
        """Test overlap with empty first string."""
        score = calculate_overlap("", "hello world")
        assert score == 0.0

    def test_overlap_empty_second(self):
        """Test overlap with empty second string."""
        score = calculate_overlap("hello world", "")
        assert score == 0.0

    def test_overlap_case_insensitive(self):
        """Test overlap is case insensitive."""
        score = calculate_overlap("Hello World", "hello world")
        assert score == 2.0  # Perfect match after lowercasing


class TestCosineSimilarity:
    """Tests for cosine_similarity function."""

    def test_identical_vectors(self):
        """Test cosine similarity with identical vectors."""
        vec = np.array([1.0, 2.0, 3.0])
        score = cosine_similarity(vec, vec)
        assert abs(score - 1.0) < 0.001

    def test_orthogonal_vectors(self):
        """Test cosine similarity with orthogonal vectors."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        score = cosine_similarity(vec1, vec2)
        assert abs(score) < 0.001

    def test_opposite_vectors(self):
        """Test cosine similarity with opposite vectors."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        score = cosine_similarity(vec1, vec2)
        assert abs(score + 1.0) < 0.001

    def test_zero_vector(self):
        """Test cosine similarity with zero vector."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([0.0, 0.0, 0.0])
        score = cosine_similarity(vec1, vec2)
        assert score == 0.0

    def test_list_input(self):
        """Test cosine similarity with list input."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        score = cosine_similarity(vec1, vec2)
        assert abs(score - 1.0) < 0.001

