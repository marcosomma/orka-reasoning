import importlib.util
import pathlib
import asyncio

# Load agent_runner module directly
ar_path = pathlib.Path(__file__).resolve().parents[3] / "orka" / "orchestrator" / "execution" / "agent_runner.py"
spec = importlib.util.spec_from_file_location("agent_runner", str(ar_path))
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
AgentRunner = ar.AgentRunner


class DummyOrch:
    def __init__(self):
        self.agents = {}
        self.workflow_name = "wf"

    def render_template(self, prompt, payload):
        return f"rendered:{prompt}"


class SyncAgent:
    def run(self, payload):
        return {"ok": True, "payload": payload}


class AsyncAgent:
    async def run(self, payload):
        await asyncio.sleep(0)
        return {"ok": "async", "payload": payload}


class NeedsOrchAgent:
    def run(self, context):
        # Expects orchestrator inside the context dict
        orch = context.get("orchestrator")
        return {"orch": orch.workflow_name if orch is not None else None}


async def _run_all():
    orch = DummyOrch()
    orch.agents["sync"] = SyncAgent()
    orch.agents["async"] = AsyncAgent()
    orch.agents["needs"] = NeedsOrchAgent()

    runner = AgentRunner(orch)

    aid, res = await runner.run_agent_async("sync", {"x": 1}, {})
    assert aid == "sync"
    assert res["ok"] is True

    aid2, res2 = await runner.run_agent_async("async", {"x": 2}, {})
    assert aid2 == "async"
    assert res2["ok"] == "async"

    # Provide orchestrator via full_payload to simulate orchestrator-enabled nodes
    aid3, res3 = await runner.run_agent_async("needs", {}, {}, full_payload={"orchestrator": orch})
    assert aid3 == "needs"
    assert res3["orch"] == "wf"


def test_agent_runner_event_loop():
    # Use asyncio.run which creates and manages its own event loop to avoid
    # interacting with test-suite event loop lifecycle.
    asyncio.run(_run_all())
