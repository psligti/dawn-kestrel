"""Orchestrator for parallel PR review agent execution."""
from __future__ import annotations

import asyncio
import logging
from typing import List, Callable, Literal


from opencode_python.agents.review.base import BaseReviewerAgent, ReviewContext
from opencode_python.agents.review.contracts import (
    Finding,
    MergeGate,
    OrchestratorOutput,
    ReviewInputs,
    ReviewOutput,
    Scope,
    ToolPlan,
)
from opencode_python.agents.review.discovery import EntryPointDiscovery
from opencode_python.agents.review.streaming import ReviewStreamManager
from opencode_python.agents.review.utils.executor import (
    CommandExecutor,
    ExecutionResult,
)

logger = logging.getLogger(__name__)


class PRReviewOrchestrator:
    def __init__(
        self,
        subagents: List[BaseReviewerAgent],
        command_executor: CommandExecutor | None = None,
        stream_manager: ReviewStreamManager | None = None,
        discovery: EntryPointDiscovery | None = None,
    ):
        self.subagents = subagents
        self.command_executor = command_executor or CommandExecutor()
        self.stream_manager = stream_manager or ReviewStreamManager()
        # Entry point discovery module for intelligent context filtering
        self.discovery = discovery or EntryPointDiscovery()

    async def run_review(
        self, inputs: ReviewInputs, stream_callback: Callable | None = None
    ) -> OrchestratorOutput:
        """Run full review with all subagents in parallel.

        Args:
            inputs: ReviewInputs containing repo details and PR metadata
            stream_callback: Optional callback for streaming progress events

        Returns:
            OrchestratorOutput with merged findings, decision, and tool plan
        """
        await self.stream_manager.start_stream()

        results = await self.run_subagents_parallel(inputs, stream_callback)

        all_findings = [finding for result in results for finding in result.findings]
        deduped_findings = self.dedupe_findings(all_findings)

        merge_decision = self.compute_merge_decision(results)
        tool_plan = self.generate_tool_plan(results)

        summary = f"Review completed by {len(results)} subagents with {len(deduped_findings)} findings"

        return OrchestratorOutput(
            merge_decision=merge_decision,
            findings=deduped_findings,
            tool_plan=tool_plan,
            subagent_results=results,
            summary=summary,
            total_findings=len(deduped_findings),
        )

    async def run_subagents_parallel(
        self, inputs: ReviewInputs, stream_callback: Callable | None = None
    ) -> List[ReviewOutput]:
        import logging
        logger = logging.getLogger(__name__)

        tasks = []
        semaphore = asyncio.Semaphore(4)
        logger.info(f"Starting parallel review with {len(self.subagents)} agents, max 4 concurrent, timeout={inputs.timeout_seconds}s")

        for idx, agent in enumerate(self.subagents):
            async def run_with_timeout(current_agent=agent):
                async with semaphore:
                    agent_name = current_agent.get_agent_name()
                    logger.info(f"[{agent_name}] Starting agent (timeout: {inputs.timeout_seconds}s)")

                    try:
                        if stream_callback:
                            await self.stream_manager.emit_progress(
                                agent_name, "started", {}
                            )

                        logger.info(f"[{agent_name}] Building context...")
                        context = await self._build_context(inputs, current_agent)
                        logger.info(f"[{agent_name}] Context built: {len(context.changed_files)} files, {len(context.diff)} chars diff")
                        logger.debug(f"[{agent_name}] Changed files: {', '.join(context.changed_files[:10])}")

                        logger.info(f"[{agent_name}] Calling LLM...")
                        result = await asyncio.wait_for(
                            current_agent.review(context), timeout=inputs.timeout_seconds
                        )

                        logger.info(f"[{agent_name}] LLM response received: {len(result.findings)} findings")
                        if stream_callback:
                            await self.stream_manager.emit_result(
                                agent_name, result
                            )

                        return result

                    except asyncio.TimeoutError:
                        error_msg = f"Agent {agent_name} timed out after {inputs.timeout_seconds}s"
                        logger.error(f"[{agent_name}] {error_msg}")
                        if stream_callback:
                            await self.stream_manager.emit_error(
                                agent_name, error_msg
                            )

                        return ReviewOutput(
                            agent=agent_name,
                            summary="Agent timed out",
                            severity="critical",
                            scope=Scope(
                                relevant_files=[], ignored_files=[], reasoning="Timeout"
                            ),
                            checks=[],
                            skips=[],
                            findings=[],
                            merge_gate=MergeGate(
                                decision="needs_changes",
                                must_fix=[],
                                should_fix=[],
                                notes_for_coding_agent=[]
                            ),
                        )

                    except Exception as e:
                        error_msg = f"Agent {agent_name} failed: {str(e)}"
                        logger.error(f"[{agent_name}] {error_msg}", exc_info=True)
                        if stream_callback:
                            await self.stream_manager.emit_error(
                                agent_name, error_msg
                            )

                        return ReviewOutput(
                            agent=agent_name,
                            summary="Agent failed with exception",
                            severity="critical",
                            scope=Scope(
                                relevant_files=[], ignored_files=[], reasoning="Exception"
                            ),
                            checks=[],
                            skips=[],
                            findings=[],
                            merge_gate=MergeGate(
                                decision="needs_changes",
                                must_fix=[],
                                should_fix=[],
                                notes_for_coding_agent=[]
                            ),
                        )

            tasks.append(run_with_timeout())

        logger.info(f"Gathering results from {len(tasks)} parallel agents...")
        results = await asyncio.gather(*tasks)
        logger.info(f"All agents completed: {len([r for r in results if r.summary != 'Agent timed out' and r.summary != 'Agent failed with exception'])} successful")

        return results

    async def execute_command(self, command: str, timeout: int = 30) -> ExecutionResult:
        """Execute a command via CommandExecutor.

        Args:
            command: Command string to execute
            timeout: Maximum execution time in seconds

        Returns:
            ExecutionResult with command output and metadata
        """
        return await self.command_executor.execute(command, timeout=timeout)

    def compute_merge_decision(self, results: List[ReviewOutput]) -> MergeGate:
        """Compute merge decision based on PRD policy.

        Policy: blocking > critical > warning > merge

        Args:
            results: List of ReviewOutput from subagents

        Returns:
            MergeGate with decision and fix lists
        """
        must_fix = []
        should_fix = []
        decision: Literal["approve", "needs_changes", "block", "approve_with_warnings"] = "approve"

        for result in results:
            must_fix.extend(result.merge_gate.must_fix)
            should_fix.extend(result.merge_gate.should_fix)

            for finding in result.findings:
                if finding.severity == "blocking":
                    must_fix.append(f"{finding.title}: {finding.recommendation}")
                elif finding.severity == "critical":
                    must_fix.append(f"{finding.title}: {finding.recommendation}")
                elif finding.severity == "warning":
                    should_fix.append(f"{finding.title}: {finding.recommendation}")

        if must_fix:
            has_blocking = any(
                f.severity == "blocking" for result in results for f in result.findings
            )
            decision = "block" if has_blocking else "needs_changes"
        elif should_fix:
            decision = "approve_with_warnings"
        else:
            decision = "approve"

        return MergeGate(
            decision=decision,
            must_fix=list(set(must_fix)),
            should_fix=list(set(should_fix)),
            notes_for_coding_agent=[
                f"Review completed by {len(results)} subagents"
            ],
        )

    def dedupe_findings(self, all_findings: List[Finding]) -> List[Finding]:
        """De-duplicate findings by grouping.

        Args:
            all_findings: List of all findings from subagents

        Returns:
            List of unique findings
        """
        seen = set()
        unique = []

        for finding in all_findings:
            key = (finding.id, finding.title, finding.severity)

            if key not in seen:
                seen.add(key)
                unique.append(finding)

        return unique

    def generate_tool_plan(self, results: List[ReviewOutput]) -> ToolPlan:
        """Generate tool plan with proposed commands.

        Args:
            results: List of ReviewOutput from subagents

        Returns:
            ToolPlan with proposed commands and execution summary
        """
        proposed_commands = []
        auto_fix_available = False

        for result in results:
            for check in result.checks:
                if check.required:
                    proposed_commands.extend(check.commands)

        if proposed_commands:
            auto_fix_available = any(
                cmd.startswith("ruff") or cmd.startswith("black")
                for cmd in proposed_commands
            )

        summary = f"Generated tool plan with {len(proposed_commands)} commands"

        return ToolPlan(
            proposed_commands=list(set(proposed_commands)),
            auto_fix_available=auto_fix_available,
            execution_summary=summary,
        )

    async def _build_context(
        self, inputs: ReviewInputs, agent: BaseReviewerAgent
    ) -> ReviewContext:
        """Build ReviewContext for a specific agent.

        This method performs intelligent context filtering using entry point discovery:
        1. Discovers entry points relevant to the agent's patterns
        2. Filters changed_files to only those containing discovered entry points
        3. Falls back to is_relevant_to_changes() if discovery fails

        Args:
            inputs: ReviewInputs with review parameters
            agent: BaseReviewerAgent to build context for

        Returns:
            ReviewContext populated with review data (filtered changed_files)
        """
        from opencode_python.agents.review.utils.git import get_changed_files, get_diff

        agent_name = agent.__class__.__name__

        all_changed_files = await get_changed_files(
            inputs.repo_root, inputs.base_ref, inputs.head_ref
        )

        entry_points = await self.discovery.discover_entry_points(
            agent_name=agent_name,
            repo_root=inputs.repo_root,
            changed_files=all_changed_files,
        )

        if entry_points is not None:
            ep_file_set = {ep.file_path for ep in entry_points}
            filtered_files = [f for f in all_changed_files if f in ep_file_set]
            logger.info(
                f"[{agent_name}] Entry point discovery found {len(entry_points)} entry points, "
                f"filtered to {len(filtered_files)}/{len(all_changed_files)} files"
            )
            changed_files = filtered_files
        else:
            logger.info(
                f"[{agent_name}] Entry point discovery returned None, "
                f"using is_relevant_to_changes() fallback"
            )
            if agent.is_relevant_to_changes(all_changed_files):
                changed_files = all_changed_files
            else:
                changed_files = []
                logger.info(
                    f"[{agent_name}] Agent not relevant to changes, skipping review"
                )

        diff = await get_diff(inputs.repo_root, inputs.base_ref, inputs.head_ref)

        return ReviewContext(
            changed_files=changed_files,
            diff=diff,
            repo_root=inputs.repo_root,
            base_ref=inputs.base_ref,
            head_ref=inputs.head_ref,
            pr_title=inputs.pr_title,
            pr_description=inputs.pr_description,
        )
