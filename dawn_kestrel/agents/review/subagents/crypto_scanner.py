"""
Crypto Scanner Agent for FSM-based Security Review.

This module provides a specialized agent for detecting weak cryptography in code:
- Uses ToolExecutor to run grep for weak crypto patterns
- Detects: MD5, SHA1, hardcoded keys, ECB mode, constant-time issues
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
from typing import TYPE_CHECKING, List, Optional

from dawn_kestrel.agents.review.fsm_security import SecurityFinding, SubagentTask
from dawn_kestrel.agents.review.tools import ToolExecutor

if TYPE_CHECKING:
    from dawn_kestrel.llm import LLMClient


logger = logging.getLogger(__name__)


# Weak cryptography patterns for grep detection
# Based on OWASP Cryptographic Storage Cheat Sheet
CRYPTO_PATTERNS = {
    # Weak hash functions (MD5, SHA1)
    "md5": [
        r"hashlib\.md5\(",  # Python: hashlib.md5()
        r"crypto\.createHash\(['\"]md5['\"]",  # Node.js: crypto.createHash('md5')
        r"MessageDigest\.getInstance\(['\"]MD5['\"]",  # Java: MessageDigest.getInstance("MD5")
        r"Hash::make\(['\"]md5['\"]",  # PHP/Laravel: Hash::make('md5')
        r"md5\(",  # Generic md5() function call
    ],
    "sha1": [
        r"hashlib\.sha1\(",  # Python: hashlib.sha1()
        r"crypto\.createHash\(['\"]sha1['\"]",  # Node.js: crypto.createHash('sha1')
        r"MessageDigest\.getInstance\(['\"]SHA-?1['\"]",  # Java: MessageDigest.getInstance("SHA1")
        r"Hash::make\(['\"]sha1['\"]",  # PHP/Laravel: Hash::make('sha1')
        r"sha1\(",  # Generic sha1() function call
    ],
    # Hardcoded cryptographic keys/secrets
    "hardcoded_key": [
        r"key\s*=\s*['\"][0-9a-zA-Z+/]{16,}['\"]",  # Keys in string literals (16+ chars)
        r"secret\s*=\s*['\"][0-9a-zA-Z+/]{16,}['\"]",  # Secrets in string literals
        r"private[_-]?key\s*=\s*['\"][^'\"]{10,}['\"]",  # Private keys in strings
        r"password\s*=\s*['\"][^'\"]{8,}['\"]",  # Passwords in strings
        r"api[_-]?key\s*=\s*['\"][^'\"]{16,}['\"]",  # API keys in strings
    ],
    # Weak encryption modes
    "ecb_mode": [
        r"AES\.new\(.*ECB",  # Python Crypto: AES.new(key, AES.MODE_ECB)
        r"Cipher\.getInstance\(['\"]AES/ECB",  # Java: Cipher.getInstance("AES/ECB/...")
        r"crypto\.createCipheriv\(['\"]aes-256-ecb",  # Node.js: aes-256-ecb
        r"openssl_encrypt\(.*['\"]aes-[0-9]+-ecb",  # PHP: openssl_encrypt(..., 'aes-256-ecb')
        r"MODE_ECB",  # Generic ECB mode constant
    ],
    # Non-constant-time comparison (timing attack vulnerability)
    "constant_time_issue": [
        r"if\s+hash1\s*==\s*hash2",  # Simple equality comparison of hashes
        r"if\s+mac1\s*==\s+mac2",  # Simple equality comparison of MACs
        r"if\s+token1\s*==\s+token2",  # Simple equality comparison of tokens
        r"==\s*['\"][^'\"]+['\"]",  # Comparing hash/token against string literal
        r"password\s*==\s*['\"][^'\"]+['\"]",  # Password comparison (simple)
    ],
}


class CryptoScannerAgent:
    """
    Agent for detecting weak cryptography in code.

    This agent uses tool-based detection only (no AI-based detection):
    1. Primary: Use grep with weak crypto patterns
    2. Detects: MD5, SHA1, hardcoded keys, ECB mode, constant-time issues
    3. Normalize all outputs to SecurityFinding format

    Returns SubagentTask-compatible result with findings and summary.
    """

    def __init__(
        self,
        tool_executor: Optional[ToolExecutor] = None,
        llm_client: Optional["LLMClient"] = None,
    ):
        """Initialize CryptoScannerAgent.

        Args:
            tool_executor: ToolExecutor for running grep.
                           If None, creates a new instance.
            llm_client: LLMClient for potential LLM-based analysis.
                       Currently not used, kept for future enhancement.
        """
        self.tool_executor = tool_executor or ToolExecutor()
        self.llm_client = llm_client
        self.logger = logger

    def execute(self, repo_root: str, files: Optional[List[str]] = None) -> SubagentTask:
        """
        Execute cryptographic weakness scanning on given repository.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional). If None, scans all source files.

        Returns:
            SubagentTask with findings and summary
        """
        self.logger.info("[CRYPTO_SCANNER] Starting weak cryptography scan...")

        # Collect findings from all patterns
        all_findings: List[SecurityFinding] = []

        # Scan with grep for each crypto pattern category
        for pattern_name, pattern_list in CRYPTO_PATTERNS.items():
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
            f"Cryptographic weakness scan completed. Found {len(all_findings)} potential issues. "
            f"Scanned for: MD5, SHA1, hardcoded keys, ECB mode, constant-time issues."
        )

        self.logger.info(f"[CRYPTO_SCANNER] {summary}")

        # Return SubagentTask result
        return SubagentTask(
            task_id="crypto_scanner_task",
            todo_id="todo_crypto_scanner",
            description="Scan for weak cryptography patterns",
            agent_name="crypto_scanner",
            prompt="Scan for weak cryptography",
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
        Scan for cryptographic weaknesses using grep pattern matching.

        Args:
            repo_root: Path to the repository root
            files: List of files to scan (optional)
            pattern_name: Name of the pattern category (e.g., "md5")
            pattern_list: List of regex patterns to search for

        Returns:
            List of SecurityFinding objects
        """
        self.logger.info(f"[CRYPTO_SCANNER] Scanning for {pattern_name}...")

        all_findings: List[SecurityFinding] = []

        # Build file list for grep
        if files:
            grep_files = files
        else:
            # Scan common source file types
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
                    if ext in [".py", ".js", ".ts", ".java", ".go", ".rb", ".php", ".cs", ".cpp"]:
                        grep_files.append(os.path.join(root, filename))

        # Scan each pattern in the pattern list
        for pattern in pattern_list:
            grep_args = [
                "-n",  # Show line numbers
                "-E",  # Extended regex
                "-i",  # Case insensitive
                pattern,
            ] + grep_files

            result = self.tool_executor.execute_tool(tool_name="grep", args=grep_args, timeout=30)

            if result.success and result.findings:
                # Enhance findings with crypto-specific metadata
                for finding in result.findings:
                    finding.title = f"Weak Cryptography ({pattern_name}): {finding.title}"
                    finding.description = self._get_pattern_description(pattern_name)
                    finding.recommendation = self._get_pattern_recommendation(pattern_name)
                    finding.severity = self._get_pattern_severity(pattern_name)

                all_findings.extend(result.findings)

        self.logger.info(f"[CRYPTO_SCANNER] {pattern_name}: {len(all_findings)} findings")

        return all_findings

    def _get_pattern_description(self, pattern_name: str) -> str:
        """Get description for a pattern category."""
        descriptions = {
            "md5": "MD5 is a cryptographically broken hash function that should not be used for security purposes.",
            "sha1": "SHA1 is deprecated and should not be used for security purposes due to collision vulnerabilities.",
            "hardcoded_key": "Hardcoded cryptographic keys or secrets in source code are a security vulnerability.",
            "ecb_mode": "ECB (Electronic Codebook) mode does not provide semantic security and should not be used for encryption.",
            "constant_time_issue": "Non-constant-time comparison of cryptographic values can lead to timing attacks.",
        }
        return descriptions.get(pattern_name, "Weak cryptographic pattern detected.")

    def _get_pattern_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for a pattern category."""
        recommendations = {
            "md5": "Replace MD5 with a secure hash function (SHA-256, SHA-3, or BLAKE2).",
            "sha1": "Replace SHA1 with a secure hash function (SHA-256, SHA-3, or BLAKE2).",
            "hardcoded_key": "Remove hardcoded keys/secrets and use environment variables or secret management services.",
            "ecb_mode": "Use a secure encryption mode (GCM, CBC with proper IV handling, or CTR) instead of ECB.",
            "constant_time_issue": "Use constant-time comparison functions (e.g., hmac.compare_digest() in Python).",
        }
        return recommendations.get(pattern_name, "Review and update cryptographic implementation.")

    def _get_pattern_severity(self, pattern_name: str) -> str:
        """Get severity level for a pattern category."""
        severity_map = {
            "md5": "medium",
            "sha1": "medium",
            "hardcoded_key": "high",
            "ecb_mode": "medium",
            "constant_time_issue": "medium",
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
