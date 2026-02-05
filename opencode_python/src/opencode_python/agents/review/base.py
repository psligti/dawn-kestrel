"""Base ReviewerAgent abstract class for all review subagents."""
from __future__ import annotations
from typing import List
from abc import ABC, abstractmethod
from pathlib import Path
import pydantic as pd

from opencode_python.agents.review.contracts import ReviewOutput


def _match_glob_pattern(file_path: str, pattern: str) -> bool:
    """Match file path against glob pattern, handling ** correctly.

    Args:
        file_path: File path to check
        pattern: Glob pattern (supports *, **, ?)

    Returns:
        True if file path matches pattern
    """
    from fnmatch import fnmatch

    path = Path(file_path)
    path_parts = list(path.parts)

    if '**' in pattern:
        parts = pattern.split('**')
        if len(parts) == 2:
            prefix = parts[0].rstrip('/')
            suffix = parts[1].lstrip('/')

            if prefix:
                prefix_parts = prefix.split('/')
                if not path_parts[:len(prefix_parts)] == prefix_parts:
                    return False
                remaining = path_parts[len(prefix_parts):]
            else:
                remaining = path_parts

            if suffix:
                suffix_parts = suffix.split('/')
                if not suffix_parts:
                    return True

                if len(remaining) >= len(suffix_parts):
                    if remaining[-len(suffix_parts):] == suffix_parts:
                        return True

                if len(suffix_parts) == 1 and remaining:
                    if fnmatch(remaining[-1], suffix_parts[0]):
                        return True
                    if fnmatch('/'.join(remaining), suffix_parts[0]):
                        return True
                return False
            return True

    return fnmatch(str(path), pattern)


class ReviewContext(pd.BaseModel):
    """Context data passed to reviewer agents."""

    changed_files: List[str]
    diff: str
    repo_root: str
    base_ref: str | None = None
    head_ref: str | None = None
    pr_title: str | None = None
    pr_description: str | None = None

    model_config = pd.ConfigDict(extra="forbid")


