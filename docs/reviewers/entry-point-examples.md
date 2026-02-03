# Entry Point Examples for PR Review Agents

This document provides comprehensive entry point examples for all 11 PR review agents. Each agent includes AST patterns, file path patterns, and heuristic rules with appropriate weights.

---

## 1. Architecture Reviewer

**Agent**: `architecture_reviewer`
**Focus**: Boundary violations, coupling issues, anti-patterns, backwards compatibility

### Patterns

```yaml
agent: architecture_reviewer
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123arch456
patterns:
  # AST Patterns
  - type: ast
    pattern: "ClassDef with decorator '@dataclass'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "ClassDef with decorator '@singleton'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "FunctionDef with decorator '@inject'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "ClassDef with name ending in 'Service' and more than 20 methods"
    language: python
    weight: 0.85
  - type: ast
    pattern: "FunctionDef with more than 5 parameters"
    language: python
    weight: 0.7
  - type: ast
    pattern: "Import with module matching '.*\\.models' and '.*\\.views'"
    language: python
    weight: 0.8

  # File Path Patterns
  - type: file_path
    pattern: "**/domain/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/services/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/core/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/lib/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/src/**/*.py"
    weight: 0.75
  - type: file_path
    pattern: "**/app/**/*.py"
    weight: 0.75

  # Content Patterns
  - type: content
    pattern: "from.*models.*import.*|from.*views.*import.*"
    language: python
    weight: 0.75
  - type: content
    pattern: "class.*\\(.*\\):.*pass"
    language: python
    weight: 0.65
  - type: content
    pattern: "def.*\\(.*self.*\\):.*\\.\\w+\\.\\w+\\(\\)"
    language: python
    weight: 0.7

heuristics:
  - "Look for circular dependencies between modules"
  - "Check for god objects with too many responsibilities"
  - "Verify dependency injection patterns are consistent"
  - "Check for tight coupling between layers (data, business, presentation)"
  - "Look for leaky abstractions exposing implementation details"
  - "Verify configuration is separated from business logic"
  - "Check for backwards compatibility breaking changes in public APIs"
  - "Look for duplicated logic across modules"
  - "Verify clear boundaries between components"
  - "Check for proper separation of concerns"
```

### Key Patterns Explained

- **ClassDef with @dataclass**: Detects data model definitions that may need architectural review
- **ClassDef with @singleton**: Singleton patterns can introduce global state - review for appropriateness
- **FunctionDef with @inject**: Dependency injection - review for coupling issues
- **Large classes (>20 methods)**: Potential god object anti-pattern
- **Functions with >5 parameters**: Flag for complexity and potential refactoring needs
- **Cross-layer imports**: Models importing views (or vice versa) indicates layer violation

---

## 2. Security Reviewer

**Agent**: `security_reviewer`
**Focus**: Secrets handling, auth/authz, injection risks, CI/CD exposures

### Patterns

```yaml
agent: security_reviewer
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123sec456
patterns:
  # AST Patterns
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
    pattern: "Call with function 'yaml.load' without Loader argument"
    language: python
    weight: 0.9

  # File Path Patterns
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
    pattern: "**/.github/workflows/**"
    weight: 0.75
  - type: file_path
    pattern: "**/Dockerfile*"
    weight: 0.7

  # Content Patterns
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
    pattern: "cursor\\.execute\\(.*%\\(|cursor\\.execute\\(.*\\.format\\("
    language: python
    weight: 0.9
  - type: content
    pattern: "import\\s+pickle|from\\s+pickle\\s+import"
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
```

### Key Patterns Explained

- **eval()/exec()**: Dangerous code execution - requires strong sandboxing
- **subprocess with shell=True**: Command injection risk
- **pickle.loads()**: Unsafe deserialization
- **Auth decorators**: Authentication changes need review
- **Hardcoded credentials**: Security violation
- **SQL with % or format()**: SQL injection vulnerability

---

## 3. Documentation Reviewer

**Agent**: `documentation_reviewer`
**Focus**: Docstrings, README updates, configuration docs, usage examples

### Patterns

