---\nagent: security\nagent_type: required\nversion: 1.0.0\ngenerated_at: 2026-02-03T18:01:03Z\nprompt_hash: 119fe0f8529a4fd4478d10be\npatterns:\n  - type: content\n    pattern: "password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]"\n    language: python\n    weight: 0.95\n  - type: content\n    pattern: "AWS_[A-Z_]+|PRIVATE_KEY"\n    language: python\n    weight: 0.95\n  - type: content\n    pattern: ".{120,}"\n    language: python\n    weight: 0.7\n  - type: ast\n    pattern: "FunctionDef with decorator"\n    language: python\n    weight: 0.7\n  - type: file_path\n    pattern: "**/*.py"\n    weight: 0.7\n  - type: file_path\n    pattern: "**/*.yml"\n    weight: 0.7\n  - type: file_path\n    pattern: "**/*.yaml"\n    weight: 0.7\n  - type: file_path\n    pattern: "**/auth*/**"\n    weight: 0.7\n  - type: file_path\n    pattern: "**/security*/**"\n    weight: 0.7\nheuristics:\n  - "plaintext secrets committed or leaked into logs"\n  - "authz bypass risk or missing permission checks"\n  - "code execution risk (eval/exec) without strong sandboxing"\n  - "command injection risk via subprocess with untrusted input"\n  - "unsafe deserialization of untrusted input"\n  - "secrets handling (keys/tokens/passwords), logging of sensitive data"\n  - "authn/authz, permission checks, RBAC"\n  - "injection risks: SQL injection, command injection, template injection"\n  - "SSRF, unsafe network calls, insecure defaults"\n  - "dependency/supply chain risk signals (new deps, loosened pins)"\n  - "cryptography misuse"\n  - "file/path handling, deserialization, eval/exec usage"\n  - "CI/CD exposures (tokens, permissions, workflow changes)"\n  - "auth/**, security/**, iam/**, permissions/**, middleware/**"\n  - "network clients, webhook handlers, request parsers"\n---\n\n# Security Reviewer Entry Points\n\nThis document defines entry points for security reviewer agent to use when determining which code to analyze in PR reviews.\n\n## Overview\n\nThe security reviewer specializes in:\n\n- - secrets handling (keys/tokens/passwords), logging of sensitive data\n\n### AST Patterns (High Weight: 0.7-0.95)\n\nAST patterns match against abstract syntax tree of Python code.\n\n**Medium patterns (0.7-0.8):**\n- FunctionDef with decorator\n\n### File Path Patterns (Weight: 0.7-0.8)\n\nFile path patterns match against changed file paths using glob patterns.\n\n- `**/*.py` (weight: 0.7)\n- `**/*.yml` (weight: 0.7)\n- `**/*.yaml` (weight: 0.7)\n- `**/auth*/**` (weight: 0.7)\n- `**/security*/**` (weight: 0.7)\n\n### Content Patterns (Weight: 0.7-0.95)\n\nContent patterns use regex to search for specific strings in file contents.\n\n**High-weight patterns (0.9+):**\n- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`\n- `AWS_[A-Z_]+|PRIVATE_KEY`\n\n**Medium patterns (0.7-0.9):**\n- `.{120,}`\n\n## Usage During Review\n\n1. When a PR is received, security reviewer loads this document\n2. For each pattern, reviewer searches changed files\n3. Matches are collected and weighted by relevance\n4. Top matches are included in the LLM context for analysis\n5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`\n\n## Heuristics for LLM\n\nThe heuristics list provides guidance to the LLM when analyzing discovered entry points.\n\n- plaintext secrets committed or leaked into logs\n- authz bypass risk or missing permission checks\n- code execution risk (eval/exec) without strong sandboxing\n- command injection risk via subprocess with untrusted input\n- unsafe deserialization of untrusted input\n- secrets handling (keys/tokens/passwords), logging of sensitive data\n- authn/authz, permission checks, RBAC\n- injection risks: SQL injection, command injection, template injection\n- SSRF, unsafe network calls, insecure defaults\n- dependency/supply chain risk signals (new deps, loosened pins)\n- cryptography misuse\n- file/path handling, deserialization, eval/exec usage\n- CI/CD exposures (tokens, permissions, workflow changes)\n- auth/**, security/**, iam/**, permissions/**, middleware/**\n- network clients, webhook handlers, request parsers\n\n## Maintenance\n\nThis document should be regenerated when security reviewer's system prompt changes to keep entry points in sync with the agent's focus.\n\n```bash\nopencode review generate-docs --agent security\n```\n
## Real Analysis Mode (Historical Transition)

