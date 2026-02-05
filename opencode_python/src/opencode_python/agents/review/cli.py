"""CLI command for running PR reviews from the command line."""
from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Literal

import click
from rich.console import Console

from opencode_python.agents.review.orchestrator import PRReviewOrchestrator
from opencode_python.agents.review.contracts import ReviewInputs

from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
from opencode_python.agents.review.agents.security import SecurityReviewer
from opencode_python.agents.review.agents.documentation import DocumentationReviewer
from opencode_python.agents.review.agents.telemetry import TelemetryMetricsReviewer
from opencode_python.agents.review.agents.linting import LintingReviewer
from opencode_python.agents.review.agents.unit_tests import UnitTestsReviewer
from opencode_python.agents.review.agents.diff_scoper import DiffScoperReviewer
from opencode_python.agents.review.agents.requirements import RequirementsReviewer
from opencode_python.agents.review.agents.performance import PerformanceReliabilityReviewer
from opencode_python.agents.review.agents.dependencies import DependencyLicenseReviewer
from opencode_python.agents.review.agents.changelog import ReleaseChangelogReviewer

console = Console()

AGENT_MAP = {
    "security": SecurityReviewer,
    "architecture": ArchitectureReviewer,
    "documentation": DocumentationReviewer,
    "telemetry": TelemetryMetricsReviewer,
    "linting": LintingReviewer,
    "unit_tests": UnitTestsReviewer,
    "diff_scoper": DiffScoperReviewer,
    "requirements": RequirementsReviewer,
    "performance": PerformanceReliabilityReviewer,
    "dependencies": DependencyLicenseReviewer,
    "changelog": ReleaseChangelogReviewer,
}


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for review CLI.

    Args:
        verbose: Enable debug level logging
    """
    log_level = logging.INFO if verbose else logging.WARNING
    log_format = '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s'
    date_format = '%H:%M:%S'

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True
    )

    from opencode_python.core.settings import settings
    if settings.debug:
        logging.getLogger().setLevel(logging.DEBUG)


def get_subagents(include_optional: bool = False) -> list:
    """Get list of subagents based on optional flag.

    Args:
        include_optional: If True, include optional subagents

    Returns:
        List of reviewer agents
    """
    core_agents = [
        ArchitectureReviewer(),
        SecurityReviewer(),
        DocumentationReviewer(),
        TelemetryMetricsReviewer(),
        LintingReviewer(),
        UnitTestsReviewer(),
    ]

    optional_agents = [
        DiffScoperReviewer(),
        RequirementsReviewer(),
        PerformanceReliabilityReviewer(),
        DependencyLicenseReviewer(),
        ReleaseChangelogReviewer(),
    ]

    if include_optional:
        return core_agents + optional_agents
    return core_agents


def format_terminal_progress(agent_name: str, status: str, data: dict) -> None:
    """Format and print progress events to terminal.

    Args:
        agent_name: Name of the agent
        status: Status of the operation (started, completed, error)
        data: Additional data from the progress event
    """
    logger = logging.getLogger(__name__)

    if status == "started":
        console.print(f"[cyan][{agent_name}][/cyan] [dim]Started review...[/dim]")
        logger.info(f"[{agent_name}] Starting review...")
    elif status == "completed":
        console.print(f"[green][{agent_name}][/green] [dim]Completed[/dim]")
        logger.info(f"[{agent_name}] Review completed successfully")
    elif status == "error":
        error_msg = data.get("error", "Unknown error")
        console.print(f"[red][{agent_name}][/red] [dim]Error: {error_msg}[/dim]")
        logger.error(f"[{agent_name}] Error: {error_msg}")


def format_terminal_result(agent_name: str, result) -> None:
    """Format and print result events to terminal.

    Args:
        agent_name: Name of the agent
        result: ReviewOutput from the agent
    """
    if result.severity == "blocking":
        console.print(f"[red][{agent_name}][/red] Found blocking issues")
    elif result.severity == "critical":
        console.print(f"[red][{agent_name}][/red] Found critical issues")
    elif result.severity == "warning":
        console.print(f"[yellow][{agent_name}][/yellow] Found warnings")
    else:
        console.print(f"[green][{agent_name}][/green] No issues found")

    if result.findings:
        console.print(f"  [dim]{len(result.findings)} finding(s)[/dim]")


def format_terminal_error(agent_name: str, error_msg: str) -> None:
    """Format and print error events to terminal.

    Args:
        agent_name: Name of the agent
        error_msg: Error message
    """
    console.print(f"[red][{agent_name}][/red] [dim]Failed: {error_msg}[/dim]")


@click.command()
@click.option(
    "--agent",
    type=click.Choice(list(AGENT_MAP.keys())),
    default=None,
    help=f"Run only a specific agent (default: run all agents). Options: {', '.join(sorted(AGENT_MAP.keys()))}",
)
@click.option(
    "--repo-root",
    type=click.Path(exists=True, path_type=Path),
    default=Path.cwd(),
    help="Repository root directory (default: current directory)",
)
@click.option(
    "--base-ref",
    default="main",
    help="Base git reference (default: main)",
)
@click.option(
    "--head-ref",
    default="HEAD",
    help="Head git reference (default: HEAD)",
)
@click.option(
    "--output",
    type=click.Choice(["json", "markdown", "terminal"]),
    default="terminal",
    help="Output format (default: terminal)",
)
@click.option(
    "--include-optional",
    is_flag=True,
    help="Include optional review subagents",
)
@click.option(
    "--timeout",
    type=int,
    default=300,
    help="Agent timeout in seconds (default: 300)",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging to see detailed progress",
)
def review(
    agent: str | None,
    repo_root: Path,
    base_ref: str,
    head_ref: str,
    output: Literal["json", "markdown", "terminal"],
    include_optional: bool,
    timeout: int,
    verbose: bool,
) -> None:
    """Run PR review on a git repository.

    Review analyzes code changes between base-ref and head-ref using
    specialized review agents running in parallel.

    Use --agent to run a single agent, or run all agents by default.

    Progress will be logged to stdout showing:
    - Which agents are starting
    - LLM calls and response sizes
    - Context building progress
    - Any errors or retries occurring
    """
    async def run_review() -> None:
        setup_logging(verbose)

        if agent:
            subagents = [AGENT_MAP[agent]()]
            console.print(f"[cyan]Running only '{agent}' agent...[/cyan]")
        else:
            subagents = get_subagents(include_optional)
            console.print(f"[cyan]Running all {len(subagents)} agents...[/cyan]")

        orchestrator = PRReviewOrchestrator(subagents=subagents)

        inputs = ReviewInputs(
            repo_root=str(repo_root),
            base_ref=base_ref,
            head_ref=head_ref,
            include_optional=include_optional,
            timeout_seconds=timeout,
        )

        console.print(f"[cyan]Starting PR review...[/cyan]")
        console.print(f"[dim]Repo: {repo_root}[/dim]")
        console.print(f"[dim]Refs: {base_ref} -> {head_ref}[/dim]")
        console.print(f"[dim]Agents: {len(subagents)}[/dim]")
        console.print()

        if output == "terminal":
            async def stream_callback(agent_name: str, status: str, data: dict, result=None, error_msg: str | None = None) -> None:
                if status == "started":
                    format_terminal_progress(agent_name, status, data)
                elif status == "completed" and result:
                    format_terminal_result(agent_name, result)
                elif status == "error" and error_msg:
                    format_terminal_error(agent_name, error_msg)

            result = await orchestrator.run_review(inputs, stream_callback=stream_callback)
        else:
            result = await orchestrator.run_review(inputs)

        console.print()
        console.print("[cyan]Review complete[/cyan]")
        console.print(f"[dim]Total findings: {result.total_findings}[/dim]")
        console.print(f"[dim]Decision: {result.merge_decision.decision}[/dim]")
        console.print()

        if output == "json":
            console.print(result.model_dump_json(indent=2))
        elif output == "markdown":
            console.print(result_to_markdown(result))
        elif output == "terminal":
            print_terminal_summary(result)

    try:
        asyncio.run(run_review())
    except KeyboardInterrupt:
        console.print("\n[yellow]Review interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.ClickException(str(e))


def result_to_markdown(result) -> str:
    """Convert review result to Markdown format.

    Args:
        result: OrchestratorOutput from review

    Returns:
        Markdown formatted string
    """
    md_lines = [
        "# PR Review Results",
        "",
        f"**Decision:** {result.merge_decision.decision}",
        f"**Total Findings:** {result.total_findings}",
        "",
    ]

    if result.merge_decision.decision == "block":
        md_lines.append("## ⛔ Blocking Issues")
    elif result.merge_decision.decision == "needs_changes":
        md_lines.append("## ⚠️ Required Changes")
    elif result.merge_decision.decision == "approve_with_warnings":
        md_lines.append("## ⚠️ Review With Warnings")

    for finding in result.findings:
        emoji = "🔴" if finding.severity == "blocking" else "🟠" if finding.severity == "critical" else "🟡"
        md_lines.extend([
            "",
            f"{emoji} **{finding.title}**",
            f"  - Severity: {finding.severity}",
            f"  - Owner: {finding.owner}",
            f"  - Estimate: {finding.estimate}",
            f"  - Evidence: `{finding.evidence}`",
            f"  - Risk: {finding.risk}",
            f"  - Recommendation: {finding.recommendation}",
        ])
        if finding.suggested_patch:
            md_lines.append(f"  - Suggested patch: `{finding.suggested_patch}`")

    if result.tool_plan.proposed_commands:
        md_lines.extend([
            "",
            "## Tool Plan",
            "",
        ])
        for cmd in result.tool_plan.proposed_commands:
            md_lines.append(f"- `{cmd}`")

    if result.merge_decision.notes_for_coding_agent:
        md_lines.extend([
            "",
            "## Notes for Coding Agent",
            "",
        ])
        for note in result.merge_decision.notes_for_coding_agent:
            md_lines.append(f"- {note}")

    return "\n".join(md_lines)


def print_terminal_summary(result) -> None:
    """Print summary of review results to terminal.

    Args:
        result: OrchestratorOutput from review
    """
    if result.merge_decision.decision == "approve":
        console.print("[green]✅ Review: APPROVED for merge[/green]")
    elif result.merge_decision.decision == "approve_with_warnings":
        console.print("[yellow]⚠️  Review: APPROVED WITH WARNINGS[/yellow]")
    elif result.merge_decision.decision == "needs_changes":
        console.print("[yellow]⚠️  Review: NEEDS CHANGES[/yellow]")
    else:
        console.print("[red]⛔ Review: BLOCKED[/red]")

    console.print()

    if result.merge_decision.must_fix:
        console.print("[red]Must Fix:[/red]")
        for item in result.merge_decision.must_fix[:5]:
            console.print(f"  • {item}")
        if len(result.merge_decision.must_fix) > 5:
            console.print(f"  [dim]...and {len(result.merge_decision.must_fix) - 5} more[/dim]")
        console.print()

    if result.merge_decision.should_fix:
        console.print("[yellow]Should Fix:[/yellow]")
        for item in result.merge_decision.should_fix[:5]:
            console.print(f"  • {item}")
        if len(result.merge_decision.should_fix) > 5:
            console.print(f"  [dim]...and {len(result.merge_decision.should_fix) - 5} more[/dim]")
        console.print()

    console.print(f"[dim]Summary: {result.summary}[/dim]")


@click.command()
@click.option(
    "--agent",
    type=str,
    default=None,
    help="Specific agent name (e.g., security, architecture)",
)
@click.option(
    "--all",
    "generate_all",
    is_flag=True,
    help="Generate documentation for all reviewers",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite existing documentation even if hash matches",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Custom output directory for documentation",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def generate_docs(
    agent: str | None,
    generate_all: bool,
    force: bool,
    output: Path | None,
    verbose: bool,
) -> None:
    """Generate entry point documentation for review agents.

    Analyzes system prompts and extracts patterns to create YAML frontmatter
    documentation for reviewer agents.
    """
    setup_logging(verbose)

    console.print(f"[cyan]Generating reviewer documentation...[/cyan]")
    console.print()

    from opencode_python.agents.review.doc_gen import DocGenAgent
    from opencode_python.agents.review.agents.architecture import ArchitectureReviewer
    from opencode_python.agents.review.agents.security import SecurityReviewer
    from opencode_python.agents.review.agents.documentation import DocumentationReviewer
    from opencode_python.agents.review.agents.telemetry import TelemetryMetricsReviewer
    from opencode_python.agents.review.agents.linting import LintingReviewer
    from opencode_python.agents.review.agents.unit_tests import UnitTestsReviewer
    from opencode_python.agents.review.agents.diff_scoper import DiffScoperReviewer
    from opencode_python.agents.review.agents.requirements import RequirementsReviewer
    from opencode_python.agents.review.agents.performance import PerformanceReliabilityReviewer
    from opencode_python.agents.review.agents.dependencies import DependencyLicenseReviewer
    from opencode_python.agents.review.agents.changelog import ReleaseChangelogReviewer

    all_agents = {
        'architecture': ArchitectureReviewer(),
        'security': SecurityReviewer(),
        'documentation': DocumentationReviewer(),
        'telemetry': TelemetryMetricsReviewer(),
        'linting': LintingReviewer(),
        'unit_tests': UnitTestsReviewer(),
        'diff_scoper': DiffScoperReviewer(),
        'requirements': RequirementsReviewer(),
        'performance': PerformanceReliabilityReviewer(),
        'dependencies': DependencyLicenseReviewer(),
        'changelog': ReleaseChangelogReviewer(),
    }

    doc_gen = DocGenAgent(agents_dir=output)

    agents_to_process = []
    if generate_all:
        agents_to_process = list(all_agents.values())
        console.print(f"[dim]Processing all {len(agents_to_process)} agents[/dim]")
    elif agent:
        if agent not in all_agents:
            console.print(f"[red]Error: Unknown agent '{agent}'[/red]")
            console.print(f"[dim]Available agents: {', '.join(sorted(all_agents.keys()))}[/dim]")
            raise click.ClickException(f"Unknown agent: {agent}")
        agents_to_process = [all_agents[agent]]
        console.print(f"[dim]Processing agent: {agent}[/dim]")
    else:
        console.print("[red]Error: Specify --agent or --all[/red]")
        raise click.ClickException("Must specify --agent or --all")

    console.print()

    results = []
    for reviewer_agent in agents_to_process:
        agent_name = getattr(reviewer_agent, 'get_agent_name', lambda: reviewer_agent.__class__.__name__.lower().replace('reviewer', ''))()
        success, message = doc_gen.generate_for_agent(reviewer_agent, force=force)

        if success:
            console.print(f"[green]✓[/green] {agent_name}: {message}")
            results.append((agent_name, True, message))
        else:
            console.print(f"[red]✗[/red] {agent_name}: {message}")
            results.append((agent_name, False, message))

    console.print()

    successes = sum(1 for _, success, _ in results if success)
    failures = len(results) - successes

    if failures == 0:
        console.print(f"[green]✓ All {len(results)} documentation(s) generated successfully[/green]")
    else:
        console.print(f"[yellow]⚠ {successes} succeeded, {failures} failed[/yellow]")
        raise click.ClickException(f"{failures} documentation(s) failed to generate")
