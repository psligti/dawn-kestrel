"""Requirements reviewer subagent for comparing implementation to ticket/PR description."""
from __future__ import annotations
from typing import List, Literal

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import ReviewOutput, Scope, Finding, MergeGate


REQUIREMENTS_SYSTEM_PROMPT = """You are the Requirements Review Subagent.

Use this shared behavior:
- If diff is missing, request it.
- If no ticket/pr description is provided, request it OR proceed by extracting implied requirements from code changes and mark confidence lower.
- Compare stated requirements and acceptance criteria to what was implemented.

Goal:
Confirm the change matches stated requirements and acceptance criteria.

Inputs may include:
- ticket_description or pr_description
- acceptance_criteria
- changed_files
- diff

What to do:
1) Extract explicit/implied requirements from description/criteria.
2) Check the diff implements them.
3) Identify gaps, scope creep, ambiguous behavior.
4) Ensure error cases and edge cases are covered or flagged.

Severity:
- warning: minor mismatch or missing note
- critical: core requirement not met or contradicts requirement
- blocking: change does the wrong thing / breaks a requirement / unsafe default

Return JSON with agent="requirements" using the standard schema.
Return JSON only."""


class RequirementsReviewer(BaseReviewerAgent):
    """Reviewer agent that compares implementation to ticket/PR description."""

    def get_agent_name(self) -> str:
        """Return the name of this reviewer agent."""
        return "requirements"

    def get_system_prompt(self) -> str:
        """Get the system prompt for this reviewer agent."""
        return REQUIREMENTS_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns this reviewer is relevant to."""
        return ["**/*"]

    def _compute_severity(self, findings: List[Finding]) -> Literal["merge", "warning", "critical", "blocking"]:
        """Compute overall severity from findings."""
        if not findings:
            return "merge"
        for f in findings:
            if f.severity == "blocking":
                return "blocking"
        for f in findings:
            if f.severity == "critical":
                return "critical"
        for f in findings:
            if f.severity == "warning":
                return "warning"
        return "merge"

    def _compute_merge_gate(
        self,
        severity: Literal["merge", "warning", "critical", "blocking"],
        findings: List[Finding],
    ) -> MergeGate:
        """Compute merge gate decision from severity and findings."""
        decision: Literal["approve", "needs_changes", "block"]
        must_fix: List[str] = []
        should_fix: List[str] = []
        notes: List[str] = []

        if severity == "blocking":
            decision = "block"
            must_fix = [f.id for f in findings if f.severity == "blocking"]
            notes.append("Critical requirements not met - changes do the wrong thing or break requirements.")
        elif severity == "critical":
            decision = "needs_changes"
            should_fix = [f.id for f in findings if f.severity in ("critical", "warning")]
            notes.append("Core requirements not met - implementation does not match stated requirements.")
        elif severity == "warning":
            decision = "needs_changes"
            should_fix = [f.id for f in findings if f.severity == "warning"]
            notes.append("Minor gaps found between requirements and implementation.")
        else:
            decision = "approve"
            notes.append("Implementation matches stated requirements.")

        return MergeGate(
            decision=decision,
            must_fix=must_fix,
            should_fix=should_fix,
            notes_for_coding_agent=notes,
        )

    def _extract_requirements_from_description(self, description: str) -> List[str]:
        """Extract requirements from ticket or PR description using heuristic patterns."""
        requirements: List[str] = []
        lines = description.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith(("-", "*", "+")) and len(line) > 2:
                requirements.append(line[1:].strip())
            elif line and line[0].isdigit() and (line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."))):
                requirements.append(line[line.find(".") + 1:].strip())
            elif any(keyword in line.lower() for keyword in ["requirement", "should:", "must:", "will:"]):
                requirements.append(line)

        return requirements

    def _check_requirements_coverage(
        self,
        requirements: List[str],
        diff: str,
        changed_files: List[str],
    ) -> List[Finding]:
        """Check if requirements are covered in the diff."""
        findings: List[Finding] = []

        if not requirements:
            return findings

        import re

        diff_lines = diff.split("\n")
        added_lines: List[tuple[str, int]] = []
        current_line = 0

        for line in diff_lines:
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line = int(match.group(1)) - 1
            elif line.startswith("+"):
                current_line += 1
                added_lines.append((line[1:], current_line))
            elif not line.startswith("-") and line.strip():
                current_line += 1

        for idx, requirement in enumerate(requirements):
            requirement_lower = requirement.lower()
            keywords = [w for w in requirement_lower.split() if len(w) > 3]

            found_evidence = False
            evidence_lines: List[tuple[str, int]] = []

            for added_line, line_num in added_lines:
                added_line_lower = added_line.lower()
                if any(keyword in added_line_lower for keyword in keywords):
                    found_evidence = True
                    evidence_lines.append((added_line, line_num))

            if not found_evidence and len(requirements) > 0:
                findings.append(
                    Finding(
                        id=f"REQ-MISSING-{idx:03d}",
                        title=f"Requirement not implemented: {requirement[:50]}...",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="M",
                        evidence=f"Requirement: {requirement}\nNo matching implementation found in diff across {len(changed_files)} changed files.",
                        risk="The requirement may be missed or implemented incorrectly, leading to incomplete feature delivery.",
                        recommendation="Verify if this requirement is implemented but not visible in the diff (e.g., in unchanged files) or add implementation for this requirement.",
                        suggested_patch=None,
                    )
                )
            elif found_evidence and evidence_lines:
                evidence_str = "\n".join(
                    [f"Line {line_num}: {line[:100]}" for line, line_num in evidence_lines[:3]]
                )
                findings.append(
                    Finding(
                        id=f"REQ-FOUND-{idx:03d}",
                        title=f"Requirement appears implemented: {requirement[:50]}...",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"Requirement: {requirement}\nEvidence found:\n{evidence_str}",
                        risk="Requirement appears to be implemented based on code patterns.",
                        recommendation="Manual verification recommended to confirm implementation matches requirement intent.",
                        suggested_patch=None,
                    )
                )

        return findings

    def _check_scope_creep(
        self,
        requirements: List[str],
        diff: str,
        changed_files: List[str],
    ) -> List[Finding]:
        """Check for scope creep - implementation of features beyond stated requirements."""
        findings: List[Finding] = []

        import re

        added_content = "\n".join([line[1:] for line in diff.split("\n") if line.startswith("+")])
        functions = re.findall(r"def\s+(\w+)", added_content)
        classes = re.findall(r"class\s+(\w+)", added_content)

        total_new_items = len(functions) + len(classes)

        if total_new_items > 5 and len(requirements) < 3:
            findings.append(
                Finding(
                    id="REQ-SCOPE-CREEP-001",
                    title="Potential scope creep: many new functions/classes with few stated requirements",
                    severity="warning",
                    confidence="low",
                    owner="dev",
                    estimate="M",
                    evidence=f"Found {total_new_items} new functions/classes but only {len(requirements)} requirements.\n"
                    f"Functions: {', '.join(functions[:5])}{'...' if len(functions) > 5 else ''}\n"
                    f"Classes: {', '.join(classes[:5])}{'...' if len(classes) > 5 else ''}",
                    risk="Implementation may include features beyond the original scope, increasing complexity and potential bugs.",
                    recommendation="Review if all new functions/classes are necessary for the stated requirements. Consider splitting into separate PRs if implementing multiple features.",
                    suggested_patch=None,
                )
            )

        return findings

    def _check_error_cases_covered(
        self,
        requirements: List[str],
        diff: str,
    ) -> List[Finding]:
        """Check if error cases and edge cases are covered."""
        findings: List[Finding] = []

        error_patterns = [
            r"raise\s+\w+",
            r"except\s+\w+",
            r"if\s+.*error",
            r"if\s+.*invalid",
            r"if\s+.*not\s+.*:",
        ]

        import re

        added_content = "\n".join([line[1:] for line in diff.split("\n") if line.startswith("+")])

        error_handling_found = False
        for pattern in error_patterns:
            if re.search(pattern, added_content, re.IGNORECASE):
                error_handling_found = True
                break

        if len(requirements) > 0 and not error_handling_found and "def " in added_content:
            findings.append(
                Finding(
                    id="REQ-ERROR-HANDLING-001",
                    title="No error handling found in implementation",
                    severity="warning",
                    confidence="low",
                    owner="dev",
                    estimate="M",
                    evidence="No raise, except, or error validation patterns found in added code.",
                    risk="Error cases and edge cases may not be handled, leading to crashes or unexpected behavior.",
                    recommendation="Add appropriate error handling for invalid inputs, network failures, and other edge cases.",
                    suggested_patch=None,
                )
            )

        return findings

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform requirements review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        if not context.pr_description:
            return ReviewOutput(
                agent=self.get_agent_name(),
                summary="Requirements review skipped - no PR description provided.",
                severity="merge",
                scope=Scope(
                    relevant_files=context.changed_files,
                    reasoning="No requirements available to verify.",
                ),
                merge_gate=MergeGate(
                    decision="approve",
                    notes_for_coding_agent=[
                        "Add PR description with requirements for automated verification.",
                    ],
                ),
            )

        requirements = self._extract_requirements_from_description(context.pr_description)
        findings: List[Finding] = []

        coverage_findings = self._check_requirements_coverage(
            requirements,
            context.diff,
            context.changed_files,
        )
        findings.extend(coverage_findings)

        scope_findings = self._check_scope_creep(
            requirements,
            context.diff,
            context.changed_files,
        )
        findings.extend(scope_findings)

        error_findings = self._check_error_cases_covered(
            requirements,
            context.diff,
        )
        findings.extend(error_findings)

        severity = self._compute_severity(findings)
        merge_gate = self._compute_merge_gate(severity, findings)

        if not requirements:
            summary = "No explicit requirements found in PR description - cannot verify implementation."
        elif not findings:
            summary = f"All {len(requirements)} requirements appear to be implemented."
        else:
            summary = f"Found {len(findings)} issues across {len(requirements)} requirements."

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=summary,
            severity=severity,
            scope=Scope(
                relevant_files=context.changed_files,
                reasoning="Requirements reviewer analyzes all files to verify implementation matches stated requirements.",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )
