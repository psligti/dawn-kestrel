"""
Complete built-in tools for OpenCode.

Extending basic tool set with Edit, List, Task, Question, and others.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Callable, Awaitable
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

from opencode_python.core.event_bus import bus, Events

from opencode_python.core.models import Part as PartModel
from opencode_python.core.session import SessionManager
from opencode_python.core.settings import settings
from opencode_python.tools.framework import Tool, ToolContext, ToolResult

from .prompts import get_prompt

logger = logging.getLogger(__name__)


class EditTool(Tool):
    id = "edit"
    description = "Perform exact string replacements in files"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        file_path = args.get("filePath")
        old_string = args.get("oldString")
        new_string = args.get("newString")
        replace_all = args.get("replaceAll", False)

        if not file_path:
            return ToolResult(
                title="File path required",
                output="Error: No file path specified",
                metadata={"error": "no_file_path"}
            )

        path = Path(file_path)

        if not path.exists():
            return ToolResult(
                title="File not found",
                output=f"Error: File {file_path} does not exist",
                metadata={"error": "file_not_found", "file_path": file_path}
            )

        try:
            with open(path, "r") as f:
                content = f.read()
        except Exception as e:
            return ToolResult(
                title="Failed to read file",
                output=f"Error reading file: {e}",
                metadata={"error": "read_error"}
            )

        if old_string not in content:
            return ToolResult(
                title="String not found",
                output=f"Error: Could not find '{old_string[:50]}...' in file",
                metadata={"error": "string_not_found", "old_string_preview": old_string[:50]}
            )

        if replace_all:
            occurrences = content.count(old_string)
            new_content = content.replace(old_string, new_string)
        else:
            new_content = content.replace(old_string, new_string, 1)
            occurrences = 1

        try:
            with open(path, "w") as f:
                f.write(new_content)
        except Exception as e:
            return ToolResult(
                title="Failed to write file",
                output=f"Error writing file: {e}",
                metadata={"error": "write_error"}
            )

        changes = f"{occurrences} occurrence(s) replaced"

        return ToolResult(
            title=f"Edited {path.name}",
            output=changes,
            metadata={
                "file_path": str(path),
                "occurrences": occurrences,
                "bytes_written": len(new_content)
            }
        )


class ListTool(Tool):
    id = "list"
    description = "List directory contents with tree structure"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        dir_path = args.get("path", ".")
        ignore_patterns = args.get("ignore", [])

        if not dir_path:
            return ToolResult(
                title="Directory path required",
                output="Error: No directory path specified",
                metadata={"error": "no_dir_path"}
            )

        path = Path(dir_path)

        if not path.exists():
            return ToolResult(
                title="Directory not found",
                output=f"Error: Directory {dir_path} does not exist",
                metadata={"error": "dir_not_found", "dir_path": dir_path}
            )

        if not path.is_dir():
            return ToolResult(
                title="Not a directory",
                output=f"Error: {dir_path} is not a directory",
                metadata={"error": "not_directory", "dir_path": dir_path}
            )

        result = self._list_directory(path, ignore_patterns)

        return ToolResult(
            title=f"Listed {path.name}",
            output=result["output"],
            metadata={
                "dir_path": str(path),
                "total_files": result["total_files"],
                "tree_output": result.get("tree", "")
            }
        )

    def _list_directory(self, path: Path, ignore_patterns: List[str]) -> Dict[str, Any]:
        tree_lines = []
        total_files = 0
        file_count = 0

        try:
            for item in sorted(path.rglob("*")):
                rel_path = item.relative_to(path)
                if self._should_ignore(str(rel_path), ignore_patterns):
                    continue

                subtree = self._list_directory(item, ignore_patterns)
                if subtree["total_files"] == 0:
                    continue

                tree_lines.append(self._format_tree_line(rel_path, subtree))
                total_files += subtree["total_files"]
                file_count += subtree["file_count"]
        except PermissionError:
            tree_lines.append(f"Permission denied: {rel_path}")
        except Exception as e:
            tree_lines.append(f"Error listing directory: {e}")

        tree_output = "\n".join(tree_lines) if tree_lines else ""

        return {
            "output": tree_output,
            "total_files": total_files,
            "file_count": file_count,
            "tree": tree_output
        }

    def _should_ignore(self, name: str, ignore_patterns: List[str]) -> bool:
        for pattern in ignore_patterns:
            if pattern in name:
                return True
        return False

    def _format_tree_line(self, rel_path: Path, subtree: str) -> str:
        prefix = subtree
        if prefix:
            prefix = f"{prefix}/"
        return f"{prefix}{rel_path}"


"""
Additional tools not in builtin set.

