"""Security Review Subagent - checks for security vulnerabilities."""
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


SECURITY_SYSTEM_PROMPT = """You are the Security Review Subagent.

Use this shared behavior:
- Identify which changed files/diffs are relevant to security.
- Propose minimal targeted checks first; escalate if risk is high.
- If changed_files or diff are missing, request them.
- Discover repo conventions (pyproject.toml, CI workflows, audit tools) to propose correct commands.

You specialize in:
- secrets handling (keys/tokens/passwords), logging of sensitive data
- authn/authz, permission checks, RBAC
- injection risks: SQL injection, command injection, template injection
- SSRF, unsafe network calls, insecure defaults
- dependency/supply chain risk signals (new deps, loosened pins)
- cryptography misuse
- file/path handling, deserialization, eval/exec usage
- CI/CD exposures (tokens, permissions, workflow changes)

High-signal file patterns:
- auth/**, security/**, iam/**, permissions/**, middleware/**
- network clients, webhook handlers, request parsers
- subprocess usage, shell commands
- config files: *.yml, *.yaml (CI), Dockerfile, terraform, deploy scripts
- dependency files: pyproject.toml, requirements*.txt, poetry.lock, uv.lock

Checks you may request (when available and relevant):
- bandit (Python SAST)
- dependency audit (pip-audit / poetry audit / uv audit)
- semgrep ruleset
- grep checks: "password", "token", "secret", "AWS_", "PRIVATE_KEY"

Security review must answer:
1) Did we introduce a new trust boundary or input surface?
2) Are inputs validated and outputs encoded appropriately?
3) Are secrets handled safely (not logged, not committed, not exposed)?
4) Are permissions least-privilege and explicit?

Blocking conditions:
- plaintext secrets committed or leaked into logs
- authz bypass risk or missing permission checks
- code execution risk (eval/exec) without strong sandboxing
- command injection risk via subprocess with untrusted input
- unsafe deserialization of untrusted input

Output MUST be valid JSON only with agent="security" and the standard schema.
Return JSON only."""


SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', "API key exposed"),
    (r'(?i)(password|passwd|pwd)["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', "Password exposed"),
    (r'(?i)(secret|token)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', "Secret/token exposed"),
    (r'(?i)(aws[_-]?(access[_-]?key|secret))["\']?\s*[:=]\s*["\']([A-Z0-9]{20,})["\']', "AWS credential exposed"),
    (r'(?i)(private[_-]?key)["\']?\s*[:=]\s*["\']([-]+BEGIN[A-Z\s]+PRIVATE KEY[^-]+[-]+END[A-Z\s]+PRIVATE KEY[^-]+[-]+)["\']', "Private key exposed"),
]

DANGEROUS_PATTERNS = [
    (r'(?i)(eval|exec)\s*\(', "Code execution via eval/exec"),
    (r'(?i)(pickle\.load|cPickle\.load)\s*\(', "Unsafe deserialization with pickle"),
    (r'(?i)(yaml\.load)\s*\([^)]*\)', "Unsafe YAML deserialization"),
    (r'(?i)(subprocess\.|os\.system|os\.popen)\s*\([^)]*\bshell\s*=\s*True', "Shell command injection risk"),
    (r'(?i)(sql.*["\']?\s*\+\s*["\'])|(["\']\s*\+\s*.*sql)', "SQL injection risk via string concatenation"),
    (r'(?i)(flask|django|pyramid)\.(render_template_string)\s*\([^)]*\buser\b', "XSS risk via template injection with user input"),
]


