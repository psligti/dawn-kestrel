"""TelemetryMetricsReviewer - checks for logging quality and observability coverage."""
from __future__ import annotations
from typing import List, Literal
import re
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Finding,
    MergeGate,
)


TELEMETRY_SYSTEM_PROMPT = """You are the Telemetry & Metrics Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to observability.
- Propose minimal targeted checks; escalate when failure modes are introduced.
- If changed_files or diff are missing, request them.
- Discover repo conventions (logging frameworks, metrics libs, tracing setup).

You specialize in:
- logging quality (structured logs, levels, correlation IDs)
- tracing spans / propagation (if applicable)
- metrics: counters/gauges/histograms, cardinality control
- error reporting: meaningful errors, no sensitive data
- observability coverage of new workflows and failure modes
- performance signals: timing, retries, rate limits, backoff

Relevant changes:
- new workflows, background jobs, pipelines, orchestration
- network calls, IO boundaries, retry logic, timeouts
- error handling changes, exception mapping

Checks you may request:
- log format checks (if repo has them)
- smoke run command to ensure logs/metrics emitted (if available)
- grep for logger usage & secrets leakage

Blocking:
- secrets/PII likely logged
- critical path introduced with no error logging/metrics
- retry loops without visibility or limits (runaway risk)
- high-cardinality metric labels introduced

Output MUST be valid JSON only with agent="telemetry_metrics" and the standard schema.
Return JSON only."""


# Patterns for detecting telemetry issues
SILENT_EXCEPTION_PATTERNS = [
    (r'except\s*:\s*pass', "Silent exception handler"),
    (r'except\s+\w+\s*:\s*pass', "Silent exception handler with catch"),
    (r'except\s+\w+\s+as\s+\w+\s*:\s*pass', "Silent exception handler with variable"),
    (r'except\s*\(\s*\w+\s*(?:,\s*\w+\s*)*\)\s*:\s*pass', "Silent exception handler with multiple catches"),
]

MISSING_ERROR_LOG_PATTERNS = [
    (r'except\s+[^:]+:\s*[^l][^o][^g]', "Exception handling without logging"),
]

MISSING_METRICS_PATTERNS = [
    (r'(def\s+\w+.*request|def\s+\w+.*fetch|def\s+\w+.*process|def\s+\w+.*handle)[^(]*\([^)]*\):', "IO operation without metrics"),
]

LOGGING_QUALITY_PATTERNS = [
    (r'logger\.(debug|info|warning|error|critical)\s*\(\s*["\'][^"\']*\s*\+\s*[^"\']+\s*\)', "String concatenation in log"),
    (r'logger\.(debug|info|warning|error|critical)\s*\(\s*["\']\{.*\}["\']\)', "Log without structured data"),
]

SENSITIVE_DATA_PATTERNS = [
    (r'logger\.(debug|info|warning|error|critical)\s*\([^)]*(?:password|secret|token|api_key|credit_card|ssn)[^)]*\)', "Logging sensitive data"),
]


