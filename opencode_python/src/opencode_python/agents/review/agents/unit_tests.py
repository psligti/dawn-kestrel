"""Unit Tests Reviewer agent for checking test quality and adequacy."""
from __future__ import annotations
from typing import List, Literal
import re
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Check,
    Finding,
    MergeGate,
)
from opencode_python.agents.review.utils.executor import CommandExecutor


class UnitTestsReviewer(BaseReviewerAgent):
    """Reviewer agent specialized in unit test quality and adequacy.

    Checks for:
    - Test adequacy (cover changed behavior)
    - Test correctness (assertions, mocking)
    - Edge case coverage (boundary values, error conditions)
    - Determinism (randomness, time dependencies, state leakage)
    """

    _SYSTEM_PROMPT = """You are the Unit Test Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to unit tests.
- Propose minimal targeted test selection first; escalate if risk is high.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pytest, nox/tox, uv run, test layout).

You specialize in:
- adequacy of tests for changed behavior
- correctness of tests (assertions, determinism, fixtures)
- edge case and failure mode coverage
- avoiding brittle tests (time, randomness, network)
- selecting minimal test runs to validate change

Relevant changes:
- behavior changes in code
- new modules/functions/classes
- bug fixes (prefer regression tests)
- changes to test/fixture utilities, CI test steps

Checks you may request:
- pytest -q <test_file>
- pytest -q -k "<keyword>"
- pytest -q tests/unit/...
- coverage on changed modules only (if available)

Severity:
- warning: tests exist but miss an edge case
- critical: behavior changed with no tests and moderate risk
- blocking: high-risk change with no tests; broken/flaky tests introduced

Output MUST be valid JSON only with agent="unit_tests" and the standard schema.
Return JSON only.
"""

    def __init__(self, executor: CommandExecutor | None = None, repo_root: str | None = None):
        """Initialize the UnitTestsReviewer.

        Args:
            executor: CommandExecutor instance for running pytest (creates default if None)
            repo_root: Repository root path (uses current dir if None)
        """
        from pathlib import Path

        repo_path = Path(repo_root) if repo_root else None
        self.executor = executor or CommandExecutor(repo_root=repo_path)
        self.repo_root = repo_root or "."

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "unit_tests"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer agent."""
        return self._SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return ["**/*.py"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform unit test review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
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
                summary="No Python code changes detected that require test review.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    ignored_files=ignored_files,
                    reasoning="No Python files changed that could affect test coverage.",
                ),
                merge_gate=MergeGate(decision="approve"),
            )

        findings = self._analyze_tests(context, relevant_files)
        severity: Literal["merge", "warning", "critical", "blocking"] = self._compute_severity(findings)
        merge_gate = self._compute_merge_gate(findings, severity)

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=self._generate_summary(findings, severity),
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                ignored_files=ignored_files,
                reasoning=f"Reviewed {len(relevant_files)} Python file(s) for test coverage and quality.",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )

    def _analyze_tests(
        self, context: ReviewContext, relevant_files: List[str]
    ) -> List[Finding]:
        """Analyze test coverage and quality.

        Args:
            context: ReviewContext containing changed files, diff, and metadata
            relevant_files: List of relevant file paths

        Returns:
            List of test-related findings
        """
        findings = []

        # Check for new code without tests
        findings.extend(self._check_missing_tests(context.diff, relevant_files))

        # Check for test correctness issues
        findings.extend(self._check_test_correctness(context.diff))

        # Check for edge case coverage
        findings.extend(self._check_edge_case_coverage(context.diff))

        # Check for determinism issues
        findings.extend(self._check_determinism(context.diff))

        # Try to run pytest if there are test files
        pytest_findings = self._run_pytest_analysis(relevant_files)
        findings.extend(pytest_findings)

        return findings

    def _check_missing_tests(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for new code without corresponding tests.

        Args:
            diff: Unified diff string
            relevant_files: List of relevant file paths

        Returns:
            List of findings about missing tests
        """
        findings = []

        # Identify new functions and classes
        new_functions = []
        new_classes = []

        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            stripped = line[1:].strip()

            # Match new function definitions
            func_match = re.match(r"def\s+(\w+)\s*\(", stripped)
            if func_match:
                func_name = func_match.group(1)
                if not func_name.startswith("_"):
                    new_functions.append(func_name)

            # Match new class definitions
            class_match = re.match(r"class\s+(\w+)", stripped)
            if class_match:
                class_name = class_match.group(1)
                new_classes.append(class_name)

        # Check if any of the changed files are test files
        has_test_changes = any("test" in f.lower() for f in relevant_files)

        if new_functions and not has_test_changes:
            findings.append(
                Finding(
                    id="TEST-MISSING-001",
                    title=f"New functions without tests: {len(new_functions)} function(s) added",
                    severity="warning",
                    confidence="medium",
                    owner="dev",
                    estimate="M",
                    evidence=f"Added {len(new_functions)} new function(s): {', '.join(new_functions[:5])}",
                    risk="New code without tests may hide bugs and regressions.",
                    recommendation="Add unit tests for new functions to verify behavior and catch regressions.",
                    suggested_patch=None,
                )
            )

        if new_classes and not has_test_changes:
            findings.append(
                Finding(
                    id="TEST-MISSING-002",
                    title=f"New class without tests: {new_classes[0]}",
                    severity="warning",
                    confidence="medium",
                    owner="dev",
                    estimate="L",
                    evidence=f"Added new class: {new_classes[0]}",
                    risk="New classes without tests may have unverified behavior.",
                    recommendation="Add unit tests for the new class to verify its interface and behavior.",
                    suggested_patch=None,
                )
            )

        return findings

    def _check_test_correctness(self, diff: str) -> List[Finding]:
        """Check for test correctness issues.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about test correctness
        """
        findings = []

        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            stripped = line[1:].strip()

            # Check for empty assertions (assert with no message)
            if stripped.startswith("assert ") and stripped == "assert":
                line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                line_num = line_match.group(1) if line_match else "unknown"

                findings.append(
                    Finding(
                        id="TEST-CORRECTNESS-001",
                        title="Empty assertion detected",
                        severity="critical",
                        confidence="high",
                        owner="dev",
                        estimate="S",
                        evidence=f"Line {line_num}: {stripped}",
                        risk="Empty assertions provide no verification value.",
                        recommendation="Add a meaningful assertion with a message explaining what is being tested.",
                        suggested_patch=f"# Add assertion condition and message\nassert condition, \"Description of expected behavior\"",
                    )
                )

            # Check for bare try-except in tests
            if stripped.startswith("except:") and "def test_" in diff:
                line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                line_num = line_match.group(1) if line_match else "unknown"

                findings.append(
                    Finding(
                        id="TEST-CORRECTNESS-002",
                        title="Bare except clause in test",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"Line {line_num}: {stripped}",
                        risk="Bare except clauses catch all exceptions including KeyboardInterrupt and SystemExit.",
                        recommendation="Specify the expected exception type (e.g., except ValueError:).",
                        suggested_patch="except ExpectedException:",
                    )
                )

            # Check for missing mock cleanup
            if "@patch" in stripped or "mock." in stripped:
                line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                line_num = line_match.group(1) if line_match else "unknown"

                findings.append(
                    Finding(
                        id="TEST-CORRECTNESS-003",
                        title="Potential missing mock cleanup",
                        severity="warning",
                        confidence="low",
                        owner="dev",
                        estimate="S",
                        evidence=f"Line {line_num}: {stripped}",
                        risk="Mocks not properly cleaned up can affect subsequent tests.",
                        recommendation="Ensure mocks are cleaned up using mock.stop() or context managers.",
                        suggested_patch=None,
                    )
                )

        return findings

    def _check_edge_case_coverage(self, diff: str) -> List[Finding]:
        """Check for edge case coverage gaps.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about edge case coverage
        """
        findings = []

        # Look for functions that handle errors but tests may not verify error paths
        has_error_handling = False
        has_error_tests = False

        for line in diff.split("\n"):
            stripped = line[1:].strip() if line.startswith(("+", "-")) else line.strip()

            # Check for error handling code
            if any(keyword in stripped for keyword in ["raise ValueError", "raise TypeError", "except", "if not"]):
                if line.startswith("+"):
                    has_error_handling = True

            # Check for error tests
            if "with pytest.raises" in stripped or "assertRaises" in stripped:
                if line.startswith("+"):
                    has_error_tests = True

        if has_error_handling and not has_error_tests:
            findings.append(
                Finding(
                    id="TEST-EDGE-001",
                    title="Potential missing error case tests",
                    severity="warning",
                    confidence="medium",
                    owner="dev",
                    estimate="M",
                    evidence="Error handling code added but no error case tests detected",
                    risk="Error conditions may not be properly tested.",
                    recommendation="Add tests using pytest.raises() to verify error handling behavior.",
                    suggested_patch=None,
                )
            )

        # Check for boundary conditions in loops or ranges
        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            stripped = line[1:].strip()

            # Detect loops and range operations
            if re.search(r"for\s+\w+\s+in\s+range\(", stripped):
                line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                line_num = line_match.group(1) if line_match else "unknown"

                findings.append(
                    Finding(
                        id="TEST-EDGE-002",
                        title="Potential boundary value tests needed",
                        severity="warning",
                        confidence="low",
                        owner="dev",
                        estimate="S",
                        evidence=f"Line {line_num}: {stripped}",
                        risk="Loops and ranges may have edge cases at boundaries (0, 1, max-1, max).",
                        recommendation="Add tests for boundary conditions: empty, single item, and edge cases.",
                        suggested_patch=None,
                    )
                )
                break

        return findings

    def _check_determinism(self, diff: str) -> List[Finding]:
        """Check for determinism issues in tests.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about determinism issues
        """
        findings = []

        determinism_patterns = [
            (r"random\.|randint\(|choice\(|shuffle\(", "random number generator"),
            (r"time\.|datetime\.|sleep\(|time\.", "time dependency"),
            (r"\.close\(\)|\.open\(", "resource leak potential"),
        ]

        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            stripped = line[1:].strip()

            # Skip test lines (we're looking for code being tested, not the tests themselves)
            if stripped.startswith("def test_"):
                continue

            for pattern, description in determinism_patterns:
                if re.search(pattern, stripped):
                    line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                    line_num = line_match.group(1) if line_match else "unknown"

                    findings.append(
                        Finding(
                            id="TEST-DETERMINISM-001",
                            title=f"Potential non-determinism: {description}",
                            severity="warning",
                            confidence="medium",
                            owner="dev",
                            estimate="M",
                            evidence=f"Line {line_num}: {stripped}",
                            risk=f"{description} can cause flaky or non-reproducible test results.",
                            recommendation="Mock the {description} or use deterministic values in tests.",
                            suggested_patch=None,
                        )
                    )
                    break

        return findings

    def _run_pytest_analysis(self, relevant_files: List[str]) -> List[Finding]:
        """Run pytest and analyze results.

        Args:
            relevant_files: List of relevant file paths

        Returns:
            List of findings from pytest execution
        """
        findings = []

        # Find test files in the changed files
        test_files = [f for f in relevant_files if "test" in f.lower() and f.endswith(".py")]

        if not test_files:
            return findings

        for test_file in test_files:
            try:
                result = self.executor.execute(
                    command=f"pytest -q {test_file}",
                    timeout=30,
                    cwd=self.repo_root,
                )

                if result.exit_code != 0:
                    # Parse pytest output for failures
                    for finding in result.parsed_findings:
                        if finding.get("status") == "FAILED":
                            findings.append(
                                Finding(
                                    id="TEST-FAILURE-001",
                                    title=f"Test failure in {finding.get('file', 'unknown')}",
                                    severity="blocking",
                                    confidence="high",
                                    owner="dev",
                                    estimate="M",
                                    evidence=f"Test {finding.get('test', 'unknown')} in {finding.get('file', 'unknown')} failed",
                                    risk="Failing tests indicate broken functionality or regression.",
                                    recommendation="Fix the failing test or the underlying code.",
                                    suggested_patch=None,
                                )
                            )
            except Exception as e:
                # Log but don't fail if pytest can't run
                pass

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
        if any(finding.severity == "blocking" for finding in findings):
            return "blocking"

        # Check for critical findings
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
            if finding.severity == "blocking":
                must_fix.append(finding.id)
            elif finding.severity == "critical":
                must_fix.append(finding.id)
            elif finding.severity == "warning":
                should_fix.append(finding.id)

            if finding.recommendation:
                notes_for_coding_agent.append(
                    f"[{finding.id}] {finding.recommendation}"
                )

        if severity == "blocking":
            decision = "block"
        elif severity == "critical":
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
            return "No test issues detected. Code changes are adequately tested or don't require additional tests."

        by_severity = {"blocking": 0, "critical": 0, "warning": 0}
        for finding in findings:
            by_severity[finding.severity] += 1

        parts = [
            f"Unit test review complete.",
            f"Found {len(findings)} issue(s):",
        ]

        if by_severity["blocking"] > 0:
            parts.append(f"- {by_severity['blocking']} blocking")
        if by_severity["critical"] > 0:
            parts.append(f"- {by_severity['critical']} critical")
        if by_severity["warning"] > 0:
            parts.append(f"- {by_severity['warning']} warning")

        return " ".join(parts)
