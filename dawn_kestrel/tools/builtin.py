"""OpenCode Python - Built-in tools (bash, read, write, grep, glob)"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, List

from pydantic import BaseModel, Field, AliasChoices

from dawn_kestrel.tools.framework import Tool, ToolContext, ToolResult
from dawn_kestrel.tools.prompts import get_prompt
from dawn_kestrel.core.security import (
    validate_command,
    validate_pattern,
    ALLOWED_SHELL_COMMANDS,
    ALLOWED_SEARCH_TOOLS,
    SecurityError,
)

logger = logging.getLogger(__name__)


class BashToolArgs(BaseModel):
    """Arguments for Bash tool"""

    command: str = Field(description="Command to execute")
    description: Optional[str] = Field(default=None, description="Description for UI")
    workdir: Optional[str] = Field(default=".", description="Working directory")


class BashTool(Tool):
    id = "bash"
    description = get_prompt("bash")
    category = "execution"
    tags = ["shell", "command-line", "git"]
    dependencies = ["read", "write", "glob", "grep"]
    examples = ["Execute shell command", "Run git status"]

    def parameters(self) -> Dict[str, Any]:
        """Get JSON schema for bash tool parameters"""
        return BashToolArgs.model_json_schema()

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Execute a bash command

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with output, title, and metadata
        """
        validated = BashToolArgs(**args)
        logger.info(f"Executing: {validated.command}")

        work_dir = validated.workdir if validated.workdir != "." else "."

        try:
            tokens = validate_command(validated.command, allowed_commands=ALLOWED_SHELL_COMMANDS)

            result = subprocess.run(
                tokens,
                shell=False,
                cwd=work_dir,
                capture_output=True,
                text=True,
                check=False,
            )

            output = result.stdout
            stderr = result.stderr

            if stderr:
                full_output = f"{output}\n[Stderr]\n{stderr}"
            else:
                full_output = output

            return ToolResult(
                title=validated.description or validated.command,
                output=full_output,
                metadata={
                    "exit_code": result.returncode,
                    "description": validated.description,
                },
            )

        except SecurityError as e:
            logger.warning(f"Command blocked by security policy: {e}")
            return ToolResult(
                title=f"Security Error: {validated.command}",
                output=f"Command rejected by security policy: {e}",
                metadata={"error": str(e), "security_error": True},
            )
        except Exception as e:
            logger.error(f"Bash tool failed: {e}")
            return ToolResult(
                title=f"Error: {validated.command}",
                output=str(e),
                metadata={"error": str(e)},
            )


class ReadToolArgs(BaseModel):
    """Arguments for Read tool - accepts both camelCase and snake_case parameter names."""

    filePath: str = Field(
        validation_alias=AliasChoices("filePath", "file_path"),
        description="Path to file (relative to project)",
    )
    limit: Optional[int] = Field(default=2000, description="Max lines to read")
    offset: Optional[int] = Field(default=0, description="Line number to start from")


class ReadTool(Tool):
    """Read file contents"""

    id = "read"
    description = get_prompt("read")

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Read a file

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with file content
        """
        # Validate args using Pydantic model
        validated = ReadToolArgs(**args)
        file_path = validated.filePath

        if not file_path:
            return ToolResult(
                title="No file specified",
                output="",
                metadata={"error": "File path is required"},
            )

        # Handle Optional[int] fields with proper type checks
        limit = validated.limit if isinstance(validated.limit, int) else 2000
        offset = validated.offset if isinstance(validated.offset, int) else 0

        try:
            full_path = Path(file_path)
            if not full_path.exists():
                return ToolResult(
                    title="File not found",
                    output="",
                    metadata={"path": str(file_path), "error": "File not found"},
                )

            # Read file content
            with open(full_path, "r") as f:
                all_lines = f.readlines()

            # Apply offset/limit
            start_line = max(0, offset - 1)
            end_line = min(start_line + limit, len(all_lines))
            lines = all_lines[start_line:end_line]
            content = "".join(lines)

            metadata = {
                "path": str(file_path),
                "lines_read": len(lines),
                "start_line": start_line + 1,
                "end_line": end_line,
            }

            return ToolResult(
                title=f"Read: {file_path}",
                output=content,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"Read tool failed: {e}")
            return ToolResult(
                title=f"Error reading: {file_path}",
                output=str(e),
                metadata={"error": str(e)},
            )


class WriteToolArgs(BaseModel):
    """Arguments for Write tool - accepts both camelCase and snake_case parameter names."""

    filePath: str = Field(
        validation_alias=AliasChoices("filePath", "file_path"),
        description="Path to file (relative to project)",
    )
    content: str = Field(description="Content to write")
    create: bool = Field(default=False, description="Create parent directories if needed")


class WriteTool(Tool):
    """Write content to files"""

    id = "write"
    description = get_prompt("write")

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Write content to a file

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with operation result
        """
        # Validate args using Pydantic model
        validated = WriteToolArgs(**args)
        file_path = validated.filePath
        content = validated.content
        create_dirs = validated.create

        try:
            full_path = Path(file_path)

            # Create directories if needed
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            with open(full_path, "w") as f:
                f.write(content)

            return ToolResult(
                title=f"Write: {file_path}",
                output=f"Wrote {len(content)} bytes",
                metadata={"path": str(full_path), "bytes": len(content)},
            )

        except Exception as e:
            logger.error(f"Write tool failed: {e}")
            return ToolResult(
                title=f"Error writing: {file_path}",
                output=str(e),
                metadata={"error": str(e)},
            )


