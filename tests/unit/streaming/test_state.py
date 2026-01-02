from orka.streaming.state import Invariants, StreamingState


def test_invariants_optional_and_immutable():
    inv = Invariants(identity="bot", voice="", refusal="strict", tool_permissions=(), safety_policies=())
    st = StreamingState(invariants=inv)

    # Can patch mutable
    v1 = st.apply_patch({"summary": "hello"}, {"timestamp_ms": 1})
    assert v1 == 1
    assert st.mutable.summary == "hello"

    # Cannot patch invariants
    try:
        st.apply_patch({"voice": "new"}, {"timestamp_ms": 2})
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_last_write_wins_by_timestamp():
    inv = Invariants()
    st = StreamingState(invariants=inv)
    st.apply_patch({"intent": "a"}, {"timestamp_ms": 2})
    st.apply_patch({"intent": "b"}, {"timestamp_ms": 1})  # older; ignored
    assert st.mutable.intent == "a"