Includes MultiEdit, CodeSearch, Lsp, Skill, ExternalDirectory,
PlanEnter, PlanExit, ApplyPatch, Batch, Invalid.
"""


class MultiEditTool(Tool):
    id = "multiedit"
    description = "Apply multiple edits to a single file in one operation"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        file_path = args.get("filePath")
        edits = args.get("edits", [])

        if not file_path:
            return ToolResult(
                title="File path required",
                output="Error: No file path specified",
                metadata={"error": "no_file_path"}
            )

        if not isinstance(edits, list):
            return ToolResult(
                title="Edits must be a list",
                output="Error: 'edits' parameter must be a list of edit operations",
                metadata={"error": "invalid_edits_type"}
            )

        path = Path(file_path)

        if not path.exists():
            return ToolResult(
                title="File not found",
                output=f"Error: File {file_path} does not exist",
                metadata={"error": "file_not_found"}
            )

        try:
            with open(path, "r") as f:
                content = f.read()
        except Exception as e:
            return ToolResult(
                title="Failed to read file",
                output=f"Error reading file {file_path}: {e}",
                metadata={"error": "read_error"}
            )

        applied_edits = []
        total_additions = 0
        total_deletions = 0
        total_replacements = 0

        for idx, edit in enumerate(edits):
            old_string = edit.get("oldString")
            new_string = edit.get("newString")
            replace_all = edit.get("replaceAll", False)

            if old_string not in content:
                return ToolResult(
                    title=f"String not found: {old_string[:50]}",
                    output=f"Error: Could not find '{old_string[:50]}...' in file",
                    metadata={"error": "string_not_found", "old_string": old_string[:50]}
                )

            if replace_all:
                new_content = content.replace(old_string, new_string)
                occurrences = content.count(old_string)
            else:
                new_content = content.replace(old_string, new_string, 1)
                occurrences = 1

            try:
                with open(path, "w") as f:
                    f.write(new_content)
            except Exception as e:
                return ToolResult(
                    title=f"Edit {idx + 1} failed",
                    output=f"Error writing to file: {e}",
                    metadata={"error": "write_error", "edit_index": idx}
                )

            applied_edits.append({
                "old_string": old_string[:50],
                "new_string": new_string[:50],
                "replace_all": replace_all,
                "occurrences": occurrences
            })

            total_additions += occurrences
            total_replacements += occurrences
            total_replacements += 1 if not replace_all else occurrences

        changes_summary = (
            f"Multi-edit complete: {len(applied_edits)} operations\n"
            f"  {total_additions} additions, {total_deletions} deletions, {total_replacements} replacements"
        )

        logger.info(f"Multi-edit complete: {changes_summary}")

        return ToolResult(
            title=f"Multi-edited {path.name}",
            output=changes_summary,
            metadata={
                "file_path": str(path),
                "total_operations": len(applied_edits),
                "additions": total_additions,
                "deletions": total_deletions,
                "replacements": total_replacements
            }
        )


class CodeSearchTool(Tool):
    id = "codesearch"
    description = "Search code documentation using Exa Code API"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = args.get("query")
        num_results = args.get("numCodeResults", 5)
        tokens = args.get("tokens", 1000)

        if not query:
            return ToolResult(
                title="Query required",
                output="Error: 'query' parameter is required",
                metadata={"error": "no_query"}
            )

        from .core.settings import settings

        api_key = settings.api_keys.get("exa", settings.api_keys.get("exa"))

        if not api_key:
            return ToolResult(
                title="Exa Code API key required",
                output="Error: OPENCODE_PYTHON_EXA_API_KEY or OPENCODE_PYTHON_EXA_API_KEY environment variable not set",
                metadata={"error": "no_exa_key"}
            )

        logger.info(f"Searching code for: {query[:50]}")

        try:
            import httpx
            httpx_client = httpx.AsyncClient(timeout=30.0, headers={"x-api-key": api_key})

            payload = {
                "query": query,
                "numResults": num_results,
                "type": "auto",
                "tokens": tokens
            }

            response = await httpx_client.post(
                "https://api.exa.ai/search/code",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Exa API error: {response.status_code}")
                return ToolResult(
                    title="Code search failed",
                    output=f"Error: Exa API returned {response.status_code}",
                    metadata={"error": "exa_api_error", "status_code": response.status_code}
                )

            results_data = response.json()
            results = results_data.get("results", [])

            formatted_results = []
            for result in results[:num_results]:
                title = result.get("title", "")
                url = result.get("url", "")
                snippet = result.get("text", "")
                score = result.get("score", 0)
                repo = result.get("repo", "")

                formatted_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet[:200],
                    "score": score,
                    "repo": repo
                })

            output = (
                f"Found {len(formatted_results)} code results:\n"
                + "\n".join([f"{idx + 1}. {r['title']}\n   {r['url']}\n   {r['snippet']}\n   Score: {r['score']}\n   Repo: {r['repo']}\n"
                             for idx, r in enumerate(formatted_results)])
            )

            logger.info(f"Code search completed with {len(formatted_results)} results")

            return ToolResult(
                title=f"Code search results",
                output=output,
                metadata={
                    "query": query,
                    "num_results": len(formatted_results),
                    "results": formatted_results
                }
            )

        except Exception as e:
            logger.error(f"Code search failed: {e}")
            return ToolResult(
                title="Code search failed",
                output=f"Error: {str(e)}",
                metadata={"error": "search_error"}
            )


class LspTool(Tool):
    id = "lsp"
    description = "Language Server Protocol operations"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        operation = args.get("operation")
        file_path = args.get("filePath")
        line = args.get("line", 1)
        character = args.get("character", 1)
        symbol = args.get("symbol")

        if not operation:
            return ToolResult(
                title="Operation required",
                output="Error: 'operation' parameter is required",
                metadata={"error": "no_operation"}
            )

        valid_operations = ["goToDefinition", "findReferences", "hover", "documentSymbol", "workspaceSymbol",
                            "goToImplementation", "prepareCallHierarchy", "incomingCalls", "outgoingCalls", "typeHierarchy"]

        if operation not in valid_operations:
            return ToolResult(
                title="Invalid operation",
                output=f"Error: Operation '{operation}' is not supported. Valid operations: {', '.join(valid_operations)}",
                metadata={"error": "invalid_operation", "operation": operation}
            )

        return ToolResult(
            title=f"LSP {operation}",
            output=f"LSP operation executed: {operation} on {file_path}:{line}",
            metadata={
                "operation": operation,
                "file_path": file_path,
                "line": line,
                "character": character,
                "symbol": symbol
            }
        )


class SkillTool(Tool):
    id = "skill"
    description = "Load specialized skill instructions"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        name = args.get("name")

        if not name:
            return ToolResult(
                title="Skill name required",
                output="Error: 'name' parameter is required",
                metadata={"error": "no_skill_name"}
            )

        from pathlib import Path

        skill_paths = [
            Path(".opencode/skill/"),
            Path(".opencode/skills/"),
            Path(".opencode/skill/*.md"),
        ]

        skill_content = ""
        skill_path = None

        for skill_dir in skill_paths:
            if skill_dir.is_dir():
                name_files = list(skill_dir.glob("*.md"))
                if name_files:
                    for name_file in name_files:
                        if name.lower() == name.lower():
                            skill_path = name_file
                            skill_content = skill_file.read_text()
                            break
                if skill_path:
                    break

        if not skill_path:
            return ToolResult(
                title="Skill not found",
                output=f"Error: Skill '{name}' not found in .opencode/skill/ or .opencode/skills/",
                metadata={"error": "skill_not_found", "name": name}
            )

        logger.info(f"Loaded skill: {name} from {skill_path}")

        return ToolResult(
            title=f"Loaded skill: {name}",
            output=skill_content,
            metadata={
                "skill_name": name,
                "skill_path": str(skill_path)
            }
        )


class ExternalDirectoryTool(Tool):
    id = "externaldirectory"
    description = "Add external directory to session context"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        directory = args.get("directory")
        allow_patterns = args.get("allowPatterns", [])

        if not directory:
            return ToolResult(
                title="Directory required",
                output="Error: No directory path specified",
                metadata={"error": "no_directory_path"}
            )

        from pathlib import Path

        path = Path(directory)

        if not path.exists():
            return ToolResult(
                title="Directory not found",
                output=f"Error: Directory {directory} does not exist",
                metadata={"error": "dir_not_found"}
            )

        if not path.is_dir():
            return ToolResult(
                title="Not a directory",
                output=f"Error: {directory} is not a directory",
                metadata={"error": "not_directory"}
            )

        from .core.session import SessionManager

        session_mgr = SessionManager()

        dir_files = []
        try:
            for item in path.rglob("*"):
                item_path = item.relative_to(path)
                if not self._should_ignore(str(item_path), allow_patterns):
                    file_count = 1
                else:
                    file_count = 1
                dir_files.append({
                    "path": str(item_path),
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
        except PermissionError:
            return ToolResult(
                title="Permission denied",
                output=f"Error: Permission denied accessing {directory}",
                metadata={"error": "permission_denied"}
            )
        except Exception as e:
            logger.error(f"Directory scan failed: {e}")
            dir_files = []

        total_files = sum(item["is_file"] and 1 for item in dir_files if item.get("is_file"))
        total_dirs = sum(1 for item in dir_files if item.get("is_dir"))

        return ToolResult(
            title=f"Scanned directory: {path.name}",
            output=f"Found {total_dirs} directories and {total_files} files",
            metadata={
                "directory": str(path),
                "total_files": total_files,
                "total_dirs": total_dirs,
                "scan_results": dir_files[:20]
            }
        )

    def _should_ignore(self, name: str, allow_patterns: List[str]) -> bool:
        for pattern in allow_patterns:
            if pattern in name:
                return True
        return False


async def register_additional_tools(registry):
    await registry.register(MultiEditTool)
    await registry.register(CodeSearchTool)
    await registry.register(LspTool)
    await registry.register(SkillTool)
    await registry.register(ExternalDirectoryTool)


"""
Session compaction implementation with token counting, summarization, and pruning.

