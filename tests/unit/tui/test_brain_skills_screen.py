"""
Unit tests for the Brain Skills TUI tab.

Covers DataManager.get_brain_skills(), SkillsTableWidget,
BrainSkillsScreen, and the binding wired into OrKaTextualApp.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from orka.brain.skill import Skill, SkillStep, SkillTransferRecord
from orka.tui.data_manager import DataManager
from orka.tui.textual_app import OrKaTextualApp
from orka.tui.textual_screens import BrainSkillsScreen
from orka.tui.textual_widgets import SkillsTableWidget


# ── Fixtures ──────────────────────────────────────────────────────────────

def _make_skill(**overrides) -> Skill:
    """Create a Skill instance with sensible defaults."""
    defaults = dict(
        id="skill-001",
        name="Sequential Analysis",
        description="Break down input and analyse each part.",
        procedure=[
            SkillStep(action="decompose", description="Split input", order=1),
            SkillStep(action="analyse", description="Process parts", order=2),
        ],
        preconditions=[],
        postconditions=[],
        source_context={"domain": "text_analysis"},
        confidence=0.75,
        usage_count=3,
        success_rate=0.85,
        tags=["analysis", "sequential"],
        transfer_history=[],
    )
    defaults.update(overrides)
    return Skill(**defaults)


@pytest.fixture
def data_manager():
    dm = DataManager()
    dm.memory_logger = MagicMock()
    dm.backend = "redisstack"
    return dm


# ── DataManager.get_brain_skills ──────────────────────────────────────────

class TestGetBrainSkills:

    def test_returns_skills_from_graph(self, data_manager):
        skills = [_make_skill(), _make_skill(id="skill-002", name="Divide and Conquer")]
        with patch("orka.tui.data_manager.SkillGraph") as MockGraph:
            MockGraph.return_value.list_skills.return_value = skills
            result = data_manager.get_brain_skills()

        assert len(result) == 2
        assert result[0].name == "Sequential Analysis"
        assert result[1].name == "Divide and Conquer"

    def test_returns_empty_when_no_logger(self):
        dm = DataManager()
        dm.memory_logger = None
        assert dm.get_brain_skills() == []

    def test_caches_on_error(self, data_manager):
        cached = [_make_skill()]
        data_manager.brain_skills = cached

        with patch("orka.tui.data_manager.SkillGraph") as MockGraph:
            MockGraph.return_value.list_skills.side_effect = RuntimeError("Redis gone")
            result = data_manager.get_brain_skills()

        # Should keep the cached value
        assert result == cached

    def test_passes_memory_logger_to_graph(self, data_manager):
        with patch("orka.tui.data_manager.SkillGraph") as MockGraph:
            MockGraph.return_value.list_skills.return_value = []
            data_manager.get_brain_skills()

        MockGraph.assert_called_once_with(memory=data_manager.memory_logger)


# ── SkillsTableWidget ────────────────────────────────────────────────────

class TestSkillsTableWidget:

    def test_class_exists_and_inherits_data_table(self):
        from textual.widgets import DataTable

        assert issubclass(SkillsTableWidget, DataTable)

    def test_has_skill_selected_message(self):
        assert hasattr(SkillsTableWidget, "SkillSelected")

    def test_skill_selected_message_attributes(self):
        msg = SkillsTableWidget.SkillSelected(
            skill_data={"id": "x", "name": "test"}, row_index=0
        )
        assert msg.skill_data == {"id": "x", "name": "test"}
        assert msg.row_index == 0

    def test_skill_selected_message_none_data(self):
        msg = SkillsTableWidget.SkillSelected(skill_data=None, row_index=-1)
        assert msg.skill_data == {}
        assert msg.row_index == -1


# ── BrainSkillsScreen ────────────────────────────────────────────────────

class TestBrainSkillsScreen:

    def test_instantiation(self):
        dm = MagicMock()
        screen = BrainSkillsScreen(dm)
        assert screen.data_manager is dm

    def test_is_base_orka_screen(self):
        from orka.tui.textual_screens import BaseOrKaScreen

        assert issubclass(BrainSkillsScreen, BaseOrKaScreen)

    def test_has_refresh_data_method(self):
        assert callable(getattr(BrainSkillsScreen, "refresh_data", None))

    def test_has_skill_selected_handler(self):
        assert hasattr(BrainSkillsScreen, "on_skills_table_widget_skill_selected")


# ── OrKaTextualApp binding ────────────────────────────────────────────────

class TestAppBrainSkillsBinding:

    def test_binding_exists(self):
        bindings = {b.key for b in OrKaTextualApp.BINDINGS}
        assert "5" in bindings

    def test_binding_action_name(self):
        binding = next(b for b in OrKaTextualApp.BINDINGS if b.key == "5")
        assert binding.action == "show_brain_skills"

    def test_action_method_exists(self):
        assert hasattr(OrKaTextualApp, "action_show_brain_skills")


# ── TTL Display ──────────────────────────────────────────────────────────

class TestSkillTTLDisplay:

    def test_format_skill_ttl_no_expiry(self):
        result = SkillsTableWidget._format_skill_ttl("")
        assert "Never" in result

    def test_format_skill_ttl_future_days(self):
        from datetime import UTC, datetime, timedelta

        future = (datetime.now(UTC) + timedelta(days=3, minutes=1)).isoformat()
        result = SkillsTableWidget._format_skill_ttl(future)
        assert "3d" in result
        assert "green" in result

    def test_format_skill_ttl_future_hours(self):
        from datetime import UTC, datetime, timedelta

        future = (datetime.now(UTC) + timedelta(hours=5, minutes=1)).isoformat()
        result = SkillsTableWidget._format_skill_ttl(future)
        assert "5h" in result
        assert "yellow" in result

    def test_format_skill_ttl_future_minutes(self):
        from datetime import UTC, datetime, timedelta

        future = (datetime.now(UTC) + timedelta(minutes=30, seconds=30)).isoformat()
        result = SkillsTableWidget._format_skill_ttl(future)
        assert "30m" in result
        assert "red" in result

    def test_format_skill_ttl_expired(self):
        from datetime import UTC, datetime, timedelta

        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        result = SkillsTableWidget._format_skill_ttl(past)
        assert "EXPIRED" in result

    def test_format_ttl_detail_no_expiry(self):
        result = BrainSkillsScreen._format_ttl_detail({})
        assert "Never" in result

    def test_format_ttl_detail_with_expiry(self):
        from datetime import UTC, datetime, timedelta

        future = (datetime.now(UTC) + timedelta(days=2, hours=5)).isoformat()
        result = BrainSkillsScreen._format_ttl_detail({"expires_at": future})
        assert "2d" in result
        assert "remaining" in result

    def test_skill_to_dict_has_expires_at(self):
        skill = _make_skill()
        d = skill.to_dict()
        assert "expires_at" in d

    def test_screen_created_in_on_mount(self):
        dm = MagicMock()
        app = OrKaTextualApp(dm)
        # on_mount creates screens dict — verify BrainSkillsScreen would be included
        # by calling on_mount directly (needs mocked install_screen / push_screen)
        with (
            patch.object(app, "install_screen"),
            patch.object(app, "push_screen"),
            patch.object(app, "set_interval"),
        ):
            app.on_mount()
        assert "brain_skills" in app.screens
        assert isinstance(app.screens["brain_skills"], BrainSkillsScreen)


# ── Skill Type Display ──────────────────────────────────────────────────

class TestSkillTypeDisplay:

    def test_format_execution_recipe(self):
        result = SkillsTableWidget._format_skill_type("execution_recipe")
        assert "RECIPE" in result
        assert "green" in result

    def test_format_anti_pattern(self):
        result = SkillsTableWidget._format_skill_type("anti_pattern")
        assert "ANTI" in result
        assert "red" in result

    def test_format_graph_path(self):
        result = SkillsTableWidget._format_skill_type("graph_path")
        assert "PATH" in result
        assert "cyan" in result

    def test_format_procedural(self):
        result = SkillsTableWidget._format_skill_type("procedural")
        assert "PROC" in result
        assert "blue" in result

    def test_format_prompt_template(self):
        result = SkillsTableWidget._format_skill_type("prompt_template")
        assert "PROMPT" in result

    def test_format_parameter_config(self):
        result = SkillsTableWidget._format_skill_type("parameter_config")
        assert "CONFIG" in result

    def test_format_domain_heuristic(self):
        result = SkillsTableWidget._format_skill_type("domain_heuristic")
        assert "DOMAIN" in result

    def test_format_unknown_type(self):
        result = SkillsTableWidget._format_skill_type("custom_thing")
        assert "CUSTOM" in result

    def test_skill_to_dict_has_skill_type(self):
        skill = _make_skill()
        d = skill.to_dict()
        assert "skill_type" in d
        assert d["skill_type"] == "procedural"

    def test_skill_to_dict_has_v2_fields(self):
        skill = _make_skill()
        d = skill.to_dict()
        for field in ["domain_keywords", "search_tokens", "anti_signals", "recipe"]:
            assert field in d, f"Missing v2 field: {field}"