```yaml
agent: documentation_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123doc456
patterns:
  # AST Patterns
  - type: ast
    pattern: "FunctionDef without docstring"
    language: python
    weight: 0.7
  - type: ast
    pattern: "ClassDef without docstring"
    language: python
    weight: 0.7
  - type: ast
    pattern: "FunctionDef with decorator '@app.route' or '@router.get'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "ClassDef with name ending in 'Command' or 'Skill'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "AsyncFunctionDef"
    language: python
    weight: 0.65
  - type: ast
    pattern: "FunctionDef with parameter 'request' or 'response'"
    language: python
    weight: 0.8

  # File Path Patterns
  - type: file_path
    pattern: "README*"
    weight: 0.9
  - type: file_path
    pattern: "**/__init__.py"
    weight: 0.75
  - type: file_path
    pattern: "docs/**"
    weight: 0.85
  - type: file_path
    pattern: "**/*.md"
    weight: 0.7
  - type: file_path
    pattern: ".env.example"
    weight: 0.85
  - type: file_path
    pattern: "**/settings/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/config/**/*.py"
    weight: 0.8

  # Content Patterns
  - type: content
    pattern: "TODO:|FIXME:|XXX:"
    language: python
    weight: 0.6
  - type: content
    pattern: "class\\s+\\w+\\(.*\\):\\s*$"
    language: python
    weight: 0.65
  - type: content
    pattern: "def\\s+\\w+\\(.*\\):\\s*$"
    language: python
    weight: 0.65
  - type: content
    pattern: "version\\s*=\\s*['\"]\\d+\\.\\d+\\.\\d+['\"]"
    language: python
    weight: 0.85

heuristics:
  - "Check for missing docstrings on public functions/classes"
  - "Verify README reflects current behavior and features"
  - "Look for changes that require configuration documentation updates"
  - "Check for new CLI flags/commands that need documentation"
  - "Verify module-level docs explain purpose and contracts"
  - "Look for edge cases that need warnings in documentation"
  - "Check for consistent terminology across docs and code"
  - "Verify examples in docs match actual CLI/output"
  - "Look for changes to error handling that need docs updates"
  - "Check for environment variables that need .env.example updates"
```

### Key Patterns Explained

- **Functions/classes without docstrings**: Missing documentation for public APIs
- **Route decorators**: API endpoints need documentation
- **Command/Skill classes**: User-facing features need docs
- **README changes**: High weight - affects all users
- **__init__.py**: Module-level documentation
- **TODO/FIXME**: May indicate missing documentation

---

## 4. Telemetry Metrics Reviewer

**Agent**: `telemetry_metrics_reviewer`
**Focus**: Logging quality, metrics, tracing, error reporting

### Patterns

```yaml
agent: telemetry_metrics_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123tel456
patterns:
  # AST Patterns
  - type: ast
    pattern: "Call with function name 'logger.info' or 'logger.warning' or 'logger.error'"
    language: python
    weight: 0.7
  - type: ast
    pattern: "Call with function name 'metrics.counter' or 'metrics.gauge' or 'metrics.histogram'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "FunctionDef with decorator '@retry'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "AsyncFunctionDef with more than one 'await'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "Try with more than one ExceptHandler"
    language: python
    weight: 0.8
  - type: ast
    pattern: "FunctionDef with name containing 'fetch' or 'query' or 'request'"
    language: python
    weight: 0.85

  # File Path Patterns
  - type: file_path
    pattern: "**/logging/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/observability/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/metrics/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/tracing/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/monitoring/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/background_jobs/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/pipelines/**/*.py"
    weight: 0.8

  # Content Patterns
  - type: content
    pattern: "logger\\.(info|warning|error|critical)\\(.*f\"\\{.*\\}\""
    language: python
    weight: 0.75
  - type: content
    pattern: "logger\\.(info|warning|error|critical)\\(.*password|secret|token"
    language: python
    weight: 0.95
  - type: content
    pattern: "except\\s+\\w+:\\s*pass"
    language: python
    weight: 0.85
  - type: content
    pattern: "while\\s+True:|for\\s+.*\\s+in\\s+.*:\\s+if\\s+.*:\\s*break"
    language: python
    weight: 0.8

heuristics:
  - "Check for secrets/PII being logged in error messages"
  - "Look for critical paths with no error logging or metrics"
  - "Verify retry loops have limits and logging for visibility"
  - "Check for high-cardinality metric labels"
  - "Look for swallowed exceptions (except: pass)"
  - "Verify correlation IDs are propagated in distributed systems"
  - "Check for structured logging with consistent format"
  - "Look for network calls without timeout or retry logging"
  - "Verify timing metrics for long-running operations"
  - "Check for unbounded loops without logging or metrics"
```

