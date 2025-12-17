# Production Readiness & Claims Mapping

This document maps high-level claims found in the repository to the concrete tests, docs, and deployment hardening required to support those claims. It is intended to be a single source of truth for validating marketing-style statements and tracking gaps.

How to use
- Add rows for claims you want to assert about the project (feature, module, file).
- Link to tests (unit/integration/e2e), CI jobs, and runbooks that verify the claim.
- Set status: Verified / Needs test / Needs config / Needs runbook.

Columns
- Claim: Short claim text (e.g., "JSON parser is production-ready")
- File: Where the claim appears
- Evidence: Tests, benchmarks, or docs that support the claim (paths)
- Required hardening: What is missing (e.g., HA Redis, TLS, secrets management)
- Status: Verified / Needs test / Needs config / Needs runbook

Starter mappings (fill & expand)

| Claim | File | Evidence | Required hardening | Status |
|-------|------|----------|--------------------|--------|
| JSON parsing robust | docs/JSON_PARSER_GUIDE.md | tests/unit/utils/test_json_parser.py | Integration tests with real LLM outputs, performance bounds | Needs test |
| HTTP server example | orka/server.py and docs/INTEGRATION_EXAMPLES.md | tests/integration/test_server.py | TLS, load balancing, secrets management, readiness probes | Needs config |
| Distributed execution support | orka/orchestrator/execution_engine.py | tests/integration/test_execution_* | Distributed execution tests, deployment examples, chaos tests | Needs test |
| RedisStack guidance | docs/README_BACKENDS.md | docs/INTEGRATION_EXAMPLES.md | HA RedisStack configuration, backup & restore guidance | Needs config |
| OrKa TUI monitoring | orka/tui_interface.py and docs/orka-ui.md | tests/integration/test_tui* | Validate performance and refresh intervals; document dependencies (Textual) | Needs test |
| Embedding fallback behavior | orka/utils/embedder.py | tests/unit/utils/test_embedder.py | Document fallback guarantees and performance bounds | Verified |


Notes
- This is a living document: every time a strong claim is added to docs or module docstrings, add an entry here and link to the test that verifies it.
- Make sure PRs that add claims also add evidence or an issue tracking the missing evidence.

Maintainers: assign an owner from architecture/QA to keep this file up to date.