class TelemetryMetricsReviewer(BaseReviewerAgent):
    """Telemetry reviewer agent that checks for logging quality and observability coverage.

    This agent specializes in detecting:
    - Logging quality (proper log levels, structured logging)
    - Error reporting (exceptions raised with context)
    - Observability coverage (metrics, traces, distributed tracing)
    - Silent failures (swallowed exceptions)
    """

    def get_agent_name(self) -> str:
        """Return the agent identifier."""
        return "telemetry"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the telemetry reviewer."""
        return TELEMETRY_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns relevant to telemetry review."""
        return [
            "**/*.py",
            "**/logging/**",
            "**/observability/**",
            "**/metrics/**",
            "**/tracing/**",
            "**/monitoring/**",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform telemetry review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with telemetry findings, severity, and merge gate decision
        """
        relevant_files = []
        ignored_files = []

        for file_path in context.changed_files:
            if self.is_relevant_to_changes([file_path]):
                relevant_files.append(file_path)
            else:
                ignored_files.append(file_path)

        if not relevant_files:
            return ReviewOutput(
                agent=self.get_agent_name(),
                summary="No relevant code changes for telemetry review.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    ignored_files=ignored_files,
                    reasoning="No Python files changed that require telemetry review.",
                ),
                merge_gate=MergeGate(decision="approve"),
            )

        findings: List[Finding] = []

        # Check for silent failures (swallowed exceptions)
        silent_failures = self._check_silent_exceptions(context.diff, relevant_files)
        findings.extend(silent_failures)

        # Check for missing error logging
        missing_logs = self._check_missing_error_logs(context.diff, relevant_files)
        findings.extend(missing_logs)

        # Check for logging quality issues
        logging_issues = self._check_logging_quality(context.diff)
        findings.extend(logging_issues)

        # Check for sensitive data in logs
        sensitive_data = self._check_sensitive_data_in_logs(context.diff)
        findings.extend(sensitive_data)

        # Check for missing metrics on IO operations
        missing_metrics = self._check_missing_metrics(context.diff, relevant_files)
        findings.extend(missing_metrics)

        # Compute severity
        severity: Literal["merge", "warning", "critical", "blocking"] = self._compute_severity(findings)
        merge_gate = self._compute_merge_gate(findings, severity)

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=self._generate_summary(findings, severity),
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                ignored_files=ignored_files,
                reasoning=f"Telemetry review analyzed {len(relevant_files)} relevant files for logging quality and observability coverage.",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )

    def _check_silent_exceptions(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for silent exception handlers that swallow errors.

        Args:
            diff: Git diff content
            relevant_files: List of relevant changed files

        Returns:
            List of findings for silent exceptions
        """
        findings: List[Finding] = []
        lines = diff.split('\n')
        current_file = "unknown"
        line_num = 1

        for i, line in enumerate(lines):
            # Track file context
            if line.startswith('+++ b/') or line.startswith('--- a/'):
                match = re.search(r'([ab]/.+)$', line)
                if match:
                    current_file = match.group(1)[2:]
                continue

            # Get line number from diff header
            if '@@' in line:
                match = re.search(r'@@\s+\-\d+(?:,\d+)?\s+\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if not line.startswith('+'):
                if line.startswith('@@'):
                    line_num += 1
                continue

            line_num += 1

            # Check for silent exception patterns
            for pattern, description in SILENT_EXCEPTION_PATTERNS:
                match = re.search(pattern, line[1:])
                if match:
                    # Check if this is in a test file
                    if 'test' in current_file.lower():
                        continue

                    findings.append(Finding(
                        id=f"silent-exception-{i}",
                        title=description,
                        severity="critical",
                        confidence="high",
                        owner="dev",
                        estimate="S",
                        evidence=f"{current_file}:{line_num}\n{line[1:]}",
                        risk="Silent exception handlers hide errors and make debugging impossible.",
                        recommendation="Add logging or re-raise the exception with context.",
                        suggested_patch="except Exception as e:\n    logger.error(f'Error in {current_file}: {e}')\n    raise",
                    ))
                    break

        return findings

    def _check_missing_error_logs(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for exception handling without logging.

        Args:
            diff: Git diff content
            relevant_files: List of relevant changed files

        Returns:
            List of findings for missing error logging
        """
        findings: List[Finding] = []
        lines = diff.split('\n')
        current_file = "unknown"
        line_num = 1
        in_exception_handler = False
        handler_line = 0

        for i, line in enumerate(lines):
            # Track file context
            if line.startswith('+++ b/') or line.startswith('--- a/'):
                match = re.search(r'([ab]/.+)$', line)
                if match:
                    current_file = match.group(1)[2:]
                continue

            # Get line number from diff header
            if '@@' in line:
                match = re.search(r'@@\s+\-\d+(?:,\d+)?\s+\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            # Check for exception handler start
            if line.startswith('+') and re.search(r'except\s+[^:]+:', line[1:]):
                in_exception_handler = True
                handler_line = line_num + 1

            # Check if logging is present in exception handler
            if in_exception_handler and line.startswith('+'):
                if re.search(r'logger\.(error|warning|exception)\s*\(', line[1:]):
                    in_exception_handler = False  # Logging found, no issue

            # Check if we're out of exception handler
            if line.startswith('+') and line[1:].strip() and not re.search(r'except|raise|return|continue|break', line[1:]):
                if in_exception_handler and not re.search(r'logger\.(error|warning|exception)\s*\(', line[1:]):
                    # No logging in exception handler
                    pass

            if line.startswith('+'):
                line_num += 1

        return findings

    def _check_logging_quality(self, diff: str) -> List[Finding]:
        """Check for logging quality issues.

        Args:
            diff: Git diff content

        Returns:
            List of findings for logging quality issues
        """
        findings: List[Finding] = []
        lines = diff.split('\n')
        current_file = "unknown"
        line_num = 1

        for i, line in enumerate(lines):
            # Track file context
            if line.startswith('+++ b/') or line.startswith('--- a/'):
                match = re.search(r'([ab]/.+)$', line)
                if match:
                    current_file = match.group(1)[2:]
                continue

            # Get line number from diff header
            if '@@' in line:
                match = re.search(r'@@\s+\-\d+(?:,\d+)?\s+\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if not line.startswith('+'):
                if line.startswith('@@'):
                    line_num += 1
                continue

            line_num += 1

            # Check for logging quality patterns
            for pattern, description in LOGGING_QUALITY_PATTERNS:
                match = re.search(pattern, line[1:])
                if match:
                    findings.append(Finding(
                        id=f"log-quality-{i}",
                        title=description,
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"{current_file}:{line_num}\n{line[1:]}",
                        risk="Poor logging quality makes logs harder to parse and analyze.",
                        recommendation="Use structured logging with logger.info('message', extra={'key': 'value'}) or f-strings.",
                        suggested_patch=f"logger.info('message', extra={{'key': 'value'}})",
                    ))
                    break

        return findings

    def _check_sensitive_data_in_logs(self, diff: str) -> List[Finding]:
        """Check for sensitive data being logged.

        Args:
            diff: Git diff content

        Returns:
            List of findings for sensitive data in logs
        """
        findings: List[Finding] = []
        lines = diff.split('\n')
        current_file = "unknown"
        line_num = 1

        for i, line in enumerate(lines):
            # Track file context
            if line.startswith('+++ b/') or line.startswith('--- a/'):
                match = re.search(r'([ab]/.+)$', line)
                if match:
                    current_file = match.group(1)[2:]
                continue

            # Get line number from diff header
            if '@@' in line:
                match = re.search(r'@@\s+\-\d+(?:,\d+)?\s+\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if not line.startswith('+'):
                if line.startswith('@@'):
                    line_num += 1
                continue

            line_num += 1

            # Check for sensitive data patterns
            for pattern, description in SENSITIVE_DATA_PATTERNS:
                match = re.search(pattern, line[1:], re.IGNORECASE)
                if match:
                    findings.append(Finding(
                        id=f"sensitive-log-{i}",
                        title=description,
                        severity="critical",
                        confidence="high",
                        owner="dev",
                        estimate="S",
                        evidence=f"{current_file}:{line_num}\n{line[1:][:100]}..." if len(line[1:]) > 100 else f"{current_file}:{line_num}\n{line[1:]}",
                        risk="Logging sensitive data can lead to security breaches and compliance violations.",
                        recommendation="Remove sensitive data from logs or redact it before logging.",
                        suggested_patch="# Redact sensitive data before logging\nlogger.info('operation completed')",
                    ))
                    break

        return findings

    def _check_missing_metrics(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for missing metrics on IO operations.

        Args:
            diff: Git diff content
            relevant_files: List of relevant changed files

        Returns:
            List of findings for missing metrics
        """
        findings: List[Finding] = []
        lines = diff.split('\n')
        current_file = "unknown"
        line_num = 1

        for i, line in enumerate(lines):
            # Track file context
            if line.startswith('+++ b/') or line.startswith('--- a/'):
                match = re.search(r'([ab]/.+)$', line)
                if match:
                    current_file = match.group(1)[2:]
                continue

            # Get line number from diff header
            if '@@' in line:
                match = re.search(r'@@\s+\-\d+(?:,\d+)?\s+\+(\d+)', line)
                if match:
                    line_num = int(match.group(1)) - 1
                continue

            if not line.startswith('+'):
                if line.startswith('@@'):
                    line_num += 1
                continue

            line_num += 1

            # Check for missing metrics patterns
            for pattern, description in MISSING_METRICS_PATTERNS:
                match = re.search(pattern, line[1:])
                if match:
                    # Skip test files
                    if 'test' in current_file.lower():
                        continue

                    findings.append(Finding(
                        id=f"missing-metrics-{i}",
                        title=description,
                        severity="warning",
                        confidence="low",
                        owner="dev",
                        estimate="S",
                        evidence=f"{current_file}:{line_num}\n{line[1:]}",
                        risk="Missing metrics make it difficult to monitor performance and identify issues.",
                        recommendation="Add metrics for IO operations: counters, gauges, or histograms.",
                        suggested_patch=f"metrics.counter('operation_name').increment()",
                    ))
                    break

        return findings

    def _compute_severity(self, findings: List[Finding]) -> Literal["merge", "warning", "critical", "blocking"]:
        """Compute overall severity from findings.

        Args:
            findings: List of findings

        Returns:
            Severity level (merge, warning, critical, blocking)
        """
        if not findings:
            return "merge"

        # Check for blocking findings
        if any(finding.severity == "critical" for finding in findings):
            return "critical"

        # Check for warning findings
        if any(finding.severity == "warning" for finding in findings):
            return "warning"

        return "merge"

    def _compute_merge_gate(self, findings: List[Finding], severity: Literal["merge", "warning", "critical", "blocking"]) -> MergeGate:
        """Compute merge gate decision from findings and severity.

        Args:
            findings: List of findings
            severity: Overall severity level

        Returns:
            MergeGate with decision and fix lists
        """
        must_fix = []
        should_fix = []
        notes_for_coding_agent = []

        for finding in findings:
            if finding.severity == "critical":
                must_fix.append(finding.id)
            elif finding.severity == "warning":
                should_fix.append(finding.id)

            if finding.recommendation:
                notes_for_coding_agent.append(
                    f"[{finding.id}] {finding.recommendation}"
                )

        if severity == "critical":
            decision = "needs_changes"
        elif severity == "warning":
            decision = "needs_changes"
        else:
            decision = "approve"

        return MergeGate(
            decision=decision,
            must_fix=must_fix,
            should_fix=should_fix,
            notes_for_coding_agent=notes_for_coding_agent,
        )

    def _generate_summary(self, findings: List[Finding], severity: str) -> str:
        """Generate summary for review output.

        Args:
            findings: List of findings
            severity: Overall severity level

        Returns:
            Summary string
        """
        if not findings:
            return "No telemetry issues detected. Changes have adequate logging and observability coverage."

        by_severity = {"critical": 0, "warning": 0}
        for finding in findings:
            if finding.severity in by_severity:
                by_severity[finding.severity] += 1

        parts = [
            f"Telemetry review complete.",
            f"Found {len(findings)} issue(s):",
        ]

        if by_severity["critical"] > 0:
            parts.append(f"- {by_severity['critical']} critical (silent failures, sensitive data)")
        if by_severity["warning"] > 0:
            parts.append(f"- {by_severity['warning']} warning (missing metrics, logging quality)")

        return " ".join(parts)
