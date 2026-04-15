# TODOS

## Issue #64 — Source Attestation Phases 2-3

### Phase 2: Write provenance metadata
- **What**: Thread `WriteProvenance` (verification state, source identities) through all write handlers
- **Why**: Auditors need to evaluate not just artifact content but the trustworthiness of the session that produced it
- **Blocked by**: Platform API schema change to accept structured provenance field (currently no consumer)
- **Where to start**: Add `WriteProvenance` dataclass to `attestation.py`, extend `upsert_evidence()` and MCP handlers

### Phase 3: Source manifest (correctness checking)
- **What**: Declarative source requirements per system ("this system expects GitHub repo org/repo in AWS account X")
- **Why**: Phase 1 only detects drift. Source manifest validates sources were correct from the start.
- **Blocked by**: Phase 1 shipping + platform metadata design for source bindings
- **Where to start**: Extend `VerifiedSnapshot` with expected-vs-actual comparison, add manifest config format

### Phase 2: System-aware provider selection
- **What**: Skip irrelevant providers based on system hosting metadata (e.g., skip Azure when system is AWS)
- **Why**: Reduces verification latency and avoids noise from irrelevant providers
- **Blocked by**: Platform system metadata API exposing hosting context
- **Where to start**: Query system metadata during `context verify`, filter providers via `resolve_providers()` config
