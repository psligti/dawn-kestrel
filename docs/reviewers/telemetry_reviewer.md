---
agent: telemetry
agent_type: optional
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: c495fb27cc4a72c8b1306c17
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
    pattern: "**/logging/**"
    weight: 0.7
  - type: file_path
    pattern: "**/observability/**"
    weight: 0.7
  - type: file_path
    pattern: "**/metrics/**"
    weight: 0.7
  - type: file_path
    pattern: "**/tracing/**"
    weight: 0.7
heuristics:
  - "logging quality (structured logs, levels, correlation IDs)"
  - "tracing spans / propagation (if applicable)"
  - "metrics: counters/gauges/histograms, cardinality control"
  - "error reporting: meaningful errors, no sensitive data"
  - "observability coverage of new workflows and failure modes"
  - "performance signals: timing, retries, rate limits, backoff"
  - "log format checks (if repo has them)"
  - "smoke run command to ensure logs/metrics emitted (if available)"
  - "grep for logger usage & secrets leakage"
---

# Telemetry Reviewer Entry Points

This document defines entry points for the telemetry reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The telemetry reviewer specializes in:

- - logging quality (structured logs, levels, correlation IDs)

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)
- `**/logging/**` (weight: 0.7)
- `**/observability/**` (weight: 0.7)
- `**/metrics/**` (weight: 0.7)
- `**/tracing/**` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, telemetry reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- logging quality (structured logs, levels, correlation IDs)
- tracing spans / propagation (if applicable)
- metrics: counters/gauges/histograms, cardinality control
- error reporting: meaningful errors, no sensitive data
- observability coverage of new workflows and failure modes
- performance signals: timing, retries, rate limits, backoff
- log format checks (if repo has them)
- smoke run command to ensure logs/metrics emitted (if available)
- grep for logger usage & secrets leakage

## Maintenance

This document should be regenerated when telemetry reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent telemetry
```