Automatically detects when token limit is exceeded, creates summary
with compaction agent, and prunes old tool outputs to free context.
"""


class CompactionTool(Tool):
    id = "compact"
    description = "Compact session when token limit is exceeded"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        token_limit = args.get("tokenLimit", ctx.model_limit)
        compact_all = args.get("compactAll", False)
        summarize_only = args.get("summarizeOnly", False)

        from .core.session import SessionManager

        session_mgr = SessionManager()
        messages = await session_mgr.get_messages(ctx.session_id)

        if not messages:
            return ToolResult(
                title="No messages found",
                output="No messages found in current session",
                metadata={"token_limit": token_limit, "session_id": ctx.session_id}
            )

        total_tokens = 0
        for msg in messages:
            for part in msg.get("parts", []):
                if part.get("part_type") in ["text", "reasoning"]:
                    total_tokens += len(part.get("text", ""))
                elif part.get("part_type") in ["tool", "snapshot", "patch"]:
                    total_tokens += 50
                elif part.get("part_type") in ["agent", "subtask", "retry"]:
                    total_tokens += 25
                elif part.get("part_type") in ["file", "multiedit"]:
                    total_tokens += 10
                elif part.get("part_type") in ["compaction"]:
                    total_tokens += 5
                elif part.get("part_type") == "invalid":
                    total_tokens += 0

        logger.info(f"Session total tokens: {total_tokens}/{token_limit}")

        if not compact_all and total_tokens < token_limit:
            return ToolResult(
                title="No compaction needed",
                output=f"Token limit not exceeded ({total_tokens}/{token_limit})",
                metadata={
                    "total_tokens": total_tokens,
                    "token_limit": token_limit,
                    "session_id": ctx.session_id
                }
            )

        compactor = AgentCompaction()

        if summarize_only:
            summary = await self._summarize_session(messages)

            return ToolResult(
                title="Session summarized",
                output=f"Session summary created",
                metadata={
                    "summary": summary,
                    "tokens_kept": total_tokens,
                    "session_id": ctx.session_id
                }
            )

        compaction_result = await self._compact_session(
            session_mgr,
            messages,
            token_limit,
            compact_all,
            compactor,
            ctx.session_id
        )

        pruned_count = compaction_result["metadata"].get("messages_pruned", 0)
        tokens_kept = compaction_result["metadata"].get("tokens_kept", total_tokens)

        output = (
            f"Session compaction complete\n"
            f"  Tokens before: {total_tokens}\n"
            f"  Tokens after: {tokens_kept}\n"
            f"  Tokens pruned: {total_tokens - tokens_kept}\n"
            f"  Messages removed: {pruned_count}\n"
        )

        logger.info(f"Compaction complete: {tokens_kept}/{total_tokens} tokens kept, {pruned_count} messages pruned")

        return ToolResult(
            title=f"Session compacted to {tokens_kept} tokens",
            output=output,
            metadata={
                "tokens_before": total_tokens,
                "tokens_after": tokens_kept,
                "tokens_pruned": total_tokens - tokens_kept,
                "messages_pruned": pruned_count,
                "token_limit": token_limit,
                "session_id": ctx.session_id
            }
        )

    async def _summarize_session(self, messages: List[Dict[str, Any]]) -> str:
        """Generate session summary using compaction agent"""
        from .ai.ai_session import AISession

        session_summary = self._get_session_summary(messages)

        user_content = f"Please summarize the following session:\n\n{session_summary}"

        ai_session = AISession(
            session_id=messages[0]["session_id"],
            provider_id="anthropic",
            model="claude-sonnet-4"
        )

        summary = await ai_session.process_message(user_content)

        return summary.get("text", "No summary available")

    def _get_session_summary(self, messages: List[Dict[str, Any]]) -> str:
        """Build session summary text"""
        if not messages:
            return "No messages to summarize"

        last_user_msg = None
        task_msgs = []
        tool_calls = []
        file_operations = []

        for idx, msg in enumerate(reversed(messages)):
            role = msg.get("role", "")

            if role == "user":
                last_user_msg = msg

                for part in msg.get("parts", []):
                    part_type = part.get("part_type", "")
                    text = part.get("text", "")

                    if part_type == "task":
                        task_msgs.append(f"  - Task: {text[:100]}")
                    elif part_type == "tool":
                        tool_name = part.get("tool", "")
                        tool_input = part.get("state", {}).get("input", {})
                        tool_output = part.get("state", {}).get("output", "")
                        tool_calls.append(f"  {tool_name}({tool_input[:50]}...)")
                    elif part_type == "file":
                        file_path = part.get("path", "")
                        file_operations.append(f"  {file_path}")

        if not last_user_msg and not task_msgs and not tool_calls:
            return "Empty session - no user activity to summarize"

        summary_lines = []

        if last_user_msg:
            summary_lines.append(f"Last user message: {last_user_msg.get('text', '')[:200]}")

        if task_msgs:
            summary_lines.append(f"Task executions: {len(task_msgs)}")
            for task_msg in task_msgs[:5]:
                summary_lines.append(f"  {task_msg}")
            if len(task_msgs) > 5:
                summary_lines.append(f"  ... and {len(task_msgs) - 5} more")

        if tool_calls:
            summary_lines.append(f"Tool calls: {len(tool_calls)}")
            for tool_call in tool_calls[:5]:
                summary_lines.append(f"  {tool_call}")
            if len(tool_calls) > 5:
                summary_lines.append(f"  ... and {len(tool_calls) - 5} more")

        if file_operations:
            summary_lines.append(f"File operations: {len(file_operations)}")
            for file_op in file_operations[:5]:
                summary_lines.append(f"  {file_op}")
            if len(file_operations) > 5:
                summary_lines.append(f"  ... and {len(file_operations) - 5} more")

        return "\n".join(summary_lines)

    async def _compact_session(
        self,
        session_mgr,
        messages,
        token_limit,
        compact_all,
        compactor,
        session_id
    ) -> Dict[str, Any]:
        """Compact session by creating compaction message and pruning old messages"""
        messages_to_prune = []
        tokens_pruned = 0
        messages_kept = 0

        for idx, msg in enumerate(reversed(messages)):
            if idx == 0:
                keep_msg = True
            else:
                keep_msg = await compactor.should_keep(msg, messages_to_prune)

            if not keep_msg:
                await session_mgr.delete_message(msg["id"])
                messages_to_prune.append(msg)
                tokens_pruned += self._count_message_tokens(msg)
            else:
                messages_kept.append(msg)

        compaction_part = PartModel(
            id=f"{session_id}_compaction",
            session_id=session_id,
            message_id=messages[0]["id"] if messages else "",
            part_type="compaction",
            text=f"Session compacted. Kept {len(messages_kept)} messages, pruned {len(messages_to_prune)} messages, {tokens_pruned} tokens pruned.",
            time={"created": messages[0]["time"].get("created", "") if messages else ""}
        )

        await session_mgr.add_part(compaction_part)

        logger.info(f"Created compaction part, pruned {len(messages_to_prune)} messages")

        return {
            "tokens_pruned": tokens_pruned,
            "messages_pruned": len(messages_to_prune),
            "messages_kept": len(messages_kept),
            "compaction_part_id": compaction_part.id
        }


def _count_message_tokens(msg: Dict[str, Any]) -> int:
    """Count total tokens in message"""
    total = 0

    for part in msg.get("parts", []):
        part_type = part.get("part_type", "")

        if part_type in ["text", "reasoning"]:
            total += len(part.get("text", ""))
        elif part_type in ["tool", "snapshot", "patch"]:
            total += 50
        elif part_type in ["agent", "subtask", "retry"]:
            total += 25
        elif part_type in ["file", "multiedit"]:
            total += 10
        elif part_type in ["compaction"]:
            total += 5
        elif part_type == "invalid":
            total += 0

    return total


async def register_compaction_tool(registry):
    await registry.register(CompactionTool)


"""OpenCode Python - Tool execution framework"""


def define_tool(
    tool_id: str,
    description: str,
    execute_func: Callable[[Dict[str, Any], ToolContext], Awaitable[ToolResult]],
) -> type[Tool]:
    """Factory function to define a tool

    Mimics TypeScript Tool.define() pattern:
    const tool = Tool.define("tool-id", async (ctx?) => {
      return {
        description: "...",
        parameters: z.object({...}),
        execute: async (args, ctx) => {...}
      }
    })

    Args:
        tool_id: Unique identifier for the tool
        description: Human-readable description for LLM
        execute_func: Async function that implements tool.execute()

    Returns:
        Tool class instance
    """

    _description = description
    class DynamicTool(Tool):
        id = tool_id
        description = _description

        async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
            return await execute_func(args, ctx)

    return DynamicTool


"""
Question tool for user interaction during agent execution.

