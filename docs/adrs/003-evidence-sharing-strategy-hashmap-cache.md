# ADR 003: Evidence Sharing Strategy With Optional HashMap Cache

- Status: Accepted
- Date: 2026-02-24

## Context

Repeated LLM requests with identical input payloads can happen during multi-agent and iterative workflows. We need a non-recursive, strategy-based evidence sharing mechanism with an in-memory hash map option for request-result reuse.

## Decision

Add a strategy pattern for LLM request-result sharing:

- New module: `dawn_kestrel/llm/evidence_sharing.py`
- New strategy protocol:
  - `EvidenceSharingStrategy`
- Implementations:
  - `NoOpEvidenceSharingStrategy` (default)
  - `HashMapEvidenceSharingStrategy` (LRU-like via `OrderedDict`, bounded by `max_entries`)
- New request fingerprint model:
  - `LLMRequestFingerprint`
- Fingerprint generation helper:
  - `create_request_fingerprint(...)`

Integrations:

- `LLMClient` accepts `evidence_sharing_strategy`.
- `LLMClient.complete()` checks cache before provider call and stores successful response after call.
- `SimpleReviewAgentRunner` accepts strategy and includes helper `enable_hashmap_evidence_sharing(...)`.

## Consequences

### Positive

- Reuses exact prior responses for identical requests.
- Fully optional and backward compatible (`NoOp` default).
- Explicit strategy interface allows alternative cache policies later.

### Negative

- In-memory cache is process-local and non-persistent.
- Cache key quality depends on canonical request serialization.

### Follow-up

- Add TTL support.
- Add cache hit/miss metrics.
- Add opt-in cache scoping (per-session/per-workspace).
