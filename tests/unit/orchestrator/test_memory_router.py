import importlib

MemoryRouter = importlib.import_module("orka.orchestrator.execution.memory_router").MemoryRouter


class DummyOrch:
    def __init__(self):
        self.agents = {}
    def _is_response_builder(self, agent_id):
        return False
    def _get_best_response_builder(self):
        return None


class MemoryReaderNode:
    pass


class MemoryWriterNode:
    pass


class RegularNode:
    pass


def test_memory_routing_order():
    orch = DummyOrch()
    orch.agents = {
        "r1": MemoryReaderNode(),
        "p1": RegularNode(),
        "w1": MemoryWriterNode(),
    }
    shortlist = [
        {"path": ["p1", "r1", "w1"]},
    ]
    mr = MemoryRouter(orch)
    seq = mr.apply_memory_routing_logic(shortlist)
    # readers first
    assert seq[0] == "r1"
    # writers last
    assert seq[-1] == "w1"
