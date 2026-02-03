---
agent: linting
agent_type: required
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 6240696c2bead427fbee100a
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
    pattern: "*.json"
    weight: 0.7
  - type: file_path
    pattern: "*.toml"
    weight: 0.7
  - type: file_path
    pattern: "*.yaml"
    weight: 0.7
  - type: file_path
    pattern: "*.yml"
    weight: 0.7
heuristics:
  - "formatting and lint adherence"
  - "import hygiene, unused vars, dead code"
  - "type hints sanity (quality, not architecture)"
  - "consistency with repo conventions"
  - "correctness smells (shadowing, mutable defaults)"
  - "ruff check <changed_files>"
  - "ruff format <changed_files>"
  - "formatter/linter commands used by the repo"
  - "type check if enforced (only when relevant)"
---

# Linting Reviewer Entry Points

This document defines entry points for the linting reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The linting reviewer specializes in:

- - formatting and lint adherence

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)
- `*.json` (weight: 0.7)
- `*.toml` (weight: 0.7)
- `*.yaml` (weight: 0.7)
- `*.yml` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, linting reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- formatting and lint adherence
- import hygiene, unused vars, dead code
- type hints sanity (quality, not architecture)
- consistency with repo conventions
- correctness smells (shadowing, mutable defaults)
- ruff check <changed_files>
- ruff format <changed_files>
- formatter/linter commands used by the repo
- type check if enforced (only when relevant)

## Maintenance

This document should be regenerated when linting reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent linting
```
