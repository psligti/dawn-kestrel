# ADR 001: Entry Point Architecture for PR Review Agents

## Status
Accepted

## Context
The current PR review system relies on `is_relevant_to_changes()` which uses glob patterns to determine if a reviewer should analyze a PR. This approach is fast but has limitations:
- Glob patterns are imprecise - they match files without understanding code semantics
- False positives: Reviewers run on irrelevant code (wasting time/money)
- False negatives: Relevant code changes are missed (security risks)

We need an entry point discovery mechanism that provides semantic understanding while maintaining performance.

## Decision

### 1. Entry Point vs is_relevant_to_changes() Relationship

**Entry points ENHANCE the existing relevance check - they do not replace it.**

The workflow is:
1. **First check**: Run `is_relevant_to_changes()` with glob patterns (fast, <100ms)
2. **If relevant**: Run entry point discovery to identify specific locations
3. **Use results**: Feed discovered entry points into LLM context

**Rationale:**
- Glob patterns are a fast pre-filter to avoid unnecessary work
- Entry points provide semantic precision once we know the reviewer is relevant
- This hybrid approach balances speed (glob) with accuracy (entry points)

**Failure mode handling:**
- **Empty discovery**: If entry points return no results, fall back to `is_relevant_to_changes()` and proceed with full context
- **Timeout/error**: Log warning, fall back to `is_relevant_to_changes()` with full context
- **Partial discovery**: Use whatever entry points were discovered (better than nothing)

### 2. Performance Budgets

To ensure entry points don't slow down the overall PR review pipeline:

| Metric | Budget | Enforcement |
|--------|--------|-------------|
| Discovery timeout | 30s per reviewer | Hard timeout in discovery code |
| Total review time increase | <20% | Monitored in CI; fail if exceeded |
| Entry point count | <50 per PR | Limit context size |

**Rationale:**
- 30s timeout: Fast enough to not block pipeline, slow enough for thorough analysis
- <20% increase: Acceptable overhead for the precision gain
- <50 entry points: Prevents context overflow to LLM

### 3. Doc-Gen Invocation Strategy

**Phase 1: Manual Invocation (Current)**
- Developers run `bun run generate-docs --agent <name>` to create initial entry point docs
- Useful for bootstrapping and testing the system
- No automation in this phase

**Phase 2: Warn on Stale Docs (Future)**
- Track `prompt_hash` in YAML frontmatter
- Compare with current agent system prompt hash
- Log warning if mismatch detected (e.g., "Entry points may be stale - regenerate with `bun run generate-docs --agent security_reviewer`")
- Optional: Integrate into pre-commit hooks to enforce freshness

**Rationale:**
- Phase 1 allows manual control and testing before automation
- Phase 2 provides guardrails without blocking workflows
- Warning-based approach balances safety with developer experience

### 4. ReviewOutput Contract Decision

**Use `output.extra_data["verification"]` for entry point verification evidence.**

The ReviewOutput contract already has `extra="ignore"` in its `model_config`, allowing arbitrary extra fields:

```python
class ReviewOutput(pd.BaseModel):
    # ... existing fields ...
    model_config = pd.ConfigDict(extra="ignore")
```

**Implementation:**
```python
output = ReviewOutput(
    # ... standard fields ...
)

# Add verification evidence
output.extra_data = {
    "verification": {
        "entry_points_discovered": 12,
        "entry_points_matched": [
            "src/auth.py:45 (AST pattern: FunctionDef with @require_auth)",
            "config.yml:10 (content pattern: 'password')"
        ],
        "discovery_time_seconds": 3.2
    }
}
```

**Rationale:**
- No contract changes required (backwards compatible)
- Extra data is ignored by existing validation
- Provides transparency into entry point discovery
- Enables debugging and monitoring

### 5. Entry Point YAML Frontmatter Schema

All reviewer entry point documents in `docs/reviewers/` must use this schema:

```yaml
---
agent: security_reviewer        # Agent identifier (must match agent.get_agent_name())
agent_type: required            # "required" or "optional"
version: 1.0.0                  # Semantic versioning for this entry point doc
generated_at: 2024-01-15T10:30:00Z  # ISO 8601 timestamp
prompt_hash: abc123def456       # Hash of agent's system prompt (for staleness detection)
patterns:                       # List of patterns to discover entry points
  - type: ast                   # "ast", "file_path", or "content"
    pattern: "FunctionDef with decorator @require_auth"
    language: python            # Required for ast/content types
    weight: 0.8                 # Relevance weight (0.0-1.0)
  - type: file_path
    pattern: "**/auth/**/*.py"
    weight: 0.7
  - type: content
    pattern: "password|token|secret"
    language: python
    weight: 0.6
heuristics:                     # List of heuristic rules for LLM
  - "Look for functions that handle user input"
  - "Check for insecure imports (pickle, eval, exec)"
  - "Verify encryption/hashing usage"
---
# Markdown documentation continues below
```

**Pattern types:**
- `ast`: AST pattern matching (via ast-grep or similar)
- `file_path`: Glob pattern matching file paths
- `content`: Regex pattern matching file content

**Weights:**
- Used to sort/rank entry points by relevance
- Higher weight → more relevant to reviewer's focus
- Helps prioritize context when limiting to top N entry points

### 6. Discovery Algorithm

**Implementation flow:**
1. Load entry point doc from `docs/reviewers/<agent_name>.md`
2. Parse YAML frontmatter
3. For each pattern:
   - `ast`: Run ast-grep on changed files
   - `file_path`: Match against changed file paths
   - `content`: Regex search in changed file contents
4. Collect all matches with weights
5. Sort by weight (descending), then by file path
6. Return top N (default: 50, configurable)
7. Attach to ReviewOutput.extra_data["verification"]

**Fallback behavior:**
- If entry point doc doesn't exist: Log warning, use is_relevant_to_changes()
- If discovery times out (>30s): Use partial results + is_relevant_to_changes()
- If no matches found: Use is_relevant_to_changes()

## Alternatives Considered

### Alternative 1: Replace is_relevant_to_changes() entirely
**Rejected:** Too risky. Entry points could fail, leaving reviewers with no way to run. The hybrid approach is safer.

### Alternative 2: LLM-based entry point discovery
**Rejected:** Too slow and expensive. Deterministic patterns (ast-grep, glob, regex) are faster and more predictable.

### Alternative 3: Automatic doc regeneration
**Rejected:** Too aggressive. Manual invocation gives developers control. Warnings (Phase 2) provide balance.

## Consequences

**Positive:**
- More precise relevance detection (fewer false positives/negatives)
- Faster reviews (less irrelevant code sent to LLM)
- Lower costs (smaller context windows)
- Better security (catching issues glob patterns miss)
- Transparent verification (extra_data shows what was discovered)

**Negative:**
- Additional complexity in the review pipeline
- Need to maintain entry point documentation
- Potential performance overhead (mitigated by 30s timeout)

**Mitigation:**
- Validate entry point docs via `scripts/validate-docs.py`
- Monitor performance metrics in CI
- Provide clear error messages and fallback behavior

## References

- PR review entry points plan: `.sisyphus/plans/pr-review-entry-points.md`
- ReviewOutput contract: `dawn_kestrel/agents/review/contracts.py`
- Base reviewer patterns: `dawn_kestrel/agents/review/base.py`
- Example reviewer: `dawn_kestrel/agents/review/agents/security.py`
