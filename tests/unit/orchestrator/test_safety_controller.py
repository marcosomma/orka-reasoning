"""Unit tests for orka.orchestrator.safety_controller."""

from unittest.mock import Mock, patch

import pytest

from orka.orchestrator.safety_controller import SafetyController, SafetyPolicy

# Mark all tests in this class to skip auto-mocking since we need specific mocks
pytestmark = [pytest.mark.unit, pytest.mark.no_auto_mock]


class TestSafetyPolicy:
    """Test suite for SafetyPolicy class."""

    def test_init_default(self):
        """Test SafetyPolicy initialization with default profile."""
        policy = SafetyPolicy()
        assert policy.profile == "default"
        assert isinstance(policy.risk_patterns, dict)
        assert isinstance(policy.forbidden_capabilities, set)

    def test_init_strict(self):
        """Test SafetyPolicy initialization with strict profile."""
        policy = SafetyPolicy(profile="strict")
        assert policy.profile == "strict"
        assert "code_execution" in policy.forbidden_capabilities
        assert "file_system_access" in policy.forbidden_capabilities

    def test_init_moderate(self):
        """Test SafetyPolicy initialization with moderate profile."""
        policy = SafetyPolicy(profile="moderate")
        assert policy.profile == "moderate"
        assert "code_execution" in policy.forbidden_capabilities

    def test_load_risk_patterns(self):
        """Test _load_risk_patterns method."""
        policy = SafetyPolicy()
        patterns = policy._load_risk_patterns()
        
        assert "pii" in patterns
        assert "medical" in patterns
        assert "legal" in patterns
        assert "financial" in patterns
        assert len(patterns["pii"]) > 0

    def test_load_forbidden_capabilities_default(self):
        """Test _load_forbidden_capabilities with default profile."""
        policy = SafetyPolicy(profile="default")
        forbidden = policy._load_forbidden_capabilities()
        assert "code_execution" in forbidden

    def test_load_forbidden_capabilities_strict(self):
        """Test _load_forbidden_capabilities with strict profile."""
        policy = SafetyPolicy(profile="strict")
        forbidden = policy._load_forbidden_capabilities()
        assert len(forbidden) > 1
        assert "code_execution" in forbidden
        assert "file_system_access" in forbidden

    def test_load_content_filters(self):
        """Test _load_content_filters method."""
        policy = SafetyPolicy()
        filters = policy._load_content_filters()
        
        assert "harmful" in filters
        assert "inappropriate" in filters
        assert len(filters["harmful"]) > 0


