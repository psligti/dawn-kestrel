---
agent: architecture
agent_type: required
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 9d078ea4ffccfe657f4c1939
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
heuristics:
  - "boundaries, layering, dependency direction"
  - "cohesion/coupling, modularity, naming consistency"
  - "data flow correctness (interfaces, contracts, invariants)"
  - "concurrency/async correctness (if applicable)"
  - "config/env separation (settings vs code)"
  - "backwards compatibility and migration concerns"
  - "anti-pattern detection: god objects, leaky abstractions, duplicated logic"
  - "What is the intended design change?"
  - "Does the change preserve clear boundaries and a single source of truth?"
  - "Does it introduce hidden coupling or duplicated logic?"
  - "Are there new edge cases, failure modes, or lifecycle issues?"
  - "Consider skipping a check, explain why it's safe"
---

# Architecture Reviewer Entry Points

This document defines entry points for the architecture reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The architecture reviewer specializes in:

- - boundaries, layering, dependency direction

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `BREAKING|breaking`
- `.{120,}`

## Usage During Review

1. When a PR is received, architecture reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- boundaries, layering, dependency direction
- cohesion/coupling, modularity, naming consistency
- data flow correctness (interfaces, contracts, invariants)
- concurrency/async correctness (if applicable)
- config/env separation (settings vs code)
- backwards compatibility and migration concerns
- anti-pattern detection: god objects, leaky abstractions, duplicated logic
- What is the intended design change?
- Does the change preserve clear boundaries and a single source of truth?
- Does it introduce hidden coupling or duplicated logic?
- Are there new edge cases, failure modes, or lifecycle issues?
- Consider skipping a check, explain why it's safe

## Maintenance

This document should be regenerated when architecture reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent architecture
```