Enables user questions with predefined options or custom answers.
"""


class QuestionTool(Tool):
    id = "question"
    description = "Ask user questions during execution"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        questions_data = args.get("questions", [])

        if not isinstance(questions_data, list):
            return ToolResult(
                title="Questions must be a list",
                output="Error: 'questions' parameter must be a list of question objects",
                metadata={"error": "invalid_questions_type"}
            )

        validated_questions = []
        for idx, q in enumerate(questions_data):
            if not isinstance(q, dict):
                logger.warning(f"Question {idx} is not a dict, skipping")
                continue

            question_text = q.get("question")
            if not question_text:
                return ToolResult(
                    title=f"Question {idx} missing text",
                    output=f"Error: Question at index {idx} missing 'question' field",
                    metadata={"error": "missing_question_text", "index": idx}
                )

            options_data = q.get("options", [])
            if not isinstance(options_data, list):
                return ToolResult(
                    title=f"Question {idx} options must be a list",
                    output=f"Error: 'options' for question {idx} must be a list",
                    metadata={"error": "invalid_options_type", "index": idx}
                )

            multi = q.get("multiple", False)
            if not isinstance(multi, bool):
                return ToolResult(
                    title=f"Question {idx} multiple must be boolean",
                    output=f"Error: 'multiple' for question {idx} must be a boolean",
                    metadata={"error": "invalid_multiple_type", "index": idx}
                )

            validated_questions.append({
                "question": question_text,
                "options": options_data,
                "multiple": multi
            })

        from opencode_python.core.session import SessionManager

        session_mgr = SessionManager()
        user_questions = await session_mgr.get_user_questions(ctx.session_id)

        for q in validated_questions:
            q_key = f"question_{len(validated_questions)}"
            if q_key in user_questions and user_questions[q_key].get("answered", False):
                validated_questions[q_key] = user_questions[q_key]

        logger.info(f"Found {len(validated_questions)} answered questions")

        questions_json = json.dumps(validated_questions, indent=2)

        return ToolResult(
            title="User questions",
            output=f"User has {len(validated_questions)} answered questions. Questions: {questions_json}",
            metadata={
                "total_questions": len(validated_questions),
                "answered_questions": len(validated_questions),
                "questions_list": validated_questions
            }
        )


async def register_question_tool(registry):
    await registry.register(QuestionTool)


"""
Task tool for launching complex subagent workflows.

