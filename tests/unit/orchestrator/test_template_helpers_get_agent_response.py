from __future__ import annotations

from orka.orchestrator.template_helpers import get_agent_response


def test_get_agent_response_unwraps_orchestrator_payload_response():
    previous_outputs = {
        "loop_processor": {
            "agent_id": "loop_processor",
            "event_type": "LoopNode",
            "payload": {
                "agent_id": "loop_processor",
                "response": {"final_score": 0.33, "threshold_met": False},
            },
        }
    }

    assert get_agent_response("loop_processor", previous_outputs) == "{'final_score': 0.33, 'threshold_met': False}"


