---
agent: security
agent_type: required
version: 1.0.0
generated_at: 2026-02-03T17:55:41Z
prompt_hash: 119fe0f8529a4fd4478d10be
patterns:
  - type: content
    pattern: "password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]"
    language: python
    weight: 0.95
  - type: content
    pattern: "PRIVATE_KEY"
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
    pattern: "**/*.yml"
    weight: 0.7
  - type: file_path
    pattern: "**/*.yaml"
    weight: 0.7
  - type: file_path
    pattern: "**/auth*/**"
    weight: 0.7
  - type: file_path
    pattern: "**/security*/**"
    weight: 0.7
heuristics:
  - "plaintext secrets committed or leaked into logs"
  - "authz bypass risk or missing permission checks"
  - "code execution risk (eval/exec) without strong sandboxing"
  - "command injection risk via subprocess with untrusted input"
  - "unsafe deserialization of untrusted input"
  - "secrets handling (keys/tokens/passwords), logging of sensitive data"
  - "authn/authz, permission checks, RBAC"
  - "injection risks: SQL injection, command injection, template injection"
  - "SSRF, unsafe network calls, insecure defaults"
  - "dependency/supply chain risk signals (new deps, loosened pins)"
  - "cryptography misuse"
  - "file/path handling, deserialization, eval/exec usage"
  - "CI/CD exposures (tokens, permissions, workflow changes)"
  - "auth/**, security/**, iam/**, permissions/**, middleware/**"
  - "network clients, webhook handlers, request parsers"
---

# Security Reviewer Entry Points

This document defines entry points for the security reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The security reviewer specializes in:

- - secrets handling (keys/tokens/passwords), logging of sensitive data

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

- `**/*.py` (weight: 0.7)
- `**/*.yml` (weight: 0.7)
- `**/*.yaml` (weight: 0.7)
- `**/auth*/**` (weight: 0.7)
- `**/security*/**` (weight: 0.7)

### Content Patterns (Weight: 0.7-0.95)

Content patterns use regex to search for specific strings in file contents.

**High-weight patterns (0.9+):**
- `password\\s*[=:]|secret\\s*[=:]|token\\s*[=:]|api_key\\s*[=:]`
- `PRIVATE_KEY`

**Medium patterns (0.7-0.9):**
- `.{120,}`

## Usage During Review

1. When a PR is received, security reviewer loads this document
2. For each pattern, reviewer searches changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points.

- plaintext secrets committed or leaked into logs
- authz bypass risk or missing permission checks
- code execution risk (eval/exec) without strong sandboxing
- command injection risk via subprocess with untrusted input
- unsafe deserialization of untrusted input
- secrets handling (keys/tokens/passwords), logging of sensitive data
- authn/authz, permission checks, RBAC
- injection risks: SQL injection, command injection, template injection
- SSRF, unsafe network calls, insecure defaults
- dependency/supply chain risk signals (new deps, loosened pins)
- cryptography misuse
- file/path handling, deserialization, eval/exec usage
- CI/CD exposures (tokens, permissions, workflow changes)
- auth/**, security/**, iam/**, permissions/**, middleware/**
- network clients, webhook handlers, request parsers

## Maintenance

This document should be regenerated when security reviewer's system prompt changes to keep entry points in sync with the agent's focus.

```bash
opencode review generate-docs --agent security
```
