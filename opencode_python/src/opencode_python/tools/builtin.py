"""OpenCode Python - Built-in tools (bash, read, write, grep, glob)"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any

from pydantic import BaseModel, Field

from opencode_python.tools.framework import Tool, ToolContext, ToolResult
from opencode_python.tools.prompts import get_prompt

logger = logging.getLogger(__name__)


class BashToolArgs(BaseModel):
    """Arguments for Bash tool"""
    command: str = Field(description="Command to execute")
    description: Optional[str] = Field(default=None, description="Description for UI")
    cwd: Optional[str] = Field(default=".", description="Working directory")


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

    async def execute(self, args: BashToolArgs, ctx: ToolContext) -> ToolResult:
        """Execute a bash command

        Args:
            args: BashToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with output, title, and metadata
        """
        logger.info(f"Executing: {args.command}")

        try:
            result = subprocess.run(
                [args.command],
                shell=True,
                cwd=ctx.session_id if args.cwd == "." else args.cwd,
                capture_output=True,
                text=True,
                check=True,
            )

            output = result.stdout
            stderr = result.stderr

            # Combine stdout and stderr
            if stderr:
                full_output = f"{output}\n[Stderr]\n{stderr}"
            else:
                full_output = output

            return ToolResult(
                title=args.description or args.command,
                output=full_output,
                metadata={
                    "exit_code": result.returncode,
                    "description": args.description,
                },
            )

        except Exception as e:
            logger.error(f"Bash tool failed: {e}")
            return ToolResult(
                title=f"Error: {args.command}",
                output=str(e),
                metadata={"error": str(e)},
            )


class ReadToolArgs(BaseModel):
    """Arguments for Read tool"""
    file: str = Field(description="Path to file (relative to project)")
    limit: Optional[int] = Field(default=2000, description="Max lines to read")
    offset: Optional[int] = Field(default=0, description="Line number to start from")


class ReadTool(Tool):
    """Read file contents"""

    id = "read"
    description = get_prompt("read")

    async def execute(self, args: ReadToolArgs, ctx: ToolContext) -> ToolResult:
        """Read a file

        Args:
            args: ReadToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with file content
        """
        file_path = args.file

        if not file_path:
            return ToolResult(
                title="No file specified",
                output="",
                metadata={"error": "File path is required"},
            )

        limit = args.limit
        offset = args.offset

        try:
            full_path = Path(ctx.session_id if ctx.session_id.startswith("/") else "") / file_path
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
    """Arguments for Write tool"""
    file: str = Field(description="Path to file (relative to project)")
    content: str = Field(description="Content to write")
    create: bool = Field(default=False, description="Create parent directories if needed")


class WriteTool(Tool):
    """Write content to files"""

    id = "write"
    description = get_prompt("write")

    async def execute(self, args: WriteToolArgs, ctx: ToolContext) -> ToolResult:
        """Write content to a file

        Args:
            args: WriteToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with operation result
        """
        file_path = args.file
        content = args.content
        create_dirs = args.create

        try:
            full_path = Path(ctx.session_id if ctx.session_id.startswith("/") else "") / file_path

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
    query: str = Field(description="Regex pattern to search")
    file_pattern: Optional[str] = Field(default="*", description="Glob pattern for files")
    max_results: int = Field(default=100, description="Max results to return")


class GrepTool(Tool):
    """Search file contents using regex patterns"""

    id = "grep"
    description = get_prompt("grep")

    async def execute(self, args: GrepToolArgs, ctx: ToolContext) -> ToolResult:
        """Search for patterns in files

        Args:
            args: GrepToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with search results
        """
        query = args.query
        file_pattern = args.file_pattern
        max_results = args.max_results

        if not query:
            return ToolResult(
                title="No query",
                output="",
                metadata={"error": "Query is required"},
            )

        logger.info(f"Searching: {query}")

        try:
            # Build ripgrep command
            cmd = ["ripgrep", "-e", query, file_pattern]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.returncode != 0:
                return ToolResult(
                    title="Search failed",
                    output=result.stderr,
                    metadata={"error": result.stderr},
                )

            output = result.stdout.strip()
            lines = output.split("\n")[:max_results]

            return ToolResult(
                title=f"Grep: {query}",
                output="\n".join(lines),
                metadata={"matches": len(lines)},
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

    async def execute(self, args: GlobToolArgs, ctx: ToolContext) -> ToolResult:
        """Find files matching glob patterns

        Args:
            args: GlobToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with matching files
        """
        pattern = args.pattern
        max_results = args.max_results

        if not pattern:
            return ToolResult(
                title="No pattern",
                output="",
                metadata={"error": "Pattern is required"},
            )

        logger.info(f"Finding: {pattern}")

        try:
            # Use ripgrep --files with glob
            cmd = ["ripgrep", "--glob", pattern]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.returncode != 0:
                return ToolResult(
                    title="Glob failed",
                    output=result.stderr,
                    metadata={"error": result.stderr},
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