### Key Patterns Explained

- **logger calls**: Logging changes need review for quality
- **metrics calls**: Metrics need review for cardinality and appropriateness
- **@retry decorators**: Retry logic needs visibility (logs/metrics)
- **Async functions**: Async operations need tracing
- **Multiple exception handlers**: Complex error handling needs review
- **Fetch/query/request functions**: Network operations need observability

---

## 5. Linting Reviewer

**Agent**: `linting_reviewer`
**Focus**: Formatting, lint adherence, type hints, code quality smells

### Patterns

```yaml
agent: linting_reviewer
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123lint456
patterns:
  # AST Patterns
  - type: ast
    pattern: "FunctionDef with parameter default '= []' or '= {}'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "FunctionDef with no return annotations and body length > 10"
    language: python
    weight: 0.75
  - type: ast
    pattern: "ClassDef with base 'object'"
    language: python
    weight: 0.6
  - type: ast
    pattern: "Import with alias 'from foo import bar as b'"
    language: python
    weight: 0.65
  - type: ast
    pattern: "Try with bare 'except:'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "FunctionDef with depth > 5"
    language: python
    weight: 0.8
  - type: ast
    pattern: "Import matching 'import \\*'"
    language: python
    weight: 0.9

  # File Path Patterns
  - type: file_path
    pattern: "**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "pyproject.toml"
    weight: 0.9
  - type: file_path
    pattern: "ruff.toml"
    weight: 0.9
  - type: file_path
    pattern: ".flake8"
    weight: 0.9
  - type: file_path
    pattern: "setup.cfg"
    weight: 0.8

  # Content Patterns
  - type: content
    pattern: "^\\s*\\t+"
    language: python
    weight: 0.9
  - type: content
    pattern: ".{120,}"
    language: python
    weight: 0.7
  - type: content
    pattern: "\\n\\n\\n+"
    language: python
    weight: 0.65
  - type: content
    pattern: "import\\s+os,sys|import\\s+\\w+,\\w+"
    language: python
    weight: 0.75

heuristics:
  - "Check for mutable default arguments (= [], = {})"
  - "Look for type hints coverage on public APIs"
  - "Check for unused imports and variables"
  - "Verify import ordering and grouping"
  - "Look for bare except: clauses"
  - "Check for nested functions (indicators of complexity)"
  - "Verify consistent indentation (no tabs)"
  - "Look for shadowing built-in names"
  - "Check for line length violations (>120 chars)"
  - "Verify PEP8 compliance for naming conventions"
```

### Key Patterns Explained

- **Mutable defaults**: `=[]` or `={}` are bugs waiting to happen
- **Bare except**: Catches all exceptions including KeyboardInterrupt
- **Import ***: Pollutes namespace
- **Tabs in Python**: Violation of PEP8
- **Long lines**: May need formatting
- **Deep nesting**: High complexity indicator

---

## 6. Unit Tests Reviewer

**Agent**: `unit_tests_reviewer`
**Focus**: Test adequacy, correctness, edge case coverage, determinism

### Patterns

```yaml
agent: unit_tests_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123test456
patterns:
  # AST Patterns
  - type: ast
    pattern: "FunctionDef with decorator '@pytest.fixture'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "FunctionDef with name starting with 'test_'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "Call with function name 'assert'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "Call with function 'mock.Mock' or 'mock.patch'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "FunctionDef with decorator '@pytest.mark.parametrize'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "FunctionDef with name containing 'time' or 'datetime' or 'random'"
    language: python
    weight: 0.85

  # File Path Patterns
  - type: file_path
    pattern: "**/test_*.py"
    weight: 0.9
  - type: file_path
    pattern: "**/tests/**/*.py"
    weight: 0.9
  - type: file_path
    pattern: "**/*_test.py"
    weight: 0.9
  - type: file_path
    pattern: "**/conftest.py"
    weight: 0.85
  - type: file_path
    pattern: "**/fixtures/**/*.py"
    weight: 0.8

  # Content Patterns
  - type: content
    pattern: "import\\s+time|from\\s+time\\s+import"
    language: python
    weight: 0.85
  - type: content
    pattern: "import\\s+random|from\\s+random\\s+import"
    language: python
    weight: 0.85
  - type: content
    pattern: "assert\\s+True|assert\\s+False|assert\\s+None"
    language: python
    weight: 0.8
  - type: content
    pattern: "monkeypatch\\.setattr|monkeypatch\\.setenv"
    language: python
    weight: 0.75

heuristics:
  - "Check for tests with time dependencies (need mocking)"
  - "Look for tests using random (need seeding for determinism)"
  - "Verify assertions are specific (not just assert True)"
  - "Check for edge case coverage (boundary values, error conditions)"
  - "Look for brittle tests (network calls, file I/O without mocking)"
  - "Verify test fixtures are properly scoped"
  - "Check for parameterized tests for better coverage"
  - "Look for missing tests for new public APIs"
  - "Verify tests cover both happy path and error paths"
  - "Check for flaky tests (timeouts, race conditions)"
```

