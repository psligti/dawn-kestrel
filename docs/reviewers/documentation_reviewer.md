---
agent: documentation
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 5311939bd8bd585c808707f7
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
    pattern: "**/*.py"
    weight: 0.7
  - type: file_path
    pattern: "README*"
    weight: 0.7
  - type: file_path
    pattern: "docs/**"
    weight: 0.7
  - type: file_path
    pattern: "*.md"
    weight: 0.7
  - type: file_path
    pattern: "pyproject.toml"
    weight: 0.7
heuristics:
  - "docstrings for public functions/classes"
  - "module-level docs explaining purpose and contracts"
  - "README / usage updates when behavior changes"
  - "configuration documentation (env vars, settings, CLI flags)"
  - "examples and edge case documentation"
  - "docs build/check (mkdocs/sphinx) if repo has it"
  - "docstring linting if configured"
  - "ensure examples match CLI/help output if changed"
  - "Would a new engineer understand how to use the changed parts?"
  - "Are contracts described (inputs/outputs/errors)?"
  - "Are sharp edges warned?"
  - "Is terminology consistent?"
---

# Documentation Reviewer Entry Points

This document defines entry points for the documentation reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The documentation reviewer specializes in:

- - docstrings for public functions/classes

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)
- `README*` (weight: 0.7)
- `docs/**` (weight: 0.7)
- `*.md` (weight: 0.7)
- `pyproject.toml` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `BREAKING|breaking`
- `.{120,}`

## Usage During Review

1. When a PR is received, documentation reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- docstrings for public functions/classes
- module-level docs explaining purpose and contracts
- README / usage updates when behavior changes
- configuration documentation (env vars, settings, CLI flags)
- examples and edge case documentation
- docs build/check (mkdocs/sphinx) if repo has it
- docstring linting if configured
- ensure examples match CLI/help output if changed
- Would a new engineer understand how to use the changed parts?
- Are contracts described (inputs/outputs/errors)?
- Are sharp edges warned?
- Is terminology consistent?

## Maintenance

This document should be regenerated when documentation reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent documentation
```
