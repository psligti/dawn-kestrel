"""
Tool Executor for FSM-based Security Review.

This module provides real security tool execution capabilities with:
- Tool execution with retries and timeout handling
- Output normalization to SecurityFinding format
- Tool availability checking with graceful degradation
- Support for bandit, semgrep, safety, and grep tools

Security notes:
- NEVER uses shell=True with user input (from napkin)
- Always uses shell=False with list arguments
- Python 3.9 compatible (uses typing.Optional[T] instead of T | None)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding


logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    findings: List[SecurityFinding] = field(default_factory=list)
    error_message: Optional[str] = None


class ToolExecutor:
    """Executor for real security tools (bandit, semgrep, safety, grep)."""

    # Maximum retries for failed tool executions
    MAX_RETRIES = 3

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 30

    # Exponential backoff base (in seconds)
    BACKOFF_BASE = 1.0

    def __init__(self, default_timeout: int = DEFAULT_TIMEOUT) -> None:
        """Initialize ToolExecutor with optional default timeout.

        Args:
            default_timeout: Default timeout in seconds for tool execution
        """
        self.default_timeout = default_timeout
        self.logger = logger

    def is_tool_installed(self, tool_name: str) -> bool:
        """Check if a tool is installed and available.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if tool is installed, False otherwise
        """
        try:
            result = subprocess.run(
                [tool_name, "--version"],
                capture_output=True,
                text=True,
                check=False,
                shell=False,  # Security: Never use shell=True with user input
            )
            is_installed = result.returncode == 0
            if not is_installed:
                self.logger.warning(f"[TOOL_MISSING] {tool_name} is not installed")
            return is_installed
        except FileNotFoundError:
            self.logger.warning(f"[TOOL_MISSING] {tool_name} is not installed")
            return False

    def _wait_for_subprocess(
        self,
        process: subprocess.Popen[str],
        timeout: int,
        tool_name: str,
    ) -> int:
        """Wait for subprocess with timeout handling.

        Args:
            process: The subprocess to wait for
            timeout: Timeout in seconds
            tool_name: Name of the tool for logging

        Returns:
            The exit code of the process, or -1 if timed out
        """
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode
        except subprocess.TimeoutExpired:
            self.logger.warning(f"[TOOL_TIMEOUT] {tool_name} timed out after {timeout}s")
            process.kill()
            process.wait()
            return -1
        except Exception as e:
            self.logger.error(f"[TOOL_ERROR] {tool_name} wait failed: {e}")
            return -1

    def execute_tool(
        self,
        tool_name: str,
        args: List[str],
        timeout: Optional[int] = None,
    ) -> ToolResult:
        """Execute a security tool with retries and timeout handling.

        Args:
            tool_name: Name of the tool to execute (bandit, semgrep, safety, grep)
            args: Command line arguments for the tool
            timeout: Timeout in seconds (defaults to instance default)

        Returns:
            ToolResult containing stdout, stderr, exit code, and normalized findings
        """
        if timeout is None:
            timeout = self.default_timeout

        # Check if tool is installed
        if not self.is_tool_installed(tool_name):
            return ToolResult(
                success=False,
                error_message=f"Tool '{tool_name}' is not installed. Please install it first.",
                exit_code=-1,
            )

        self.logger.info(f"[TOOL_EXEC] Starting tool {tool_name}")

        # Execute with retry logic
        last_error: Optional[str] = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Build command as list for security (no shell=True)
                cmd = [tool_name] + args

                self.logger.debug(
                    f"[TOOL_EXEC] {tool_name} attempt {attempt}/{self.MAX_RETRIES}: {' '.join(cmd)}"
                )

                # Run subprocess without shell for security
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=False,  # Security: Never use shell=True with user input
                )

                try:
                    # Wait with timeout
                    stdout, stderr = process.communicate(timeout=timeout)
                    exit_code = process.returncode
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"[TOOL_TIMEOUT] {tool_name} timed out after {timeout}s")
                    process.kill()
                    stdout, stderr = process.communicate()
                    return ToolResult(
                        success=False,
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=-1,
                        timed_out=True,
                        error_message=f"Tool '{tool_name}' timed out after {timeout}s",
                    )

                # Check if command succeeded
                if exit_code != 0 and exit_code not in [1]:  # Exit code 1 is often "findings found"
                    last_error = stderr or f"Exit code {exit_code}"
                    self.logger.warning(
                        f"[TOOL_EXEC] {tool_name} failed (attempt {attempt}): {last_error}"
                    )
                    # Retry on failure
                    if attempt < self.MAX_RETRIES:
                        backoff = self.BACKOFF_BASE * (2 ** (attempt - 1))
                        self.logger.info(f"[TOOL_EXEC] Retrying in {backoff}s...")
                        time.sleep(backoff)
                        continue
                    else:
                        self.logger.error(
                            f"[TOOL_EXEC] {tool_name} failed after {self.MAX_RETRIES} attempts"
                        )
                        return ToolResult(
                            success=False,
                            stdout=stdout,
                            stderr=stderr,
                            exit_code=exit_code,
                            error_message=last_error,
                        )

                # Success - normalize output
                self.logger.info(f"[TOOL_DONE] {tool_name} completed")
                findings = self._normalize_output(tool_name, stdout, stderr)

                return ToolResult(
                    success=True,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    findings=findings,
                )

            except FileNotFoundError:
                self.logger.warning(f"[TOOL_MISSING] {tool_name} is not installed")
                return ToolResult(
                    success=False,
                    error_message=f"Tool '{tool_name}' is not installed. Please install it first.",
                    exit_code=-1,
                )
            except Exception as e:
                last_error = str(e)
                self.logger.error(f"[TOOL_ERROR] {tool_name} error (attempt {attempt}): {e}")
                if attempt < self.MAX_RETRIES:
                    backoff = self.BACKOFF_BASE * (2 ** (attempt - 1))
                    self.logger.info(f"[TOOL_EXEC] Retrying in {backoff}s...")
                    time.sleep(backoff)
                    continue

        # All retries exhausted
        return ToolResult(
            success=False,
            error_message=f"Tool '{tool_name}' failed after {self.MAX_RETRIES} attempts: {last_error}",
            exit_code=-1,
        )

    def _normalize_output(
        self,
        tool_name: str,
        stdout: str,
        stderr: str,
    ) -> List[SecurityFinding]:
        """Normalize tool output to SecurityFinding format.

        Args:
            tool_name: Name of the tool that generated the output
            stdout: Standard output from the tool
            stderr: Standard error from the tool

        Returns:
            List of normalized SecurityFinding objects
        """
        try:
            if tool_name == "bandit":
                return self._normalize_bandit_output(stdout)
            elif tool_name == "semgrep":
                return self._normalize_semgrep_output(stdout)
            elif tool_name == "safety":
                return self._normalize_safety_output(stdout)
            elif tool_name == "grep":
                return self._normalize_grep_output(stdout)
            else:
                self.logger.warning(f"[TOOL_NORMALIZE] Unknown tool: {tool_name}")
                return []
        except Exception as e:
            self.logger.error(f"[TOOL_NORMALIZE] Failed to normalize {tool_name} output: {e}")
            return []

    def _generate_deterministic_id(self, tool_name: str, finding_data: Dict[str, Any]) -> str:
        """Generate a deterministic ID from finding data.

        Args:
            tool_name: Name of the tool
            finding_data: Dictionary with finding data

        Returns:
            Deterministic hash string
        """
        # Create a string representation of the finding data
        data_str = json.dumps(finding_data, sort_keys=True)
        # Hash with tool name for uniqueness across tools
        hash_input = f"{tool_name}:{data_str}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def normalize_bandit_output(self, json_data: str) -> List[SecurityFinding]:
        """Normalize bandit JSON output to SecurityFinding format.

        Args:
            json_data: JSON string from bandit output

        Returns:
            List of SecurityFinding objects
        """
        return self._normalize_bandit_output(json_data)

    def _normalize_bandit_output(self, json_data: str) -> List[SecurityFinding]:
        """Internal method to normalize bandit output."""
        findings: List[SecurityFinding] = []

        try:
            data = json.loads(json_data)
            results = data.get("results", [])

            for result in results:
                # Determine severity
                severity = result.get("issue_severity", "low").lower()
                if severity in ["high", "medium", "low"]:
                    severity_map = {"high": "high", "medium": "medium", "low": "low"}
                    severity = severity_map.get(severity, "low")

                # Get test info
                test_id = result.get("test_id", "unknown")
                test_name = result.get("test_name", "Unknown Test")

                # Get location
                location = result.get("location", {})
                file_path = location.get("path", "")
                line_number = location.get("line")

                # Get code snippet
                code = result.get("code", "")

                # Create deterministic ID
                finding_data = {
                    "test_id": test_id,
                    "test_name": test_name,
                    "file_path": file_path,
                    "line_number": line_number,
                    "code": code,
                }
                finding_id = self._generate_deterministic_id("bandit", finding_data)

                finding = SecurityFinding(
                    id=finding_id,
                    severity=severity,
                    title=f"{test_name} ({test_id})",
                    description=result.get("issue_text", "Security issue detected"),
                    evidence=f"File: {file_path}\nLine: {line_number}\nCode: {code}",
                    file_path=file_path,
                    line_number=line_number,
                    recommendation=result.get("issue_text", "Fix the security issue"),
                    confidence_score=0.70,  # Bandit has good accuracy
                    requires_review=True,
                )
                findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error(f"[TOOL_NORMALIZE] Failed to parse bandit JSON: {e}")
        except Exception as e:
            self.logger.error(f"[TOOL_NORMALIZE] Bandit normalization error: {e}")

        return findings

    def normalize_semgrep_output(self, json_data: str) -> List[SecurityFinding]:
        """Normalize semgrep JSON output to SecurityFinding format.

        Args:
            json_data: JSON string from semgrep output

        Returns:
            List of SecurityFinding objects
        """
        return self._normalize_semgrep_output(json_data)

    def _normalize_semgrep_output(self, json_data: str) -> List[SecurityFinding]:
        """Internal method to normalize semgrep output."""
        findings: List[SecurityFinding] = []

        try:
            data = json.loads(json_data)
            results = data.get("results", [])

            for result in results:
                # Get severity
                severity = result.get("extra", {}).get("severity", "INFO").lower()
                severity_map = {
                    "error": "critical",
                    "warning": "high",
                    "info": "medium",
                }
                severity = severity_map.get(severity, "low")

                # Get rule info
                rule_id = result.get("check_id", "unknown")
                message = result.get("extra", {}).get("message", "Security issue detected")

                # Get location
                start = result.get("start", {})
                end = result.get("end", {})
                file_path = result.get("path", "")
                line_number = start.get("line")

                # Get code snippet
                lines = result.get("extra", {}).get("lines", "")

                # Create deterministic ID
                finding_data = {
                    "rule_id": rule_id,
                    "file_path": file_path,
                    "line_number": line_number,
                    "message": message,
                }
                finding_id = self._generate_deterministic_id("semgrep", finding_data)

                finding = SecurityFinding(
                    id=finding_id,
                    severity=severity,
                    title=f"Semgrep Rule: {rule_id}",
                    description=message,
                    evidence=f"File: {file_path}\nLine: {line_number}\nCode:\n{lines}",
                    file_path=file_path,
                    line_number=line_number,
                    recommendation=message,
                    confidence_score=0.80,  # Semgrep has high accuracy
                    requires_review=True,
                )
                findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error(f"[TOOL_NORMALIZE] Failed to parse semgrep JSON: {e}")
        except Exception as e:
            self.logger.error(f"[TOOL_NORMALIZE] Semgrep normalization error: {e}")

        return findings

    def normalize_safety_output(self, json_data: str) -> List[SecurityFinding]:
        """Normalize safety JSON output to SecurityFinding format.

        Args:
            json_data: JSON string from safety output

        Returns:
            List of SecurityFinding objects
        """
        return self._normalize_safety_output(json_data)

    def _normalize_safety_output(self, json_data: str) -> List[SecurityFinding]:
        """Internal method to normalize safety output."""
        findings: List[SecurityFinding] = []

        try:
            data = json.loads(json_data)

            # Safety output format: list of vulnerability entries
            vulnerabilities = data if isinstance(data, list) else data.get("vulnerabilities", [])

            for vuln in vulnerabilities:
                # Get package info
                package_name = vuln.get("name", "unknown")
                installed_version = vuln.get("installed_version", "unknown")
                affected_versions = vuln.get("affected_versions", [])
                advisory = vuln.get("advisory", "")
                vulnerability_id = vuln.get("id", vuln.get("cve", "unknown"))

                # Create deterministic ID
                finding_data = {
                    "package_name": package_name,
                    "installed_version": installed_version,
                    "vulnerability_id": vulnerability_id,
                }
                finding_id = self._generate_deterministic_id("safety", finding_data)

                finding = SecurityFinding(
                    id=finding_id,
                    severity="high",  # Dependency vulnerabilities are high severity
                    title=f"Vulnerable dependency: {package_name} {installed_version}",
                    description=advisory,
                    evidence=f"Package: {package_name}\n"
                    f"Installed: {installed_version}\n"
                    f"Affected versions: {', '.join(affected_versions)}\n"
                    f"Vulnerability ID: {vulnerability_id}",
                    file_path=None,  # No file path for dependency issues
                    line_number=None,
                    recommendation=f"Upgrade {package_name} to a safe version",
                    confidence_score=0.90,  # Safety has very high accuracy
                    requires_review=True,
                )
                findings.append(finding)

        except json.JSONDecodeError as e:
            self.logger.error(f"[TOOL_NORMALIZE] Failed to parse safety JSON: {e}")
        except Exception as e:
            self.logger.error(f"[TOOL_NORMALIZE] Safety normalization error: {e}")

        return findings

    def normalize_grep_output(self, text_data: str) -> List[SecurityFinding]:
        """Normalize grep text output to SecurityFinding format.

        Args:
            text_data: Text string from grep output (format: file:line:match)

        Returns:
            List of SecurityFinding objects
        """
        return self._normalize_grep_output(text_data)

    def _normalize_grep_output(self, text_data: str) -> List[SecurityFinding]:
        """Internal method to normalize grep output."""
        findings: List[SecurityFinding] = []

        try:
            lines = text_data.strip().split("\n")

            for line in lines:
                if not line.strip():
                    continue

                # Parse grep output format: file:line:match
                parts = line.split(":", 2)
                if len(parts) < 3:
                    continue

                file_path = parts[0].strip()
                line_number_str = parts[1].strip()
                match_content = parts[2].strip()

                try:
                    line_number = int(line_number_str)
                except ValueError:
                    line_number = None

                # Create deterministic ID
                finding_data = {
                    "file_path": file_path,
                    "line_number": line_number,
                    "match_content": match_content,
                }
                finding_id = self._generate_deterministic_id("grep", finding_data)

                finding = SecurityFinding(
                    id=finding_id,
                    severity="medium",  # Default severity for grep findings
                    title=f"Pattern matched in {file_path}",
                    description=f"Grep pattern matched at line {line_number}",
                    evidence=f"File: {file_path}\nLine: {line_number}\nMatch: {match_content}",
                    file_path=file_path,
                    line_number=line_number,
                    recommendation="Review the matched pattern for security implications",
                    confidence_score=0.60,  # Grep findings require review
                    requires_review=True,
                )
                findings.append(finding)

        except Exception as e:
            self.logger.error(f"[TOOL_NORMALIZE] Grep normalization error: {e}")

        return findings


# Convenience function for creating an executor
def create_tool_executor(default_timeout: int = ToolExecutor.DEFAULT_TIMEOUT) -> ToolExecutor:
    """Create a ToolExecutor instance.

    Args:
        default_timeout: Default timeout in seconds

    Returns:
        ToolExecutor instance
    """
    return ToolExecutor(default_timeout=default_timeout)