class SecurityReviewer(BaseReviewerAgent):
    """Security reviewer agent that checks for security vulnerabilities.

    This agent specializes in detecting:
    - Secrets handling (API keys, passwords, tokens)
    - Authentication/authorization issues
    - Injection risks (SQL, XSS, command)
    - CI/CD exposures
    - Unsafe code execution patterns
    """

    def get_agent_name(self) -> str:
        """Return the agent identifier."""
        return "security"

    def get_system_prompt(self) -> str:
        """Get the system prompt for the security reviewer."""
        return SECURITY_SYSTEM_PROMPT

    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns relevant to security review."""
        return [
            "**/*.py",
            "**/*.yml",
            "**/*.yaml",
            "**/auth*/**",
            "**/security*/**",
            "**/iam/**",
            "**/permissions/**",
            "**/middleware/**",
            "**/requirements*.txt",
            "**/pyproject.toml",
            "**/poetry.lock",
            "**/uv.lock",
            "**/Dockerfile*",
            "**/*.tf",
            "**/.github/workflows/**",
            "**/.gitlab-ci.yml",
        ]

    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform security review on the given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with security findings, severity, and merge gate decision
        """
        relevant_files = []
        for file_path in context.changed_files:
            if self.is_relevant_to_changes([file_path]):
                relevant_files.append(file_path)

        findings: List[Finding] = []

        secret_findings = self._check_for_secrets(context.diff)
        findings.extend(secret_findings)

        dangerous_findings = self._check_for_dangerous_patterns(context.diff)
        findings.extend(dangerous_findings)

        cicd_findings = self._check_for_cicd_exposures(context.diff, relevant_files)
        findings.extend(cicd_findings)

        severity: Literal["merge", "warning", "critical", "blocking"]
        blocking_findings = [f for f in findings if f.severity == "blocking"]
        critical_findings = [f for f in findings if f.severity == "critical"]

        if blocking_findings:
            severity = "blocking"
        elif critical_findings:
            severity = "critical"
        elif findings:
            severity = "warning"
        else:
            severity = "merge"

        if severity == "blocking":
            gate_decision = "block"
            must_fix_ids = [f.id for f in blocking_findings]
            should_fix_ids = [f.id for f in critical_findings]
        elif severity == "critical":
            gate_decision = "needs_changes"
            must_fix_ids = []
            should_fix_ids = [f.id for f in critical_findings]
        elif severity == "warning":
            gate_decision = "needs_changes"
            must_fix_ids = []
            should_fix_ids = [f.id for f in findings if f.severity == "warning"]
        else:
            gate_decision = "approve"
            must_fix_ids = []
            should_fix_ids = []

        if findings:
            summary_parts = [
                f"Found {len(findings)} security issue(s).",
            ]
            if blocking_findings:
                summary_parts.append(f"{len(blocking_findings)} blocking (secrets exposed).")
            if critical_findings:
                summary_parts.append(f"{len(critical_findings)} critical.")
            summary = " ".join(summary_parts)
        else:
            summary = "No security vulnerabilities detected."

        return ReviewOutput(
            agent=self.get_agent_name(),
            summary=summary,
            severity=severity,
            scope=Scope(
                relevant_files=relevant_files,
                ignored_files=[],
                reasoning=f"Security review analyzed {len(relevant_files)} relevant files for secrets, injection risks, and auth issues.",
            ),
            findings=findings,
            merge_gate=MergeGate(
                decision=gate_decision,
                must_fix=must_fix_ids,
                should_fix=should_fix_ids,
                notes_for_coding_agent=[
                    f"Ensure all secrets are stored in environment variables or secret managers.",
                    f"Validate all user inputs and use parameterized queries.",
                    f"Implement proper authentication and authorization checks.",
                ],
            ),
        )

    def _check_for_secrets(self, diff: str) -> List[Finding]:
        """Check diff for exposed secrets.

        Args:
            diff: Git diff content

        Returns:
            List of findings for exposed secrets
        """
        findings: List[Finding] = []
        lines = diff.split('\n')

        for i, line in enumerate(lines, 1):
            if not line.startswith('+'):
                continue

            for pattern, description in SECRET_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    findings.append(Finding(
                        id=f"secret-{i}",
                        title=description,
                        severity="blocking",
                        confidence="high",
                        owner="security",
                        estimate="S",
                        evidence=f"Line {i}: {line[:100]}..." if len(line) > 100 else f"Line {i}: {line}",
                        risk="Exposed credentials can be used to compromise systems and data.",
                        recommendation="Remove secrets from code and use environment variables or secret managers.",
                        suggested_patch="Replace hardcoded secret with os.getenv('SECRET_NAME')",
                    ))
                    break

        return findings

    def _check_for_dangerous_patterns(self, diff: str) -> List[Finding]:
        """Check diff for dangerous code patterns.

        Args:
            diff: Git diff content

        Returns:
            List of findings for dangerous patterns
        """
        findings: List[Finding] = []
        lines = diff.split('\n')

        for i, line in enumerate(lines, 1):
            if not line.startswith('+'):
                continue

            for pattern, description in DANGEROUS_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    severity: Literal["critical", "warning", "blocking"]
                    if "exec" in description or "eval" in description or "command injection" in description:
                        severity = "critical"
                    else:
                        severity = "warning"

                    findings.append(Finding(
                        id=f"dangerous-{i}",
                        title=description,
                        severity=severity,
                        confidence="medium",
                        owner="dev",
                        estimate="M",
                        evidence=f"Line {i}: {line[:100]}..." if len(line) > 100 else f"Line {i}: {line}",
                        risk=f"Using {description} can lead to code execution or injection attacks.",
                        recommendation=self._get_recommendation_for_pattern(description),
                        suggested_patch=self._get_suggested_patch_for_pattern(description),
                    ))
                    break

        return findings

    def _check_for_cicd_exposures(
        self,
        diff: str,
        relevant_files: List[str]
    ) -> List[Finding]:
        """Check for CI/CD security exposures.

        Args:
            diff: Git diff content
            relevant_files: List of relevant changed files

        Returns:
            List of findings for CI/CD exposures
        """
        findings: List[Finding] = []
        lines = diff.split('\n')

        cicd_files = [
            f for f in relevant_files
            if any(pattern in f for pattern in ['.github/workflows', '.gitlab-ci.yml', 'Jenkinsfile'])
        ]

        if not cicd_files:
            return findings

        for i, line in enumerate(lines, 1):
            if not line.startswith('+'):
                continue

            for pattern, description in SECRET_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    findings.append(Finding(
                        id=f"cicd-secret-{i}",
                        title=f"CI/CD {description}",
                        severity="blocking",
                        confidence="high",
                        owner="devops",
                        estimate="S",
                        evidence=f"Line {i}: {line[:100]}..." if len(line) > 100 else f"Line {i}: {line}",
                        risk="Secrets in CI/CD workflows are exposed in logs and repository history.",
                        recommendation="Use GitHub Actions secrets, GitLab CI variables, or external secret managers.",
                    suggested_patch="Replace with ${{ secrets.SECRET_NAME }} or $SECRET_NAME",
                ))
                    break

            if re.search(r'(pull-requests: write|contents: write|issues: write)', line, re.IGNORECASE):
                findings.append(Finding(
                    id=f"cicd-perms-{i}",
                    title="Overly permissive CI/CD permissions",
                    severity="warning",
                    confidence="medium",
                    owner="devops",
                    estimate="S",
                    evidence=f"Line {i}: {line[:100]}..." if len(line) > 100 else f"Line {i}: {line}",
                    risk="Excessive permissions in CI/CD workflows can lead to unauthorized changes.",
                    recommendation="Use least-privilege permissions (read-only where possible).",
                    suggested_patch="Change write permissions to read where applicable",
                ))

        return findings

    def _get_recommendation_for_pattern(self, description: str) -> str:
        """Get security recommendation for a pattern.

        Args:
            description: Pattern description

        Returns:
            Recommendation string
        """
        if "eval" in description or "exec" in description:
            return "Avoid eval/exec. Use safer alternatives like ast.literal_eval or proper deserialization."
        elif "pickle" in description:
            return "Use safe serialization formats like JSON or implement custom validation."
        elif "shell" in description or "command injection" in description:
            return "Use subprocess without shell=True or use shlex.quote() to escape arguments."
        elif "SQL" in description:
            return "Use parameterized queries (prepared statements) instead of string concatenation."
        elif "XSS" in description or "template" in description:
            return "Validate and sanitize user input before using in templates."
        else:
            return "Review and sanitize inputs, use secure coding practices."

    def _get_suggested_patch_for_pattern(self, description: str) -> str:
        """Get suggested patch for a pattern.

        Args:
            description: Pattern description

        Returns:
            Suggested patch string
        """
        if "eval" in description:
            return "Replace eval() with safer alternatives like ast.literal_eval()"
        elif "exec" in description:
            return "Remove exec() and use proper function calls or imports"
        elif "pickle" in description:
            return "Replace pickle.load with json.load or implement safe deserialization"
        elif "shell" in description:
            return "Use subprocess.run([...], shell=False) instead of shell=True"
        elif "SQL" in description:
            return "Use cursor.execute('SELECT * FROM table WHERE id = %s', (user_id,))"
        elif "XSS" in description:
            return "Escape user input with markupsafe.escape() before rendering"
        else:
            return "Review security implications and implement proper sanitization"
