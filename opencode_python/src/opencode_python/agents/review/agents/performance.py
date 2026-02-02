"""Performance & Reliability Review Subagent."""
from __future__ import annotations
import logging
import re
from pathlib import Path
from typing import List, Literal

import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    MergeGate,
    Finding,
)

logger = logging.getLogger(__name__)

PERFORMANCE_SYSTEM_PROMPT = """You are the Performance & Reliability Review Subagent.

Use this shared behavior:
- If changed_files or diff are missing, request them.
- Focus on hot paths, IO amplification, retries, timeouts, concurrency hazards.
- Propose minimal checks first; escalate if core systems changed.

Specialize in:
- complexity regressions (O(n^2), unbounded loops)
- IO amplification (extra queries/reads)
- retry/backoff/timeouts correctness
- concurrency hazards (async misuse, shared mutable state)
- memory/cpu hot paths, caching correctness
- failure modes and graceful degradation

Relevant changes:
- loops, batching, pagination, retries
- network clients, DB access, file IO
- orchestration changes, parallelism, caching

Checks you may request:
- targeted benchmarks (if repo has them)
- profiling hooks or smoke run command
- unit tests for retry/timeout behavior

Blocking:
- infinite/unbounded retry risk
- missing timeouts on network calls in critical paths
- concurrency bugs with shared mutable state

Return JSON with agent="performance_reliability" using the standard schema.
Return JSON only."""