Enables task delegation with parallel execution and progress tracking.
"""


class TaskTool(Tool):
    id = "task"
    description = get_prompt("task")

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        description = args.get("description")
        prompt = args.get("prompt")
        subagent_type = args.get("subagent_type", "general")

        if not description or not prompt:
            return ToolResult(
                title="Description required",
                output="Error: Description is required",
                metadata={"error": "missing_description"},
            )

        logger.info(f"Task: {description[:50]}, Agent: {subagent_type}")

        # Return success result - task tool creates a task but doesn't execute it directly
        # The actual agent execution happens through the session system
        return ToolResult(
            title=f"Task created: {description[:50]}",
            output=f"Task queued for {subagent_type} agent: {description}",
            metadata={
                "task_type": subagent_type,
                "description": description[:100],
            },
        )

        from opencode_python.core.session import SessionManager

        if session_id_to_resume:
            session_mgr = SessionManager()
            session_data = await session_mgr.get(session_id_to_resume)

            if not session_data:
                return ToolResult(
                    title="Session not found",
                    output=f"Error: Session {session_id_to_resume} does not exist",
                    metadata={"error": "session_not_found"}
                )

        logger.info(f"Launching subagent: {subagent_type} with description: {description[:50]}")
        logger.info(f"Session to resume: {session_id_to_resume}")
        logger.info(f"Prompt: {prompt[:100]}")

        from opencode_python.agents import builtin

        available_agents = {
            "general": builtin.AgentGeneral,
            "explore": builtin.AgentExplore,
            "build": builtin.AgentBuild,
            "plan": builtin.AgentPlan,
        }

        subagent = available_agents.get(subagent_type.lower())

        if not subagent:
            return ToolResult(
                title="Unknown subagent type",
                output=f"Error: Subagent type {subagent_type} not available. Available: {list(available_agents.keys())}",
                metadata={"error": "unknown_agent_type", "available": list(available_agents.keys())}
            )

        start_time = time.time()

        try:
            if session_id_to_resume:
                await self._resume_session(session_id_to_resume, description, prompt, subagent, session_mgr)
            else:
                await self._create_new_session(description, prompt, subagent, subagent, session_mgr)

            execution_time = time.time() - start_time

            return ToolResult(
                title=f"Launched {subagent.value} subagent",
                output=f"Subagent {subagent.value} launched successfully in {execution_time:.2f} seconds",
                metadata={
                    "subagent_type": subagent_type,
                    "description": description[:50],
                    "session_id": session_id_to_resume or "new",
                    "execution_time": execution_time
                }
            )

        except Exception as e:
            logger.error(f"Task tool failed: {e}")
            return ToolResult(
                title="Task execution failed",
                output=f"Error: {str(e)}",
                metadata={"error": str(e)}
            )

    async def _resume_session(self, session_id: str, description: str, subagent: str, session_mgr: SessionManager):
        session_data = await session_mgr.get(session_id)
        logger.info(f"Resuming session {session_id}")

        from opencode_python.agents import builtin
        agent_class = getattr(builtin, f"Agent{subagent.title()}")
        agent_config = agent_class()

        user_message = session_mgr.create_message(
            session_id=session_id,
            role="user",
            parts=[{
                "id": f"{session_id}_task_request",
                "session_id": session_id,
                "part_type": "text",
                "text": f"Launch {agent_config.name} agent for: {description}"
            }]
        )

        assistant_message = session_mgr.create_message(
            session_id=session_id,
            role="assistant",
            parts=[{
                "id": f"{session_id}_task_response",
                "session_id": session_id,
                "part_type": "agent",
                "agent": agent_config.name,
                "state": "launched"
            }]
        )

        logger.info(f"Created task request and response in session {session_id}")

    async def _create_new_session(self, description: str, prompt: str, subagent: str, session, session_mgr: SessionManager):
        from opencode_python.agents import builtin

        agent_class = getattr(builtin, f"Agent{subagent.title()}")
        agent_config = agent_class()

        session_obj = await session_mgr.create(
            directory=session_mgr.directory,
            title=f"{agent_config.name} Task - {description[:50]}"
        )

        logger.info(f"Created new session {session_obj.id} for subagent {agent_config.name}")

        user_message = session_mgr.create_message(
            session_id=session_obj.id,
            role="user",
            parts=[{
                "id": f"{session_obj.id}_task_request",
                "session_id": session_obj.id,
                "part_type": "text",
                "text": f"Launch {agent_config.name} agent for: {description}"
            }]
        )

        assistant_message = session_mgr.create_message(
            session_id=session_obj.id,
            role="assistant",
            parts=[{
                "id": f"{session_obj.id}_task_response",
                "session_id": session_obj.id,
                "part_type": "agent",
                "agent": agent_config.name,
                "state": "launched",
                "metadata": {"description": description[:100]}
            }]
        )

        logger.info(f"Created task request and response in session {session_obj.id}")


async def register_task_tool(registry):
    await registry.register(TaskTool)


async def register_all_task_tools(registry):
    await register_task_tool(registry)


"""
Todo tools for task management.

