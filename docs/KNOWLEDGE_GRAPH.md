# OrKa Knowledge Graph Design (Proposal)

Goal
- Persist reasoning outputs as structured skills with TTL, enabling agents to reuse validated knowledge across workflows.

Overview
- Introduce a graph-backed memory alongside RedisStack vector memory.
- Model key entities (Skill, Concept, Agent, Workflow, Observation) and relationships (DERIVES_FROM, VALIDATED_BY, PRODUCED_BY, DEPENDS_ON).
- Support TTL on nodes/edges via expiry metadata and scheduled cleanup, aligned with existing decay mechanisms.

Why a Graph
- Expresses multi-hop relations and provenance better than flat vectors.
- Enables queries like: “skills validated by X within 7 days related to concept Y produced by agent Z”.
- Complements retrieval: use vector search to shortlist, then traverse graph for trustworthy, causally-linked knowledge.

MVP Schema
- Node: Skill { id, name, description, embedding_ref, confidence, created_at, expires_at, source_trace_id }
- Node: Concept { id, name, ontology, created_at }
- Node: Agent { id, type, version }
- Node: Workflow { id, name, run_id }
- Node: Observation { id, text, evidence_type, created_at, expires_at }
- Edge: PRODUCED_BY (Skill -> Agent|Workflow)
- Edge: VALIDATED_BY (Skill -> Observation)
- Edge: DERIVES_FROM (Skill -> Skill|Observation)
- Edge: RELATES_TO (Skill -> Concept)

Backends
- Option A (no external deps): Redis Hash/Set based property graph
  - Node key: orka:kg:node:{id} (HASH)
  - Edge key: orka:kg:edge:{id} (HASH) + adjacency sets per node
  - TTL: store expires_at; background sweeper deletes expired nodes/edges; mirror MemoryDecayMixin
- Option B: Neo4j/Memgraph (optional, behind a flag)
  - Use bolt driver; map TTL via expires_at + scheduled purge; no hard TTL in engine
  - Prefer optional installation for users who need deep graph analytics

API Surface (new package orka.kg)
- KGClient interface:
  - upsert_skill(skill: dict, relations: list[tuple]) -> str
  - get_skills(query: dict, limit: int, with_paths: bool=False) -> list[dict]
  - relate(src_id: str, rel: str, dst_id: str, props: dict|None=None) -> None
  - expire_entities(before_ts: int, dry_run: bool=False) -> dict
- Orchestrator integration:
  - Add `type: kg-writer` agent to persist selected outputs as skills with TTL
  - Add `type: kg-reader` agent to query graph (entity/rel expansions, path constraints)
  - YAML example:

```yaml
agents:
  - id: derive_skill
    type: loop
    prompt: "{{ input }}"
    params: { ... }

  - id: persist_skill
    type: kg-writer
    params:
      ttl_hours: 72
      concept_map: ["topic", "domain"]

  - id: reuse_skills
    type: kg-reader
    params:
      where:
        concept: "{{ input_domain }}"
        min_confidence: 0.7
      with_paths: true
```

Interplay with Vector Memory
- On skill write: optionally store `content_vector` in RedisStack and keep `embedding_ref` on Skill node.
- On query: compute query vector once; perform vector shortlist (N best); fetch linked Skill nodes via `embedding_ref`; expand relations.
- This hybrid keeps vector ops blazing fast while KG captures structure and provenance.

TTL & Decay
- Reuse existing decay scheduler patterns:
  - expires_at on nodes/edges
  - periodic `expire_entities()` sweep
  - optional promotion: if VALIDATED_BY edges accumulate, extend TTL (“sticky” skills)

Observability
- Counters: nodes_by_type, edges_by_type, expired_pruned, promotions
- Tracing: graph mutations tagged with `trace_id` and `agent_id`

Security/Isolation
- Namespaces via key prefixes and labels: tenant, project, environment
- Deterministic IDs derived from content hashes to avoid duplicates when desired

Migration Plan
1. Land `orka/kg` with `KGClient` interface and Redis backend (no external deps)
2. Add `kg-writer` and `kg-reader` agents + examples/tests
3. Wire TTL sweeper to scheduler alongside memory decay
4. Optionally add Neo4j backend behind `ORKA_ENABLE_NEO4J` flag later

Open Questions
- Ontology alignment: optional `docs/ONTOLOGY.md` subset as validation?
- Versioning: immutability vs in-place updates; propose immutable nodes with supersedes edge
- Permissions: per-namespace write/read controls for multi-tenant deployments

Testing
- Unit tests: fakeredis for Redis backend; deterministic ID generation
- Integration: end-to-end workflow writes a skill, validates it, queries via concept filter, asserts TTL behavior

Next Steps
- If you want, I can scaffold `orka/kg` with the Redis backend and a tiny `kg-writer` agent to start iterating.