### Key Patterns Explained

- **test_ functions**: Test functions need review for coverage
- **assert calls**: Assertions need to be meaningful
- **mock.Mock/mock.patch**: Mocking needs review for correctness
- **time/random imports**: Non-deterministic - need mocking
- **conftest.py**: Fixture definitions affect many tests
- **@pytest.mark.parametrize**: Parameterized tests - check coverage

---

## 7. Diff Scoper Reviewer

**Agent**: `diff_scoper_reviewer`
**Focus**: Risk classification, routing attention, change scope analysis

### Patterns

```yaml
agent: diff_scoper_reviewer
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123diff456
patterns:
  # AST Patterns
  - type: ast
    pattern: "ClassDef with more than 10 methods"
    language: python
    weight: 0.8
  - type: ast
    pattern: "FunctionDef with depth > 5"
    language: python
    weight: 0.85
  - type: ast
    pattern: "AsyncFunctionDef with more than 5 'await'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "ClassDef with name ending in 'Migration'"
    language: python
    weight: 0.9

  # File Path Patterns (diff scoper matches everything)
  - type: file_path
    pattern: "**/*"
    weight: 0.5
  - type: file_path
    pattern: "**/migrations/**/*.py"
    weight: 0.9
  - type: file_path
    pattern: "**/database/**/*.py"
    weight: 0.85

  # Content Patterns for risk assessment
  - type: content
    pattern: "^\\+.*class\\s+\\w+\\("
    language: python
    weight: 0.75
  - type: content
    pattern: "^\\+.*def\\s+\\w+\\(.*\\):"
    language: python
    weight: 0.7
  - type: content
    pattern: "^\\+.*import\\s+"
    language: python
    weight: 0.65
  - type: content
    pattern: "^\\-.*def\\s+\\w+\\(.*\\):"
    language: python
    weight: 0.85
  - type: content
    pattern: "^\\-.*class\\s+\\w+\\("
    language: python
    weight: 0.9
  - type: content
    pattern: "^[-+].*password|^[-+].*secret|^[-+].*token"
    language: python
    weight: 0.95
  - type: content
    pattern: "^\\+.*@|^\\-.*@"
    language: python
    weight: 0.7

heuristics:
  - "Classify diff risk based on lines changed (>500 lines = high risk)"
  - "Look for deletions of classes/functions (breaking changes)"
  - "Check for changes to critical paths (auth, payments, core logic)"
  - "Look for new imports that suggest added dependencies"
  - "Verify changes affect multiple files (cross-cutting concern)"
  - "Check for changes to configuration or environment variables"
  - "Look for changes to database schema or migrations"
  - "Route high-risk changes to appropriate reviewers (security, architecture)"
  - "Identify changes that need performance review (loops, queries)"
  - "Flag changes that affect user-visible behavior"
```

### Key Patterns Explained

- **Added/removed classes**: High structural change
- **Added/removed functions**: Breaking change indicator
- **Added imports**: New dependencies
- **Removed definitions**: Potential breaking changes
- **Secrets in diff**: Immediate security risk
- **Decorator changes**: Behavior changes

---

## 8. Requirements Reviewer

**Agent**: `requirements_reviewer`
**Focus**: Requirements compliance, acceptance criteria, scope validation

### Patterns

