from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def normalize_score(raw: float, pattern: Optional[str] = None, matched_text: Optional[str] = None) -> float:
    """Normalize raw numeric extraction into 0.0-1.0 range.

    This is intentionally equivalent to the legacy LoopNode._normalize_score logic.
    """
    try:
        score = float(raw)
    except Exception:
        return 0.0

    # Detect percent markers
    text = (pattern or "") + (matched_text or "")
    if "%" in text or (pattern and "%" in pattern):
        try:
            score = score / 100.0
            logger.debug("Normalizing percentage score %s -> %s", raw, score)
        except Exception:
            pass

    # Detect /10 style patterns
    elif pattern and ("/10" in pattern or "out of 10" in pattern.lower()):
        try:
            score = score / 10.0
            logger.debug("Normalizing /10 score %s -> %s", raw, score)
        except Exception:
            pass

    # Heuristic: if score > 1 and looks like percentage (<=100)
    if score > 1.0:
        try:
            raw_f = float(raw)
        except Exception:
            raw_f = score

        if raw_f <= 100.0:
            new_score = raw_f / 100.0
            logger.warning("Interpreting score %s as percentage and normalizing to %s", raw, new_score)
            score = new_score
        else:
            logger.warning("Score %s out of expected range, clamping to 1.0", raw)
            score = 1.0

    # Clamp to [0.0, 1.0]
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    # Diagnostic log to aid debugging in live runs
    try:
        raw_f = float(raw)
    except Exception:
        raw_f = score
    if score != raw_f and ("%" in (pattern or "") or "%" in (matched_text or "") or raw_f > 1.0):
        logger.info("Normalized extracted score: raw=%s -> normalized=%s (pattern=%s)", raw, score, pattern)

    return float(score)


def extract_nested_path(result: dict[str, Any], path: str) -> Optional[float]:
    """Extract score from nested path (e.g., 'result.score')."""
    try:
        keys = path.split(".")
        current: Any = result
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        return float(current)
    except Exception:
        return None


def extract_pattern(result: dict[str, Any], patterns: list[str]) -> Optional[float]:
    """Extract score using regex patterns from any string-like field in the result."""
    try:
        # Coerce the whole result to a searchable string (LoopNode does this as a fallback)
        text = str(result)
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.groups():
                    raw = match.group(1)
                else:
                    raw = match.group(0)
                try:
                    return float(raw)
                except Exception:
                    continue
        return None
    except Exception as e:
        logger.debug("Pattern extraction failed: %s", e)
        return None


