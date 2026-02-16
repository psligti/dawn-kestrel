"""Input validation utilities for security.

Provides functions to validate and sanitize user input to prevent:
- Command injection
- Path traversal
- Pattern injection attacks

All validation functions raise SecurityError on validation failure.
"""

from __future__ import annotations

import re
import shlex
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Set, List, TypeVar

# ParamSpec was added in Python 3.10
try:
    from typing import ParamSpec
except ImportError:
    from typing_extensions import ParamSpec


class SecurityError(Exception):
    """Raised when input validation fails."""

    pass


def safe_path(path_str: str, base_dir: Path | None = None, allow_absolute: bool = False) -> Path:
    """Validate and normalize a file path to prevent path traversal.

    Args:
        path_str: User-provided path string
        base_dir: Base directory to restrict paths to (default: current working directory)
        allow_absolute: Whether to allow absolute paths (default: False)

    Returns:
        Normalized Path object

    Raises:
        SecurityError: If path contains traversal attempts or invalid characters
        ValueError: If path is outside base_dir when base_dir is specified

    Examples:
        >>> safe_path("file.txt")
        PosixPath('file.txt')

        >>> safe_path("../etc/passwd")  # Raises SecurityError

        >>> safe_path("/etc/passwd")  # Raises SecurityError unless allow_absolute=True
    """
    if not path_str:
        raise SecurityError("Path cannot be empty")

    # Convert to Path
    path = Path(path_str)

    # Check for path traversal sequences
    if ".." in path_str or "\\.." in path_str:
        raise SecurityError(f"Path traversal detected: {path_str}")

    # Check for null bytes
    if "\x00" in path_str:
        raise SecurityError(f"Null byte detected in path: {path_str}")

    # Reject absolute paths unless explicitly allowed
    if path.is_absolute() and not allow_absolute:
        raise SecurityError(f"Absolute path not allowed: {path_str}")

    # Resolve symlinks and normalize
    try:
        resolved = path.resolve(strict=False)
    except (OSError, RuntimeError) as e:
        raise SecurityError(f"Invalid path: {path_str}") from e

    # Restrict to base directory if specified
    if base_dir:
        base_resolved = base_dir.resolve()
        try:
            resolved.relative_to(base_resolved)
        except ValueError as e:
            raise SecurityError(f"Path outside base directory: {path_str} not in {base_dir}") from e

    return resolved


def validate_command(command: str, allowed_commands: Set[str] | None = None) -> List[str]:
    """Validate a shell command to prevent command injection.

    Parses the command using shlex to extract tokens and validates against
    an allowlist of permitted commands.

    Args:
        command: Command string to validate
        allowed_commands: Set of allowed command names (e.g., {"git", "ls", "cat"})
                         If None, only allows alphanumeric commands

    Returns:
        List of command tokens for safe execution

    Raises:
        SecurityError: If command contains injection attempts or disallowed commands

    Examples:
        >>> validate_command("git status")
        ['git', 'status']

        >>> validate_command("git; rm -rf /")  # Raises SecurityError

        >>> validate_command("ls | cat file.txt")  # Raises SecurityError (pipe)
    """
    if not command:
        raise SecurityError("Command cannot be empty")

    injection_patterns = [
        ";",
        "&",
        "|",
        "&&",
        "||",
        ">",
        "<",
        "`",
        "$(",
        "$`",
        "\n",
        "\r",
    ]

    for pattern in injection_patterns:
        if pattern in command:
            raise SecurityError(
                f"Shell metacharacter '{pattern}' not allowed in command: {command}"
            )

    try:
        tokens = shlex.split(command)
    except ValueError as e:
        raise SecurityError(f"Invalid command syntax: {command}") from e

    if not tokens:
        raise SecurityError("Command produced no tokens")

    cmd_name = tokens[0]

    if allowed_commands is None:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", cmd_name):
            raise SecurityError(
                f"Command name must be alphanumeric: {cmd_name}. "
                "Use allowed_commands to explicitly permit specific commands."
            )
    else:
        if cmd_name not in allowed_commands:
            raise SecurityError(
                f"Command not in allowlist: {cmd_name}. "
                f"Allowed: {', '.join(sorted(allowed_commands))}"
            )

    for arg in tokens[1:]:
        if "--" in arg and any(c in arg for c in [";", "|", "&", "$"]):
            raise SecurityError(f"Suspicious argument detected: {arg}")

    return tokens


