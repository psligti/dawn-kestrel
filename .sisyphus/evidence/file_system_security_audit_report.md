# File System Security Audit Report

**Date**: 2026-02-10
**Auditor**: Autonomous Security Review
**Branch**: wt/harness-agent-rework
**Base**: main
**Scope**: File system operations for path traversal and access control

## Executive Summary

This audit reviewed file system operations across the dawn-kestrel codebase for path traversal vulnerabilities, access control issues, and related security concerns.

**Overall Severity**: 2 CRITICAL, 3 HIGH, 2 MEDIUM, 4 LOW

### Quick Summary

- **CRITICAL** (2): Storage layer path traversal, Tool file operation vulnerabilities
- **HIGH** (3): Export/import path handling, Snapshot file operations, CLI path handling
- **MEDIUM** (2): Directory traversal in tools, Missing symlink handling
- **LOW** (4): Directory creation without ownership checks, File deletion without validation

---

## 1. CRITICAL Vulnerabilities

### 1.1 Path Traversal in Storage Layer

**File**: `dawn_kestrel/storage/store.py`
**Lines**: 16-24
**Severity**: CRITICAL
**CVE-like**: CWE-22 (Path Traversal)

```python
class Storage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.storage_dir = self.base_dir / "storage"

    async def _get_path(self, *keys: str) -> Path:
        """Get full path for a key"""
        return self.storage_dir / "/".join(keys)  # VULNERABLE: No path sanitization
```

**Vulnerability**:
- The `_get_path()` method joins keys with `/` separator without validating for `..` sequences
- An attacker with control over `keys` parameter can access files outside the storage directory
- This affects `read()`, `write()`, `remove()`, and `list()` operations

**Attack Vector**:
```python
# Malicious session_id with directory traversal
keys = ["session", "project_id", "../../../../etc/passwd"]
path = await storage._get_path(*keys)
# Results in: /storage/session/project_id/../../../../etc/passwd
# Which resolves to: /etc/passwd
```

**Impact**:
- **Arbitrary file read**: Can read any file accessible by the process user
- **Arbitrary file write**: Can overwrite any file accessible by the process user
- **Arbitrary file deletion**: Can delete any file accessible by the process user
- **Information disclosure**: Access to sensitive configuration files, logs, credentials

**Affected Components**:
- `SessionStorage` (inherits from Storage)
- `MessageStorage` (inherits from Storage)
- `PartStorage` (inherits from Storage)
- `MemoryStorage` (inherits from Storage)

**Recommendation**:
```python
import os

async def _get_path(self, *keys: str) -> Path:
    """Get full path for a key with path traversal protection"""
    # Validate keys don't contain path traversal sequences
    for key in keys:
        if ".." in key or key.startswith("/") or key.startswith("\\"):
            raise ValueError(f"Invalid key: {key}")

    # Build path and verify it's within storage_dir
    path = self.storage_dir / "/".join(keys)
    # Resolve to absolute path and verify it's still within storage_dir
    resolved = path.resolve()
    try:
        resolved.relative_to(self.storage_dir.resolve())
    except ValueError:
        raise ValueError(f"Path traversal detected: {keys}")
    return resolved
```

---

### 1.2 Unvalidated File Paths in Built-in Tools

**Files**:
- `dawn_kestrel/tools/builtin.py` (ReadTool, WriteTool, ListTool, EditTool)
- `dawn_kestrel/tools/additional.py` (EditTool, MultiEditTool)

**Lines**: 
- builtin.py: 128 (ReadTool), 198 (WriteTool), 202 (mkdir), 87 (EditTool)
- additional.py: 77 (EditTool), 111 (MultiEditTool), 148 (ListTool), 257 (EditTool)

**Severity**: CRITICAL
**CVE-like**: CWE-22 (Path Traversal)

#### ReadTool (builtin.py:128)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    validated = ReadToolArgs(**args)
    file_path = validated.filePath

    try:
        full_path = Path(file_path)  # VULNERABLE: No validation
        if not full_path.exists():
            return ToolResult(...)

        with open(full_path, "r") as f:  # VULNERABLE: Direct open
            all_lines = f.readlines()