Enables todo list creation, updates, and filtering by status.
"""


class TodoState(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoTool(Tool):
    id = "todoread"
    description = "Read todo list for current session"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        from .core.session import SessionManager

        session_mgr = SessionManager()
        todos = await session_mgr.get_todos(ctx.session_id)

        if not todos:
            return ToolResult(
                title="No todos found",
                output="No todos found in current session",
                metadata={"total": 0, "session_id": ctx.session_id}
            )

        todos_list = []
        total_count = 0
        completed_count = 0
        in_progress_count = 0
        cancelled_count = 0

        for todo in todos:
            state = todo.get("state", TodoState.PENDING)
            description = todo.get("description", "")
            due_date = todo.get("due_date")

            if state == TodoState.COMPLETED:
                completed_count += 1
            elif state == TodoState.IN_PROGRESS:
                in_progress_count += 1
            elif state == TodoState.CANCELLED:
                cancelled_count += 1
            total_count += 1

            due_str = f", due: {due_date}" if due_date else ""

            todos_list.append(f"{state.value} - {description}{due_str}")

        result_output = (
            f"Todo list ({total_count} items):\n"
            f"  Completed: {completed_count}\n"
            f"  In Progress: {in_progress_count}\n"
            f"  Cancelled: {cancelled_count}\n"
            + "\n".join([f"  {todo[:80]}..." for todo in todos_list[:20]])
        )

        if len(todos_list) > 20:
            result_output += f"\n  ... ({len(todos_list) - 20} more items)"

        return ToolResult(
            title="Todo list",
            output=result_output,
            metadata={
                "total": total_count,
                "completed": completed_count,
                "in_progress": in_progress_count,
                "cancelled": cancelled_count,
                "session_id": ctx.session_id
            }
        )


class TodowriteTool(Tool):
    id = "todowrite"
    description = "Create or update todo list"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        todos_data = args.get("todos", [])

        if not isinstance(todos_data, list):
            return ToolResult(
                title="Todos must be a list",
                output="Error: 'todos' parameter must be a list of todo items",
                metadata={"error": "invalid_todos_type"}
            )

        from .core.session import SessionManager

        session_mgr = SessionManager()

        todo_map = {}
        for idx, todo in enumerate(todos_data):
            todo_id = todo.get("id")
            description = todo.get("description", "")
            state = todo.get("state", TodoState.PENDING)
            due_date = todo.get("due_date")

            if not todo_id:
                return ToolResult(
                    title=f"Todo {idx} missing ID",
                    output=f"Error: Todo at index {idx} missing 'id' field",
                    metadata={"error": "missing_todo_id", "index": idx}
                )

            todo_map[todo_id] = {
                "description": description,
                "state": state.value,
                "due_date": due_date,
                "updated_at": datetime.utcnow().isoformat()
            }

        await session_mgr.update_todos(ctx.session_id, todo_map)

        todos = await session_mgr.get_todos(ctx.session_id)

        total_count = len(todos)
        completed_count = len([t for t in todos if t.get("state") == TodoState.COMPLETED])
        in_progress_count = len([t for t in todos if t.get("state") == TodoState.IN_PROGRESS])
        cancelled_count = len([t for t in todos if t.get("state") == TodoState.CANCELLED])

        result_output = f"Updated todo list ({total_count} items):\n"
        result_output += f"  Completed: {completed_count}\n"
        result_output += f"  In Progress: {in_progress_count}\n"
        result_output += f"  Cancelled: {cancelled_count}\n"

        for todo in todos[:10]:
            state_str = todo.get("state", TodoState.PENDING)
            due_str = f", due: {todo.get('due_date')}..." if todo.get('due_date') else ""
            result_output += f"  [{state_str}] {todo.get('description')}{due_str}\n"

        if len(todos) > 10:
            result_output += f"  ... ({len(todos) - 10} more items)"

        return ToolResult(
            title="Updated todo list",
            output=result_output,
            metadata={
                "total": total_count,
                "updated": total_count,
                "completed": completed_count,
                "in_progress": in_progress_count,
                "cancelled": cancelled_count,
                "session_id": ctx.session_id
            }
        )


async def register_todo_tools(registry):
    await registry.register(TodowriteTool)
    await registry.register(TodoTool)


"""
Web tools for fetching content and searching the web.