```yaml
agent: requirements_reviewer
agent_type: required
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123req456
patterns:
  # AST Patterns
  - type: ast
    pattern: "Raise with value 'NotImplementedError'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "FunctionDef with body containing only 'pass'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "Import matching 'import \\*'"
    language: python
    weight: 0.7
  - type: ast
    pattern: "FunctionDef with return statement 'return None'"
    language: python
    weight: 0.7

  # File Path Patterns (requirements reviewer checks all files)
  - type: file_path
    pattern: "**/*.py"
    weight: 0.7
  - type: file_path
    pattern: "*.md"
    weight: 0.8
  - type: file_path
    pattern: "CHANGELOG*"
    weight: 0.75
  - type: file_path
    pattern: "*.md"
    weight: 0.8
  - type: file_path
    pattern: "CHANGELOG*"
    weight: 0.75

  # Content Patterns for requirements validation
  - type: content
    pattern: "TODO:.*|FIXME:.*|XXX:.*"
    language: python
    weight: 0.7
  - type: content
    pattern: "NotImplementedError|raise\\s+Exception"
    language: python
    weight: 0.85
  - type: content
    pattern: "pass\\s*$|\\(\\s*\\)\\s*:\\s*pass"
    language: python
    weight: 0.75
  - type: content
    pattern: "#.*hack|#.*TODO|#.*XXX"
    language: python
    weight: 0.65
  - type: content
    pattern: "def\\s+\\w+\\(.*\\):\\s*return\\s+None"
    language: python
    weight: 0.7
  - type: content
    pattern: "version\\s*=\\s*['\"]\\d+\\.\\d+\\.\\d+['\"]"
    language: python
    weight: 0.8

heuristics:
  - "Compare implementation to PR description/ticket requirements"
  - "Check for acceptance criteria coverage"
  - "Look for incomplete implementations (NotImplementedError, pass)"
  - "Verify error cases are handled or explicitly documented"
  - "Check for scope creep (features not in requirements)"
  - "Look for missing edge cases in implementation"
  - "Verify ambiguous behavior is resolved"
  - "Check for safe defaults vs unsafe defaults"
  - "Look for changes that contradict stated requirements"
  - "Verify breaking changes are intentional and documented"
```

### Key Patterns Explained

- **NotImplementedError**: Incomplete implementation
- **pass statements**: Stub code
- **TODO/FIXME**: Unfinished work
- **Function returning None**: May indicate missing implementation
- **Version changes**: Release-related
- **Hack comments**: Technical debt indicator

---

## 9. Performance & Reliability Reviewer

**Agent**: `performance_reliability_reviewer`
**Focus**: Complexity, IO amplification, retries, concurrency issues

### Patterns

```yaml
agent: performance_reliability_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123perf456
patterns:
  # AST Patterns
  - type: ast
    pattern: "For with nested For"
    language: python
    weight: 0.85
  - type: ast
    pattern: "While with nested While"
    language: python
    weight: 0.9
  - type: ast
    pattern: "FunctionDef with decorator '@retry'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "AsyncFunctionDef with keyword argument 'timeout'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "AsyncFor with nested AsyncFor"
    language: python
    weight: 0.85
  - type: ast
    pattern: "Call with function 'cache' or '@lru_cache'"
    language: python
    weight: 0.8
  - type: ast
    pattern: "Call with function 'Session.query' or 'session.execute'"
    language: python
    weight: 0.85

  # File Path Patterns
  - type: file_path
    pattern: "**/database/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/db/**/*.py"
    weight: 0.85
  - type: file_path
    pattern: "**/network/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/api/**/*.py"
    weight: 0.8
  - type: file_path
    pattern: "**/services/**/*.py"
    weight: 0.75
  - type: file_path
    pattern: "**/config/**/*.py"
    weight: 0.7

  # Content Patterns
  - type: content
    pattern: "for\\s+\\w+\\s+in\\s+.*:\\s*for\\s+\\w+\\s+in\\s+.*:"
    language: python
    weight: 0.9
  - type: content
    pattern: "while\\s+\\w+:\\s*while\\s+\\w+:"
    language: python
    weight: 0.9
  - type: content
    pattern: "\\w+\\.query\\(\\).*\\.fetchall\\(\\)"
    language: python
    weight: 0.85
  - type: content
    pattern: "@retry|tenacity\\.retry|backoff"
    language: python
    weight: 0.85
  - type: content
    pattern: "async\\s+def\\s+\\w+\\(.*\\):[^:]*await\\s+\\w+\\("  # Multiple awaits
    language: python
    weight: 0.75

heuristics:
  - "Look for nested loops (O(n^2) complexity)"
  - "Check for N+1 query patterns (queries inside loops)"
  - "Verify retry logic has exponential backoff and max attempts"
  - "Check for missing timeouts on network calls"
  - "Look for unbounded retry loops (runaway risk)"
  - "Verify cache correctness (invalidation, TTL)"
  - "Check for concurrency issues with shared mutable state"
  - "Look for blocking operations in async functions"
  - "Verify proper use of connection pools"
  - "Check for memory leaks (caches, accumulators)"
```

