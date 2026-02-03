---
agent: release_changelog
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: e020a8901ecbbfc19d0e95af
patterns:
  - type: content
    pattern: "password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]"
    language: python
    weight: 0.95
  - type: content
    pattern: "BREAKING|breaking"
    language: python
    weight: 0.85
  - type: content
    pattern: ".{120,}"
    language: python
    weight: 0.7
  - type: file_path
    pattern: "CHANGELOG*"
    weight: 0.7
  - type: file_path
    pattern: "CHANGES*"
    weight: 0.7
  - type: file_path
    pattern: "HISTORY*"
    weight: 0.7
  - type: file_path
    pattern: "pyproject.toml"
    weight: 0.7
  - type: file_path
    pattern: "setup.py"
    weight: 0.7
heuristics:
  - "CHANGELOG presence/update"
  - "version bump policy checks"
  - "help text / docs updated"
---

# Release Changelog Reviewer Entry Points

This document defines entry points for the release changelog reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `CHANGELOG*` (weight: 0.7)
- `CHANGES*` (weight: 0.7)
- `HISTORY*` (weight: 0.7)
- `pyproject.toml` (weight: 0.7)
- `setup.py` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `BREAKING|breaking`
- `.{120,}`

## Usage During Review

1. When a PR is received, release changelog reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- CHANGELOG presence/update
- version bump policy checks
- help text / docs updated

## Maintenance

This document should be regenerated when release changelog reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent release_changelog
```
