"""Architecture Reviewer agent for checking architectural issues."""
from __future__ import annotations
from typing import List, Literal
import re
import pydantic as pd

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Scope,
    Check,
    Skip,
    Finding,
    MergeGate,
)


class ArchitectureReviewer(BaseReviewerAgent):
    """Reviewer agent specialized in architectural analysis.

    Checks for:
    - Boundary violations (cross-module dependencies)
    - Coupling issues (tight coupling between components)
    - Anti-patterns (god objects, leaky abstractions)
    - Backwards compatibility concerns
    """

    _SYSTEM_PROMPT = """You are the Architecture Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to architecture.
- Decide what checks/tools to run based on what changed; propose minimal targeted checks first.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pyproject.toml, CI workflows, make/just/nox/tox) to propose correct commands.

You specialize in:
- boundaries, layering, dependency direction
- cohesion/coupling, modularity, naming consistency
- data flow correctness (interfaces, contracts, invariants)
- concurrency/async correctness (if applicable)
- config/env separation (settings vs code)
- backwards compatibility and migration concerns
- anti-pattern detection: god objects, leaky abstractions, duplicated logic

Scoping heuristics:
- Relevant when changes include: src/**, app/**, domain/**, services/**, core/**, libs/**,
  API route layers, dependency injection, orchestration layers, agent/skills/tools frameworks.
- Often ignore: docs-only, comments-only, formatting-only changes (unless refactor hides risk).

Checks you may request (only if relevant):
- Type checks (mypy/pyright) when interfaces changed
- Unit tests when behavior changed
- Targeted integration tests when contracts or IO boundaries changed

Architecture review must answer:
1) What is the intended design change?
2) Does the change preserve clear boundaries and a single source of truth?
3) Does it introduce hidden coupling or duplicated logic?
4) Are there new edge cases, failure modes, or lifecycle issues?

Common blocking issues:
- circular dependencies introduced
- public API/contract changed without updating call sites/tests
- configuration hard-coded into business logic
- breaking changes without migration path

Output MUST be valid JSON only with this schema:

{
  "agent": "architecture",
  "summary": "...",
  "severity": "merge|warning|critical|blocking",
  "scope": { "relevant_files": [], "ignored_files": [], "reasoning": "..." },
  "checks": [{ "name": "...", "required": true, "commands": [], "why": "...", "expected_signal": "..." }],
  "skips": [{ "name": "...", "why_safe": "...", "when_to_run": "..." }],
  "findings": [{
    "id": "ARCH-001",
    "title": "...",
    "severity": "warning|critical|blocking",
    "confidence": "high|medium|low",
    "owner": "dev|docs|devops|security",
    "estimate": "S|M|L",
    "evidence": "...",
    "risk": "...",
    "recommendation": "...",
    "suggested_patch": "..."
  }],
  "merge_gate": { "decision": "approve|needs_changes|block", "must_fix": [], "should_fix": [], "notes_for_coding_agent": [] }
}

Rules:
- If there are no relevant files, return severity "merge" and note "no relevant changes".
- Tie every finding to evidence. No vague statements.
- If you recommend skipping a check, explain why it's safe.
Return JSON only.
"""

    def get_agent_name(self) -> str:
        """Return the agent name."""
        return "architecture"

    def get_system_prompt(self) -> str:
        """Return the system prompt for this reviewer agent."""
        return self._SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Return file patterns this reviewer is relevant to."""
        return ["**/*.py"]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform architectural review on the given context.

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
                summary="No relevant architectural changes detected.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    ignored_files=ignored_files,
                    reasoning="No Python files changed that require architectural review.",
                ),
                merge_gate=MergeGate(decision="approve"),
            )

        findings = self._analyze_architecture(context.diff, relevant_files)
        severity: Literal["merge", "warning", "critical", "blocking"] = self._compute_severity(findings)
        merge_gate = self._compute_merge_gate(findings, severity)

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=self._generate_summary(findings, severity),
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                ignored_files=ignored_files,
                reasoning=f"Reviewed {len(relevant_files)} Python file(s) for architectural issues.",
            ),
            findings=findings,
            merge_gate=merge_gate,
        )

    def _analyze_architecture(
        self, diff: str, relevant_files: List[str]
    ) -> List[Finding]:
        """Analyze diff for architectural issues.

        Args:
            diff: Unified diff string
            relevant_files: List of relevant file paths

        Returns:
            List of architectural findings
        """
        findings = []

        findings.extend(self._check_circular_imports(diff))
        findings.extend(self._check_boundary_violations(diff, relevant_files))
        findings.extend(self._check_tight_coupling(diff))
        findings.extend(self._check_hardcoded_config(diff))
        findings.extend(self._check_god_objects(diff))
        findings.extend(self._check_breaking_changes(diff))

        return findings

    def _check_circular_imports(self, diff: str) -> List[Finding]:
        """Check for potential circular imports.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about circular imports
        """
        findings = []
        import_lines = []

        for line in diff.split("\n"):
            if line.strip().startswith(("+", "-")):
                stripped = line[1:].strip()
                if stripped.startswith(("import ", "from ")):
                    import_lines.append(line)

        file_imports = {}
        for line in import_lines:
            if line.startswith("+"):
                match = re.search(r"^\+\s*from\s+(\S+)", line[1:])
                if match:
                    module = match.group(1)
                    file_match = re.search(r"^\+\+\+\s*(\S+)", diff)
                    if file_match:
                        file_path = file_match.group(1)
                        if file_path not in file_imports:
                            file_imports[file_path] = []
                        file_imports[file_path].append(module)

        for file_a, modules_a in file_imports.items():
            for file_b, modules_b in file_imports.items():
                if file_a != file_b:
                    for mod_a in modules_a:
                        for mod_b in modules_b:
                            mod_a_parts = mod_a.split(".")
                            mod_b_parts = mod_b.split(".")

                            if (
                                len(mod_a_parts) > 1
                                and len(mod_b_parts) > 1
                                and mod_a_parts[0] == mod_b_parts[0]
                            ):
                                findings.append(
                                    Finding(
                                        id="ARCH-CIRCULAR-001",
                                        title="Potential circular dependency detected",
                                        severity="critical",
                                        confidence="medium",
                                        owner="dev",
                                        estimate="M",
                                        evidence=f"Cross-module imports found:\n{file_a} imports from {mod_a}\n{file_b} imports from {mod_b}",
                                        risk="Circular dependencies can cause import-time errors and make code hard to test.",
                                        recommendation="Refactor to use dependency injection or introduce a new module to break the cycle.",
                                        suggested_patch=None,
                                    )
                                )
                                break

        return findings

    def _check_boundary_violations(
        self, diff: str, relevant_files: List[str]
    ) -> List[Finding]:
        """Check for boundary violations (cross-layer dependencies).

        Args:
            diff: Unified diff string
            relevant_files: List of relevant file paths

        Returns:
            List of findings about boundary violations
        """
        findings = []

        layer_patterns = {
            "presentation": ["handlers", "views", "api", "routes", "controllers"],
            "application": ["services", "use_cases", "workflows", "orchestrators"],
            "domain": ["entities", "models", "domain", "value_objects"],
            "infrastructure": ["repositories", "adapters", "external", "db", "storage"],
        }

        for file_path in relevant_files:
            file_layer = None
            for layer, patterns in layer_patterns.items():
                if any(pattern in file_path.lower() for pattern in patterns):
                    file_layer = layer
                    break

            if not file_layer:
                continue

            for line in diff.split("\n"):
                if not line.startswith("+"):
                    continue

                stripped = line[1:].strip()
                if not stripped.startswith(("import ", "from ")):
                    continue

                if "from infrastructure" in stripped and file_layer == "presentation":
                    line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                    line_num = line_match.group(1) if line_match else "unknown"

                    findings.append(
                        Finding(
                            id="ARCH-BOUNDARY-001",
                            title="Boundary violation: presentation imports infrastructure",
                            severity="warning",
                            confidence="high",
                            owner="dev",
                            estimate="M",
                            evidence=f"{file_path}:{line_num}\n{stripped}",
                            risk="Direct infrastructure imports in presentation layer violate clean architecture principles.",
                            recommendation="Introduce an application service or repository interface to abstract infrastructure concerns.",
                            suggested_patch=None,
                        )
                    )

        return findings

    def _check_tight_coupling(self, diff: str) -> List[Finding]:
        """Check for tight coupling between components.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about tight coupling
        """
        findings = []
        module_imports = {}

        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            stripped = line[1:].strip()
            if not stripped.startswith(("import ", "from ")):
                continue

            if stripped.startswith("from "):
                match = re.match(r"from\s+(\S+)\s+import", stripped)
                if match:
                    module = match.group(1)
                    if module not in module_imports:
                        module_imports[module] = 0
                    module_imports[module] += 1

        for module, count in module_imports.items():
            if count >= 5:
                findings.append(
                    Finding(
                        id="ARCH-COUPLING-001",
                        title=f"Potential tight coupling: {count} imports from {module}",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"Module '{module}' imported {count} times in changed files",
                        risk="High coupling to specific module makes code fragile to changes in that module.",
                        recommendation="Consider introducing a facade or abstraction layer to reduce coupling.",
                        suggested_patch=None,
                    )
                )

        return findings

    def _check_hardcoded_config(self, diff: str) -> List[Finding]:
        """Check for hardcoded configuration values.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about hardcoded configuration
        """
        findings = []

        hardcoded_patterns = [
            (r'PORT\s*=\s*\d{4,5}', "hardcoded port"),
            (r'HOST\s*=\s*["\']localhost["\']', "hardcoded host"),
            (r'URL\s*=\s*["\']http[s]?://', "hardcoded URL"),
            (r'API_KEY\s*=\s*["\'][^"\']+["\']', "hardcoded API key"),
            (r'SECRET\s*=\s*["\'][^"\']+["\']', "hardcoded secret"),
            (r'TIMEOUT\s*=\s*\d+', "hardcoded timeout"),
        ]

        for line in diff.split("\n"):
            if not line.startswith("+"):
                continue

            for pattern, description in hardcoded_patterns:
                if re.search(pattern, line[1:], re.IGNORECASE):
                    line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                    line_num = line_match.group(1) if line_match else "unknown"

                    findings.append(
                        Finding(
                            id="ARCH-CONFIG-001",
                            title=f"Hardcoded configuration: {description}",
                            severity="critical",
                            confidence="high",
                            owner="dev",
                            estimate="S",
                            evidence=f"Line {line_num}: {line[1:]}",
                            risk="Hardcoded configuration should be in environment variables or config files.",
                            recommendation="Move configuration to environment variables or config module.",
                            suggested_patch=f"# Move to config file or environment variable\n# {line[1:]}",
                        )
                    )
                    break

        return findings

    def _check_god_objects(self, diff: str) -> List[Finding]:
        """Check for potential god objects (very large classes/methods).

        Args:
            diff: Unified diff string

        Returns:
            List of findings about god objects
        """
        findings = []
        current_class = None
        method_count = 0

        for line in diff.split("\n"):
            stripped = line[1:].strip() if line.startswith(("+", "-")) else line.strip()

            if stripped.startswith("class "):
                if method_count > 20:
                    findings.append(
                        Finding(
                            id="ARCH-GOD-001",
                            title=f"Potential god class: {current_class} with {method_count} methods",
                            severity="warning",
                            confidence="medium",
                            owner="dev",
                            estimate="L",
                            evidence=f"Class {current_class} has {method_count} methods detected in changes",
                            risk="God classes violate Single Responsibility Principle and are hard to maintain.",
                            recommendation="Consider splitting into multiple smaller classes with focused responsibilities.",
                            suggested_patch=None,
                        )
                    )

                match = re.match(r"class\s+(\w+)", stripped)
                if match:
                    current_class = match.group(1)
                    method_count = 0
                else:
                    current_class = None
                    method_count = 0

            if stripped.startswith("def ") and current_class:
                params = re.findall(r"(\w+)\s*,", stripped)
                if len(params) > 7:
                    findings.append(
                        Finding(
                            id="ARCH-GOD-002",
                            title=f"Method with too many parameters: {stripped[:50]}",
                            severity="warning",
                            confidence="high",
                            owner="dev",
                            estimate="M",
                            evidence=f"Method has {len(params)} parameters",
                            risk="Methods with many parameters indicate tight coupling and poor design.",
                            recommendation="Consider introducing a parameter object or using named parameters.",
                            suggested_patch=None,
                        )
                    )
                method_count += 1

        return findings

    def _check_breaking_changes(self, diff: str) -> List[Finding]:
        """Check for breaking API changes.

        Args:
            diff: Unified diff string

        Returns:
            List of findings about breaking changes
        """
        findings = []

        breaking_patterns = [
            (r"^\-\s*def\s+(public_|api_)", "removed public function"),
            (r"^\-\s*class\s+(Public|API)", "removed public class"),
            (r"^\-\s*@.*(?:public|api|external)", "removed public decorator"),
        ]

        for line in diff.split("\n"):
            if not line.startswith("-"):
                continue

            for pattern, description in breaking_patterns:
                if re.search(pattern, line[1:]):
                    line_match = re.search(r"@@\s+\-(\d+),\d+\s+\+\d+,\d+\s+@@", diff)
                    line_num = line_match.group(1) if line_match else "unknown"

                    findings.append(
                        Finding(
                            id="ARCH-BREAKING-001",
                            title=f"Potential breaking change: {description}",
                            severity="blocking",
                            confidence="high",
                            owner="dev",
                            estimate="M",
                            evidence=f"Line {line_num}: {line[1:]}",
                            risk="Removing public API breaks existing consumers without migration path.",
                            recommendation="Provide deprecation warning first, or maintain backward compatibility.",
                            suggested_patch=None,
                        )
                    )
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
            return "No architectural issues detected. Changes follow good architectural principles."

        by_severity = {"blocking": 0, "critical": 0, "warning": 0}
        for finding in findings:
            by_severity[finding.severity] += 1

        parts = [
            f"Architectural review complete.",
            f"Found {len(findings)} issue(s):",
        ]

        if by_severity["blocking"] > 0:
            parts.append(f"- {by_severity['blocking']} blocking")
        if by_severity["critical"] > 0:
            parts.append(f"- {by_severity['critical']} critical")
        if by_severity["warning"] > 0:
            parts.append(f"- {by_severity['warning']} warning")

        return " ".join(parts)