### Key Patterns Explained

- **Nested loops**: O(n^2) or worse complexity
- **@retry**: Retry logic needs backoff/max_attempts
- **Async without timeout**: Can hang indefinitely
- **Query inside loops**: N+1 query anti-pattern
- **cache decorator**: Check invalidation strategy
- **AsyncFor nested**: Concurrency complexity

---

## 10. Dependency & License Reviewer

**Agent**: `dependency_license_reviewer`
**Focus**: Dependency changes, license compatibility, supply chain risk

### Patterns

```yaml
agent: dependency_license_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123dep456
patterns:
  # AST Patterns
  - type: ast
    pattern: "Import matching 'import requests' or 'from requests import'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "Import matching 'import pandas' or 'from pandas import'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "Import matching 'import numpy' or 'from numpy import'"
    language: python
    weight: 0.75
  - type: ast
    pattern: "Import matching 'import tensorflow' or 'from tensorflow import'"
    language: python
    weight: 0.8

  # File Path Patterns
  - type: file_path
    pattern: "pyproject.toml"
    weight: 0.9
  - type: file_path
    pattern: "requirements*.txt"
    weight: 0.9
  - type: file_path
    pattern: "requirements.txt"
    weight: 0.9
  - type: file_path
    pattern: "Pipfile"
    weight: 0.85
  - type: file_path
    pattern: "poetry.lock"
    weight: 0.9
  - type: file_path
    pattern: "uv.lock"
    weight: 0.9
  - type: file_path
    pattern: "setup.py"
    weight: 0.8
  - type: file_path
    pattern: "setup.cfg"
    weight: 0.8
  - type: file_path
    pattern: "tox.ini"
    weight: 0.75

  # Content Patterns for dependency analysis
  - type: content
    pattern: "^\\+.*==\\s*\\d+\\.\\d+\\.\\d+"
    language: text
    weight: 0.7
  - type: content
    pattern: "^\\+.*>=\\s*\\d+\\.\\d+\\.\\d+"
    language: text
    weight: 0.75
  - type: content
    pattern: "^\\-.*==\\s*\\d+\\.\\d+\\.\\d+"
    language: text
    weight: 0.7
  - type: content
    pattern: "^\\+.*~=\\s*\\d+\\.\\d+"
    language: text
    weight: 0.7
  - type: content
    pattern: "license\\s*=\\s*['\"]GPL"
    language: text
    weight: 0.85
  - type: content
    pattern: "license\\s*=\\s*['\"]AGPL"
    language: text
    weight: 0.9
  - type: content
    pattern: "^\\+.*git\\+https://"
    language: text
    weight: 0.85

heuristics:
  - "Check for new dependencies added without justification"
  - "Verify license compatibility (avoid GPL/AGPL if proprietary)"
  - "Look for loosened version pins (reproducibility risk)"
  - "Check for typosquatting or untrusted package names"
  - "Verify lockfile consistency with dependency file"
  - "Look for dependencies from git repositories (supply chain risk)"
  - "Check for stale dependencies (security patches needed)"
  - "Verify dependency versions align with project policy"
  - "Look for dependency conflicts or circular dependencies"
  - "Check for unused dependencies that can be removed"
```

### Key Patterns Explained

- **Added dependencies (==)**: New pinned dependency
- **Loosened pins (>=, ~=)**: Reduced reproducibility
- **Removed dependencies**: Check for breaking changes
- **GPL/AGPL licenses**: Copyleft - review for commercial use
- **git+https://**: Development dependency - supply chain risk

---

## 11. Release & Changelog Reviewer

**Agent**: `release_changelog_reviewer`
**Focus**: Changelog updates, version bumps, breaking changes, migration docs

### Patterns