```

**Vulnerability**:
- Direct use of user-provided `filePath` without validation
- Allows reading arbitrary files via path traversal (`../../etc/passwd`)

**Attack Vector**:
```json
{
  "filePath": "../../../../etc/passwd"
}
```

#### WriteTool (builtin.py:198)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    validated = WriteToolArgs(**args)
    file_path = validated.filePath
    content = validated.content
    create_dirs = validated.create

    try:
        full_path = Path(file_path)  # VULNERABLE: No validation

        if create_dirs:
            full_path.parent.mkdir(parents=True, exist_ok=True)  # DANGEROUS: Creates directories

        with open(full_path, "w") as f:  # VULNERABLE: Direct write
            f.write(content)
```

**Vulnerability**:
- Direct use of user-provided `filePath` without validation
- Allows writing arbitrary files and creating directories anywhere on the filesystem
- Can overwrite critical system files

**Attack Vector**:
```json
{
  "filePath": "../../../../tmp/evil.sh",
  "content": "#!/bin/bash\nevil commands",
  "create": true
}
```

#### EditTool (additional.py:77)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    file_path = args.get("filePath")

    path = Path(file_path)  # VULNERABLE: No validation

    if not path.exists():
        return ToolResult(...)

    with open(path, "r") as f:  # VULNERABLE: Direct read
        content = f.read()

    # ... edit logic ...

    with open(path, "w") as f:  # VULNERABLE: Direct write
        f.write(new_content)
```

**Vulnerability**:
- Direct use of user-provided `filePath` without validation
- Allows editing arbitrary files

#### ListTool (additional.py:148)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    dir_path = args.get("path", ".")
    ignore_patterns = args.get("ignore", [])

    path = Path(dir_path)  # VULNERABLE: No validation

    if not path.exists():
        return ToolResult(...)

    if not path.is_dir():
        return ToolResult(...)

    result = self._list_directory(path, ignore_patterns)  # VULNERABLE: rglob traverses anywhere
```

**Vulnerability**:
- Can list any directory on the filesystem
- `path.rglob("*")` can traverse entire filesystem
- Information disclosure

**Impact**:
- **Arbitrary file read**: Read any file on the filesystem
- **Arbitrary file write**: Overwrite any file on the filesystem
- **Directory creation**: Create directories anywhere
- **Information disclosure**: List any directory contents
- **Privilege escalation**: Overwrite configuration files, add cron jobs, etc.

**Recommendation**:
All tools should:
1. Resolve file paths relative to a trusted base directory (e.g., project root)
2. Validate paths don't escape the base directory using `relative_to()`
3. Reject paths containing `..`, absolute paths, or special sequences
4. Use `resolve().relative_to(base_dir)` to verify paths stay within bounds

```python
# Safe pattern for tool file operations
def validate_file_path(file_path: str, base_dir: Path) -> Path:
    """Validate file path is within base directory"""
    full_path = base_dir / file_path
    resolved = full_path.resolve()

    try:
        resolved.relative_to(base_dir.resolve())
        return resolved
    except ValueError:
        raise ValueError(f"Path traversal detected: {file_path}")

# Usage in ReadTool
base_dir = Path(ctx.session_id if ctx.session_id else ".")
full_path = validate_file_path(file_path, base_dir)
```

---

## 2. HIGH Severity Vulnerabilities

### 2.1 Unvalidated Export/Import Paths

**File**: `dawn_kestrel/session/export_import.py`
**Lines**: 66, 70, 77, 125, 128
**Severity**: HIGH
**CVE-like**: CWE-22 (Path Traversal), CWE-20 (Improper Input Validation)

