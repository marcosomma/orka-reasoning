# OrKa: Orchestrator Kit Agents — Brain Context Analyzer Tests

"""Tests for the ContextAnalyzer and ContextFeatures."""

import pytest

from orka.brain.context_analyzer import ContextAnalyzer, ContextFeatures


class TestContextFeatures:
    def test_roundtrip(self):
        features = ContextFeatures(
            task_structures=["decomposition", "sequential"],
            cognitive_patterns=["analysis", "synthesis"],
            input_shape="single_text",
            output_shape="structured",
            complexity=7,
            domain_hints=["nlp"],
            abstract_goal="Analyze text and produce structured output",
        )
        data = features.to_dict()
        restored = ContextFeatures.from_dict(data)
        assert restored.task_structures == features.task_structures
        assert restored.cognitive_patterns == features.cognitive_patterns
        assert restored.complexity == 7

    def test_to_embedding_text(self):
        features = ContextFeatures(
            task_structures=["decomposition"],
            cognitive_patterns=["analysis"],
            abstract_goal="Break down input",
        )
        text = features.to_embedding_text()
        assert "decomposition" in text
        assert "analysis" in text
        assert "Break down input" in text

    def test_fingerprint_stable(self):
        features = ContextFeatures(
            task_structures=["a", "b"],
            cognitive_patterns=["x", "y"],
            input_shape="text",
            output_shape="list",
            abstract_goal="test",
        )
        fp1 = features.fingerprint()
        fp2 = features.fingerprint()
        assert fp1 == fp2

    def test_fingerprint_order_independent(self):
        f1 = ContextFeatures(
            task_structures=["a", "b"],
            cognitive_patterns=["x", "y"],
            abstract_goal="test",
        )
        f2 = ContextFeatures(
            task_structures=["b", "a"],
            cognitive_patterns=["y", "x"],
            abstract_goal="test",
        )
        assert f1.fingerprint() == f2.fingerprint()

    def test_similarity_identical(self):
        f = ContextFeatures(
            task_structures=["decomposition", "sequential"],
            cognitive_patterns=["analysis"],
            input_shape="text",
            output_shape="text",
        )
        assert f.similarity_to(f) == 1.0

    def test_similarity_different(self):
        f1 = ContextFeatures(
            task_structures=["decomposition"],
            cognitive_patterns=["analysis"],
            input_shape="text",
            output_shape="text",
        )
        f2 = ContextFeatures(
            task_structures=["routing"],
            cognitive_patterns=["classification"],
            input_shape="structured",
            output_shape="boolean",
        )
        score = f1.similarity_to(f2)
        assert score < 0.3

    def test_similarity_partial_overlap(self):
        f1 = ContextFeatures(
            task_structures=["decomposition", "sequential"],
            cognitive_patterns=["analysis", "synthesis"],
            input_shape="text",
            output_shape="text",
        )
        f2 = ContextFeatures(
            task_structures=["decomposition", "parallel"],
            cognitive_patterns=["analysis", "generation"],
            input_shape="text",
            output_shape="structured",
        )
        score = f1.similarity_to(f2)
        # Should be moderate — shares some structures and patterns
        assert 0.3 < score < 0.8

    def test_similarity_empty_features(self):
        f1 = ContextFeatures()
        f2 = ContextFeatures()
        # Both empty — shapes match (both "unknown")
        score = f1.similarity_to(f2)
        assert score > 0.0


class TestContextAnalyzer:
    def setup_method(self):
        self.analyzer = ContextAnalyzer()

    def test_detect_decomposition(self):
        context = {"task": "Break down this document into sections and analyze each"}
        features = self.analyzer.analyze(context)
        assert "decomposition" in features.task_structures

    def test_detect_sequential(self):
        context = {"task": "First parse the input, then validate, then store"}
        features = self.analyzer.analyze(context)
        assert "sequential" in features.task_structures

    def test_detect_parallel(self):
        context = {"task": "Run all checks simultaneously", "strategy": "parallel"}
        features = self.analyzer.analyze(context)
        assert "parallel" in features.task_structures

    def test_detect_validation(self):
        context = {"task": "Validate the data and check for errors"}
        features = self.analyzer.analyze(context)
        assert "validation" in features.task_structures

    def test_detect_analysis_pattern(self):
        context = {"task": "Analyze the sentiment of customer reviews"}
        features = self.analyzer.analyze(context)
        assert "analysis" in features.cognitive_patterns

    def test_detect_generation_pattern(self):
        context = {"task": "Generate a summary report"}
        features = self.analyzer.analyze(context)
        assert "generation" in features.cognitive_patterns

    def test_detect_classification_pattern(self):
        context = {"task": "Classify these tickets into categories"}
        features = self.analyzer.analyze(context)
        assert "classification" in features.cognitive_patterns

    def test_input_shape_text(self):
        context = {"input": "short text"}
        features = self.analyzer.analyze(context)
        assert features.input_shape == "single_text"

    def test_input_shape_long_text(self):
        context = {"input": "x" * 1500}
        features = self.analyzer.analyze(context)
        assert features.input_shape == "long_text"

    def test_input_shape_list(self):
        context = {"input": ["item1", "item2"]}
        features = self.analyzer.analyze(context)
        assert features.input_shape == "list"

    def test_input_shape_dict(self):
        context = {"input": {"key": "value"}}
        features = self.analyzer.analyze(context)
        assert features.input_shape == "structured"

    def test_output_shape_json(self):
        context = {"output_format": "json", "task": "do stuff"}
        features = self.analyzer.analyze(context)
        assert features.output_shape == "structured"

    def test_output_shape_boolean(self):
        context = {"output_format": "yes/no", "task": "decide"}
        features = self.analyzer.analyze(context)
        assert features.output_shape == "boolean"

    def test_complexity_increases_with_structures(self):
        simple = {"task": "Do one thing"}
        complex_ctx = {
            "task": "First break down, then compare and filter, route to best, loop until optimal",
            "agents": ["a", "b", "c", "d"],
        }
        simple_features = self.analyzer.analyze(simple)
        complex_features = self.analyzer.analyze(complex_ctx)
        assert complex_features.complexity > simple_features.complexity

    def test_domain_hints_extracted(self):
        context = {"domain": "finance", "task": "analyze data"}
        features = self.analyzer.analyze(context)
        assert "finance" in features.domain_hints

    def test_abstract_goal_generated(self):
        context = {"task": "Analyze the data and generate a report"}
        features = self.analyzer.analyze(context)
        assert features.abstract_goal != ""

    def test_metadata_preserved(self):
        context = {"domain": "nlp", "task": "parse", "strategy": "sequential", "extra": "ignored"}
        features = self.analyzer.analyze(context)
        assert features.metadata.get("domain") == "nlp"
        assert features.metadata.get("strategy") == "sequential"
        assert "extra" not in features.metadata

    def test_empty_context(self):
        features = self.analyzer.analyze({})
        assert isinstance(features, ContextFeatures)
        assert features.input_shape == "unknown"