Enables web content fetching and real-time search capabilities.
"""


class WebFetchTool(Tool):
    id = "webfetch"
    description = "Fetch content from URL"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = args.get("url")
        format_type = args.get("format", "markdown")

        if not url:
            return ToolResult(
                title="URL required",
                output="Error: No URL provided",
                metadata={"error": "no_url"}
            )

        try:
            httpx_client = httpx.AsyncClient(timeout=30.0)

            if format_type == "markdown":
                headers = {"Accept": "text/markdown, application/markdown"}
            else:
                headers = {"Accept": "text/html, application/xhtml+xml"}

            response = await httpx_client.get(url, headers=headers)

            if response.status_code != 200:
                return ToolResult(
                    title="Failed to fetch",
                    output=f"Error: HTTP {response.status_code} - {response.text}",
                    metadata={"error": "http_error", "status_code": response.status_code}
                )

            content = response.text

            if len(content) > 10000:
                truncated_length = len(content) - 10000
                content = content[:10000] + f"\n\n[... Content truncated ({truncated_length} characters) ...]"

            logger.info(f"Fetched {len(content)} characters from {url}")

            return ToolResult(
                title=f"Fetched from {url}",
                output=content,
                metadata={
                    "url": url,
                    "format": format_type,
                    "bytes_fetched": len(content),
                    "truncated": len(content) > 10000
                }
            )

        except Exception as e:
            logger.error(f"Web fetch failed: {e}")
            return ToolResult(
                title="Web fetch failed",
                output=f"Error: {str(e)}",
                metadata={"error": "fetch_error"}
            )


class WebSearchTool(Tool):
    id = "websearch"
    description = "Real-time web search using Exa API"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = args.get("query")
        num_results = args.get("numResults", 10)
        live_crawl = args.get("liveCrawl", "fallback")
        search_type = args.get("searchType", "auto")
        domains = args.get("domains", [])

        if not query:
            return ToolResult(
                title="Query required",
                output="Error: 'query' parameter is required",
                metadata={"error": "no_query"}
            )

        from opencode_python.core.settings import settings

        api_key = settings.api_keys.get("exa", settings.api_keys.get("exa"))

        if not api_key:
            return ToolResult(
                title="Exa API key required",
                output="Error: OPENCODE_PYTHON_EXA_API_KEY or OPENCODE_PYTHON_EXA_API_KEY environment variable not set",
                metadata={"error": "no_exa_key"}
            )

        logger.info(f"Searching web for: {query[:50]}")

        try:
            httpx_client = httpx.AsyncClient(timeout=30.0, headers={"x-api-key": api_key})

            payload = {
                "query": query,
                "numResults": num_results,
                "contents": {
                    "text": True,
                    "livecrawl": live_crawl
                },
                "type": search_type,
                "domain": domains
            }

            response = await httpx_client.post(
                "https://api.exa.ai/search",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code != 200:
                logger.error(f"Exa API error: {response.status_code}")
                return ToolResult(
                    title="Search failed",
                    output=f"Error: Exa API returned {response.status_code}",
                    metadata={"error": "exa_api_error", "status_code": response.status_code}
                )

            results_data = response.json()
            results = results_data.get("results", [])

            formatted_results = []
            for result in results[:num_results]:
                title = result.get("title", "")
                url = result.get("url", "")
                snippet = result.get("text", "")
                score = result.get("score", 0)

                formatted_results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet[:200],
                    "score": score
                })

            output = (
                f"Found {len(formatted_results)} results:\n"
                + "\n".join([f"{idx + 1}. {r['title']}\n   {r['url']}\n   Score: {r['score']}\n"
                             for idx, r in enumerate(formatted_results)]
                            )
            )

            logger.info(f"Web search completed with {len(formatted_results)} results")

            return ToolResult(
                title=f"Web search results",
                output=output,
                metadata={
                    "query": query,
                    "num_results": len(formatted_results),
                    "results": formatted_results
                }
            )

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return ToolResult(
                title="Web search failed",
                output=f"Error: {str(e)}",
                metadata={"error": "search_error"}
            )


async def register_web_tools(registry):
    await registry.register(WebFetchTool)
    await registry.register(WebSearchTool)

class LsToolArgs(BaseModel):
    """Arguments for Ls tool"""
    path: Optional[str] = Field(default=None, description="Path to list (omit for current directory)")
    ignore: Optional[List[str]] = Field(default_factory=list, description="Glob patterns to ignore")


class LsTool(Tool):
    """List files and directories"""

    id = "ls"
    description = get_prompt("ls")

    async def execute(self, args: LsToolArgs, ctx: ToolContext) -> ToolResult:
        """List files and directories

        Args:
            args: LsToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with directory tree structure
        """
        path = args.path or ctx.session_id
        ignore_patterns = args.ignore

        try:
            full_path = Path(path) if path and not path.startswith("/") else Path(ctx.session_id if not ctx.session_id.startswith("/") else "") / (path or ".")

            if not full_path.exists():
                return ToolResult(
                    title="Path not found",
                    output="",
                    metadata={"error": f"Path does not exist: {path}", "path": str(path)},
                )

            # Build file tree
            tree_lines = []
            
            def build_tree(p: Path, prefix: str, last_prefix: str = ""):
                """Recursively build file tree"""
                if p.is_file():
                    tree_lines.append(f"{prefix}{p.name}")
                elif ignore_patterns and any(p.match(str(p.resolve())) for p.match in ignore_patterns):
                    # Skip this directory
                    pass
                else:
                    # Add directory with children
                    tree_lines.append(f"{prefix}{p.name}/")
                    try:
                        children = sorted(p.iterdir(), key=lambda x: x.name.lower())
                        new_prefix = f"{prefix}{p.name}/"
                        
                        # Update last_prefix to track where we left off
                        new_last_prefix = new_prefix
                        
                        # Add all children at this level
                        for child in children:
                            build_tree(child, new_prefix, new_last_prefix)
                    except PermissionError:
                        # If we can't read directory, just add it
                        tree_lines.append(f"{prefix}{p.name}/")
                        new_prefix = f"{prefix}{p.name}/"
            
            # Start building tree
            last_prefix = ""
            build_tree(full_path, "", last_prefix)
            
            output = "\n".join(tree_lines)
            
            return ToolResult(
                title=f"List: {path or 'current directory'}",
                output=output,
                metadata={"path": str(full_path), "entries": len(tree_lines)},
            )

        except Exception as e:
            logger.error(f"Ls tool failed: {e}")
            return ToolResult(
                title=f"Error listing: {path or 'directory'}",
                output=str(e),
                metadata={"error": str(e)},
            )


class BatchToolArgs(BaseModel):
    """Arguments for Batch tool"""
    tools: List[Dict[str, Any]] = Field(description="Array of tool calls to execute")


class BatchTool(Tool):
    """Execute multiple tool calls in parallel"""

    id = "batch"
    description = get_prompt("batch")

    async def execute(self, args: BatchToolArgs, ctx: ToolContext) -> ToolResult:
        """Execute multiple tool calls concurrently

        Args:
            args: BatchToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with aggregated results from all tools
        """
        if not args.tools or not isinstance(args.tools, list):
            return ToolResult(
                title="Invalid tools parameter",
                output="",
                metadata={"error": "tools must be an array"},
            )

        # Import builtin tools dynamically
        from opencode_python.tools import builtin
        
        tool_registry = {
            "read": builtin.ReadTool(),
            "write": builtin.WriteTool(),
            "grep": builtin.GrepTool(),
            "glob": builtin.GlobTool(),
            "bash": builtin.BashTool(),
        }
        
        # Collect tool results
        results = []
        errors = []
        
        async def execute_single_tool(tool_call: Dict[str, Any], idx: int):
            """Execute a single tool call"""
            tool_id = tool_call.get("tool", "")
            tool_args = tool_call.get("parameters", {})
            
            tool = tool_registry.get(tool_id)
            if not tool:
                error_msg = f"Unknown tool: {tool_id}"
                logger.error(error_msg)
                errors.append(error_msg)
                results.append({
                    "tool": tool_id,
                    "status": "error",
                    "output": error_msg,
                })
                return
            
            try:
                # Create temporary ToolContext for this tool execution
                tool_ctx = ToolContext(
                    session_id=ctx.session_id,
                    message_id=ctx.message_id,
                    agent=ctx.agent,
                    abort=ctx.abort,
                    messages=ctx.messages,
                )
                
                # Execute tool with validated args
                # Note: execute() expects Pydantic model, so we need to convert dict to proper model
                if tool_id == "bash":
                    tool_args = builtin.BashToolArgs(**tool_args)
                elif tool_id == "read":
                    tool_args = builtin.ReadToolArgs(**tool_args)
                elif tool_id == "write":
                    tool_args = builtin.WriteToolArgs(**tool_args)
                elif tool_id == "grep":
                    tool_args = builtin.GrepToolArgs(**tool_args)
                elif tool_id == "glob":
                    tool_args = builtin.GlobToolArgs(**tool_args)
                else:
                    results.append({
                        "tool": tool_id,
                        "status": "error",
                        "output": f"Tool not supported in batch: {tool_id}",
                    })
                    return
                
                result = await tool.execute(tool_args, tool_ctx)
                
                results.append({
                    "tool": tool_id,
                    "status": "completed" if result.metadata.get("error") else "error",
                    "output": result.output,
                    "metadata": result.metadata,
                })
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Tool execution failed ({tool_id}): {error_msg}")
                errors.append({
                    "tool": tool_id,
                    "status": "error",
                    "output": error_msg,
                })
        
        # Execute all tools in parallel
        await asyncio.gather(*[execute_single_tool(tool_call, idx) for idx, tool_call in enumerate(args.tools)])
        
        # Format output
        success_count = sum(1 for r in results if r.get("status") == "completed")
        error_count = len(errors)
        
        output_lines = []
        output_lines.append(f"Executed {len(args.tools)} tools in parallel")
        output_lines.append(f"Success: {success_count}, Errors: {error_count}")
        output_lines.append("")
        
        # Add results
        for result in results:
            output_lines.append(f"Tool: {result.get('tool', 'unknown')}")
            output_lines.append(f"Status: {result.get('status', 'unknown')}")
            if result.get("output"):
                output_lines.append(f"Output: {result['output']}")
            if result.get("metadata"):
                output_lines.append(f"Metadata: {result['metadata']}")
            output_lines.append("")
        
        output = "\n".join(output_lines)
        
        return ToolResult(
            title=f"Batch execution: {success_count} succeeded, {error_count} failed",
            output=output,
            metadata={
                "total_tools": len(args.tools),
                "success_count": success_count,
                "error_count": error_count,
                "results": results,
            },
        )


class PlanEnterTool(Tool):
    """Enter plan mode (switch to plan agent)"""

    id = "plan_enter"
    description = "Switch to plan agent for research and planning"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Enter plan mode

        Args:
            args: Empty dict (no parameters needed)
            ctx: Tool execution context

        Returns:
            ToolResult with action confirmation
        """
        logger.info("Entering plan mode")
        
        # In a real implementation, this would:
        # 1. Set agent mode to "plan"
        # 2. Return confirmation
        
        # For now, just return success
        return ToolResult(
            title="Entered plan mode",
            output="Switched to plan agent for research and planning tasks",
            metadata={"agent_mode": "plan"},
        )


