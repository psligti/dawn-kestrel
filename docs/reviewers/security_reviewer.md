---
agent: security
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123def456
patterns:
  - type: ast
    pattern: "FunctionDef with decorator '@require_auth'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "FunctionDef with decorator '@login_required'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "Call with function name 'eval'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function name 'exec'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function 'pickle.loads'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "Call with function 'subprocess.run' and keyword argument 'shell=True'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function 'subprocess.Popen' and keyword argument 'shell=True'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function 'subprocess.call' and keyword argument 'shell=True'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function 'os.system'"
    language: python
    weight: 0.95
  - type: ast
    pattern: "Call with function 'yaml.load' without Loader argument"
    language: python
    weight: 0.9
  - type: file_path
    pattern: "**/auth*/**"
    weight: 0.8
  - type: file_path
    pattern: "**/security*/**"
    weight: 0.8
  - type: file_path
    pattern: "**/iam/**"
    weight: 0.8
  - type: file_path
    pattern: "**/permissions/**"
    weight: 0.8
  - type: file_path
    pattern: "**/middleware/**"
    weight: 0.8
  - type: file_path
    pattern: "**/requirements*.txt"
    weight: 0.7
  - type: file_path
    pattern: "**/pyproject.toml"
    weight: 0.7
  - type: file_path
    pattern: "**/poetry.lock"
    weight: 0.7
  - type: file_path
    pattern: "**/uv.lock"
    weight: 0.7
  - type: file_path
    pattern: "**/.github/workflows/**"
    weight: 0.75
  - type: file_path
    pattern: "**/.gitlab-ci.yml"
    weight: 0.75
  - type: file_path
    pattern: "**/Dockerfile*"
    weight: 0.7
  - type: file_path
    pattern: "**/*.tf"
    weight: 0.7
  - type: content
    pattern: "password\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "api_key\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "secret\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "token\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "AWS_[A-Z_]+\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "PRIVATE_KEY\\s*=\\s*['\"][^'\"]+['\"]"
    language: python
    weight: 0.95
  - type: content
    pattern: "f\"\\{.*\\}\".*\\+.*execute\\(|execute\\(.*f\"\\{.*\\}\""
    language: python
    weight: 0.9
  - type: content
    pattern: "\\+.*\".*%s.*\"|\".*%s.*\".*\\+"
    language: python
    weight: 0.85
  - type: content
    pattern: "cursor\\.execute\\(.*%\\(|cursor\\.execute\\(.*\\.format\\("
    language: python
    weight: 0.9
  - type: content
    pattern: "import\\s+pickle|from\\s+pickle\\s+import"
    language: python
    weight: 0.8
  - type: content
    pattern: "import\\s+marshal|from\\s+marshal\\s+import"
    language: python
    weight: 0.8
  - type: content
    pattern: "import\\s+shelve|from\\s+shelve\\s+import"
    language: python
    weight: 0.8
heuristics:
  - "Look for functions that handle user input without validation"
  - "Check for insecure imports (pickle, eval, exec, marshal, shelve)"
  - "Verify encryption/hashing usage (avoid MD5, SHA1, weak ciphers)"
  - "Check for hardcoded secrets, API keys, or passwords"
  - "Look for SQL injection vulnerabilities in database queries"
  - "Verify proper error handling that doesn't leak sensitive information"
  - "Check for unsafe deserialization patterns"
  - "Look for command injection risks in subprocess calls"
  - "Verify proper authentication and authorization checks"
  - "Check for SSRF (Server-Side Request Forgery) risks in network calls"
  - "Look for insecure defaults in configuration"
  - "Verify proper secret management (not in code, use env vars)"
  - "Check for path traversal vulnerabilities in file operations"
  - "Look for XSS (Cross-Site Scripting) risks in output encoding"
  - "Verify CI/CD workflows don't expose secrets or have excessive permissions"
---

# Security Reviewer Entry Points

This document defines entry points for the security reviewer agent to use when determining which code to analyze in PR reviews.

## Overview

The security reviewer specializes in detecting:
- Secrets handling (API keys, passwords, tokens)
- Authentication/authorization issues
- Injection risks (SQL, XSS, command)
- CI/CD exposures
- Unsafe code execution patterns

## Pattern Categories

### AST Patterns (High Weight: 0.8-0.95)

AST patterns match against the abstract syntax tree of Python code. These are high-signal patterns that directly match code structures.

**High-weight patterns (0.95):**
- Code execution: `eval()`, `exec()`, `os.system()`
- Subprocess with shell: `subprocess.run(..., shell=True)`
- Hardcoded secrets: `password=`, `api_key=`, `secret=`, `token=`

**Medium-high patterns (0.9):**
- Deserialization: `pickle.loads()`, `yaml.load()` without Loader
- Authentication decorators: `@require_auth`, `@login_required`

### File Path Patterns (Weight: 0.7-0.8)

File path patterns match against changed file paths using glob patterns.

**Security-sensitive directories (0.8):**
- `auth*/**`, `security*/**`, `iam/**`, `permissions/**`, `middleware/**`

**Dependency files (0.7):**
- `requirements*.txt`, `pyproject.toml`, `poetry.lock`, `uv.lock`

**CI/CD files (0.75):**
- `.github/workflows/**`, `.gitlab-ci.yml`

**Infrastructure (0.7):**
- `Dockerfile*`, `*.tf`

### Content Patterns (Weight: 0.8-0.95)

Content patterns use regex to search for specific strings in file contents.

**Secrets detection (0.95):**
- Hardcoded credentials: `password=`, `api_key=`, `secret=`, `token=`
- Cloud credentials: `AWS_*`, `PRIVATE_KEY`

**Injection risks (0.85-0.9):**
- SQL injection: `cursor.execute(...)` with `%` or `.format()`
- Format string vulnerabilities: `f"{...}"` + `execute()`

**Unsafe imports (0.8):**
- `pickle`, `marshal`, `shelve`

## Usage During Review

1. When a PR is received, the security reviewer loads this document
2. For each pattern, the reviewer searches the changed files
3. Matches are collected and weighted by relevance
4. Top matches are included in the LLM context for analysis
5. Verification evidence is attached to `ReviewOutput.extra_data["verification"]`

## Heuristics for LLM

The heuristics list provides guidance to the LLM when analyzing discovered entry points. These are high-level rules that help the reviewer focus on the most important security concerns.

## Maintenance

This document should be regenerated when the security reviewer's system prompt changes to keep the entry points in sync with the agent's focus.

```bash
bun run generate-docs --agent security
```