```python
class ExportImportManager:
    async def export_session(self, session_id: str, output_path: Optional[Path] = None, format: str = "json"):
        if not output_path:
            output_path = Path.cwd() / f"{session_id}.{format}"  # Uses cwd

        # Write to file
        if format == "json":
            with open(output_path, "w", encoding="utf-8") as f:  # VULNERABLE
                json.dump(export_data, f, indent=2, ensure_ascii=False)

    async def import_session(self, import_path: Path, project_id: Optional[str] = None):
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")

        # Read and parse
        if format == "json" or format == "jsonl":
            with open(import_path, "r", encoding="utf-8") as f:  # VULNERABLE
                export_data = json.load(f)
```

**Vulnerability**:
- Direct use of user-provided `output_path` and `import_path` without validation
- No restriction on where files can be read from or written to
- Can overwrite any file via export
- Can read any file via import (JSON parsing may fail but file is opened)

**Attack Vectors**:
```python
# Export to sensitive location
await manager.export_session("session_id", Path("/etc/malicious.json"), "json")

# Import from sensitive location (though JSON parsing may fail)
await manager.import_session(Path("/etc/passwd"))
```

**Impact**:
- **Arbitrary file write**: Overwrite system files via export
- **Information disclosure**: Read arbitrary files via import (partial)
- **Denial of service**: Write large files to fill disk

**Recommendation**:
```python
async def export_session(self, session_id: str, output_path: Optional[Path] = None, format: str = "json"):
    if not output_path:
        output_path = Path.cwd() / f"{session_id}.{format}"

    # Validate output path
    resolved = output_path.resolve()
    try:
        resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        raise ValueError(f"Output path must be within current directory: {output_path}")

    # ... rest of code
```

---

### 2.2 Snapshot File Revert Vulnerability

**File**: `dawn_kestrel/snapshot.py`
**Lines**: 114, 137
**Severity**: HIGH
**CVE-like**: CWE-22 (Path Traversal)

```python
class GitSnapshot:
    async def revert_file(self, file_path: str, snapshot_hash: str) -> bool:
        try:
            full_path = self.project_root / file_path  # VULNERABLE: No validation

            if not full_path.exists():
                logger.error(f"File not found: {full_path}")
                return False

            blob = tree[file_path]

            with open(full_path, "wb") as f:  # VULNERABLE: Direct write
                f.write(blob.data)
```

**Vulnerability**:
- `file_path` comes from git tree, but could be manipulated
- Direct file write without validation
- If `file_path` contains `..` sequences, can write outside project root

**Attack Vector**:
```python
# If git tree contains malicious file path
file_path = "../../etc/passwd"
full_path = self.project_root / file_path  # Escapes project_root
```

**Impact**:
- **Arbitrary file write**: Overwrite any file accessible by process
- **Privilege escalation**: Overwrite system files

**Recommendation**:
```python
async def revert_file(self, file_path: str, snapshot_hash: str) -> bool:
    # Validate file_path doesn't contain path traversal
    if ".." in file_path or file_path.startswith("/") or file_path.startswith("\\"):
        logger.error(f"Invalid file path: {file_path}")
        return False

    full_path = self.project_root / file_path

    # Verify path is within project_root
    resolved = full_path.resolve()
    try:
        resolved.relative_to(self.project_root.resolve())
    except ValueError:
        logger.error(f"Path traversal detected: {file_path}")
        return False

    # ... rest of code
```

---

### 2.3 CLI Path Handling Without Validation

**File**: `dawn_kestrel/cli/main.py`
**Lines**: 79, 214, 287
**Severity**: HIGH
**CVE-like**: CWE-22 (Path Traversal)

```python
@click.option("--directory", "-d", type=click.Path(), help="Project directory")
def list_sessions(directory: str | None) -> None:
    work_dir = Path(directory).expanduser() if directory else Path.cwd()  # VULNERABLE

@click.option("--output", "-o", type=click.Path(), help="Output file path")
def export_session(session_id: str, output: str | None, format: str):
    output_path = Path(output) if output else None  # VULNERABLE

@click.argument("import_path", type=click.Path(exists=True))
def import_session(import_path: str, project_id: str | None):
    result = await manager.import_session(import_path=Path(import_path))  # VULNERABLE
```

**Vulnerability**:
- User-provided paths used directly without validation
- `expanduser()` can be misused
- No restrictions on which directories can be accessed

