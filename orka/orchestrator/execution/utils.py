# OrKa: Orchestrator Kit Agents
# by Marco Somma
#
# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning
#
# Licensed under the Apache License, Version 2.0 (Apache 2.0).
#
# Full license: https://www.apache.org/licenses/LICENSE-2.0
#
# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning

from datetime import datetime
import re
from typing import Any


def json_serializer(obj: Any):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO strings in nested structures."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


def _check_unresolved_variables(text: str) -> bool:
    """Check if text contains unresolved Jinja2 variables."""
    pattern = r"\{\{\s*[^}]+\s*\}\}"
    return bool(re.search(pattern, text))


def _extract_template_variables(template: str):
    """Extract all Jinja2 variables from template."""
    pattern = r"\{\{\s*([^}]+)\s*\}\}"
    return re.findall(pattern, template)
