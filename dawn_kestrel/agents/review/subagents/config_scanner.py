"""
Config Scanner Agent for FSM-based Security Review.

This module provides a specialized agent for detecting security misconfigurations:
- Uses ToolExecutor to run grep for security misconfigurations
- Detects: DEBUG=True, test keys in production, insecure defaults, exposed env vars
- Normalizes grep output to SecurityFinding format
- Returns SubagentTask-compatible results

Security notes:
- NEVER uses shell=True with user input (from napkin)
- Always uses shell=False with list arguments
- Python 3.9 compatible (uses typing.Optional[T] instead of T | None)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.tools import ToolExecutor


logger = logging.getLogger(__name__)


# Configuration security patterns for grep detection
# Based on OWASP Configuration Cheat Sheet and common security misconfigurations
CONFIG_PATTERNS = {
    # Debug mode enabled in production
    "debug_mode": [
        r"DEBUG\s*=\s*True",  # Python: DEBUG = True
        r"DEBUG\s*=\s*['\"]true['\"]",  # Config files: DEBUG = "true"
        r"debug\s*=\s*True",  # Lowercase: debug = True
        r"app\.debug\s*=\s*True",  # Flask: app.debug = True
        r"DEBUG\s*==\s*True",  # Comparison: DEBUG == True
        r"debug\s*=\s*['\"]true['\"]",  # Node.js/other languages
    ],
    # Test keys in production
    "test_keys": [
        r"AWS.*TEST.*KEY",  # AWS test keys: AWS_TEST_ACCESS_KEY, AWS_TEST_SECRET_KEY
        r"STRIPE_TEST.*SECRET",  # Stripe test keys: STRIPE_TEST_SECRET_KEY
        r"TEST_KEY\s*=",  # Generic TEST_KEY= in configs
        r"API_KEY_TEST\s*=",  # API_KEY_TEST= patterns
        r"SECRET_TEST\s*=",  # SECRET_TEST= patterns
        r"key.*test.*=",  # Generic key=test patterns
    ],
    # Insecure defaults (open CORS, wildcard hosts, etc.)
    "insecure_defaults": [
        r"ALLOWED_HOSTS\s*=\s*\[.*['\"]\*['\"].*\]",  # Django: ALLOWED_HOSTS = ['*']
        r"CORS_ORIGIN_ALLOW_ALL\s*=\s*True",  # Django CORS: allow all origins
        r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True",  # Django CORS: allow all origins
        r"cors\.origin\s*=\s*['\"]\*['\"]",  # Express: cors.origin = '*'
        r"allowedOrigins.*\*",  # Generic wildcard in allowed origins
        r"accessControlAllowOrigin\s*=\s*['\"]\*['\"]",  # CORS: accessControlAllowOrigin = '*'
        r"SECURE\s*=\s*False",  # Django: SECURE = False (cookies, SSL, etc.)
        r"SESSION_COOKIE_SECURE\s*=\s*False",  # Django: SESSION_COOKIE_SECURE = False
        r"CSRF_COOKIE_SECURE\s*=\s*False",  # Django: CSRF_COOKIE_SECURE = False
    ],
    # Exposed environment variables (os.environ directly in code, hardcoded secrets)
    "exposed_env_vars": [
        r"os\.environ\s*\[[^]]+\]",  # Python: os.environ['KEY']
        r"os\.getenv\([^)]+\)",  # Python: os.getenv('KEY')
        r"os\.environ\.get\([^)]+\)",  # Python: os.environ.get('KEY')
        r"process\.env\.",  # Node.js: process.env.KEY
        r"ENV\[",  # Ruby: ENV['KEY']
        r"getenv\(",  # PHP: getenv('KEY')
        r"\$\{[A-Z_]+\}",  # Bash/shell: ${VAR}
        r"System\.getenv\(",  # Java: System.getenv('KEY')
        r"Environment\.GetEnvironmentVariable",  # .NET: Environment.GetEnvironmentVariable
    ],
    # Database passwords in settings (PASSWORD=, SECRET_KEY= in config files)
    "db_passwords": [
        r"PASSWORD\s*=\s*['\"][^'\"]{8,}['\"]",  # Generic: PASSWORD = "password"
        r"DB_PASSWORD\s*=\s*['\"][^'\"]{8,}['\"]",  # DB_PASSWORD patterns
        r"DATABASE_PASSWORD\s*=\s*['\"][^'\"]{8,}['\"]",  # DATABASE_PASSWORD patterns
        r"SECRET_KEY\s*=\s*['\"][^'\"]{20,}['\"]",  # Django: SECRET_KEY = '...'
        r"SECRET\s*=\s*['\"][^'\"]{20,}['\"]",  # Generic: SECRET = '...'
        r"API_SECRET\s*=\s*['\"][^'\"]{20,}['\"]",  # API_SECRET patterns
        r"private_key\s*=\s*['\"][^'\"]{20,}['\"]",  # private_key patterns
        r"private[_-]?key\s*=\s*['\"][^'\"]{20,}['\"]",  # variations with underscore/dash
    ],
    # Insecure SSL configurations (SSL_VERIFY=False, SECURE_SSL_REDIRECT=False)
    "insecure_ssl": [
        r"SSL_VERIFY\s*=\s*False",  # SSL_VERIFY = False
        r"SSL\s*=\s*False",  # SSL = False
        r"verify\s*=\s*False",  # verify = False (requests library)
        r"ssl_verify\s*=\s*False",  # ssl_verify = False
        r"SECURE_SSL_REDIRECT\s*=\s*False",  # Django: SECURE_SSL_REDIRECT = False
        r"SECURE_HSTS_SECONDS\s*=\s*0",  # Django: SECURE_HSTS_SECONDS = 0 (disabled)
        r"SECURE_HSTS_INCLUDE_SUBDOMAINS\s*=\s*False",  # Django HSTS disabled
        r"SECURE_PROXY_SSL_HEADER\s*=\s*None",  # Django: SECURE_PROXY_SSL_HEADER = None
        r"CHECK_SSL_CERT\s*=\s*False",  # MySQL/DB drivers: CHECK_SSL_CERT = False
        r"TLS_VERIFY\s*=\s*False",  # TLS_VERIFY = False
        r"tls_verify\s*=\s*False",  # tls_verify = False
    ],
}


class ConfigScannerAgent:
    """
    Agent for detecting security misconfigurations in code.

    This agent uses tool-based detection only (no AI-based detection):
    1. Primary: Use grep with config misconfiguration patterns
    2. Detects: DEBUG mode, test keys, insecure defaults, exposed env vars, db passwords, SSL issues
    3. Normalize all outputs to SecurityFinding format

    Returns SubagentTask-compatible result with findings and summary.
    """

    def __init__(self, tool_executor: Optional[ToolExecutor] = None):
        """Initialize ConfigScannerAgent.

        Args:
            tool_executor: ToolExecutor for running grep.
                          If None, creates a new instance.
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.logger = logger

    def execute(self, repo_root: str, files: Optional[List[str]] = None) -> SubagentTask:
        """
        Execute security configuration scanning on given repository.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional). If None, scans all source files.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[CONFIG_SCANNER] Starting security configuration scan...")

        # Collect findings from all patterns
        all_findings: List[SecurityFinding] = []

        # Scan with grep for each config pattern category
        for pattern_name, pattern_list in CONFIG_PATTERNS.items():
            pattern_findings = self._scan_with_grep(repo_root, files, pattern_name, pattern_list)
            all_findings.extend(pattern_findings)

        # Deduplicate findings (same file, line, and pattern)
        all_findings = self._deduplicate_findings(all_findings)

        # Convert findings to dict format for SubagentTask result
        findings_data = []
        for finding in all_findings:
            findings_data.append(
                {
                    "id": finding.id,
                    "severity": finding.severity,
                    "title": finding.title,
                    "description": finding.description,
                    "evidence": finding.evidence,
                    "file_path": finding.file_path,
                    "line_number": finding.line_number,
                    "recommendation": finding.recommendation,
                    "requires_review": finding.requires_review,
                }
            )

        # Build summary
        summary = (
            f"Security configuration scan completed. Found {len(all_findings)} potential misconfigurations. "
            f"Scanned for: debug mode, test keys, insecure defaults, exposed env vars, db passwords, SSL issues."
        )

        self.logger.info(f"[CONFIG_SCANNER] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="config_scanner_task",
            todo_id="todo_config_scanner",
            description="Scan for security misconfigurations",
            agent_name="config_scanner",
            prompt="Scan for security misconfigurations",
            tools=["grep"],
            result={
                "findings": findings_data,
                "summary": summary,
            },
        )

    def _scan_with_grep(
        self,
        repo_root: str,
        files: Optional[List[str]],
        pattern_name: str,
        pattern_list: List[str],
    ) -> List[SecurityFinding]:
        """
        Scan for security misconfigurations using grep pattern matching.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional)
            pattern_name: Name of the pattern category (e.g., "debug_mode")
            pattern_list: List of regex patterns to search for

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info(f"[CONFIG_SCANNER] Scanning for {pattern_name}...")

        all_findings: List[SecurityFinding] = []

        # Build file list for grep
        if files:
            grep_files = files
        else:
            # Scan common source file types and config files
            grep_files = []
            for root, dirs, filenames in os.walk(repo_root):
                # Skip hidden directories and common non-code directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".")
                    and d
                    not in [
                        "node_modules",
                        "__pycache__",
                        "venv",
                        ".venv",
                        "dist",
                        "build",
                        ".git",
                    ]
                ]
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    # Include source files and common config files
                    if ext in [
                        ".py",
                        ".js",
                        ".ts",
                        ".java",
                        ".go",
                        ".rb",
                        ".php",
                        ".cs",
                        ".cpp",
                        ".c",
                        ".sh",
                    ] or filename in [
                        "settings.py",
                        "config.py",
                        ".env",
                        ".env.local",
                        ".env.development",
                        ".env.production",
                        "Dockerfile",
                        "docker-compose.yml",
                        "docker-compose.yaml",
                        "requirements.txt",
                        "setup.py",
                        "pyproject.toml",
                        "package.json",
                    ]:
                        grep_files.append(os.path.join(root, filename))

        # Scan each pattern in the pattern list
        for pattern in pattern_list:
            grep_args = [
                "-n",  # Show line numbers
                "-E",  # Extended regex
                pattern,
            ] + grep_files

            result = self.tool_executor.execute_tool(tool_name="grep", args=grep_args, timeout=30)

            if result.success and result.findings:
                # Enhance findings with config-specific metadata
                for finding in result.findings:
                    finding.title = f"Security Misconfiguration ({pattern_name}): {finding.title}"
                    finding.description = self._get_pattern_description(pattern_name)
                    finding.recommendation = self._get_pattern_recommendation(pattern_name)
                    finding.severity = self._get_pattern_severity(pattern_name)

                all_findings.extend(result.findings)

        self.logger.info(f"[CONFIG_SCANNER] {pattern_name}: {len(all_findings)} findings")

        return all_findings

    def _get_pattern_description(self, pattern_name: str) -> str:
        """Get description for a pattern category."""
        descriptions = {
            "debug_mode": "Debug mode enabled in production environment can leak sensitive information and disable security features.",
            "test_keys": "Test keys or credentials detected in production code or configuration.",
            "insecure_defaults": "Insecure default configurations (wildcard CORS, insecure cookie settings) detected.",
            "exposed_env_vars": "Environment variables accessed directly in code may leak sensitive information in logs or error messages.",
            "db_passwords": "Hardcoded database passwords or secret keys found in configuration files.",
            "insecure_ssl": "Insecure SSL/TLS configuration detected (SSL verification disabled, secure redirect disabled).",
        }
        return descriptions.get(pattern_name, "Security misconfiguration detected.")

    def _get_pattern_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for a pattern category."""
        recommendations = {
            "debug_mode": "Disable debug mode in production. Use environment variables (DEBUG=False) and enforce production settings.",
            "test_keys": "Remove test keys and credentials from production code. Use separate configuration files for different environments.",
            "insecure_defaults": "Review and secure default configurations. Use specific allowed origins, enable secure cookies, and enable HSTS.",
            "exposed_env_vars": "Use environment variable loaders or secret management services. Avoid direct os.environ access in production code.",
            "db_passwords": "Remove hardcoded passwords and secrets. Use environment variables, secret managers, or secure configuration files.",
            "insecure_ssl": "Enable SSL/TLS verification and secure redirects. Use HSTS with proper headers and certificate validation.",
        }
        return recommendations.get(pattern_name, "Review and fix security misconfiguration.")

    def _get_pattern_severity(self, pattern_name: str) -> str:
        """Get severity level for a pattern category."""
        severity_map = {
            "debug_mode": "high",
            "test_keys": "high",
            "insecure_defaults": "medium",
            "exposed_env_vars": "medium",
            "db_passwords": "critical",
            "insecure_ssl": "high",
        }
        return severity_map.get(pattern_name, "medium")

    def _deduplicate_findings(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """
        Deduplicate findings based on file path and line number.

        Args:
            findings: List of SecurityFinding objects

        Returns:
            Deduplicated list of SecurityFinding objects
        """
        seen = set()
        deduplicated = []

        for finding in findings:
            key = (finding.file_path, finding.line_number)
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return deduplicated