**Impact**:
- **Information disclosure**: Access arbitrary directories
- **Arbitrary file operations**: Read/write files outside intended scope

**Recommendation**:
Add path validation in CLI commands:
```python
def list_sessions(directory: str | None) -> None:
    work_dir = Path(directory).expanduser().resolve() if directory else Path.cwd()

    # Validate work_dir exists and is accessible
    if not work_dir.exists():
        console.print(f"[red]Directory not found: {work_dir}[/red]")
        sys.exit(1)

    # Consider restricting to subdirectories of current working directory
    # or explicitly allowlisted directories
```

---

## 3. MEDIUM Severity Vulnerabilities

### 3.1 Directory Traversal in Additional Tools

**Files**:
- `dawn_kestrel/tools/additional.py` - ExternalDirectoryTool, SkillTool

**Lines**: 540, 602, 620
**Severity**: MEDIUM

#### SkillTool (additional.py:540)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    base_dir = Path(ctx.session_id if ctx.session_id else ".")  # VULNERABLE
    loader = SkillLoader(base_dir)
```

**Vulnerability**:
- Uses `ctx.session_id` as base directory without validation
- If `session_id` contains path traversal sequences, can access arbitrary directories

#### ExternalDirectoryTool (additional.py:602)
```python
async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
    directory = args.get("directory")

    path = Path(directory)  # VULNERABLE

    if not path.exists():
        return ToolResult(...)

    for item in path.rglob("*"):  # VULNERABLE: rglob can traverse anywhere
```

**Vulnerability**:
- Can list any directory on the filesystem
- `rglob` traverses recursively without restrictions

**Impact**:
- **Information disclosure**: List directory contents anywhere
- **Directory scanning**: Reconnaissance for sensitive files

**Recommendation**:
- Restrict ExternalDirectoryTool to explicitly allowed paths
- Validate session_id doesn't contain path traversal

---

### 3.2 Missing Symlink Handling

**Files**: Multiple (storage layer, tools, snapshot)

**Severity**: MEDIUM
**CVE-like**: CWE-59 (Improper Link Resolution)

**Issue**:
- No symlink validation or checking for symlink attacks
- Attackers could create symlinks to sensitive files
- Operations may follow symlinks to unintended locations

**Example Attack**:
```bash
# Create malicious symlink
ln -s /etc/passwd /storage/session/evil/malicious.json

# Application reads/writes the symlink
# File operations actually target /etc/passwd
```

**Impact**:
- **Symlink attacks**: Redirect file operations to sensitive files
- **TOCTOU issues**: Race conditions between path validation and use

**Recommendation**:
- Use `os.path.realpath()` or `Path.resolve(strict=True)` to follow symlinks
- Check for symlinks before sensitive operations
- Validate resolved path, not just the provided path

```python
def is_safe_path(path: Path, base_dir: Path) -> bool:
    """Check if path is safe (no symlink traversal)"""
    try:
        resolved = path.resolve(strict=True)
        base_resolved = base_dir.resolve()
        resolved.relative_to(base_resolved)
        return True
    except (ValueError, FileNotFoundError, RuntimeError):
        return False
```

---

## 4. LOW Severity Vulnerabilities

### 4.1 Directory Creation Without Ownership Checks

**Files**: Multiple
**Severity**: LOW

**Locations**:
- `dawn_kestrel/storage/store.py:27` - `path.parent.mkdir()`
- `dawn_kestrel/tools/builtin.py:202` - `full_path.parent.mkdir()`
- `dawn_kestrel/providers/registry.py:43` - `self.storage_dir.mkdir()`
- Many others

**Issue**:
- `mkdir(parents=True, exist_ok=True)` creates directories without checking ownership
- Could potentially exploit existing directories owned by other users

**Impact**: Limited, but could be used for information disclosure or persistence

**Recommendation**:
- Check directory ownership after creation
- Verify directory is writable by expected user only

---

### 4.2 File Deletion Without Validation

**File**: `dawn_kestrel/storage/store.py:55-62`
**Severity**: LOW

```python
async def remove(self, key: List[str]) -> bool:
    """Remove data by key"""
    try:
        path = await self._get_path(*key)
        path.unlink()  # VULNERABLE: No additional validation
        return True
    except FileNotFoundError:
        return False
