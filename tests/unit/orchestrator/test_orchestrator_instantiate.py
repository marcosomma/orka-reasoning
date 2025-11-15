import importlib.util
import pathlib


def test_orchestrator_init_executes_with_monkeypatched_mixins(monkeypatch):
    """Execute the top-level `orka/orchestrator.py` and instantiate Orchestrator while
    monkeypatching mixin __init__ methods to no-ops so the body of Orchestrator.__init__ runs
    without side effects.
    """
    # Patch mixin __init__ methods to be safe no-ops that provide minimal attributes
    def fake_exec_init(self, config_path):
        # minimal state
        setattr(self, "_exec_inited", True)

    def fake_base_init(self, config_path):
        setattr(self, "orchestrator_cfg", {})
        setattr(self, "agent_cfgs", {})
        setattr(self, "memory", None)

    def fake_agent_factory_init(self, orchestrator_cfg, agent_cfgs, memory):
        setattr(self, "_agent_factory_inited", True)

    def fake_noop(self):
        return None

    monkeypatch.setattr(
        "orka.orchestrator.execution_engine.ExecutionEngine.__init__",
        fake_exec_init,
        raising=False,
    )
    monkeypatch.setattr(
        "orka.orchestrator.base.OrchestratorBase.__init__",
        fake_base_init,
        raising=False,
    )
    monkeypatch.setattr(
        "orka.orchestrator.agent_factory.AgentFactory.__init__",
        fake_agent_factory_init,
        raising=False,
    )
    monkeypatch.setattr(
        "orka.orchestrator.error_handling.ErrorHandler.__init__",
        fake_noop,
        raising=False,
    )
    monkeypatch.setattr(
        "orka.orchestrator.metrics.MetricsCollector.__init__",
        fake_noop,
        raising=False,
    )

    # Load the specific top-level file by path so we execute that file's Orchestrator class
    base = pathlib.Path(__file__).resolve().parents[3]
    file_path = base / "orka" / "orchestrator.py"
    assert file_path.exists(), f"expected top-level orchestrator file at {file_path}"

    spec = importlib.util.spec_from_file_location("_orka_top_level_orchestrator", str(file_path))
    module = importlib.util.module_from_spec(spec)

    # Execute the module after mixin patches
    spec.loader.exec_module(module)  # type: ignore[attr-defined]

    # prevent heavy agent initialization inside the module's Orchestrator
    if hasattr(module.Orchestrator, "_init_agents"):
        monkeypatch.setattr(module.Orchestrator, "_init_agents", lambda self: {})

    # Instantiate - this runs the __init__ body and therefore covers those lines
    inst = module.Orchestrator("dummy.yml")
    assert hasattr(inst, "agents")
    # Our monkeypatched base __init__ sets orchestrator_cfg to a dict
    assert isinstance(inst.orchestrator_cfg, dict)
