"""Release & Changelog Review Subagent.

Reviews code changes for release hygiene including:
- CHANGELOG updates for new features
- Version bumps (major, minor, patch)
- Breaking changes documentation
- Migration guides
"""

from __future__ import annotations
from typing import List, Optional
import re
from pathlib import Path

from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    ReviewOutput,
    Finding,
    Scope,
    MergeGate,
    Check,
    Skip,
)


SYSTEM_PROMPT = """You are the Release & Changelog Review Subagent.

Use this shared behavior:
- If user-visible behavior changes, ensure release hygiene artifacts are updated.
- If no changelog/versioning policy exists, note it and adjust severity.

Goal:
Ensure user-visible changes are communicated and release hygiene is maintained.

Relevant:
- CLI flags changed
- outputs changed (schemas, logs users rely on)
- breaking changes
- version bump / changelog / migration docs

Checks you may request:
- CHANGELOG presence/update
- version bump policy checks
- help text / docs updated

Severity:
- warning for missing changelog entry
- critical for breaking change without migration note

Return JSON with agent="release_changelog" using the standard schema.
Return JSON only."""


def _extract_version_from_toml(content: str) -> Optional[tuple[int, int, int, int]]:
    """Extract version from pyproject.toml or setup.py content.

    Args:
        content: File content

    Returns:
        Tuple of (major, minor, patch, line_number) or None if not found
    """
    toml_match = re.search(r'version\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if toml_match:
        major, minor, patch = map(int, toml_match.groups())
        line_num = content[:toml_match.start()].count('\n') + 1
        return (major, minor, patch, line_num)

    setup_match = re.search(r'version\s*=\s*["\'](\d+)\.(\d+)\.(\d+)["\']', content)
    if setup_match:
        major, minor, patch = map(int, setup_match.groups())
        line_num = content[:setup_match.start()].count('\n') + 1
        return (major, minor, patch, line_num)

    return None


def _detect_breaking_changes(diff: str) -> List[dict]:
    """Detect potential breaking changes in diff.

    Args:
        diff: Git diff content

    Returns:
        List of dicts with file_path, line_number, change_type
    """
    breaking_patterns = [
        (r'^[-].*def\s+\w+\([^)]*\)\s*->\s*\w+:', 'function signature change'),
        (r'^[-].*class\s+\w+\([^)]*\):', 'class signature change'),
        (r'^[-].*@\w+\.setter', 'property removed'),
        (r'^[-].*def\s+__\w+__', 'magic method removed'),
        (r'^[-].*\s+\w+\s*:', 'field removed from class/dataclass'),
    ]

    findings = []
    current_file = None

    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            match = re.search(r'b/(.+)', line)
            if match:
                current_file = match.group(1)

        if current_file and not current_file.endswith('.py'):
            continue

        for pattern, change_type in breaking_patterns:
            if re.search(pattern, line):
                line_num = 1
                match = re.search(r'@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@', line)
                if not match:
                    prev_lines = diff.split('\n')
                    current_idx = prev_lines.index(line)
                    for i in range(current_idx - 1, max(0, current_idx - 10), -1):
                        context_match = re.search(r'@@\s+-\d+(?:,\d+)?\s+\+(\d+)', prev_lines[i])
                        if context_match:
                            line_num = int(context_match.group(1))
                            break

                findings.append({
                    'file_path': current_file,
                    'line_number': line_num,
                    'change_type': change_type,
                    'diff_line': line,
                })

    return findings


def _detect_api_changes(diff: str) -> List[dict]:
    """Detect API changes in diff.

    Args:
        diff: Git diff content

    Returns:
        List of dicts with file_path, line_number, change_type
    """
    api_patterns = [
        (r'^[+].*def\s+\w+\([^)]*\)\s*->\s*\w+:', 'new public function'),
        (r'^[+].*class\s+\w+\([^)]*\):', 'new public class'),
        (r'^[-].*def\s+\w+\([^)]*\)\s*->\s*\w+:', 'removed public function'),
        (r'^[-].*class\s+\w+\([^)]*\):', 'removed public class'),
    ]

    findings = []
    current_file = None

    for line in diff.split('\n'):
        if line.startswith('diff --git'):
            match = re.search(r'b/(.+)', line)
            if match:
                current_file = match.group(1)

        if current_file and not current_file.endswith('.py'):
            continue

        for pattern, change_type in api_patterns:
            if re.search(pattern, line):
                line_num = 1
                match = re.search(r'@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@', line)
                if not match:
                    prev_lines = diff.split('\n')
                    current_idx = prev_lines.index(line)
                    for i in range(current_idx - 1, max(0, current_idx - 10), -1):
                        context_match = re.search(r'@@\s+-\d+(?:,\d+)?\s+\+(\d+)', prev_lines[i])
                        if context_match:
                            line_num = int(context_match.group(1))
                            break

                findings.append({
                    'file_path': current_file,
                    'line_number': line_num,
                    'change_type': change_type,
                    'diff_line': line,
                })

    return findings


def _check_changelog_exists(
    changed_files: List[str],
    repo_root: str,
) -> tuple[bool, Optional[str], Optional[int]]:
    """Check if changelog file exists and was changed.

    Args:
        changed_files: List of changed files
        repo_root: Repository root

    Returns:
        Tuple of (exists, file_path, line_number_of_latest_entry)
    """
    changelog_patterns = ["CHANGELOG*", "CHANGES*", "HISTORY*"]

    for pattern in changelog_patterns:
        for file_path in changed_files:
            if re.match(pattern.replace('*', '.*'), Path(file_path).name):
                full_path = Path(repo_root) / file_path
                if full_path.exists():
                    content = full_path.read_text()
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if re.match(r'^##\s+\[?\d+\.\d+\.\d+', line):
                            return (True, file_path, i)
                    return (True, file_path, 1)

    return (False, None, None)


def _check_version_bump(
    changed_files: List[str],
    repo_root: str,
) -> Optional[tuple[str, int, int, int, int]]:
    """Check if version file was bumped.

    Args:
        changed_files: List of changed files
        repo_root: Repository root

    Returns:
        Tuple of (file_path, major, minor, patch, line_number) or None
    """
    version_files = ["pyproject.toml", "setup.py", "setup.cfg", "__init__.py"]

    for file_path in changed_files:
        if Path(file_path).name in version_files:
            full_path = Path(repo_root) / file_path
            if full_path.exists():
                content = full_path.read_text()
                version_info = _extract_version_from_toml(content)
                if version_info:
                    major, minor, patch, line_num = version_info
                    return (file_path, major, minor, patch, line_num)

    return None


class ReleaseChangelogReviewer(BaseReviewerAgent):
    """Reviewer agent for release hygiene and changelog compliance."""

    def __init__(self) -> None:
        self.agent_name = "release_changelog"

    def get_agent_name(self) -> str:
        return self.agent_name

    def get_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        return [
            "CHANGELOG*",
            "CHANGES*",
            "HISTORY*",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "**/__init__.py",
            "**/*.py",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform changelog/release review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        findings: List[Finding] = []
        relevant_files: List[str] = []
        ignored_files: List[str] = []

        for file_path in context.changed_files:
            if not self.is_relevant_to_changes([file_path]):
                ignored_files.append(file_path)
                continue

            relevant_files.append(file_path)

        breaking_changes = _detect_breaking_changes(context.diff)
        api_changes = _detect_api_changes(context.diff)

        changelog_exists, changelog_path, changelog_line = _check_changelog_exists(
            context.changed_files, context.repo_root
        )

        version_info = _check_version_bump(context.changed_files, context.repo_root)

        if breaking_changes:
            if not changelog_exists:
                findings.append(
                    Finding(
                        id="release-no-changelog-for-breaking",
                        title="Breaking changes detected but no CHANGELOG found",
                        severity="critical",
                        confidence="high",
                        owner="dev",
                        estimate="M",
                        evidence=f"Breaking changes found in {len(breaking_changes)} locations but no CHANGELOG file exists. "
                        f"Examples: {breaking_changes[0]['file_path']}:{breaking_changes[0]['line_number']} - {breaking_changes[0]['change_type']}",
                        risk="Users will not be aware of breaking changes, leading to integration failures",
                        recommendation="Create a CHANGELOG file and document all breaking changes with migration guides",
                    )
                )
            elif changelog_path not in context.changed_files:
                findings.append(
                    Finding(
                        id="release-changelog-not-updated-for-breaking",
                        title="Breaking changes detected but CHANGELOG not updated",
                        severity="critical",
                        confidence="high",
                        owner="dev",
                        estimate="M",
                        evidence=f"Breaking changes found in {len(breaking_changes)} locations but CHANGELOG not in changed files. "
                        f"Example: {breaking_changes[0]['file_path']}:{breaking_changes[0]['line_number']} - {breaking_changes[0]['change_type']}",
                        risk="Users will not be aware of breaking changes, leading to integration failures",
                        recommendation=f"Update {changelog_path} to document breaking changes and provide migration instructions",
                    )
                )

        if api_changes:
            if not changelog_exists:
                findings.append(
                    Finding(
                        id="release-no-changelog-for-api",
                        title="API changes detected but no CHANGELOG found",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"API changes found in {len(api_changes)} locations but no CHANGELOG file exists. "
                        f"Example: {api_changes[0]['file_path']}:{api_changes[0]['line_number']} - {api_changes[0]['change_type']}",
                        risk="Users may not be aware of API changes",
                        recommendation="Consider creating a CHANGELOG file to document API changes for users",
                    )
                )
            elif changelog_path not in context.changed_files:
                public_api_changes = [
                    c for c in api_changes
                    if not c['file_path'].endswith('_test.py')
                    and '/tests/' not in c['file_path']
                    and '/test/' not in c['file_path']
                ]

                if public_api_changes:
                    findings.append(
                        Finding(
                            id="release-changelog-not-updated-for-api",
                            title="API changes detected but CHANGELOG not updated",
                            severity="warning",
                            confidence="medium",
                            owner="dev",
                            estimate="S",
                            evidence=f"Public API changes found in {len(public_api_changes)} locations but CHANGELOG not in changed files. "
                            f"Example: {public_api_changes[0]['file_path']}:{public_api_changes[0]['line_number']} - {public_api_changes[0]['change_type']}",
                            risk="Users may not be aware of API changes",
                            recommendation=f"Update {changelog_path} to document new or modified APIs",
                        )
                    )

        if version_info:
            file_path, major, minor, patch, line_num = version_info
            if not api_changes and not breaking_changes:
                findings.append(
                    Finding(
                        id="release-version-bump-without-changes",
                        title=f"Version bumped to {major}.{minor}.{patch} but no API changes detected",
                        severity="warning",
                        confidence="medium",
                        owner="dev",
                        estimate="S",
                        evidence=f"File: {file_path}:{line_num} - Version is {major}.{minor}.{patch} but no API or breaking changes found in diff",
                        risk="Unnecessary version bumps may confuse users about release significance",
                        recommendation="Verify if version bump is justified or if this is a documentation/internal-only change",
                    )
                )

        scope = Scope(
            relevant_files=relevant_files,
            ignored_files=ignored_files,
            reasoning=f"Analyzed {len(relevant_files)} relevant files for release hygiene. "
            f"Checked for {len(breaking_changes)} breaking changes and {len(api_changes)} API changes. "
            f"Ignored {len(ignored_files)} files not matching release patterns.",
        )

        severity = "merge"
        critical_findings = [f for f in findings if f.severity == "critical"]
        blocking_findings = [f for f in findings if f.severity == "blocking"]
        warning_findings = [f for f in findings if f.severity == "warning"]

        if blocking_findings:
            severity = "blocking"
        elif critical_findings:
            severity = "critical"
        elif warning_findings:
            severity = "warning"

        must_fix = [f.id for f in findings if f.severity in ("blocking", "critical")]
        should_fix = [f.id for f in findings if f.severity == "warning"]

        merge_gate = MergeGate(
            decision="block" if blocking_findings else "needs_changes" if must_fix else "approve",
            must_fix=must_fix,
            should_fix=should_fix,
            notes_for_coding_agent=[
                "Add CHANGELOG entry for user-visible changes",
                "Document breaking changes with migration guides",
                "Verify version bump is justified",
            ]
            if warning_findings
            else [],
        )

        return ReviewOutput(
            agent=self.agent_name,
            summary=self._build_summary(findings, breaking_changes, api_changes, version_info),
            severity=severity,
            scope=scope,
            findings=findings,
            merge_gate=merge_gate,
        )

    def _build_summary(
        self,
        findings: List[Finding],
        breaking_changes: List[dict],
        api_changes: List[dict],
        version_info: Optional[tuple],
    ) -> str:
        """Build a summary of changelog review findings.

        Args:
            findings: List of findings
            breaking_changes: List of breaking changes detected
            api_changes: List of API changes detected
            version_info: Version info tuple if version was bumped

        Returns:
            Summary string
        """
        if not findings:
            parts = ["Release hygiene review passed."]
            if version_info:
                file_path, major, minor, patch, _ = version_info
                parts.append(f"Version {major}.{minor}.{patch} bumped appropriately.")
            return " ".join(parts)

        by_severity = {
            "warning": [f for f in findings if f.severity == "warning"],
            "critical": [f for f in findings if f.severity == "critical"],
            "blocking": [f for f in findings if f.severity == "blocking"],
        }

        parts = []

        if by_severity["blocking"]:
            parts.append(f"Found {len(by_severity['blocking'])} blocking release issues")

        if by_severity["critical"]:
            parts.append(f"Found {len(by_severity['critical'])} critical release issues")

        if by_severity["warning"]:
            parts.append(f"Found {len(by_severity['warning'])} warnings about release hygiene")

        if breaking_changes:
            parts.append(f"Detected {len(breaking_changes)} potential breaking changes")

        if api_changes:
            parts.append(f"Detected {len(api_changes)} API changes")

        return ". ".join(parts) + "."