```

**Issue**:
- Relies only on `_get_path()` for validation
- If `_get_path()` has bugs, can delete arbitrary files

**Recommendation**:
- Add additional validation in `remove()` method
- Verify path is within storage directory before deletion

---

### 4.3 Unrestricted File Listing

**File**: `dawn_kestrel/storage/store.py:64-74`
**Severity**: LOW

```python
async def list(self, prefix: List[str]) -> List[List[str]]:
    """List all keys with given prefix"""
    prefix_path = await self._get_path(*prefix)
    if not prefix_path.exists():
        return []
    keys = []
    for path in prefix_path.rglob("*.json"):  # rglob can traverse
        relative = path.relative_to(self.storage_dir)
        keys.append(list(relative.parts)[0:len(prefix)] + [relative.stem])
```

**Issue**:
- `rglob()` can potentially traverse outside intended directory if symlinks are present

**Impact**: Information disclosure

**Recommendation**:
- Validate each path returned by `rglob()` is within storage directory
- Use symlink-safe iteration

---

### 4.4 Temporary File Usage

**Files**: Various test files, snapshot.py:179

**Severity**: LOW

**Analysis**:
- All `tempfile.TemporaryDirectory()` usage is correct (context manager)
- Test files properly clean up
- Snapshot.py uses temporary directory correctly

**Status**: NO ISSUES FOUND - This is good practice

---

## 5. Access Control Issues

### 5.1 Missing File Permission Checks

**Severity**: MEDIUM

**Issue**:
- No explicit file permission checks before operations
- Assumes OS permissions are sufficient
- No explicit read/write permission validation

**Recommendation**:
- Check file permissions before operations
- Log permission denied events
- Consider implementing application-level permissions

---

### 5.2 No Storage Directory Permission Enforcement

**File**: `dawn_kestrel/core/settings.py`

**Issue**:
- Storage directory permissions are not enforced at application level
- Relies on filesystem permissions only

**Recommendation**:
- Validate storage directory has appropriate permissions on startup
- Warn if directory is world-writable
- Consider creating storage directory with restricted permissions

---

## 6. Configuration Security

### 6.1 Storage Directory Configuration

**File**: `dawn_kestrel/core/settings.py:319-337`

```python
def storage_dir_path(self) -> Path:
    return Path(self.storage_dir).expanduser()

def config_dir_path(self) -> Path:
    return Path(self.config_dir).expanduser()

def cache_dir_path(self) -> Path:
    return Path(self.cache_dir).expanduser()
```

**Analysis**:
- Uses `expanduser()` which is correct for user directories
- No validation that expanded path is safe
- Could be misconfigured via environment variables

**Recommendation**:
- Validate configured directories exist and are writable
- Check for symlinks to sensitive locations
- Add configuration validation

---

## 7. Recommendations Summary

### Immediate Actions (Critical/High)

1. **Fix Storage Layer Path Traversal** (CRITICAL)
   - Add path validation in `_get_path()` method
   - Use `resolve().relative_to()` to verify paths stay within bounds
   - Reject keys containing `..`, absolute paths, special sequences

2. **Fix Built-in Tools Path Validation** (CRITICAL)
   - Add path validation in ReadTool, WriteTool, EditTool, ListTool
   - Restrict all file operations to base directory (project root)
   - Use safe path resolution pattern

3. **Fix Export/Import Path Validation** (HIGH)
   - Validate output and import paths are within expected directories
   - Reject paths that escape current directory or allowed paths

4. **Fix Snapshot Revert Path Validation** (HIGH)
   - Validate `file_path` doesn't contain path traversal sequences
   - Verify resolved path is within project root

5. **Add CLI Path Restrictions** (HIGH)
   - Restrict directory access to safe locations
   - Validate user-provided paths before use

### Short-term Actions (Medium)

6. **Add Symlink Protection**
   - Use `resolve(strict=True)` for path validation
   - Check for symlinks before sensitive operations
   - Validate resolved paths, not just provided paths

7. **Improve Access Control**
   - Add explicit file permission checks
   - Log permission denied events
   - Consider application-level permissions

8. **Validate Configuration**
   - Check storage directory permissions on startup
   - Warn if directories are world-writable
   - Validate environment variables

### Long-term Actions (Low)

9. **Security Headers/Metadata**
   - Add security documentation to storage layer
   - Document safe path handling patterns
   - Add security tests for path traversal

10. **Security Testing**
    - Add unit tests for path traversal attacks
    - Add fuzzing for file operations
    - Test symlink attacks

---

## 8. Testing Recommendations

### Test Cases to Add

```python
# Path traversal tests
def test_storage_path_traversal_prevented():
    storage = Storage("/tmp/safe")
    with pytest.raises(ValueError):
        await storage._get_path("session", "project", "../../../etc/passwd")

