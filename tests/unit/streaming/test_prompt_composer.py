from orka.streaming.state import Invariants, StreamingState
from orka.streaming.prompt_composer import PromptComposer
from orka.streaming.types import PromptBudgets


def test_composer_enforces_budgets_and_invariants_present():
    inv = Invariants(identity="A", voice="", refusal="r", tool_permissions=(), safety_policies=())
    st = StreamingState(invariants=inv)
    st.apply_patch({"summary": "one two three four five"}, {"timestamp_ms": 1})
    st.apply_patch({"intent": "alpha beta gamma"}, {"timestamp_ms": 2})

    # Total budget must exceed invariant tokens to allow enforcement check
    budgets = PromptBudgets(total_tokens=20, sections={"summary": 4, "intent": 4})
    comp = PromptComposer(budgets=budgets)
    result = comp.compose(st)

    sections = result["sections"]
    assert "invariants" in sections
    # per-section cap applied
    assert len(sections["summary"].split()) <= 4
    # total cap applied (invariants excluded from trim) -> mutable total <= total_tokens - inv_tokens
    mutable_tokens = result["section_tokens"]["summary"] + result["section_tokens"]["intent"]
    assert mutable_tokens + result["section_tokens"]["invariants"] <= budgets.total_tokens
