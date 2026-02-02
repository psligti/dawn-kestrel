"""Dependency & License Review Subagent implementation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Literal
import re

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Finding,
    MergeGate,
)


DEPENDENCY_SYSTEM_PROMPT = """You are the Dependency & License Review Subagent.

Use this shared behavior:
- If dependency changes are present but file contents are missing, request dependency files and lockfiles.
- Evaluate reproducibility and audit readiness.

Focus:
- new deps added, version bumps, loosened pins
- supply chain risk signals (typosquatting, untrusted packages)
- license compatibility (if enforced)
- build reproducibility (lockfile consistency)

Relevant files:
- pyproject.toml, requirements*.txt, poetry.lock, uv.lock
- CI dependency steps

Checks you may request:
- pip-audit / poetry audit / uv audit
- license checker if repo uses it
- lockfile diff sanity checks

Severity:
- critical/blocking for risky dependency introduced without justification
- critical if pins loosened causing non-repro builds
- warning for safe bumps but missing notes

Return JSON with agent="dependency_license" using the standard schema.
Return JSON only."""


class DependencyLicenseReviewer(BaseReviewerAgent):
    """Reviewer agent for dependency and license compliance."""

    def __init__(self):
        """Initialize the dependency reviewer."""
        pass

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "dependencies"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the dependency reviewer."""
        return DEPENDENCY_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns relevant to dependency review."""
        return [
            "pyproject.toml",
            "requirements*.txt",
            "requirements.txt",
            "setup.py",
            "Pipfile",
            "poetry.lock",
            "uv.lock",
            "setup.cfg",
            "tox.ini",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform dependency and license review.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        findings: List[Finding] = []

        relevant_files = [f for f in context.changed_files if self.is_relevant_to_changes([f])]

        if not relevant_files:
            return ReviewOutput(
                agent=self.get_agent_name(),
                summary="No dependency files changed - review not applicable",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    reasoning="No dependency configuration files in changes",
                ),
                merge_gate=MergeGate(decision="approve"),
            )

        findings.extend(self._check_new_dependencies(context.diff, relevant_files))
        findings.extend(self._check_version_bumps(context.diff, relevant_files))
        findings.extend(self._check_loosened_pins(context.diff, relevant_files))
        findings.extend(self._check_license_compatibility(context.diff, relevant_files))

        severity: Literal["merge", "warning", "critical", "blocking"] = self._compute_severity(findings)

        merge_gate = self._compute_merge_gate(findings, severity)

        summary = self._generate_summary(findings)

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=summary,
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                ignored_files=[f for f in context.changed_files if f not in relevant_files],
                reasoning="All dependency-related files in changes",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )

    def _check_new_dependencies(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for newly added dependencies.

        Args:
            diff: Git diff content
            relevant_files: List of relevant dependency files

        Returns:
            List of findings about new dependencies
        """
        findings: List[Finding] = []
        current_file = None

        for line in diff.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                current_file = line.split("/", 1)[1] if "/" in line else None
                continue

            if not current_file:
                continue

            if current_file.endswith("pyproject.toml") and line.startswith("+"):
                match = re.search(r'(["\'])([\w-]+)["\']\s*=\s*["\']', line)
                if match:
                    dep_name = match.group(2)
                    if re.search(r'^\+.*=\s*["\']\d', line):
                        finding_id = f"dep-new-{dep_name}"
                        findings.append(
                            Finding(
                                id=finding_id,
                                title=f"New dependency added: {dep_name}",
                                severity="warning",
                                confidence="high",
                                owner="dev",
                                estimate="S",
                                evidence=f"File: {current_file} | Added: {dep_name}",
                                risk="New dependency introduces supply chain risk and increases attack surface",
                                recommendation="Justify the need for this dependency and review its security posture",
                            )
                        )

                match2 = re.match(r'^\s*\+\s*["\']([\w-]+)["\']', line)
                if match2:
                    dep_name = match2.group(1)
                    finding_id = f"dep-new-{dep_name}"
                    findings.append(
                        Finding(
                            id=finding_id,
                            title=f"New dependency added: {dep_name}",
                            severity="warning",
                            confidence="high",
                            owner="dev",
                            estimate="S",
                            evidence=f"File: {current_file} | Line: {line.strip()}",
                            risk="New dependency introduces supply chain risk and increases attack surface",
                            recommendation="Justify the need for this dependency and review its security posture",
                        )
                    )

            if "requirements" in current_file and current_file.endswith(".txt") and line.startswith("+"):
                match = re.match(r"^\+\s*([a-zA-Z0-9_-]+)", line.strip())
                if match and not line.strip().startswith("+#"):
                    dep_name = match.group(1)
                    finding_id = f"dep-new-req-{dep_name}"
                    findings.append(
                        Finding(
                            id=finding_id,
                            title=f"New dependency added: {dep_name}",
                            severity="warning",
                            confidence="high",
                            owner="dev",
                            estimate="S",
                            evidence=f"File: {current_file} | Line: {line.strip()}",
                            risk="New dependency introduces supply chain risk and increases attack surface",
                            recommendation="Justify the need for this dependency and review its security posture",
                        )
                    )

        return findings

    def _check_version_bumps(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for version bumps in dependencies.

        Args:
            diff: Git diff content
            relevant_files: List of relevant dependency files

        Returns:
            List of findings about version bumps
        """
        findings: List[Finding] = []
        current_file = None
        line_number = 0

        for line in diff.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                current_file = line.split("/", 1)[1] if "/" in line else None
                line_number = 0
                continue

            if not current_file:
                continue

            line_number += 1

            if current_file.endswith("pyproject.toml") and line.startswith("+"):
                match = re.search(r'([\'"])([\w-]+)(?:==|~=|>=|<=|>|<|===)(\d+\.\d+\.\d+)', line)
                if match:
                    dep_name = match.group(2)
                    version = match.group(3)
                    finding_id = f"dep-bump-{dep_name}"
                    findings.append(
                        Finding(
                            id=finding_id,
                            title=f"Dependency version bumped: {dep_name} to {version}",
                            severity="warning",
                            confidence="medium",
                            owner="dev",
                            estimate="S",
                            evidence=f"File: {current_file} | Line: {line_number} | {line.strip()}",
                            risk=f"Version bump may introduce breaking changes or new bugs",
                            recommendation=f"Review changelog for {dep_name} version {version} and ensure compatibility",
                        )
                    )

        return findings

    def _check_loosened_pins(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for loosened dependency version pins.

        Args:
            diff: Git diff content
            relevant_files: List of relevant dependency files

        Returns:
            List of findings about loosened pins
        """
        findings: List[Finding] = []
        current_file = None
        line_number = 0

        for line in diff.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                current_file = line.split("/", 1)[1] if "/" in line else None
                line_number = 0
                continue

            if not current_file:
                continue

            line_number += 1

            if current_file.endswith("pyproject.toml") and line.startswith("+"):
                match = re.search(r'([\'"])([\w-]+)\^(\d+\.\d+\.\d+)([\'"])', line)
                if match:
                    dep_name = match.group(2)
                    constraint = f"^{match.group(3)}"
                    finding_id = f"dep-loose-{dep_name}"
                    findings.append(
                        Finding(
                            id=finding_id,
                            title=f"Loosened version pin: {dep_name} with {constraint}",
                            severity="critical",
                            confidence="high",
                            owner="dev",
                            estimate="M",
                            evidence=f"File: {current_file} | Line: {line_number} | {line.strip()}",
                            risk="Loosened version pins may cause non-reproducible builds",
                            recommendation="Use exact versions or strict constraints (~=) for reproducibility",
                        )
                    )

        return findings

    def _check_license_compatibility(self, diff: str, relevant_files: List[str]) -> List[Finding]:
        """Check for license compatibility issues.

        Args:
            diff: Git diff content
            relevant_files: List of relevant dependency files

        Returns:
            List of findings about license issues
        """
        findings: List[Finding] = []
        current_file = None
        line_number = 0

        risky_licenses = ["GPL", "AGPL", "LGPL", "MPL", "CDDL"]

        for line in diff.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                current_file = line.split("/", 1)[1] if "/" in line else None
                line_number = 0
                continue

            if not current_file:
                continue

            line_number += 1

            if any(f in current_file for f in ["pyproject.toml", "setup.py", "Pipfile"]):
                if line.startswith("+"):
                    for license_name in risky_licenses:
                        if license_name.lower() in line.lower():
                            finding_id = f"dep-license-{license_name.lower()}"
                            findings.append(
                                Finding(
                                    id=finding_id,
                                    title=f"Potentially incompatible license detected: {license_name}",
                                    severity="critical",
                                    confidence="medium",
                                    owner="dev",
                                    estimate="M",
                                    evidence=f"File: {current_file} | Line: {line_number} | {line.strip()}",
                                    risk=f"{license_name} license may conflict with project license policy",
                                    recommendation=f"Review {license_name} license compatibility and consider alternative with compatible license",
                                )
                            )

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

        for finding in findings:
            if finding.severity == "blocking":
                return "blocking"
            if finding.severity == "critical":
                return "critical"

        return "warning"

    def _compute_merge_gate(self, findings: List[Finding], severity: str) -> MergeGate:
        """Compute merge gate decision based on findings and severity.

        Args:
            findings: List of findings
            severity: Overall severity

        Returns:
            MergeGate with decision and fix lists
        """
        if severity == "blocking":
            must_fix = [f.id for f in findings if f.severity in ["blocking", "critical"]]
            return MergeGate(
                decision="block",
                must_fix=must_fix,
                should_fix=[f.id for f in findings if f.severity == "warning"],
                notes_for_coding_agent=[
                    "Critical dependency license incompatibility detected - review and resolve before merge",
                    "Ensure all dependencies have compatible licenses with project policy",
                ],
            )
        elif severity == "critical":
            must_fix = [f.id for f in findings if f.severity == "critical"]
            return MergeGate(
                decision="needs_changes",
                must_fix=must_fix,
                should_fix=[f.id for f in findings if f.severity == "warning"],
                notes_for_coding_agent=[
                    "Critical dependency issues detected - fix before merging",
                    "Review loosened version pins and license compatibility",
                ],
            )
        elif severity == "warning":
            return MergeGate(
                decision="needs_changes",
                should_fix=[f.id for f in findings],
                notes_for_coding_agent=[
                    "Dependency changes detected - review and update changelog",
                    "Consider adding release notes for version bumps",
                ],
            )
        else:
            return MergeGate(decision="approve")

    def _generate_summary(self, findings: List[Finding]) -> str:
        """Generate review summary.

        Args:
            findings: List of findings

        Returns:
            Summary string
        """
        if not findings:
            return "No dependency issues found"

        blocking = sum(1 for f in findings if f.severity == "blocking")
        critical = sum(1 for f in findings if f.severity == "critical")
        warnings = sum(1 for f in findings if f.severity == "warning")

        parts = []
        if blocking > 0:
            parts.append(f"{blocking} blocking")
        if critical > 0:
            parts.append(f"{critical} critical")
        if warnings > 0:
            parts.append(f"{warnings} warning(s)")

        return f"Found {', '.join(parts)} dependency issue(s) - review required"
