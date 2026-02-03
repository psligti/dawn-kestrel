---
agent: unit_tests
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 97dc1ef44f99c69363f4ac19
patterns:
  - type: content
    pattern: "password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]"
    language: python
    weight: 0.95
  - type: content
    pattern: ".{120,}"
    language: python
    weight: 0.7
  - type: file_path
    pattern: "**/*.py"
    weight: 0.7
heuristics:
  - "adequacy of tests for changed behavior"
  - "correctness of tests (assertions, determinism, fixtures)"
  - "edge case and failure mode coverage"
  - "avoiding brittle tests (time, randomness, network)"
  - "selecting minimal test runs to validate change"
  - "pytest -q <test_file>"
  - "pytest -q -k "<keyword>""
  - "pytest -q tests/unit/..."
  - "coverage on changed modules only (if available)"
---

# Unit Tests Reviewer Entry Points

This document defines entry points for the unit tests reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The unit_tests reviewer specializes in:

- - adequacy of tests for changed behavior

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, unit tests reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- adequacy of tests for changed behavior
- correctness of tests (assertions, determinism, fixtures)
- edge case and failure mode coverage
- avoiding brittle tests (time, randomness, network)
- selecting minimal test runs to validate change
- pytest -q <test_file>
- pytest -q -k "<keyword>"
- pytest -q tests/unit/...
- coverage on changed modules only (if available)

## Maintenance

This document should be regenerated when unit tests reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent unit_tests
```