### Previous Mock Behavior (DEPRECATED)

The security reviewer previously used `_simulate_subagent_execution()` which returned static mock findings.

**Problems with Mock Mode:**
- Findings were not tied to actual code changes in the PR
- No evidence from real diff content
- Same findings reported regardless of what changed
- No way to validate against `changed_files` scope

### Current Real Analysis

Subagents now analyze actual diff content:

```python
# Subagent receives diff context, not just file names
prompt = f"""
CONTEXT:
  - Changed files: {', '.join(context.changed_files[:10])}
  - Total diff size: {len(context.diff)} characters
  - Diff hunks: {truncated_diff_hunks}
"""
```

**Real Scanner Capabilities:**
- Secret scanning: Examines only added/modified lines from diff
- Injection checks: Focuses on changed input handling in diff
- Unsafe function detection: Scans diff for `eval()`, `exec()`, `system()`
- Crypto analysis: Detects weak hash functions, hardcoded keys in diff

**Diff-aware behavior:**
- Maximum: 5000 characters per subagent prompt segment
- Deterministic ordering: Files sorted alphabetically, hunks ordered by file position
- Truncation: Large diffs truncated with explicit log

## Deduplication Strategy

### Finding Uniqueness

Findings are deduplicated using two mechanisms:

1. **ID-based deduplication:**
   - Each finding has a unique `id` field
   - Already-processed IDs are tracked: `processed_finding_ids: Set[str]`
   - Duplicate IDs are skipped during result processing

2. **Content signature deduplication:**
   - Semantic duplicates from different scanners are merged
   - Signature: `{file_path}:{line_number}:{severity}`
   - Findings with same signature are merged, keeping highest confidence

### Idempotent Task Processing

- Completed tasks are never redelegated: Tasks marked `COMPLETED` are skipped in subsequent iterations
- Todo completion is idempotent: Todo status is set to `COMPLETED` exactly once
- Loop stability: "Todos completed" count matches actual completed/total count

## Validation Gates

### 1. Changed-Files Scope

Rule: Findings must reference files that were actually changed in the PR.

```python
# Validation logic
if finding.file_path not in context.changed_files:
    logger.warning(f"Finding {finding.id} references unchanged file {finding.file_path}")
    continue  # Filter out this finding
```

### 2. Evidence Quality

Rule: Findings must include non-empty evidence from actual diff content.

```python
# Validation logic
if not finding.evidence or finding.evidence.strip() == "":
    logger.warning(f"Finding {finding.id} has empty evidence - rejecting")
    continue  # Filter out this finding
```

Evidence Requirements:
- Must be a code snippet from the diff
- Should include surrounding context (±2 lines)
- Line numbers must match actual locations in changed files

### 3. Uniqueness Validation

Rule: Each finding appears only once in the final report.

## Changed-Files-Only Finding Example

Scenario: PR changes `config.py` adding a hardcoded AWS access key.

Finding:
```json
{
  "id": "SEC-001",
  "title": "Hardcoded AWS access key",
  "severity": "blocking",
  "confidence": "high",
  "owner": "security",
  "estimate": "S",
  "evidence": "Line 42 in config.py: AWS_ACCESS_KEY_ID='AKIAIOSFODNN7EXAMPLE'",
  "risk": "AWS access key committed to source code can be used to impersonate AWS account",
  "recommendation": "Remove the hardcoded key and load from environment variable or secret manager"
}
```

## References

- [Security Agent Improvement Plan](../security-agent-improvement-plan.md)
- [ADR: Security Review Defaults](../adr/security-review-diff-context-validation-dedup.md)
- [Review Contracts](../../dawn_kestrel/agents/review/contracts.py)

