"""OpenCode Python - Review Loop System"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import logging
import subprocess
from pathlib import Path



logger = logging.getLogger(__name__)


class ReviewLoop:
    """
    Review loop for linting, testing, and structured output
    
    Provides automated code review with findings categorization
    and actionable next steps for fixing issues.
    """
    
    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    async def review(
        self,
        session_id: str,
        commit_hash: Optional[str] = None,
        branch_name: Optional[str] = None,
        pr_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run review of changes
        
        Args:
            session_id: Session ID to review
            commit_hash: Git commit hash (default: HEAD)
            branch_name: Branch name (default: current)
            pr_number: PR number (for PRs)
            
        Returns:
            Review results with findings, status, and next steps
        """
        
        # Get changed files
        changed_files = await self._get_changed_files()
        
        if not changed_files:
            return {
                "status": "no_changes",
                "message": "No changes to review",
                "findings": [],
                "next_steps": [],
            }
        
        # Initialize review results
        findings = []
        next_steps = []
        
        # Check each file for linting issues
        for file_path in changed_files:
            findings.extend(await self._check_file(file_path))
        
        # Check for test coverage
        if findings:
            test_results = await self._run_tests(changed_files)
            findings.append({
                "type": "test",
                "message": f"Tests {'passed' if test_results['success'] else 'failed'}",
            })
            
            if not test_results["success"]:
                next_steps.append("Fix test failures")
        
        # Generate structured output
        status = "success" if not any(f["severity"] == "error" for f in findings) else "warnings"
        
        if not findings:
            next_steps.append("Add tests for new code")
        
        return {
                "status": status,
                "message": f"Review complete: {len(findings)} findings",
                "findings": findings,
                "next_steps": next_steps,
            }

    async def _get_changed_files(self) -> List[str]:
        """
        Get list of changed files
        
        Uses git diff to detect changed files since last commit.
        """
        # Use git to detect changes
        if self.project_dir.is_dir():
            try:
                result = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    check=True,
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"git diff failed: {result.stderr}")
                
                files = result.stdout.strip().split("\n")
                return [f for f in files if f]
            
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to get changed files: {e}")
                return []
        
        # Fallback for single file changes
        return []

    async def _check_file(self, file_path: str) -> Dict[str, Any]:
        """
        Check a file for issues

        Currently implements placeholder checks.
        In full parity, would integrate with linters like:
        - pylint, flake8, mypy, ruff, black, isort

        Returns:
            File findings with issue details
        """
        findings = []

        path = Path(file_path)

        # Check for common issues
        if path.suffix == ".py":
            # Placeholder: implement actual linting
            pass
        elif path.suffix in [".js", ".ts", ".jsx", ".tsx"]:
            # Placeholder: implement linter checks
            pass

        return {
                "file": file_path,
                "findings": findings,
            }

    async def _run_tests(self, files: List[str]) -> Dict[str, Any]:
        """
        Run tests on changed files
        
        Currently implements placeholder.
        In full parity, would integrate with test frameworks like:
        - pytest, unittest, coverage
        
        Returns:
            Test execution results
        """
        # TODO: Implement actual test execution
        return {
                "success": True,
                "files_tested": len(files),
            }
