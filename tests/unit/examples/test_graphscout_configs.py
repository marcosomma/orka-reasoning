import sys
from pathlib import Path

import pytest

from scripts.check_graphscout_configs import scan_examples


def test_graphscout_examples_have_provider_and_model_url():
    problems = scan_examples()
    if problems:
        msgs = []
        for path, entries in problems.items():
            for agent_id, missing in entries:
                msgs.append(f"{path} - {agent_id} missing {missing}")
        pytest.fail("GraphScout config issues found:\n" + "\n".join(msgs))
