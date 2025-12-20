import json
from datetime import datetime
import importlib.util
import pathlib

# Load utils module directly to avoid package-level heavy imports during pytest
utils_path = pathlib.Path(__file__).resolve().parents[3] / "orka" / "orchestrator" / "execution" / "utils.py"
spec = importlib.util.spec_from_file_location("execution_utils", str(utils_path))
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

json_serializer = utils.json_serializer
sanitize_for_json = utils.sanitize_for_json


def test_json_serializer_datetime():
    dt = datetime(2025, 1, 1, 12, 0, 0)
    assert json_serializer(dt) == dt.isoformat()


def test_sanitize_for_json_nested():
    nested = {"a": datetime(2025, 1, 1), "b": [datetime(2025, 2, 2), {"c": datetime(2025, 3, 3)}]}
    sanitized = sanitize_for_json(nested)
    # Should be JSON serializable
    s = json.dumps(sanitized)
    assert "2025-01-01" in s
    assert "2025-02-02" in s
    assert "2025-03-03" in s
