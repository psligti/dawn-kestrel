---
agent: dependencies
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 01ce9883af010498c8f40968
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
    pattern: "pyproject.toml"
    weight: 0.7
  - type: file_path
    pattern: "requirements*.txt"
    weight: 0.7
  - type: file_path
    pattern: "requirements.txt"
    weight: 0.7
  - type: file_path
    pattern: "setup.py"
    weight: 0.7
  - type: file_path
    pattern: "Pipfile"
    weight: 0.7
heuristics:
  - "pip-audit / poetry audit / uv audit"
  - "license checker if repo uses it"
  - "lockfile diff sanity checks"
---

# Dependencies Reviewer Entry Points

This document defines entry points for the dependencies reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `pyproject.toml` (weight: 0.7)
- `requirements*.txt` (weight: 0.7)
- `requirements.txt` (weight: 0.7)
- `setup.py` (weight: 0.7)
- `Pipfile` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, dependencies reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- pip-audit / poetry audit / uv audit
- license checker if repo uses it
- lockfile diff sanity checks

## Maintenance

This document should be regenerated when dependencies reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent dependencies
```