def validate_pattern(pattern: str, max_length: int = 1000) -> str:
    """Validate a regex or glob pattern to prevent ReDoS and injection.

    Args:
        pattern: Pattern string to validate
        max_length: Maximum allowed pattern length

    Returns:
        Validated pattern string

    Raises:
        SecurityError: If pattern contains dangerous constructs or is too long

    Examples:
        >>> validate_pattern(".*test.*")
        '.*test.*'

        >>> validate_pattern("(?R)")  # Raises SecurityError (recursive pattern)

        >>> validate_pattern("a" * 2000)  # Raises SecurityError (too long)
    """
    if not pattern:
        raise SecurityError("Pattern cannot be empty")

    if len(pattern) > max_length:
        raise SecurityError(f"Pattern exceeds maximum length of {max_length}: {len(pattern)}")

    literal_dangerous = [
        "(?R)",
        "(?0)",
        "(.*?){100,}",
        "(.+?){100,}",
        "){100,}",
        "){50,}",
    ]
    for dangerous in literal_dangerous:
        if dangerous in pattern:
            raise SecurityError(f"Pattern contains dangerous construct (ReDoS risk): {pattern}")

    if "\x00" in pattern:
        raise SecurityError(f"Null byte detected in pattern")

    return pattern


def validate_git_hash(hash_value: str) -> str:
    """Validate a Git commit hash.

    Git hashes must be 40 hexadecimal characters (SHA-1) or 64 (SHA-256).

    Args:
        hash_value: Git hash string to validate

    Returns:
        Validated hash string

    Raises:
        SecurityError: If hash is invalid

    Examples:
        >>> validate_git_hash("a1b2c3d4e5f6...")
        'a1b2c3d4e5f6...'

        >>> validate_git_hash("../../../etc/passwd")  # Raises SecurityError
    """
    if not hash_value:
        raise SecurityError("Git hash cannot be empty")

    hash_value = hash_value.strip()

    if ".." in hash_value or "/" in hash_value or "\\" in hash_value:
        raise SecurityError(f"Path traversal detected in git hash: {hash_value}")

    if len(hash_value) not in (40, 64) or not re.match(r"^[0-9a-f]+$", hash_value):
        if len(hash_value) < 7 or not re.match(r"^[0-9a-f]+$", hash_value):
            raise SecurityError(f"Invalid git hash format: {hash_value}")

    return hash_value


def validate_url(url: str, allow_https_only: bool = True, max_length: int = 2048) -> str:
    """Validate a URL to prevent SSRF attacks.

    Args:
        url: URL string to validate
        allow_https_only: Only allow HTTPS URLs (default: True)
        max_length: Maximum URL length

    Returns:
        Validated URL string

    Raises:
        SecurityError: If URL is invalid or potentially malicious

    Examples:
        >>> validate_url("https://example.com/api")
        'https://example.com/api'

        >>> validate_url("http://localhost/admin")  # Raises SecurityError

        >>> validate_url("file:///etc/passwd")  # Raises SecurityError
    """
    if not url:
        raise SecurityError("URL cannot be empty")

    if len(url) > max_length:
        raise SecurityError(f"URL exceeds maximum length of {max_length}")

    dangerous_patterns = [
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",
        "file:///",
        "ftp://",
        "file:\\\\",
        "ftp:\\\\",
    ]

    url_lower = url.lower()
    for pattern in dangerous_patterns:
        if pattern in url_lower:
            raise SecurityError(f"URL contains blocked pattern (SSRF risk): {url}")

    if allow_https_only and not url.startswith(("https://", "HTTPS://")):
        raise SecurityError(f"Only HTTPS URLs allowed: {url}")

    return url


# Decorators for input validation
P = ParamSpec("P")
R = TypeVar("R")


def validate_path_param(param_name: str, base_dir: Path | None = None) -> Callable[..., Any]:
    """Decorator to validate a function parameter as a safe path.

    Usage:
        @validate_path_param("file_path", base_dir=Path("/safe/dir"))
        def process_file(file_path: str) -> None:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            param_value = kwargs.get(param_name)
            if param_value is None:
                raise SecurityError(f"Parameter '{param_name}' not found")

            safe_path(str(param_value), base_dir=base_dir)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_command_param(
    param_name: str, allowed_commands: Set[str] | None = None
) -> Callable[..., Any]:
    """Decorator to validate a function parameter as a safe command.

    Usage:
        @validate_command_param("cmd", allowed_commands={"git", "hg"})
        def run_cmd(cmd: str) -> None:
            ...
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            param_value = kwargs.get(param_name)
            if param_value is None:
                raise SecurityError(f"Parameter '{param_name}' not found")

            validate_command(str(param_value), allowed_commands=allowed_commands)

            return func(*args, **kwargs)

        return wrapper

    return decorator


# Pre-defined allowlists for common operations
ALLOWED_GIT_COMMANDS = {
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

ALLOWED_SEARCH_TOOLS = {
    "rg",  # ripgrep
    "grep",
    "ast-grep",
    "find",
}

ALLOWED_SHELL_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
}