class PerformanceReliabilityReviewer(BaseReviewerAgent):
    """Reviewer agent for performance and reliability checks.

    Checks for:
    - Code complexity (nested loops, deep nesting, cyclomatic complexity)
    - IO amplification (N+1 database queries, excessive API calls in loops)
    - Retry logic (exponential backoff, proper retry policies)
    - Concurrency issues (race conditions, missing locks, shared state)
    """

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "performance"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer."""
        return PERFORMANCE_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return [
            "**/*.py",
            "**/*.rs",
            "**/*.go",
            "**/*.js",
            "**/*.ts",
            "**/*.tsx",
            "**/config/**",
            "**/database/**",
            "**/db/**",
            "**/network/**",
            "**/api/**",
            "**/services/**",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform performance and reliability review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        findings: List[Finding] = []

        relevant_files = [
            f for f in context.changed_files
            if self.is_relevant_to_changes([f])
        ]

        if not relevant_files:
            return ReviewOutput(
                agent="performance",
                summary="No performance-critical files changed. Performance review not applicable.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    reasoning="No relevant files for performance review",
                ),
                findings=findings,
                merge_gate=MergeGate(
                    decision="approve",
                    notes_for_coding_agent=[
                        "No performance-critical files were changed.",
                    ],
                ),
            )

        findings.extend(self._check_complexity(context.diff))
        findings.extend(self._check_io_amplification(context.diff))
        findings.extend(self._check_retry_logic(context.diff))
        findings.extend(self._check_concurrency_issues(context.diff))

        severity: Literal["merge", "warning", "critical", "blocking"] = self._compute_severity(findings)
        merge_gate = self._compute_merge_gate(severity, findings)

        summary = self._generate_summary(findings)

        return ReviewOutput(
            agent="performance",
            summary=summary,
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                reasoning="Analyzed performance and reliability patterns in changed files",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )

    def _check_complexity(self, diff: str) -> List[Finding]:
        """Check for code complexity issues.

        Args:
            diff: Git diff content

        Returns:
            List of findings for complexity issues
        """
        findings: List[Finding] = []

        nested_loop_pattern = re.compile(
            r'^\+\s*for\s+\w+.*:\s*$.*^\+\s{4,}for\s+\w+',
            re.MULTILINE | re.DOTALL
        )

        for match in nested_loop_pattern.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-COMPLEX-001",
                title="Nested loop detected",
                severity="warning",
                confidence="high",
                owner="dev",
                estimate="M",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Nested loops can lead to O(n^2) or worse time complexity",
                recommendation="Consider refactoring to use lookup tables, sets, or batch processing to reduce complexity",
            ))

        deep_nesting_pattern = re.compile(r'^\+(\s{12,})')
        for match in deep_nesting_pattern.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-COMPLEX-002",
                title="Deep nesting detected (3+ levels)",
                severity="warning",
                confidence="medium",
                owner="dev",
                estimate="S",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Deep nesting makes code hard to understand and may indicate complex logic",
                recommendation="Consider extracting nested logic into separate functions or using early returns",
            ))

        return findings

    def _check_io_amplification(self, diff: str) -> List[Finding]:
        """Check for IO amplification issues.

        Args:
            diff: Git diff content

        Returns:
            List of findings for IO amplification issues
        """
        findings: List[Finding] = []

        db_query_in_loop = re.compile(
            r'^\+\s*for\s+\w+.*:.*(?:db\.execute|query\.execute|session\.query|collection\.find)',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        for match in db_query_in_loop.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-IO-001",
                title="Database query inside loop detected (N+1 problem)",
                severity="critical",
                confidence="high",
                owner="dev",
                estimate="L",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="N+1 query pattern causes O(n) database calls instead of O(1) or O(1/batch)",
                recommendation="Use batch queries, JOIN, prefetch_related, or load all data before the loop",
                suggested_patch="Consider using: batch fetch, bulk operations, or eager loading patterns",
            ))

        api_call_in_loop = re.compile(
            r'^\+\s*for\s+\w+.*:.*(?:requests\.|http\.|fetch\(|axios\.|\.get\(|\.post\()',
            re.IGNORECASE | re.MULTILINE | re.DOTALL
        )

        for match in api_call_in_loop.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-IO-002",
                title="API call inside loop detected",
                severity="critical",
                confidence="high",
                owner="dev",
                estimate="L",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Multiple API calls in a loop can cause rate limiting, timeouts, and poor performance",
                recommendation="Batch API requests, use parallel requests with concurrency limits, or cache results",
            ))

        return findings

    def _check_retry_logic(self, diff: str) -> List[Finding]:
        """Check for retry logic issues.

        Args:
            diff: Git diff content

        Returns:
            List of findings for retry logic issues
        """
        findings: List[Finding] = []

        infinite_retry_pattern = re.compile(
            r'^\+.*while\s+True:\s*$.*^\+\s+try:',
            re.MULTILINE | re.DOTALL
        )

        for match in infinite_retry_pattern.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-RETRY-001",
                title="Potential infinite retry loop (while True)",
                severity="blocking",
                confidence="medium",
                owner="dev",
                estimate="M",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Infinite retry loops can hang applications and exhaust resources",
                recommendation="Always include retry limits, exponential backoff, and timeout mechanisms",
                suggested_patch="Use retry libraries like tenacity, or implement max_retries + exponential backoff",
            ))

        no_backoff_pattern = re.compile(
            r'^\+.*(?:time\.sleep\s*\(\d+\)|await\s+asyncio\.sleep\s*\(\d+\)).*(?!\s*#\s*[Bb]ackoff)',
            re.MULTILINE
        )

        for match in no_backoff_pattern.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            if 'retry' in evidence_line.lower() or 'attempt' in evidence_line.lower():
                findings.append(Finding(
                    id="PERF-RETRY-002",
                    title="Retry without exponential backoff detected",
                    severity="critical",
                    confidence="medium",
                    owner="dev",
                    estimate="M",
                    evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                    risk="Fixed-delay retries can overwhelm services and cause cascading failures",
                    recommendation="Use exponential backoff with jitter to spread out retry attempts",
                    suggested_patch="sleep(base_delay * (2 ** attempt) + random_jitter)",
                ))

        return findings

    def _check_concurrency_issues(self, diff: str) -> List[Finding]:
        """Check for concurrency issues.

        Args:
            diff: Git diff content

        Returns:
            List of findings for concurrency issues
        """
        findings: List[Finding] = []

        shared_state_without_lock = re.compile(
            r'^\+\s*global\s+\w+.*^\+.*(?<!\b(?:asyncio\.Lock|threading\.Lock|Lock\(\)))\s*\w+\s*[+\-*/]=',
            re.MULTILINE | re.DOTALL
        )

        for match in shared_state_without_lock.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-CONC-001",
                title="Shared state modification without lock",
                severity="critical",
                confidence="medium",
                owner="dev",
                estimate="L",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Concurrent access to shared mutable state without synchronization causes race conditions",
                recommendation="Use locks (asyncio.Lock, threading.Lock), queues, or immutable data structures",
                suggested_patch="async with lock: or with lock: around shared state modifications",
            ))

        async_fire_forget = re.compile(
            r'^\+\s*(?:asyncio\.create_task|\.create_task|asyncio\.ensure_future)\s*\(',
            re.MULTILINE
        )

        for match in async_fire_forget.finditer(diff):
            lines = diff[:match.start()].count('\n')
            evidence_line = diff.splitlines()[lines + 1] if lines + 1 < len(diff.splitlines()) else ""

            findings.append(Finding(
                id="PERF-CONC-002",
                title="Fire-and-forget async task created without error handling",
                severity="warning",
                confidence="medium",
                owner="dev",
                estimate="M",
                evidence=f"Line {lines + 1}: {evidence_line[:100]}",
                risk="Uncaught exceptions in fire-and-forget tasks can fail silently",
                recommendation="Add try/except in the task or use asyncio.gather with return_exceptions=True",
                suggested_patch="Wrap task in try/except or await/track task lifecycle",
            ))

        return findings

    def _compute_severity(self, findings: List[Finding]) -> Literal["merge", "warning", "critical", "blocking"]:
        """Compute overall severity from findings.

        Args:
            findings: List of findings

        Returns:
            Overall severity level
        """
        if not findings:
            return "merge"

        has_blocking = any(f.severity == "blocking" for f in findings)
        has_critical = any(f.severity == "critical" for f in findings)
        has_warning = any(f.severity == "warning" for f in findings)

        if has_blocking:
            return "blocking"
        elif has_critical:
            return "critical"
        elif has_warning:
            return "warning"
        else:
            return "merge"

    def _compute_merge_gate(
        self,
        severity: Literal["merge", "warning", "critical", "blocking"],
        findings: List[Finding]
    ) -> MergeGate:
        """Compute merge gate decision based on severity and findings.

        Args:
            severity: Overall severity level
            findings: List of findings

        Returns:
            MergeGate decision
        """
        if severity == "blocking":
            return MergeGate(
                decision="block",
                must_fix=[f.id for f in findings if f.severity == "blocking"],
                should_fix=[f.id for f in findings if f.severity in ["critical", "warning"]],
                notes_for_coding_agent=[
                    "Blocking performance issues detected that must be fixed before merge.",
                    "Review infinite retry risks and concurrency hazards.",
                ],
            )
        elif severity == "critical":
            return MergeGate(
                decision="needs_changes",
                must_fix=[f.id for f in findings if f.severity == "critical"],
                should_fix=[f.id for f in findings if f.severity == "warning"],
                notes_for_coding_agent=[
                    "Critical performance issues detected that should be addressed.",
                    "Review IO amplification and retry logic.",
                ],
            )
        elif severity == "warning":
            return MergeGate(
                decision="needs_changes",
                should_fix=[f.id for f in findings if f.severity == "warning"],
                notes_for_coding_agent=[
                    "Performance improvements suggested but not blocking.",
                    "Consider addressing complexity issues when possible.",
                ],
            )
        else:
            return MergeGate(
                decision="approve",
                notes_for_coding_agent=[
                    "No performance or reliability issues detected.",
                ],
            )

    def _generate_summary(self, findings: List[Finding]) -> str:
        """Generate summary for review output.

        Args:
            findings: List of findings

        Returns:
            Summary string
        """
        if not findings:
            return "No performance or reliability issues found."

        blocking = [f for f in findings if f.severity == "blocking"]
        critical = [f for f in findings if f.severity == "critical"]
        warning = [f for f in findings if f.severity == "warning"]

        parts = [f"Found {len(findings)} performance and reliability issues:"]

        if blocking:
            parts.append(f"  - {len(blocking)} blocking: infinite retries, missing concurrency safeguards")
        if critical:
            parts.append(f"  - {len(critical)} critical: IO amplification, missing backoff, race conditions")
        if warning:
            parts.append(f"  - {len(warning)} warning: code complexity, fire-and-forget tasks")

        return "\n".join(parts)
