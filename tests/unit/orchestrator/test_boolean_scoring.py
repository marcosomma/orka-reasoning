"""Unit tests for orka.orchestrator.boolean_scoring."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from orka.orchestrator.boolean_scoring import BooleanCriteriaResult, BooleanScoringEngine

# Mark all tests in this module for unit testing
pytestmark = [pytest.mark.unit]


class TestBooleanCriteriaResult:
    """Test suite for BooleanCriteriaResult dataclass."""

    def test_boolean_criteria_result_creation(self):
        """Test creating a BooleanCriteriaResult."""
        result = BooleanCriteriaResult(
            path=["agent1", "agent2"],
            criteria_results={"input_readiness": {"all_required_inputs_available": True}},
            passed_criteria=1,
            total_criteria=1,
            overall_pass=True,
            critical_failures=[],
            pass_percentage=1.0,
            audit_trail="Test audit trail",
            reasoning="Test reasoning",
        )
        assert result.path == ["agent1", "agent2"]
        assert result.overall_pass is True
        assert result.passed_criteria == 1
        assert result.pass_percentage == 1.0

    def test_boolean_criteria_result_default_reasoning(self):
        """Test BooleanCriteriaResult with default reasoning."""
        result = BooleanCriteriaResult(
            path=["agent1"],
            criteria_results={},
            passed_criteria=0,
            total_criteria=0,
            overall_pass=False,
            critical_failures=[],
            pass_percentage=0.0,
            audit_trail="",
        )
        assert result.reasoning == ""


class TestBooleanScoringEngine:
    """Test suite for BooleanScoringEngine class."""

    def create_mock_config(self, **kwargs):
        """Helper to create a mock config object."""
        config = Mock()
        config.min_success_rate = kwargs.get("min_success_rate", 0.70)
        config.min_domain_overlap = kwargs.get("min_domain_overlap", 0.30)
        config.max_acceptable_cost = kwargs.get("max_acceptable_cost", 0.10)
        config.max_acceptable_latency = kwargs.get("max_acceptable_latency", 10000)
        config.optimal_path_length = kwargs.get("optimal_path_length", (2, 3))
        config.risky_capabilities = kwargs.get(
            "risky_capabilities",
            {"file_write", "code_execution", "external_api", "database_write"},
        )
        config.required_safety_markers = kwargs.get(
            "required_safety_markers", {"sandboxed", "read_only", "validated"}
        )
        config.strict_mode = kwargs.get("strict_mode", False)
        config.require_critical = kwargs.get("require_critical", True)
        config.important_threshold = kwargs.get("important_threshold", 0.8)
        config.include_nice_to_have = kwargs.get("include_nice_to_have", True)
        return config

    def test_init_defaults(self):
        """Test BooleanScoringEngine initialization with defaults."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)
        assert engine.min_success_rate == 0.70
        assert engine.min_domain_overlap == 0.30
        assert engine.max_acceptable_cost == 0.10
        assert engine.max_acceptable_latency == 10000
        assert engine.optimal_path_length == (2, 3)
        assert engine.strict_mode is False
        assert engine.require_critical is True

    def test_init_custom_values(self):
        """Test BooleanScoringEngine initialization with custom values."""
        config = self.create_mock_config(
            min_success_rate=0.80,
            max_acceptable_cost=0.05,
            strict_mode=True,
            require_critical=False,
        )
        engine = BooleanScoringEngine(config)
        assert engine.min_success_rate == 0.80
        assert engine.max_acceptable_cost == 0.05
        assert engine.strict_mode is True
        assert engine.require_critical is False

    @pytest.mark.asyncio
    async def test_check_input_readiness_all_available(self):
        """Test _check_input_readiness when all inputs are available."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = ["input1", "input2"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {
            "orchestrator": mock_orchestrator,
            "previous_outputs": {"input1": "value1", "input2": "value2"},
        }

        result = await engine._check_input_readiness(candidate, context)

        assert result["all_required_inputs_available"] is True
        assert result["no_circular_dependencies"] is True
        assert result["input_types_compatible"] is True

    @pytest.mark.asyncio
    async def test_check_input_readiness_missing_inputs(self):
        """Test _check_input_readiness when inputs are missing."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = ["input1", "input2", "input3"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {
            "orchestrator": mock_orchestrator,
            "previous_outputs": {"input1": "value1"},  # Missing input2 and input3
        }

        result = await engine._check_input_readiness(candidate, context)

        assert result["all_required_inputs_available"] is False
        assert result["no_circular_dependencies"] is True

    @pytest.mark.asyncio
    async def test_check_input_readiness_no_required_inputs(self):
        """Test _check_input_readiness when agent has no required inputs."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator, "previous_outputs": {}}

        result = await engine._check_input_readiness(candidate, context)

        assert result["all_required_inputs_available"] is True  # No requirements

    @pytest.mark.asyncio
    async def test_check_input_readiness_circular_dependency(self):
        """Test _check_input_readiness detects circular dependencies."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = ["input1"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {
            "orchestrator": mock_orchestrator,
            "previous_outputs": {"agent1": "output"},  # Agent already executed
        }

        result = await engine._check_input_readiness(candidate, context)

        assert result["no_circular_dependencies"] is False

    @pytest.mark.asyncio
    async def test_check_input_readiness_no_orchestrator(self):
        """Test _check_input_readiness when orchestrator is missing."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {}

        result = await engine._check_input_readiness(candidate, context)

        assert result["all_required_inputs_available"] is True
        assert result["no_circular_dependencies"] is True
        assert result["input_types_compatible"] is True

    @pytest.mark.asyncio
    async def test_check_safety_no_risky_capabilities(self):
        """Test _check_safety when agent has no risky capabilities."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["text_generation"]
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["no_risky_capabilities_without_sandbox"] is True

    @pytest.mark.asyncio
    async def test_check_safety_risky_with_safety_markers(self):
        """Test _check_safety when risky capabilities have safety markers."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["file_write", "code_execution"]
        mock_agent.safety_tags = ["sandboxed", "validated"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["no_risky_capabilities_without_sandbox"] is True

    @pytest.mark.asyncio
    async def test_check_safety_risky_without_safety_markers(self):
        """Test _check_safety when risky capabilities lack safety markers."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["file_write"]
        mock_agent.safety_tags = []  # No safety markers

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["no_risky_capabilities_without_sandbox"] is False

    @pytest.mark.asyncio
    async def test_check_safety_output_validation(self):
        """Test _check_safety checks for output validation."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["file_write"]
        mock_agent.safety_tags = ["validated"]
        mock_agent.output_validation = True

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["output_validation_present"] is True

    @pytest.mark.asyncio
    async def test_check_safety_rate_limits(self):
        """Test _check_safety checks for rate limits."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["external_api"]
        mock_agent.rate_limit = 100
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["rate_limits_configured"] is True

    @pytest.mark.asyncio
    async def test_check_safety_rate_limits_max_requests(self):
        """Test _check_safety checks for rate limits using max_requests_per_minute."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["external_api"]
        mock_agent.max_requests_per_minute = 100
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        assert result["rate_limits_configured"] is True

    @pytest.mark.asyncio
    async def test_check_safety_rate_limits_no_external_api(self):
        """Test _check_safety rate limits not required for non-external-api agents."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["text_generation"]  # No external_api
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_safety(candidate, context)

        # Rate limits not required for non-external-api agents
        assert result["rate_limits_configured"] is True

    @pytest.mark.asyncio
    async def test_check_capabilities_search_question(self):
        """Test _check_capabilities with search question."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["web_search", "information_retrieval"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}
        question = "Search for latest news"

        result = await engine._check_capabilities(candidate, question, context)

        assert result["capabilities_cover_question_type"] is True

    @pytest.mark.asyncio
    async def test_check_capabilities_analysis_question(self):
        """Test _check_capabilities with analysis question."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["analysis", "reasoning"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}
        question = "Analyze this data"

        result = await engine._check_capabilities(candidate, question, context)

        assert result["capabilities_cover_question_type"] is True

    @pytest.mark.asyncio
    async def test_check_capabilities_memory_question(self):
        """Test _check_capabilities with memory question."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["memory_retrieval"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}
        question = "Remember the previous conversation"

        result = await engine._check_capabilities(candidate, question, context)

        assert result["capabilities_cover_question_type"] is True

    @pytest.mark.asyncio
    async def test_check_capabilities_image_modality(self):
        """Test _check_capabilities with image modality."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["vision", "image_processing"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}
        question = "What is in this image?"

        result = await engine._check_capabilities(candidate, question, context)

        assert result["modality_match"] is True

    @pytest.mark.asyncio
    async def test_check_capabilities_domain_overlap(self):
        """Test _check_capabilities checks domain overlap."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.capabilities = ["text_generation"]

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"search_agent": mock_agent}

        candidate = {"node_id": "search_agent", "path": ["search_agent"]}
        context = {"orchestrator": mock_orchestrator}
        question = "search for information"

        result = await engine._check_capabilities(candidate, question, context)

        assert isinstance(result["domain_overlap_sufficient"], bool)

    @pytest.mark.asyncio
    async def test_check_efficiency_optimal_path_length(self):
        """Test _check_efficiency with optimal path length."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2"],  # Length 2, within (2, 3)
            "estimated_cost": 0.05,
            "estimated_latency": 5000,
        }
        context = {}

        result = await engine._check_efficiency(candidate, context)

        assert result["path_length_optimal"] is True
        assert result["cost_within_budget"] is True
        assert result["latency_acceptable"] is True

    @pytest.mark.asyncio
    async def test_check_efficiency_path_too_long(self):
        """Test _check_efficiency with path too long."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2", "agent3", "agent4"],  # Length 4, exceeds max
            "estimated_cost": 0.05,
            "estimated_latency": 5000,
        }
        context = {}

        result = await engine._check_efficiency(candidate, context)

        assert result["path_length_optimal"] is False

    @pytest.mark.asyncio
    async def test_check_efficiency_cost_too_high(self):
        """Test _check_efficiency with cost too high."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2"],
            "estimated_cost": 0.15,  # Exceeds max_acceptable_cost of 0.10
            "estimated_latency": 5000,
        }
        context = {}

        result = await engine._check_efficiency(candidate, context)

        assert result["cost_within_budget"] is False

    @pytest.mark.asyncio
    async def test_check_efficiency_latency_too_high(self):
        """Test _check_efficiency with latency too high."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1", "agent2"],
            "estimated_cost": 0.05,
            "estimated_latency": 15000,  # Exceeds max_acceptable_latency of 10000
        }
        context = {}

        result = await engine._check_efficiency(candidate, context)

        assert result["latency_acceptable"] is False

    @pytest.mark.asyncio
    async def test_check_history_success_rate_above_threshold(self):
        """Test _check_history with success rate above threshold."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_memory_manager = Mock()
        mock_memory_manager.get_metric = Mock(side_effect=lambda key: 0.85 if "success_rate" in key else 0)

        mock_orchestrator = Mock()
        mock_orchestrator.memory_manager = mock_memory_manager

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_history(candidate, context)

        assert result["success_rate_above_threshold"] is True

    @pytest.mark.asyncio
    async def test_check_history_success_rate_below_threshold(self):
        """Test _check_history with success rate below threshold."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_memory_manager = Mock()
        mock_memory_manager.get_metric = Mock(side_effect=lambda key: 0.50 if "success_rate" in key else 0)

        mock_orchestrator = Mock()
        mock_orchestrator.memory_manager = mock_memory_manager

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_history(candidate, context)

        assert result["success_rate_above_threshold"] is False

    @pytest.mark.asyncio
    async def test_check_history_no_recent_failures(self):
        """Test _check_history with no recent failures."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_memory_manager = Mock()
        mock_memory_manager.get_metric = Mock(side_effect=lambda key: 0 if "failures" in key else None)

        mock_orchestrator = Mock()
        mock_orchestrator.memory_manager = mock_memory_manager

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_history(candidate, context)

        assert result["no_recent_failures"] is True

    @pytest.mark.asyncio
    async def test_check_history_recent_failures(self):
        """Test _check_history with recent failures."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_memory_manager = Mock()
        mock_memory_manager.get_metric = Mock(side_effect=lambda key: 3 if "failures" in key else None)

        mock_orchestrator = Mock()
        mock_orchestrator.memory_manager = mock_memory_manager

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {"orchestrator": mock_orchestrator}

        result = await engine._check_history(candidate, context)

        assert result["no_recent_failures"] is False

    @pytest.mark.asyncio
    async def test_check_history_no_memory_manager(self):
        """Test _check_history when memory manager is missing."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1"]}
        context = {}  # No orchestrator

        result = await engine._check_history(candidate, context)

        assert result["success_rate_above_threshold"] is True
        assert result["no_recent_failures"] is True

    def test_calculate_overall_pass_all_pass(self):
        """Test _calculate_overall_pass when all criteria pass."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {
                "all_required_inputs_available": True,
                "no_circular_dependencies": True,
                "input_types_compatible": True,
            },
            "safety": {
                "no_risky_capabilities_without_sandbox": True,
                "output_validation_present": True,
                "rate_limits_configured": True,
            },
            "capability_match": {
                "capabilities_cover_question_type": True,
                "modality_match": True,
                "domain_overlap_sufficient": True,
            },
            "efficiency": {
                "path_length_optimal": True,
                "cost_within_budget": True,
                "latency_acceptable": True,
            },
            "historical_performance": {
                "success_rate_above_threshold": True,
                "no_recent_failures": True,
            },
        }

        overall_pass, critical_failures = engine._calculate_overall_pass(criteria_results)

        assert overall_pass is True
        assert len(critical_failures) == 0

    def test_calculate_overall_pass_critical_failure(self):
        """Test _calculate_overall_pass with critical failure."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {
                "all_required_inputs_available": False,  # Critical failure
                "no_circular_dependencies": True,
                "input_types_compatible": True,
            },
            "safety": {
                "no_risky_capabilities_without_sandbox": True,
                "output_validation_present": True,
                "rate_limits_configured": True,
            },
            "capability_match": {
                "capabilities_cover_question_type": True,
                "modality_match": True,
                "domain_overlap_sufficient": True,
            },
            "efficiency": {
                "path_length_optimal": True,
                "cost_within_budget": True,
                "latency_acceptable": True,
            },
            "historical_performance": {
                "success_rate_above_threshold": True,
                "no_recent_failures": True,
            },
        }

        overall_pass, critical_failures = engine._calculate_overall_pass(criteria_results)

        assert overall_pass is False
        assert len(critical_failures) > 0
        assert any("input_readiness" in f for f in critical_failures)

    def test_calculate_overall_pass_capability_threshold_failure(self):
        """Test _calculate_overall_pass with capability threshold failure."""
        config = self.create_mock_config(important_threshold=0.8)
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {
                "all_required_inputs_available": True,
                "no_circular_dependencies": True,
                "input_types_compatible": True,
            },
            "safety": {
                "no_risky_capabilities_without_sandbox": True,
                "output_validation_present": True,
                "rate_limits_configured": True,
            },
            "capability_match": {
                "capabilities_cover_question_type": False,  # 1/3 = 0.33 < 0.8
                "modality_match": False,
                "domain_overlap_sufficient": True,
            },
            "efficiency": {
                "path_length_optimal": True,
                "cost_within_budget": True,
                "latency_acceptable": True,
            },
            "historical_performance": {
                "success_rate_above_threshold": True,
                "no_recent_failures": True,
            },
        }

        overall_pass, critical_failures = engine._calculate_overall_pass(criteria_results)

        assert overall_pass is False
        assert any("capability_match" in f for f in critical_failures)

    def test_calculate_overall_pass_strict_mode_efficiency(self):
        """Test _calculate_overall_pass in strict mode with efficiency failure."""
        config = self.create_mock_config(strict_mode=True, include_nice_to_have=True)
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {
                "all_required_inputs_available": True,
                "no_circular_dependencies": True,
                "input_types_compatible": True,
            },
            "safety": {
                "no_risky_capabilities_without_sandbox": True,
                "output_validation_present": True,
                "rate_limits_configured": True,
            },
            "capability_match": {
                "capabilities_cover_question_type": True,
                "modality_match": True,
                "domain_overlap_sufficient": True,
            },
            "efficiency": {
                "path_length_optimal": False,  # Efficiency failure in strict mode
                "cost_within_budget": True,
                "latency_acceptable": True,
            },
            "historical_performance": {
                "success_rate_above_threshold": True,
                "no_recent_failures": True,
            },
        }

        overall_pass, critical_failures = engine._calculate_overall_pass(criteria_results)

        assert overall_pass is False
        assert any("efficiency" in f for f in critical_failures)

    def test_generate_audit_trail(self):
        """Test _generate_audit_trail generation."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {
                "all_required_inputs_available": True,
                "no_circular_dependencies": False,
            },
            "safety": {"no_risky_capabilities_without_sandbox": True},
        }
        critical_failures = ["input_readiness.no_circular_dependencies"]

        audit_trail = engine._generate_audit_trail(criteria_results, critical_failures)

        assert "Boolean Criteria Evaluation:" in audit_trail
        assert "INPUT_READINESS:" in audit_trail
        assert "SAFETY:" in audit_trail
        assert "CRITICAL FAILURES:" in audit_trail
        assert "input_readiness.no_circular_dependencies" in audit_trail

    def test_generate_reasoning_pass(self):
        """Test _generate_reasoning for passing path."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {"all_required_inputs_available": True},
            "safety": {"no_risky_capabilities_without_sandbox": True},
            "capability_match": {"capabilities_cover_question_type": True},
        }
        overall_pass = True
        critical_failures = []

        reasoning = engine._generate_reasoning(criteria_results, overall_pass, critical_failures)

        assert "All critical and important criteria passed" in reasoning

    def test_generate_reasoning_failure_input_readiness(self):
        """Test _generate_reasoning for input readiness failure."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "input_readiness": {"all_required_inputs_available": False},
        }
        overall_pass = False
        critical_failures = ["input_readiness.all_required_inputs_available"]

        reasoning = engine._generate_reasoning(criteria_results, overall_pass, critical_failures)

        assert "Path rejected" in reasoning
        assert "Required inputs are not available" in reasoning

    def test_generate_reasoning_failure_safety(self):
        """Test _generate_reasoning for safety failure."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        criteria_results = {
            "safety": {"no_risky_capabilities_without_sandbox": False},
        }
        overall_pass = False
        critical_failures = ["safety.no_risky_capabilities_without_sandbox"]

        reasoning = engine._generate_reasoning(criteria_results, overall_pass, critical_failures)

        assert "Safety requirements not met" in reasoning

    def test_create_error_result(self):
        """Test _create_error_result."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {"node_id": "agent1", "path": ["agent1", "agent2"]}
        error = "Test error message"

        result = engine._create_error_result(candidate, error)

        assert result.path == ["agent1", "agent2"]
        assert result.overall_pass is False
        assert result.passed_criteria == 0
        assert result.total_criteria == 0
        assert len(result.critical_failures) == 1
        assert "evaluation_error" in result.critical_failures[0]
        assert error in result.audit_trail

    @pytest.mark.asyncio
    async def test_evaluate_candidate_success(self):
        """Test evaluate_candidate with successful evaluation."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = []
        mock_agent.capabilities = ["text_generation"]
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}
        mock_orchestrator.memory_manager = Mock()
        mock_orchestrator.memory_manager.get_metric = Mock(return_value=None)

        candidate = {
            "node_id": "agent1",
            "path": ["agent1"],
            "estimated_cost": 0.05,
            "estimated_latency": 5000,
        }
        question = "Test question"
        context = {"orchestrator": mock_orchestrator, "previous_outputs": {}}

        result = await engine.evaluate_candidate(candidate, question, context)

        assert isinstance(result, BooleanCriteriaResult)
        assert result.path == ["agent1"]
        assert result.total_criteria > 0
        assert isinstance(result.overall_pass, bool)
        assert len(result.criteria_results) == 5  # All 5 categories

    @pytest.mark.asyncio
    async def test_evaluate_candidate_exception(self):
        """Test evaluate_candidate handles exceptions."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        candidate = {"node_id": "agent1"}
        question = "Test question"
        context = {}  # Missing orchestrator will cause issues

        # Mock the check methods to raise an exception
        with patch.object(engine, "_check_input_readiness", side_effect=Exception("Test error")):
            result = await engine.evaluate_candidate(candidate, question, context)

            assert isinstance(result, BooleanCriteriaResult)
            assert result.overall_pass is False
            assert len(result.critical_failures) > 0
            assert "evaluation_error" in result.critical_failures[0]

    @pytest.mark.asyncio
    async def test_evaluate_candidate_path_from_node_id(self):
        """Test evaluate_candidate uses node_id when path is missing."""
        config = self.create_mock_config()
        engine = BooleanScoringEngine(config)

        mock_agent = Mock()
        mock_agent.required_inputs = []
        mock_agent.capabilities = ["text_generation"]
        mock_agent.safety_tags = []

        mock_orchestrator = Mock()
        mock_orchestrator.agents = {"agent1": mock_agent}
        mock_orchestrator.memory_manager = Mock()
        mock_orchestrator.memory_manager.get_metric = Mock(return_value=None)

        candidate = {
            "node_id": "agent1",  # No path field
            "estimated_cost": 0.05,
            "estimated_latency": 5000,
        }
        question = "Test question"
        context = {"orchestrator": mock_orchestrator, "previous_outputs": {}}

        result = await engine.evaluate_candidate(candidate, question, context)

        assert result.path == ["agent1"]  # Should use node_id

