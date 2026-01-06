import pytest

from orka.utils.structured_output import (
    StructuredOutputConfig,
    AGENT_DEFAULT_SCHEMAS,
)


class TestStructuredOutputConfig:
    def test_from_params_defaults(self):
        cfg = StructuredOutputConfig.from_params(agent_params={}, agent_type="openai-answer")
        assert cfg.enabled is False
        assert cfg.mode == "auto"
        assert cfg.schema is None
        assert cfg.require_code_block is False
        assert cfg.coerce_types is True
        assert cfg.strict is False

    def test_from_params_enabled_uses_agent_default_schema(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-answer",
        )
        assert cfg.enabled is True
        assert cfg.schema is not None
        assert cfg.schema["required"] == AGENT_DEFAULT_SCHEMAS["openai-answer"]["required"]

    def test_from_params_binary_agent_default_schema(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-binary",
        )
        assert cfg.schema is not None
        assert "result" in cfg.schema["required"]
        assert cfg.schema.get("types", {}).get("result") == "boolean"

    def test_from_params_classification_agent_default_schema(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-classification",
        )
        assert set(cfg.schema["required"]) == {"category", "confidence"}

    def test_from_params_custom_schema_overrides_default(self):
        custom = {"required": ["foo"], "optional": {"bar": "number"}}
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True, "schema": custom}},
            agent_type="openai-answer",
        )
        assert cfg.schema is not None
        assert cfg.schema["required"] == ["foo"]
        assert cfg.schema["optional"]["bar"] == "number"

    def test_from_params_orchestrator_defaults_inherited(self):
        orchestrator_defaults = {
            "enabled": True,
            "mode": "prompt",
            "require_code_block": True,
            "strict": True,
        }
        cfg = StructuredOutputConfig.from_params(
            agent_params={},
            agent_type="openai-answer",
            orchestrator_defaults=orchestrator_defaults,
        )
        assert cfg.enabled is True
        assert cfg.mode == "prompt"
        assert cfg.require_code_block is True
        assert cfg.strict is True
        assert cfg.schema is not None  # default schema gets applied when enabled

    def test_from_params_agent_overrides_orchestrator(self):
        orchestrator_defaults = {"enabled": False, "mode": "prompt"}
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True, "mode": "model_json"}},
            agent_type="openai-answer",
            orchestrator_defaults=orchestrator_defaults,
        )
        assert cfg.enabled is True
        assert cfg.mode == "model_json"

    def test_resolve_mode_auto_openai(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-answer",
        )
        resolved = cfg.resolve_mode(provider="openai", model="gpt-4o")
        # tool_call preferred over model_json
        assert resolved == "tool_call"

    def test_resolve_mode_auto_ollama(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="local_llm",
        )
        resolved = cfg.resolve_mode(provider="ollama", model="llama3")
        assert resolved == "prompt"

    def test_resolve_mode_explicit_passthrough(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True, "mode": "model_json"}},
            agent_type="openai-answer",
        )
        resolved = cfg.resolve_mode(provider="openai", model="gpt-4o")
        assert resolved == "model_json"

    def test_build_json_schema_default(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-answer",
        )
        schema = cfg.build_json_schema()
        assert schema["type"] == "object"
        assert "response" in schema["required"]
        assert schema["properties"]["response"]["type"] == "string"
        # optional fields present
        assert "confidence" in schema["properties"]

    def test_build_json_schema_binary_boolean(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-binary",
        )
        schema = cfg.build_json_schema()
        assert schema["properties"]["result"]["type"] == "boolean"
        assert "result" in schema["required"]

    def test_build_json_schema_strict_mode(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True, "strict": True}},
            agent_type="openai-answer",
        )
        schema = cfg.build_json_schema()
        assert schema["additionalProperties"] is False

    def test_build_prompt_instructions(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="openai-answer",
        )
        text = cfg.build_prompt_instructions()
        assert "```json" in text
        assert '"response"' in text

    def test_path_evaluator_default_schema(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="path-evaluator",
        )
        assert cfg.schema is not None
        assert set(cfg.schema["required"]) == {"relevance_score", "confidence", "reasoning"}
        js = cfg.build_json_schema()
        assert js["properties"]["relevance_score"]["type"] == "number"
        assert js["properties"]["confidence"]["type"] == "number"

    def test_plan_validator_schema_exists(self):
        cfg = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="plan-validator",
        )
        assert cfg.schema is not None
        assert set(cfg.schema["required"]) == {"completeness", "efficiency", "safety", "coherence"}

    def test_graphscout_default_schemas_present(self):
        # path-evaluator
        cfg_eval = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="path-evaluator",
        )
        schema_eval = cfg_eval.build_json_schema()
        for f in ("relevance_score", "confidence", "reasoning"):
            assert f in schema_eval["required"]
            assert f in schema_eval["properties"]

        # path-validator
        cfg_val = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="path-validator",
        )
        schema_val = cfg_val.build_json_schema()
        assert schema_val["properties"]["approved"]["type"] in ("boolean",)
        assert schema_val["properties"]["validation_score"]["type"] in ("number",)

        # plan-validator
        cfg_plan = StructuredOutputConfig.from_params(
            agent_params={"structured_output": {"enabled": True}},
            agent_type="plan-validator",
        )
        schema_plan = cfg_plan.build_json_schema()
        for k in ("completeness", "efficiency", "safety", "coherence"):
            assert k in schema_plan["required"]
