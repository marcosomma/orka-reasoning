# Additional tests for loop_helpers to increase coverage

import pytest

from orka.orchestrator.prompt_rendering.loop_helpers import create_loop_helpers


class ObjWithRaw:
    def __init__(self, d):
        self._d = d

    def raw(self):
        return self._d


class TestLoopHelpersAdditional:
    def test_get_past_loops_from_input_previous_outputs(self):
        helpers = create_loop_helpers({
            "input": {
                "previous_outputs": {
                    "past_loops": [{"round": 1}, {"round": 2}],
                }
            }
        })
        pls = helpers["get_past_loops"]()
        assert isinstance(pls, list) and len(pls) == 2

    def test_get_past_loops_from_nested_result(self):
        helpers = create_loop_helpers({
            "previous_outputs": {
                "loop_agent": {
                    "result": {"past_loops": [{"round": 9}]}
                }
            }
        })
        pls = helpers["get_past_loops"]()
        assert len(pls) == 1 and pls[0]["round"] == 9

    def test_get_past_loops_metadata_paths(self):
        # From payload directly
        helpers = create_loop_helpers({"past_loops_metadata": {"x": 1}})
        assert helpers["get_past_loops_metadata"]() == {"x": 1}
        # From input
        helpers = create_loop_helpers({"input": {"past_loops_metadata": {"y": 2}}})
        assert helpers["get_past_loops_metadata"]() == {"y": 2}

    def test_get_score_threshold_paths_and_default(self):
        helpers = create_loop_helpers({"score_threshold": 0.9})
        assert helpers["get_score_threshold"]() == 0.9
        helpers = create_loop_helpers({"input": {"score_threshold": 0.7}})
        assert helpers["get_score_threshold"]() == 0.7
        helpers = create_loop_helpers({})
        assert helpers["get_score_threshold"]() == 0.8

    def test_get_loop_rounds_using_loops_completed(self):
        # Direct in agent_result
        helpers = create_loop_helpers({
            "previous_outputs": {
                "loop": {"loops_completed": 4}
            }
        })
        assert helpers["get_loop_rounds"]() == 4
        # Nested inside result
        helpers = create_loop_helpers({
            "previous_outputs": {
                "loop": {"result": {"loops_completed": 7}}
            }
        })
        assert helpers["get_loop_rounds"]() == 7

    def test_get_final_score_from_nested_and_string(self):
        # Score as string value in agent_result
        helpers = create_loop_helpers({
            "previous_outputs": {
                "loop": {"result_score": "0.66"}
            }
        })
        val = helpers["get_final_score"]()
        assert abs(val - 0.66) < 1e-6

        # Score in nested result dict
        helpers = create_loop_helpers({
            "previous_outputs": {
                "loop": {"result": {"best_score": 0.75}}
            }
        })
        assert helpers["get_final_score"]() == 0.75

        # Unknown if nothing is present
        helpers = create_loop_helpers({"previous_outputs": {}})
        assert helpers["get_final_score"]() == "Unknown"

    def test_get_loop_status_from_result_or_nested(self):
        helpers = create_loop_helpers({
            "previous_outputs": {"loop": {"status": "running"}}
        })
        assert helpers["get_loop_status"]() == "running"

        helpers = create_loop_helpers({
            "previous_outputs": {"loop": {"result": {"status": "halted"}}}
        })
        assert helpers["get_loop_status"]() == "halted"

    def test_get_loop_output_with_raw_and_response_non_dict(self):
        prev = {
            "loop": ObjWithRaw({"response": 123, "value": 5})
        }
        helpers = create_loop_helpers({"previous_outputs": prev})
        out = helpers["get_loop_output"]("loop")
        # response non-dict -> should return entire dict from raw()
        assert out == {"response": 123, "value": 5}

    def test_get_loop_output_direct_dict_without_response(self):
        prev = {"loop": {"a": 1}}
        helpers = create_loop_helpers({"previous_outputs": prev})
        assert helpers["get_loop_output"]("loop") == {"a": 1}

    def test_get_round_info_defaults_to_loop_number(self):
        helpers = create_loop_helpers({"loop_number": 3})
        assert helpers["get_round_info"]() == "3"