```yaml
agent: release_changelog_reviewer
agent_type: optional
version: 1.0.0
generated_at: 2024-01-15T10:30:00Z
prompt_hash: abc123rel456
patterns:
  # AST Patterns
  - type: ast
    pattern: "FunctionDef with decorator '@deprecated'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "ClassDef with decorator '@deprecated'"
    language: python
    weight: 0.9
  - type: ast
    pattern: "FunctionDef with name starting with 'deprecate_'"
    language: python
    weight: 0.85
  - type: ast
    pattern: "Call with function 'warnings.warn'"
    language: python
    weight: 0.8

  # File Path Patterns
  - type: file_path
    pattern: "CHANGELOG*"
    weight: 0.95
  - type: file_path
    pattern: "CHANGES*"
    weight: 0.95
  - type: file_path
    pattern: "HISTORY*"
    weight: 0.95
  - type: file_path
    pattern: "pyproject.toml"
    weight: 0.9
  - type: file_path
    pattern: "setup.py"
    weight: 0.85
  - type: file_path
    pattern: "**/__init__.py"
    weight: 0.8
  - type: file_path
    pattern: "**/version.py"
    weight: 0.9

  # Content Patterns for release hygiene
  - type: content
    pattern: "^version\\s*=\\s*['\"]\\d+\\.\\d+\\.\\d+['\"]"
    language: python
    weight: 0.9
  - type: content
    pattern: "^\\+.*##\\s+\\d+\\.\\d+\\.\\d+"
    language: text
    weight: 0.9
  - type: content
    pattern: "BREAKING|breaking|deprecated|DEPRECATED"
    language: text
    weight: 0.85
  - type: content
    pattern: "migration|MIGRATION|upgrade|UPGRADE"
    language: text
    weight: 0.85
  - type: content
    pattern: "^\\+.*Added|^\\+.*Fixed|^\\+.*Changed"
    language: text
    weight: 0.75
  - type: content
    pattern: "version\\s*=\\s*['\"]\\d+\\.\\d+\\.\\d+['\"]"
    language: text
    weight: 0.9
  - type: content
    pattern: "semver|semantic.*version"
    language: text
    weight: 0.7

heuristics:
  - "Check for breaking changes without migration notes"
  - "Verify version bump matches change scope (major/minor/patch)"
  - "Look for user-visible behavior changes without changelog entry"
  - "Check for CLI flag changes that need docs updates"
  - "Verify deprecation warnings are documented"
  - "Look for output format changes that break user scripts"
  - "Check for configuration changes that need migration docs"
  - "Verify release notes follow project's changelog format"
  - "Look for missing entries for added features or bug fixes"
  - "Check that unreleased section is cleared on release"
```

### Key Patterns Explained

- **Version changes**: Version bump detected
- **Changelog entries**: Added release notes
- **BREAKING/deprecated**: Breaking changes need migration docs
- **Migration/upgrade**: Migration documentation
- **Added/Fixed/Changed**: Changelog categories

---

## Pattern Weight Guidelines

| Weight Range | Meaning | Examples |
|--------------|---------|----------|
| 0.95 | Critical - Immediate attention | Secrets, code execution, unsafe defaults |
| 0.9 | High Risk - Major concerns | N+1 queries, GPL licenses, breaking changes |
| 0.85 | Significant - Needs careful review | Nested loops, missing docs, complex error handling |
| 0.8 | Medium-High - Common issues | Logging quality, retry logic, type hints |
| 0.75 | Medium - Standard review points | Route handlers, test fixtures, config files |
| 0.7 | Low-Medium - Minor concerns | Import ordering, line length, comments |
| 0.65 | Low - Nice to have | Minor style issues, small improvements |
| 0.6 | Very Low - Optional | Extra whitespace, minor naming issues |

## Validation

To validate this document:

```bash
# Ensure all agents have required fields
# - agent
# - agent_type
# - version
# - generated_at
# - prompt_hash
# - patterns (min 3)
# - heuristics (min 3)

# Each pattern must have:
# - type (ast, file_path, content)
# - pattern (string)
# - weight (0.0-1.0)
# - language (for ast and content)

# For each agent, verify:
# - At least 3 AST patterns
# - At least 2 file path patterns
# - At least 3 heuristic rules
```

## Maintenance

This document should be regenerated when any reviewer agent's system prompt changes to keep entry points in sync with the agent's focus.