def test_read_tool_path_traversal_prevented():
    result = await read_tool.execute({"filePath": "../../../../etc/passwd"}, ctx)
    assert "path traversal" in result.metadata.get("error", "")

def test_write_tool_path_traversal_prevented():
    result = await write_tool.execute({
        "filePath": "/etc/malicious",
        "content": "evil"
    }, ctx)
    assert "path traversal" in result.metadata.get("error", "")

# Symlink tests
def test_symlink_protection():
    # Create symlink to sensitive file
    Path("/tmp/safe/link").symlink_to("/etc/passwd")
    # Should not be able to read via symlink
    result = await read_tool.execute({"filePath": "/tmp/safe/link"}, ctx)
    assert "symlink" in result.metadata.get("error", "")

# Configuration tests
def test_world_writable_directory_warning():
    # Create world-writable directory
    os.makedirs("/tmp/unsafe", mode=0o777)
    # Should warn on startup
    with warnings.catch_warnings(record=True) as w:
        settings.storage_dir = "/tmp/unsafe"
        assert any("world-writable" in str(w.message) for w in w)
```

---

## 9. Compliance Notes

### CWE Mapping

- **CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')**
  - Issues: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1
- **CWE-20: Improper Input Validation**
  - Issues: 1.1, 1.2, 2.1, 2.3
- **CWE-59: Improper Link Resolution Before File Access ('Link Following')**
  - Issue: 3.2
- **CWE-276: Incorrect Default Permissions**
  - Issue: 4.1

### OWASP Top 10 Mapping

- **A01:2021 - Broken Access Control**
  - Issues: 1.1, 1.2, 2.1, 2.2
- **A03:2021 - Injection**
  - Issues: 1.2 (path injection)
- **A05:2021 - Security Misconfiguration**
  - Issues: 4.1, 6.1

---

## 10. Conclusion

The dawn-kestrel codebase has several critical and high-severity file system security vulnerabilities that should be addressed immediately:

1. **Storage layer path traversal** is the most critical issue, affecting all file operations
2. **Built-in tools** lack proper path validation, allowing arbitrary file access
3. **Export/import** and **snapshot** functionality can be abused for file system access

All these issues stem from a common root cause: **lack of proper path validation and sanitization** before file operations.

**Recommended Action Plan**:
1. Implement a centralized `validate_safe_path()` utility function
2. Add this validation to all file operations (storage, tools, export/import, snapshot)
3. Add comprehensive security tests for path traversal and symlink attacks
4. Document secure path handling patterns for future development

**Estimated Effort**: 2-3 days for critical fixes, 1 week for comprehensive security hardening

---

**Auditor Notes**:
- All vulnerabilities are exploitable by attackers with the ability to control input to affected functions
- Some vulnerabilities may be mitigated by network-level access controls (if API is internal-only)
- Defense in depth recommended: validate at multiple layers (input, storage, tools)
- Consider adding security audit logging for all file operations

**Next Review**: After implementing fixes, re-audit to verify all vulnerabilities are addressed
