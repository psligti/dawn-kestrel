---
agent: diff_scoper
agent_type: required
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: d4a013dbd09e5ef6d886a562

patterns:
  - type: content
    pattern: "password|secret|token|api_key"
    language: python
    weight: 0.95
  - type: content
    pattern: ".{120,}"
    language: python
    weight: 0.7
  - type: file_path
    pattern: "**/*"
    weight: 0.7
heuristics:
  - Check for large files with more than 200 lines changed
  - Identify complex functions with more than 30 lines
  - Analyze file changes for diff complexity

---

# Diff Scoper Reviewer Entry Points

This document defines entry points for the diff scoper reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password|secret|token|api_key`

**Medium patterns (0.7-0.9):**
- `.{120,}` - Checks for functions with many arguments

## Usage During Review

1. When a PR is received, diff scoper reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Discovered entry points are sorted by weight (highest first)
4. Top entry points are used to build focused review context
5. Heuristics provide additional guidance for manual review