class BaseReviewerAgent(ABC):
    """Abstract base class for all review subagents.

    All specialized reviewers must inherit from this class and implement
    the required abstract methods. This ensures consistent interface across
    all review agents.
    """

    @abstractmethod
    async def review(self, context: ReviewContext) -> ReviewOutput:
        """Perform review on given context.

        Args:
            context: ReviewContext containing changed files, diff, and metadata

        Returns:
            ReviewOutput with findings, severity, and merge gate decision
        """
        pass

    @abstractmethod
    def get_agent_name(self) -> str:
        """Get agent identifier."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get system prompt for this reviewer agent.

        Returns:
            System prompt string for LLM
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this reviewer agent.

        Returns:
            System prompt string for LLM
        """
        pass

    @abstractmethod
    def get_relevant_file_patterns(self) -> List[str]:
        """Get file patterns this reviewer is relevant to.

        Returns:
            List of glob patterns (e.g., ["*.py", "src/**/*.py"])
        """
        pass

    @abstractmethod
    def get_allowed_tools(self) -> List[str]:
        """Get allowed tool/command prefixes for this reviewer.

        Returns:
            List of command/tool prefixes this reviewer may propose in checks
        """
        pass

    def is_relevant_to_changes(self, changed_files: List[str]) -> bool:
        """Check if this reviewer is relevant to the given changed files.

        Args:
            changed_files: List of changed file paths

        Returns:
            True if any changed file matches the relevant patterns
        """
        patterns = self.get_relevant_file_patterns()
        if not patterns:
            return False

        for file_path in changed_files:
            for pattern in patterns:
                try:
                    if _match_glob_pattern(file_path, pattern):
                        return True
                except ValueError:
                    continue
        return False

    def format_inputs_for_prompt(self, context: ReviewContext) -> str:
        """Format review context for inclusion in LLM prompt.

        Args:
            context: ReviewContext to format

        Returns:
            Formatted string suitable for inclusion in prompt
        """
        import logging
        logger = logging.getLogger(__name__)

        agent_name = self.__class__.__name__
        logger.info(f"[{agent_name}] Building prompt context:")
        logger.info(f"[{agent_name}]   Repo root: {context.repo_root}")
        logger.info(f"[{agent_name}]   Changed files: {len(context.changed_files)}")
        logger.info(f"[{agent_name}]   Diff size: {len(context.diff)} chars")

        parts = [
            "## Review Context",
            "",
            f"**Repository Root**: {context.repo_root}",
            "",
            "### Changed Files",
        ]

        for file_path in context.changed_files:
            parts.append(f"- {file_path}")

        if context.base_ref and context.head_ref:
            parts.append("")
            parts.append("### Git Diff")
            parts.append(f"**Base Ref**: {context.base_ref}")
            parts.append(f"**Head Ref**: {context.head_ref}")

        parts.append("")
        parts.append("### Diff Content")
        parts.append("```diff")
        parts.append(context.diff)
        parts.append("```")

        if context.pr_title:
            parts.append("")
            parts.append("### Pull Request")
            parts.append(f"**Title**: {context.pr_title}")
            if context.pr_description:
                parts.append(f"**Description**:\n{context.pr_description}")

        return "\n".join(parts)

    def verify_findings(
        self,
        findings: List,
        changed_files: List[str],
        repo_root: str
    ) -> List[dict]:
        """Verify findings by cross-checking with code analysis tools.

        This method performs self-verification of findings by:
        1. Extracting search patterns from finding evidence
        2. Using grep to search for patterns in changed files
        3. Collecting verification evidence (matches, line numbers)
        4. Returning structured verification data

        Args:
            findings: List of Finding objects from ReviewOutput
            changed_files: List of changed file paths
            repo_root: Repository root path

        Returns:
            List of verification entries, each containing:
                - tool_type: str ("grep" or "lsp")
                - search_pattern: str (pattern searched for)
                - matches: List[str] (matching lines/content)
                - line_numbers: List[int] (line numbers where matches found)
                - file_path: str (file where matches found)

        Note:
            Graceful degradation: If verification fails, returns empty list
            and logs warning without blocking review completion.
        """
        import logging
        import re
        from pathlib import Path

        logger = logging.getLogger(__name__)
        agent_name = self.__class__.__name__

        verification_evidence = []

        if not findings:
            logger.debug(f"[{agent_name}] No findings to verify")
            return verification_evidence

        logger.info(f"[{agent_name}] Verifying {len(findings)} findings")

        for finding in findings:
            try:
                # Extract search pattern from finding evidence
                evidence_text = finding.evidence if hasattr(finding, 'evidence') else ""
                title_text = finding.title if hasattr(finding, 'title') else ""

                # Try to extract meaningful search terms from evidence
                search_terms = self._extract_search_terms(evidence_text, title_text)

                for search_term in search_terms:
                    # Use grep to search for the term in changed files
                    grep_results = self._grep_files(search_term, changed_files, repo_root)

                    if grep_results:
                        verification_entry = {
                            "tool_type": "grep",
                            "search_pattern": search_term,
                            "matches": grep_results.get("matches", []),
                            "line_numbers": grep_results.get("line_numbers", []),
                            "file_path": grep_results.get("file_path", "")
                        }
                        verification_evidence.append(verification_entry)
                        logger.debug(
                            f"[{agent_name}] Verified finding '{title_text}': "
                            f"{len(grep_results.get('matches', []))} grep matches"
                        )

            except Exception as e:
                # Graceful degradation: log warning and continue
                logger.warning(
                    f"[{agent_name}] Verification failed for finding "
                    f"'{getattr(finding, 'title', 'unknown')}': {e}"
                )
                continue

        logger.info(f"[{agent_name}] Verification complete: {len(verification_evidence)} evidence entries")
        return verification_evidence

    def _extract_search_terms(self, evidence_text: str, title_text: str) -> List[str]:
        """Extract meaningful search terms from evidence and title.

        Args:
            evidence_text: Evidence text from finding
            title_text: Title of the finding

        Returns:
            List of search terms extracted from the text
        """
        import re

        search_terms = []

        # Extract quoted strings (e.g., "API_KEY", 'password')
        quoted_pattern = r'["\']([^"\']{3,})["\']'
        for match in re.finditer(quoted_pattern, evidence_text):
            term = match.group(1).strip()
            if term and term not in search_terms:
                search_terms.append(term)

        # Extract code identifiers (e.g., eval, subprocess.run)
        # Match words that look like function calls or variable names
        code_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]{2,})\s*(?:\(|=|\.)'
        for match in re.finditer(code_pattern, evidence_text):
            term = match.group(1)
            # Filter out common words
            if term.lower() not in ['the', 'and', 'for', 'are', 'line', 'file']:
                if term not in search_terms:
                    search_terms.append(term)

        # Extract key terms from title
        title_words = re.findall(r'\b([A-Z_]{2,})\b|[a-z_]{3,}', title_text)
        for word in title_words:
            if word and word.upper() == word:  # All caps - likely code identifier
                if word not in search_terms:
                    search_terms.append(word)

        # Limit search terms to avoid excessive grep calls and filter empty strings
        return [term for term in search_terms[:5] if term]

    def _grep_files(
        self,
        pattern: str,
        file_paths: List[str],
        repo_root: str
    ) -> dict:
        """Search for pattern in files using grep.

        Args:
            pattern: Search pattern (string literal, not regex)
            file_paths: List of file paths to search
            repo_root: Repository root path

        Returns:
            Dict with keys:
                - matches: List[str] (matching lines)
                - line_numbers: List[int] (line numbers)
                - file_path: str (first file where matches found)

        Note:
            Graceful degradation: Returns empty dict on failure
        """
        import logging
        import subprocess
        import shlex
        from pathlib import Path

        logger = logging.getLogger(__name__)

        matches = []
        line_numbers = []
        first_match_file = ""

        # Escape the pattern for safe shell use
        escaped_pattern = shlex.quote(pattern)

        for file_path in file_paths:
            try:
                full_path = Path(repo_root) / file_path
                if not full_path.exists():
                    continue

                # Use grep with line numbers (-n) and fixed string matching (-F)
                result = subprocess.run(
                    ['grep', '-n', '-F', escaped_pattern, str(full_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            line_num_str, content = line.split(':', 1)
                            try:
                                line_num = int(line_num_str)
                                line_numbers.append(line_num)
                                matches.append(content.strip())
                                if not first_match_file:
                                    first_match_file = file_path
                            except ValueError:
                                continue

            except subprocess.TimeoutExpired:
                logger.debug(f"Grep timeout for pattern '{pattern}' in {file_path}")
                continue
            except Exception as e:
                logger.debug(f"Grep failed for pattern '{pattern}' in {file_path}: {e}")
                continue

        return {
            "matches": matches,
            "line_numbers": line_numbers,
            "file_path": first_match_file
        }

    async def _execute_review_with_runner(
        self,
        context: ReviewContext,
        *,
        early_return_on_no_relevance: bool = False,
        no_relevance_summary: str | None = None,
    ) -> ReviewOutput:
        """Shared execution flow for review agents using SimpleReviewAgentRunner.

        This template method centralizes the common pattern used by all review agents:
        1. Filter relevant files (optional early return)
        2. Build system prompt and formatted context
        3. Create SimpleReviewAgentRunner instance
        4. Execute LLM call with retry
        5. Parse JSON response with validation fallback
        6. Handle errors appropriately

        Args:
            context: ReviewContext containing changed files, diff, and metadata
            early_return_on_no_relevance: If True, return merge-severity ReviewOutput
                when no relevant files are found. If False, proceed regardless.
            no_relevance_summary: Custom summary message for no-relevance case.
                If None, uses default message.

        Returns:
            ReviewOutput with findings, severity, and merge gate decision

        Raises:
            ValueError: If API key is missing or invalid
            TimeoutError: If LLM request times out
            Exception: For other API-related errors

        Example:
            >>> class MyReviewer(BaseReviewerAgent):
            ...     async def review(self, context: ReviewContext) -> ReviewOutput:
            ...         return await self._execute_review_with_runner(
            ...             context,
            ...             early_return_on_no_relevance=True,
            ...             no_relevance_summary="No MyReviewer-relevant files changed"
            ...         )
        """
        import logging
        from opencode_python.core.harness import SimpleReviewAgentRunner
        from opencode_python.agents.review.contracts import Scope, MergeGate

        logger = logging.getLogger(__name__)
        class_name = self.__class__.__name__

        relevant_files = [
            file_path
            for file_path in context.changed_files
            if self.is_relevant_to_changes([file_path])
        ]

        logger.info(f"[{class_name}] Filtering relevant files: {len(relevant_files)}/{len(context.changed_files)} matched")

        if early_return_on_no_relevance and not relevant_files:
            logger.info(f"[{class_name}] No relevant files found, returning early with 'merge' severity")
            return ReviewOutput(
                agent=self.get_agent_name(),
                summary=no_relevance_summary or f"No {self.get_agent_name()}-relevant files changed. Review not applicable.",
                severity="merge",
                scope=Scope(
                    relevant_files=[],
                    reasoning="No files matched relevance patterns",
                ),
                findings=[],
                merge_gate=MergeGate(
                    decision="approve",
                    must_fix=[],
                    should_fix=[],
                    notes_for_coding_agent=[no_relevance_summary or f"No {self.get_agent_name()}-relevant files were changed."],
                ),
            )

        system_prompt = self.get_system_prompt()
        formatted_context = self.format_inputs_for_prompt(context)

        user_message = f"""{system_prompt}

{formatted_context}

Please analyze the above changes and provide your review in the specified JSON format."""

        logger.info(f"[{class_name}] Prompt construction complete:")
        logger.info(f"[{class_name}]   System prompt: {len(system_prompt)} chars")
        logger.info(f"[{class_name}]   Formatted context: {len(formatted_context)} chars")
        logger.info(f"[{class_name}]   Full user_message: {len(user_message)} chars")
        logger.info(f"[{class_name}]   Relevant files: {len(relevant_files)}")

        runner = SimpleReviewAgentRunner(
            agent_name=self.get_agent_name(),
            allowed_tools=self.get_allowed_tools(),
        )

        try:
            response_text = await runner.run_with_retry(system_prompt, formatted_context)
            logger.info(f"[{class_name}] Got response: {len(response_text)} chars")

            output = ReviewOutput.model_validate_json(response_text)
            logger.info(f"[{class_name}] JSON validation successful!")
            logger.info(f"[{class_name}]   agent: {output.agent}")
            logger.info(f"[{class_name}]   severity: {output.severity}")
            logger.info(f"[{class_name}]   findings: {len(output.findings)}")

            return output

        except pd.ValidationError as e:
            logger.error(f"[{class_name}] JSON validation error: {e}")
            logger.error(f"[{class_name}]   Error count: {len(e.errors())}")
            for error in e.errors()[:5]:
                logger.error(f"[{class_name}]     - {error['loc']}: {error['msg']}")
            logger.error(f"[{class_name}]   Original response (first 500 chars): {response_text[:500]}...")

            return ReviewOutput(
                agent=self.get_agent_name(),
                summary=f"Error parsing LLM response: {str(e)}",
                severity="critical",
                scope=Scope(
                    relevant_files=relevant_files,
                    ignored_files=[],
                    reasoning="Failed to parse LLM JSON response due to validation error."
                ),
                findings=[],
                merge_gate=MergeGate(
                    decision="needs_changes",
                    must_fix=[],
                    should_fix=[],
                    notes_for_coding_agent=[
                        "Review LLM response format and ensure it matches expected schema."
                    ]
                )
            )
        except (TimeoutError, ValueError):
            raise
        except Exception as e:
            raise Exception(f"LLM API error: {str(e)}") from e

    def learn_entry_point_pattern(self, pattern: dict) -> bool:
        """Learn a new entry point pattern from PR review.

        This method allows reviewers to discover and learn new patterns during
        review. Patterns are staged for manual approval before integration.

        Args:
            pattern: Pattern dictionary with keys:
                - type: "ast", "file_path", or "content"
                - pattern: The pattern string
                - weight: Relevance weight (0.0-1.0)
                - language: Optional language field (required for ast/content)
                - source: Optional source description (e.g., "PR #123")

        Returns:
            True if pattern was staged successfully, False otherwise

        Example:
            During review, discover a new security pattern:
            >>> pattern = {
            ...     'type': 'content',
            ...     'pattern': r'AWS_ACCESS_KEY\\s*[=:]',
            ...     'language': 'python',
            ...     'weight': 0.95,
            ...     'source': 'PR #123 - AWS key found in code'
            ... }
            >>> self.learn_entry_point_pattern(pattern)
            True

        Note:
            This is an optional method. Default implementation does nothing.
            Reviewers can override this to enable pattern learning.
        """
        import logging

        logger = logging.getLogger(__name__)

        logger.debug(
            f"[{self.__class__.__name__}] learn_entry_point_pattern called "
            f"but not implemented (pattern: {pattern.get('type', 'unknown')})"
        )
        return False