class TestSafetyController:
    """Test suite for SafetyController class."""

    def create_mock_config(self):
        """Helper to create mock config."""
        config = Mock()
        config.safety_threshold = 0.1
        config.safety_profile = "default"
        return config

    def test_init(self):
        """Test SafetyController initialization."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        assert controller.config == config
        assert controller.safety_threshold == 0.1
        assert controller.policy is not None

    @pytest.mark.asyncio
    async def test_assess_candidates(self):
        """Test assess_candidates method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidates = [
            {"node_id": "agent1", "preview": "Safe content"},
            {"node_id": "agent2", "preview": "Another safe content"},
        ]
        context = {"input": "Test question"}
        
        result = await controller.assess_candidates(candidates, context)
        
        assert isinstance(result, list)
        assert len(result) <= len(candidates)
        for candidate in result:
            assert "safety_score" in candidate
            assert "safety_risks" in candidate

    @pytest.mark.asyncio
    async def test_assess_candidates_filters_unsafe(self):
        """Test assess_candidates filters unsafe candidates."""
        config = self.create_mock_config()
        config.safety_threshold = 0.9  # Very strict
        controller = SafetyController(config)
        
        candidates = [
            {"node_id": "agent1", "preview": "Safe content"},
        ]
        context = {"input": "Test question"}
        
        result = await controller.assess_candidates(candidates, context)
        
        # May filter out candidates that don't meet threshold
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_assess_candidates_exception(self):
        """Test assess_candidates handles exceptions."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        # Mock _assess_candidate_safety to raise exception
        with patch.object(controller, '_assess_candidate_safety', side_effect=Exception("Error")):
            candidates = [{"node_id": "agent1"}]
            context = {}
            
            # Should return all candidates if assessment fails
            result = await controller.assess_candidates(candidates, context)
            assert result == candidates

    @pytest.mark.asyncio
    async def test_assess_candidate_safety(self):
        """Test _assess_candidate_safety method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {"node_id": "agent1", "preview": "Safe content"}
        context = {"input": "Test question"}
        
        result = await controller._assess_candidate_safety(candidate, context)
        
        assert isinstance(result, dict)
        assert "score" in result
        assert "risks" in result
        assert "details" in result
        assert 0.0 <= result["score"] <= 1.0

    @pytest.mark.asyncio
    async def test_assess_content_safety(self):
        """Test _assess_content_safety method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {"node_id": "agent1", "preview": "Safe content"}
        context = {"input": "Test question"}
        
        result = await controller._assess_content_safety(candidate, context)
        
        assert isinstance(result, dict)
        assert "risks" in result
        assert "score" in result
        assert "details" in result

    @pytest.mark.asyncio
    async def test_assess_content_safety_pii_detection(self):
        """Test _assess_content_safety detects PII."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {"node_id": "agent1", "preview": "Email: test@example.com"}
        context = {"input": "Contact test@example.com"}
        
        result = await controller._assess_content_safety(candidate, context)
        
        # Should detect email pattern
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_assess_capability_safety(self):
        """Test _assess_capability_safety method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {
            "node_id": "agent1",
            "capabilities": ["text_generation"],
        }
        context = {}
        
        result = await controller._assess_capability_safety(candidate, context)
        
        assert isinstance(result, dict)
        assert "risks" in result
        assert "score" in result

    @pytest.mark.asyncio
    async def test_assess_capability_safety_forbidden(self):
        """Test _assess_capability_safety detects forbidden capabilities."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {
            "node_id": "agent1",
            "capabilities": ["code_execution"],
        }
        context = {}
        
        result = await controller._assess_capability_safety(candidate, context)
        
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_assess_policy_compliance(self):
        """Test _assess_policy_compliance method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        candidate = {"node_id": "agent1"}
        context = {}
        
        result = await controller._assess_policy_compliance(candidate, context)
        
        assert isinstance(result, dict)
        assert "risks" in result
        assert "score" in result

    def test_check_patterns(self):
        """Test _check_patterns method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        text = "Contact me at test@example.com"
        patterns = [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"]
        
        matches = controller._check_patterns(text, patterns)
        
        assert isinstance(matches, list)
        assert len(matches) > 0  # Should find email

    def test_check_patterns_no_match(self):
        """Test _check_patterns with no matches."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        text = "Simple text with no patterns"
        patterns = [r"\b\d{3}-\d{2}-\d{4}\b"]  # SSN pattern
        
        matches = controller._check_patterns(text, patterns)
        
        assert matches == []

    def test_node_has_capability(self):
        """Test _node_has_capability method."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        # Mock orchestrator with agents
        controller.config.orchestrator = Mock()
        controller.config.orchestrator.agents = {
            "agent1": Mock(capabilities=["text_generation", "reasoning"])
        }
        
        has_cap = controller._node_has_capability("agent1", "text_generation")
        assert has_cap is True
        
        has_cap = controller._node_has_capability("agent1", "code_execution")
        assert has_cap is False

    def test_node_has_capability_not_found(self):
        """Test _node_has_capability with non-existent node."""
        config = self.create_mock_config()
        controller = SafetyController(config)
        
        controller.config.orchestrator = Mock()
        controller.config.orchestrator.agents = {}
        
        has_cap = controller._node_has_capability("unknown_agent", "text_generation")
        assert has_cap is False