class GrepToolArgs(BaseModel):
    """Arguments for Grep tool"""

    pattern: str = Field(description="Regex pattern to search")
    include: Optional[str] = Field(default="*", description="Glob pattern for files")
    max_results: int = Field(default=100, description="Max results to return")


class GrepTool(Tool):
    """Search file contents using regex patterns"""

    id = "grep"
    description = get_prompt("grep")

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Search for patterns in files

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with search results
        """
        # Validate args using Pydantic model
        validated = GrepToolArgs(**args)
        query = validated.pattern
        file_pattern = validated.include
        max_results = validated.max_results

        if not query:
            return ToolResult(
                title="No query",
                output="",
                metadata={"error": "Query is required"},
            )

        logger.info(f"Searching: {query}")

        try:
            validate_pattern(query, max_length=1000)

            file_pattern_str = file_pattern if file_pattern is not None else "*"
            cmd = ["rg", "-e", query, file_pattern_str]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )

            output = result.stdout.strip()
            lines = output.split("\n")[:max_results]

            return ToolResult(
                title=f"Grep: {query}",
                output="\n".join(lines),
                metadata={"matches": len(lines)},
            )

        except SecurityError as e:
            logger.warning(f"Pattern blocked by security policy: {e}")
            return ToolResult(
                title=f"Security Error: {query}",
                output=f"Pattern rejected by security policy: {e}",
                metadata={"error": str(e), "security_error": True},
            )
        except Exception as e:
            logger.error(f"Grep tool failed: {e}")
            return ToolResult(
                title=f"Error searching: {query}",
                output=str(e),
                metadata={"error": str(e)},
            )


class GlobToolArgs(BaseModel):
    """Arguments for Glob tool"""

    pattern: str = Field(description="Glob pattern")
    max_results: int = Field(default=100, description="Max results to return")


class GlobTool(Tool):
    """Find files using glob patterns"""

    id = "glob"
    description = get_prompt("glob")

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Find files matching glob patterns

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with matching files
        """
        # Validate args using Pydantic model
        validated = GlobToolArgs(**args)
        pattern = validated.pattern
        max_results = validated.max_results

        if not pattern:
            return ToolResult(
                title="No pattern",
                output="",
                metadata={"error": "Pattern is required"},
            )

        logger.info(f"Finding: {pattern}")

        try:
            validate_pattern(pattern, max_length=500)

            pattern_str = pattern if isinstance(pattern, str) else "*"
            cmd = ["rg", "--files", "--glob", pattern_str]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                shell=False,
            )

            output = result.stdout.strip()
            lines = output.split("\n")[:max_results]

            return ToolResult(
                title=f"Glob: {pattern}",
                output="\n".join(lines),
                metadata={"matches": len(lines)},
            )

        except SecurityError as e:
            logger.warning(f"Pattern blocked by security policy: {e}")
            return ToolResult(
                title=f"Security Error: {pattern}",
                output=f"Pattern rejected by security policy: {e}",
                metadata={"error": str(e), "security_error": True},
            )
        except Exception as e:
            logger.error(f"Glob tool failed: {e}")
            return ToolResult(
                title=f"Error finding: {pattern}",
                output=str(e),
                metadata={"error": str(e)},
            )

        logger.info(f"Finding: {pattern}")

        try:
            pattern_str: str = pattern if isinstance(pattern, str) else "*"
            cmd = ["rg", "--files", "--glob", pattern_str]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
            )

            output = result.stdout.strip()
            lines = output.split("\n")[:max_results]

            return ToolResult(
                title=f"Glob: {pattern}",
                output="\n".join(lines),
                metadata={"matches": len(lines)},
            )

        except Exception as e:
            logger.error(f"Glob tool failed: {e}")
            return ToolResult(
                title=f"Error finding: {pattern}",
                output=str(e),
                metadata={"error": str(e)},
            )


