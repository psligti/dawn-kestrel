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
  - type: content
    pattern: "requirements.txt|pyproject.toml|package.json"
    language: text
    weight: 0.8
  - type: file_path
    pattern: "**/*"
    weight: 0.7
heuristics:
  - Check for missing requirements.txt entries
  - Verify dependency version ranges

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
- `.{120,}` - Checks for functions with many arguments
- `requirements.txt|pyproject.toml|package.json` - Dependency file patterns

## Usage During Review

1. When a PR is received, requirements reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Discovered entry points are sorted by weight (highest first)
4. Top entry points are used to build focused review context
5. Heuristics provide additional guidance for manual review
