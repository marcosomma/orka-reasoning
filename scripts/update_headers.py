import os
from pathlib import Path

HEADER = (
    "# OrKa: Orchestrator Kit Agents\n"
    "# by Marco Somma\n"
    "#\n"
    "# This file is part of OrKa – https://github.com/marcosomma/orka-reasoning\n"
    "#\n"
    "# Licensed under the Apache License, Version 2.0 (Apache 2.0).\n"
    "#\n"
    "# Full license: https://www.apache.org/licenses/LICENSE-2.0\n"
    "#\n"
    "# Attribution would be appreciated: OrKa by Marco Somma – https://github.com/marcosomma/orka-reasoning\n"
)

ORKA_DIR = Path(__file__).resolve().parents[1] / "orka"


def normalize_line_endings(text: str) -> str:
    """Normalize to LF to compare consistently; preserve original on write."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def ensure_header_for_file(path: Path) -> bool:
    """Ensure the header is present at the top of a single Python file.

    Returns True if the file was modified, False otherwise.
    """
    original = path.read_text(encoding="utf-8")
    normalized = normalize_line_endings(original)

    # Extract and preserve shebang if present
    shebang = ""
    rest = normalized
    if rest.startswith("#!"):
        nl = rest.find("\n")
        if nl != -1:
            shebang = rest[: nl + 1]
            rest = rest[nl + 1 :]
        else:
            # File contains only shebang; append header after it
            rest = ""

    # Already compliant (after optional shebang)
    if rest.startswith(HEADER):
        return False

    lines = rest.split("\n")

    # Determine current header block (initial comments and blank lines)
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("#") or line.strip() == "":
            idx += 1
            continue
        break

    # Replace existing comment header (if any) with the canonical header
    new_content = shebang + HEADER + "\n" + "\n".join(lines[idx:]).lstrip("\n")

    # Preserve original line endings (CRLF if present)
    uses_crlf = "\r\n" in original
    out = new_content.replace("\n", "\r\n") if uses_crlf else new_content
    path.write_text(out, encoding="utf-8")
    return True


def main() -> None:
    if not ORKA_DIR.exists():
        raise SystemExit(f"OrKa directory not found: {ORKA_DIR}")

    changed = 0
    scanned = 0
    for py_path in ORKA_DIR.rglob("*.py"):
        # Skip generated/egg-info or tests outside 'orka' if any
        if any(part.endswith(".egg-info") for part in py_path.parts):
            continue
        scanned += 1
        try:
            if ensure_header_for_file(py_path):
                changed += 1
        except Exception as e:
            print(f"[WARN] Failed to update {py_path}: {e}")

    print(f"Scanned {scanned} files. Updated {changed} files.")


if __name__ == "__main__":
    main()
