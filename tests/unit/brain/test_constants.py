# OrKa: Orchestrator Kit Agents — Brain Constants Tests

"""Tests for the brain constants module."""

from orka.brain.constants import ACTION_VERB_CANONICAL, ACTION_VERBS, MAX_ACTION_LENGTH


class TestActionVerbs:
    def test_is_frozenset(self):
        assert isinstance(ACTION_VERBS, frozenset)

    def test_non_empty(self):
        assert len(ACTION_VERBS) > 100

    def test_all_lowercase(self):
        for verb in ACTION_VERBS:
            assert verb == verb.lower(), f"Verb '{verb}' is not lowercase"

    def test_no_whitespace(self):
        for verb in ACTION_VERBS:
            assert verb.strip() == verb, f"Verb '{verb}' has whitespace"

    def test_common_verbs_present(self):
        """Core cognitive verbs must be present."""
        expected = {"analyze", "evaluate", "implement", "validate", "deploy", "document"}
        assert expected.issubset(ACTION_VERBS)


class TestActionVerbCanonical:
    def test_keys_are_in_action_verbs(self):
        """Every canonical mapping key must exist in the ACTION_VERBS set."""
        for key in ACTION_VERB_CANONICAL:
            assert key in ACTION_VERBS, f"Canonical key '{key}' not in ACTION_VERBS"

    def test_values_are_strings(self):
        for key, val in ACTION_VERB_CANONICAL.items():
            assert isinstance(val, str), f"Value for '{key}' is not a string"

    def test_known_mappings(self):
        assert ACTION_VERB_CANONICAL["fix"] == "mitigate"
        assert ACTION_VERB_CANONICAL["build"] == "construct"
        assert ACTION_VERB_CANONICAL["test"] == "validate"

    def test_is_not_empty(self):
        assert len(ACTION_VERB_CANONICAL) > 10


class TestMaxActionLength:
    def test_positive_integer(self):
        assert isinstance(MAX_ACTION_LENGTH, int)
        assert MAX_ACTION_LENGTH > 0

    def test_value(self):
        assert MAX_ACTION_LENGTH == 60
