---
agent: performance
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 28843e7c1ed9ccb7cf9260d4
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
  - type: file_path
    pattern: "**/*.rs"
    weight: 0.7
  - type: file_path
    pattern: "**/*.go"
    weight: 0.7
  - type: file_path
    pattern: "**/*.js"
    weight: 0.7
  - type: file_path
    pattern: "**/*.ts"
    weight: 0.7
heuristics:
  - "targeted benchmarks (if repo has them)"
  - "profiling hooks or smoke run command"
  - "unit tests for retry/timeout behavior"
---

# Performance Reviewer Entry Points

This document defines entry points for the performance reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)
- `**/*.rs` (weight: 0.7)
- `**/*.go` (weight: 0.7)
- `**/*.js` (weight: 0.7)
- `**/*.ts` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, performance reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- targeted benchmarks (if repo has them)
- profiling hooks or smoke run command
- unit tests for retry/timeout behavior

## Maintenance

This document should be regenerated when performance reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent performance
```
