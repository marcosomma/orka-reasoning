# OrKa-Reasoning – Un-official CHANGELOG  
*(derived from the public-repo commit history as of **May 10 2025**)*  

---

## [0.5.7] · 2025-05-18
### Changed
* Consolidated test suite into domain-specific files for better organization and maintenance.
* Updated CI workflow to run domain-based tests for improved clarity and efficiency.
* Added deprecation markers to legacy test files while preserving test coverage.

---

## [0.5.6] · 2025-05-17
### Fixed
* LLM agent test suite now uses unified mocking ensuring reliability across local runs and GitHub Actions.
* CI workflow updated to set `PYTEST_RUNNING` early and avoid skipping coverage.
* Documentation and import paths adjusted for `LegacyBaseAgent`.

---

## [0.5.5] · 2025-05-10
### Changed
* Bumped version to **0.5.5** in *pyproject.toml* / *setup.py*.  
* Polished README (new badges, wording) and expanded docs.  
* Refactored CI scripts & Codecov wiring; test-badge now green. :contentReference[oaicite:0]{index=0}  

---

## [0.5.2] · 2025-05-10
### Added
* Initial **Codecov** integration & coverage upload workflow.  
* Extra unit-tests ⇒ higher overall coverage.  
### Changed
* Project metadata set to **0.5.2**. :contentReference[oaicite:1]{index=1}  

---

## [0.5.0] · 2025-05-10  
*(tag implied by version bump in later commits)*  
### Added
* **Service-node / Memory subsystem**  
  * `MemoryReaderNode`, `MemoryWriterNode`, `memory_logger.py`  
  * JSON-sanitising logger + Redis backing.  
  * Embedding utility (`utils/embedder.py`) for future RAG hooks.  
* >2 kLoC of tests covering the new nodes and logger.  
### Changed
* Orchestrator patched to wire per-node embeddings & scoped memory. :contentReference[oaicite:2]{index=2}  

---

## [0.3.7] · 2025-05-03
### Added
* Docker artefacts (`orka/docker/*`, root `docker-compose.yml`).  
* `orka_start.py` — one-shot CLI launcher for Redis + backend.  
### Changed
* README completely reorganised; clearer "PIP Installation" and YAML sample. :contentReference[oaicite:3]{index=3}  

---

## [0.3.64] · 2025-05-03
### Added
* Repo-wide branding refresh (new logo URL, website link).  
* Additional Codecov / Test badges.  
### Changed
* README tweaks, Dockerfile re-location, misc path fixes. :contentReference[oaicite:4]{index=4}  

---

## [0.3.6] · 2025-05-03
### Added
* **CLI `orka-start`** docs & helper text.  
* Bulk test suite (`test_orka_*`, fake-Redis) + coverage scripts.  
### Changed
* README: quick-start for full stack via Docker Compose. :contentReference[oaicite:5]{index=5}  

---

## [0.3.5] · 2025-05-02
### Added
* First **fork/join** logic polish – big diff in `join_node.py`.  
* Example YAML (`example.yml`) with agent definitions.  
### Changed
* `ORKA` LLM agent temperature default raised to 1.0. :contentReference[oaicite:6]{index=6}  

---

> **Note:** versions earlier than 0.3.5 are not tagged in the public repo; private `orca-core` work (0.4.x) is outside this history.

