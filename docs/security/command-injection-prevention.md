# Security: Command Injection Prevention

This document describes command injection vulnerabilities found in Dawn Kestrel and the mitigation strategies implemented.

## Overview

Command injection is a critical security vulnerability where untrusted input is executed as a shell command. This can lead to:

- Arbitrary code execution
- Data exfiltration
- System compromise

## Vulnerabilities Identified

### 1. Bash Tool Shell Execution (CRITICAL)
**File:** `dawn_kestrel/tools/builtin.py`
**Issue:** BashTool used `shell=True` with raw command string

```python
# VULNERABLE CODE
result = subprocess.run(
    [validated.command],
    shell=True,  # DANGEROUS: enables shell interpretation
    cwd=work_dir,
    capture_output=True,
    text=True,
    check=True,
)
```

**Exploit:** `command="ls; rm -rf /"`

**Fix Implemented:**
```python
# SECURE CODE
tokens = validate_command(validated.command, allowed_commands=ALLOWED_SHELL_COMMANDS)
result = subprocess.run(
    tokens,
    shell=False,  # SAFE: use list format
    cwd=work_dir,
    capture_output=True,
    text=True,
    check=False,
)
```

### 2. Git Hash Validation (CRITICAL)
**File:** `dawn_kestrel/git/commands.py`
**Issue:** User-provided hash values passed directly to git

```python
# VULNERABLE CODE
def get_diff(self, from_hash: str, to_hash: str) -> str:
    result = self._run_git("diff", from_hash, to_hash)
```

**Exploit:** `from_hash="../../../etc/passwd"`

**Fix Implemented:**
```python
# SECURE CODE
def get_diff(self, from_hash: str, to_hash: str) -> str:
    try:
        from_validated = validate_git_hash(from_hash)
        to_validated = validate_git_hash(to_hash)
    except SecurityError as e:
        raise ValueError(f"Invalid git hash: {e}")
    result = self._run_git("diff", from_validated, to_validated)
```

### 3. Storage Path Traversal (CRITICAL)
**File:** `dawn_kestrel/storage/store.py`
**Issue:** Direct path joining without sanitization

```python
# VULNERABLE CODE
async def _get_path(self, *keys: str) -> Path:
    return self.storage_dir / "/".join(keys)
```

**Exploit:** `keys=["session", "..", "..", "etc", "passwd"]`

**Fix Implemented:**
```python
# SECURE CODE
async def _get_path(self, *keys: str) -> Path:
    for key in keys:
        if not key or ".." in key or "/" in key or "\\" in key or "\x00" in key:
            raise SecurityError(f"Invalid storage key: {key}")

    path = self.storage_dir / "/".join(keys)
    try:
        resolved = path.resolve()
        if not str(resolved).startswith(str(self.storage_dir.resolve())):
            raise SecurityError(f"Path traversal attempt detected: {path}")
        return path
```

### 4. Grep, Glob, AST-Grep Pattern Injection (HIGH)
**File:** `dawn_kestrel/tools/builtin.py`
**Issue:** User-provided regex patterns without validation

```python
# VULNERABLE CODE
cmd = ["rg", "-e", query, file_pattern_str]
result = subprocess.run(cmd, ...)
```

**Exploit:** `query="(?R)"` (catastrophic backtracking)

**Fix Implemented:**
```python
# SECURE CODE
validate_pattern(query, max_length=1000)
cmd = ["rg", "-e", query, file_pattern_str]
result = subprocess.run(cmd, ..., shell=False)
```

### 5. CLI Module Loading (HIGH)
**File:** `dawn_kestrel/cli/main.py`
**Issue:** Dynamic import without path validation

```python
# VULNERABLE CODE
def _load_review_cli_command(command_name: str) -> Any:
    cli_path = Path(__file__).resolve().parent.parent / "agents" / "review" / "cli.py"
    spec = importlib.util.spec_from_file_location("dawn_kestrel_review_cli", cli_path)
```

**Exploit:** Symlink attack to load arbitrary module

**Fix Implemented:**
```python
# SECURE CODE
def _load_review_cli_command(command_name: str) -> Any:
    cli_path = Path(__file__).resolve().parent.parent / "agents" / "review" / "cli.py"
    try:
        safe_path(cli_path)
    except SecurityError as e:
        raise click.ClickException(f"Module path validation failed: {e}")
    ...
```

## Security Framework: Input Validation Module

### Location
`dawn_kestrel/core/security/input_validation.py`

### Key Functions

#### `safe_path(path_str, base_dir, allow_absolute)`
Validates file paths and prevents directory traversal:
- Rejects `..` sequences
- Rejects null bytes
- Resolves symlinks
- Enforces base directory boundaries
- Optionally blocks absolute paths