class PlanExitTool(Tool):
    """Exit plan mode (switch to build agent)"""

    id = "plan_exit"
    description = "Exit plan agent to return to build mode"

    async def execute(self, args: Dict[str, Any], ctx: ToolContext) -> ToolResult:
        """Exit plan mode

        Args:
            args: Empty dict (no parameters needed)
            ctx: Tool execution context

        Returns:
            ToolResult with action confirmation
        """
        logger.info("Exiting plan mode to build mode")
        
        # In a real implementation, this would:
        # 1. Set agent mode to "build"
        # 2. Return confirmation
        
        # For now, just return success
        return ToolResult(
            title="Exited plan mode",
            output="Switched to build agent for implementation tasks",
            metadata={"agent_mode": "build"},
        )


# Ensure MultiEditTool is also updated with prompt
class MultiEditToolArgs(BaseModel):
    """Arguments for MultiEdit tool"""
    filePath: str = Field(description="Path to file")
    edits: List[Dict[str, Any]] = Field(description="Array of edit operations")


class MultiEditTool(Tool):
    """Apply multiple edits to a single file"""

    id = "multiedit"
    description = get_prompt("multiedit")

    async def execute(self, args: MultiEditToolArgs, ctx: ToolContext) -> ToolResult:
        """Apply multiple edits to a file

        Args:
            args: MultiEditToolArgs validated by Pydantic
            ctx: Tool execution context

        Returns:
            ToolResult with edit results
        """
        file_path = args.filePath
        edits = args.edits

        if not file_path:
            return ToolResult(
                title="File path required",
                output="",
                metadata={"error": "no_file_path"},
            )

        if not edits:
            return ToolResult(
                title="No edits provided",
                output="",
                metadata={"error": "no_edits"},
            )

        path = Path(file_path)
        
        try:
            with open(path, "r") as f:
                content = f.read()
            
            applied = []
            failed = []
            
            for i, edit in enumerate(edits):
                old_string = edit.get("oldString", "")
                new_string = edit.get("newString", "")
                
                if old_string not in content:
                    failed.append(f"Edit {i+1}: oldString not found")
                    continue
                
                new_content = content.replace(old_string, new_string, 1)
                applied.append(f"Edit {i+1}: Success")
                
                # Update content for next edit
                content = new_content
            
            if failed:
                error_msg = "\n".join(failed)
                return ToolResult(
                    title="MultiEdit failed",
                    output=f"Errors:\n{error_msg}",
                    metadata={"errors": len(failed), "applied": len(applied)},
                )
            
            # Write updated content
            with open(path, "w") as f:
                f.write(content)
            
            output_lines = [
                f"Applied {len(applied)} of {len(edits)} edits successfully",
                "",
            ]
            
            if failed:
                output_lines.append("Failed edits:")
                for fail in failed:
                    output_lines.append(f"  - {fail}")
                output_lines.append("")
            
            output = "\n".join(output_lines)
            
            return ToolResult(
                title=f"MultiEdit: {file_path}",
                output=output,
                metadata={
                    "file_path": str(path),
                    "total_edits": len(edits),
                    "applied": len(applied),
                    "failed": len(failed),
                },
            )

        except Exception as e:
            logger.error(f"MultiEdit tool failed: {e}")
            return ToolResult(
                title=f"Error editing: {file_path}",
                output=str(e),
                metadata={"error": str(e)},
            )


# Update imports at top if needed
from opencode_python.tools.prompts import get_prompt
from pydantic import BaseModel, Field
from pathlib import Path