class ASTGrepToolArgs(BaseModel):
    """Arguments for AST Grep tool"""

    pattern: str = Field(description="AST pattern to search")
    language: str = Field(
        default="python", description="Language (python, javascript, typescript, etc.)"
    )
    paths: Optional[List[str]] = Field(default=None, description="Specific file paths to search")


class ASTGrepTool(Tool):
    """Search code using AST patterns via ast-grep"""

    id = "ast_grep_search"
    description = "Search code using AST patterns (ast-grep) for structural code matching"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Search for AST patterns in code

        Args:
            args: Raw tool arguments (will be validated)
            ctx: Tool execution context

        Returns:
            ToolResult with search results in format: file_path:line_number:code
        """
        # Validate args using Pydantic model
        validated = ASTGrepToolArgs(**args)
        pattern = validated.pattern
        language = validated.language
        paths = validated.paths

        if not pattern:
            return ToolResult(
                title="No pattern",
                output="",
                metadata={"error": "Pattern is required"},
            )

        logger.info(f"AST grep searching: {pattern} ({language})")

        try:
            validate_pattern(pattern, max_length=500)

            cmd = ["ast-grep", "run", "--pattern", pattern, "--lang", language]
            if paths:
                cmd.extend(paths)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
                shell=False,
            )

            if result.returncode != 0 and result.stderr:
                if "error" in result.stderr.lower() or "not found" in result.stderr.lower():
                    logger.warning(f"AST grep tool issue: {result.stderr}")

            output = result.stdout.strip()

            return ToolResult(
                title=f"AST Grep: {pattern}",
                output=output,
                metadata={
                    "language": language,
                    "matches": len(output.split("\n")) if output else 0,
                },
            )

        except SecurityError as e:
            logger.warning(f"Pattern blocked by security policy: {e}")
            return ToolResult(
                title=f"Security Error: {pattern}",
                output=f"Pattern rejected by security policy: {e}",
                metadata={"error": str(e), "security_error": True},
            )
        except subprocess.TimeoutExpired:
            logger.warning(f"AST grep search timed out: {pattern}")
            return ToolResult(
                title=f"AST Grep timeout: {pattern}",
                output="",
                metadata={"error": "timeout"},
            )
        except FileNotFoundError:
            logger.warning("ast-grep tool not found")
            return ToolResult(
                title="AST Grep not available",
                output="ast-grep tool not found in PATH",
                metadata={"error": "tool_not_found"},
            )
        except Exception as e:
            logger.error(f"AST grep tool failed: {e}")
            return ToolResult(
                title=f"Error in AST grep: {pattern}",
                output=str(e),
                metadata={"error": str(e)},
            )

        logger.info(f"AST grep searching: {pattern} ({language})")

        try:
            cmd = ["ast-grep", "run", "--pattern", pattern, "--lang", language]
            if paths:
                cmd.extend(paths)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )

            if result.returncode != 0 and result.stderr:
                # Non-zero exit could be "no matches", so check for actual errors
                if "error" in result.stderr.lower() or "not found" in result.stderr.lower():
                    logger.warning(f"AST grep tool issue: {result.stderr}")

            output = result.stdout.strip()

            return ToolResult(
                title=f"AST Grep: {pattern}",
                output=output,
                metadata={
                    "language": language,
                    "matches": len(output.split("\n")) if output else 0,
                },
            )

        except subprocess.TimeoutExpired:
            logger.warning(f"AST grep search timed out: {pattern}")
            return ToolResult(
                title=f"AST Grep timeout: {pattern}",
                output="",
                metadata={"error": "timeout"},
            )
        except FileNotFoundError:
            logger.warning("ast-grep tool not found")
            return ToolResult(
                title="AST Grep not available",
                output="ast-grep tool not found in PATH",
                metadata={"error": "tool_not_found"},
            )
        except Exception as e:
            logger.error(f"AST grep tool failed: {e}")
            return ToolResult(
                title=f"Error in AST grep: {pattern}",
                output=str(e),
                metadata={"error": str(e)},
            )