#### `validate_command(command, allowed_commands)`
Validates shell commands to prevent injection:
- Uses `shlex.split()` for safe parsing
- Blocks shell metacharacters (`;`, `|`, `&`, `$()`, `` ` ``, etc.)
- Enforces allowlist of permitted commands
- Validates arguments don't contain injection patterns

#### `validate_pattern(pattern, max_length)`
Validates regex/glob patterns to prevent ReDoS:
- Enforces maximum pattern length (default: 1000)
- Blocks recursive patterns (`(?R)`, `(?0)`)
- Blocks catastrophic backtracking patterns
- Rejects null bytes

#### `validate_git_hash(hash_value)`
Validates Git commit hashes:
- Rejects path traversal sequences
- Enforces hexadecimal-only format
- Supports full (40/64 chars) and abbreviated (7+ chars) hashes

#### `validate_url(url, allow_https_only, max_length)`
Validates URLs to prevent SSRF:
- Enforces HTTPS-only (when required)
- Blocks internal addresses (localhost, 127.0.0.1, etc.)
- Blocks cloud metadata endpoints (169.254.169.254)
- Blocks unsafe schemes (file://, ftp://)

### Decorators

#### `@validate_path_param(param_name, base_dir)`
Validates function parameters as safe paths.

```python
@validate_path_param("file_path", base_dir=Path("/safe/dir"))
def process_file(file_path: str) -> None:
    ...
```

#### `@validate_command_param(param_name, allowed_commands)`
Validates function parameters as safe commands.

```python
@validate_command_param("cmd", allowed_commands={"git", "ls"})
def run_cmd(cmd: str) -> None:
    ...
```

## Best Practices

### 1. Never Use `shell=True` with User Input
```python
# DANGEROUS
subprocess.run(user_input, shell=True)

# SAFE
tokens = shlex.split(user_input)
subprocess.run(tokens, shell=False)
```

### 2. Always Validate Before Execution
```python
# DANGEROUS
subprocess.run(["git", "diff", user_hash])

# SAFE
validated_hash = validate_git_hash(user_hash)
subprocess.run(["git", "diff", validated_hash])
```

### 3. Use Allowlists Over Blocklists
```python
# DANGEROUS (incomplete)
if "rm" not in command:  # Easy to bypass
    subprocess.run(command, shell=True)

# SAFE
allowed = {"git", "ls", "cat"}
if command.split()[0] in allowed:
    subprocess.run(command.split(), shell=False)
```

### 4. Resolve and Bound Paths
```python
# DANGEROUS
full_path = base_dir / user_path

# SAFE
full_path = safe_path(user_path, base_dir=base_dir)
```

### 5. Enforce Input Length Limits
```python
# DANGEROUS (unbounded input)
process_pattern(user_pattern)

# SAFE (bounded)
if len(user_pattern) > 1000:
    raise SecurityError("Pattern too long")
process_pattern(user_pattern)
```

## Pre-Defined Allowlists

### ALLOWED_SHELL_COMMANDS
```python
{
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
}
```

### ALLOWED_GIT_COMMANDS
```python
{
    "git",
    "git-status",
    "git-log",
    "git-diff",
    "git-show",
    "git-rev-parse",
    "git-write-tree",
    "git-read-tree",
    "git-checkout-index",
    "git-gc",
}
```

### ALLOWED_SEARCH_TOOLS
```python
{
    "rg",  # ripgrep
    "grep",
    "ast-grep",
    "find",
}
```

## Testing Security

### Unit Tests
Test all validation functions with malicious inputs:

```python
# Test path traversal
with pytest.raises(SecurityError):
    safe_path("../../../etc/passwd")

# Test command injection
with pytest.raises(SecurityError):
    validate_command("ls; rm -rf /")

# Test ReDoS patterns
with pytest.raises(SecurityError):
    validate_pattern("(?R)")

# Test invalid git hashes
with pytest.raises(SecurityError):
    validate_git_hash("../../etc/passwd")
```

### Integration Tests
Test tools reject malicious inputs:

```python
# Test BashTool rejects shell metacharacters
result = await bash_tool.execute({"command": "ls; cat /etc/passwd"}, ctx)
assert result.metadata.get("security_error") == True

# Test Storage rejects path traversal
with pytest.raises(SecurityError):
    await storage._get_path("session", "..", "..", "etc", "passwd")
```

## Security Checklist

When adding new tools or features:

- [ ] All user input is validated before use
- [ ] `shell=False` used with subprocess
- [ ] Commands are parsed as lists, not strings
- [ ] Paths are validated against allowlist/allowlist
- [ ] Patterns have length limits
- [ ] Git hashes validated as hexadecimal
- [ ] URLs validated for SSRF
- [ ] Security errors are logged (WARNING level)
- [ ] Sensitive data never logged
- [ ] Tests include malicious input cases

## References

- [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
- [OWASP Command Injection](https://owasp.org/www-community/attacks/Command_Injection)
- [Python subprocess Security](https://docs.python.org/3/library/subprocess.html#security-considerations)
