---
agent: requirements
agent_type: required
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: e22dd4c98b712baade07ea91
patterns:
  - type: content
    pattern: ".{120,}"
    language: python
    weight: 0.7
  - type: file_path
    pattern: "**/*"
    weight: 0.7
heuristics:
---

# Requirements Reviewer Entry Points

This document defines entry points for the requirements reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, requirements reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Maintenance

This document should be regenerated when requirements reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent requirements
```
