"""CLI command for FSM-based security review with uv tool support.

This CLI provides:
- FSM-based security review with subagent delegation
- Dynamic todo creation based on exploration
- Automatic tool installation via `uv tool install`
- Rich terminal output with progress tracking
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Literal, Any

import click  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]
from rich.panel import Panel  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]

console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for security review CLI.

    Args:
        verbose: Enable debug level logging
    """
    log_level = logging.INFO if verbose else logging.WARNING
    log_format = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    date_format = "%H:%M:%S"

    logging.basicConfig(
        level=log_level, format=log_format, datefmt=date_format, stream=sys.stdout, force=True
    )

    from dawn_kestrel.core.settings import settings

    if settings.debug:
        logging.getLogger().setLevel(logging.DEBUG)


def check_uv_installed() -> bool:
    """Check if uv is installed on the system.

    Returns:
        True if uv is installed, False otherwise
    """
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_tool_with_uv(tool_name: str, verbose: bool = False) -> bool:
    """Install a tool using `uv tool install`.

    Args:
        tool_name: Name of the tool to install
        verbose: Enable verbose output from uv

    Returns:
        True if installation successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    if not check_uv_installed():
        console.print("[red]Error: uv is not installed[/red]")
        console.print("[dim]Please install uv first:[/dim]")
        console.print("[cyan]curl -LsSf https://astral.sh/uv | sh[/cyan]")
        return False

    console.print(f"[cyan]Installing {tool_name} with uv...[/cyan]")

    cmd: list[str] = ["uv", "tool", "install", tool_name]
    if not verbose:
        cmd.insert(1, "--quiet")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Successfully installed {tool_name}")
        console.print(f"[green]✓ {tool_name} installed[/green]")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install {tool_name}: {e.stderr}")
        console.print(f"[red]✗ Failed to install {tool_name}[/red]")
        if e.stderr:
            console.print(f"[dim]{e.stderr}[/dim]")
        return False


def check_tool_installed(tool_name: str) -> bool:
    """Check if a tool is already installed.

    Args:
        tool_name: Name of the tool to check

    Returns:
        True if tool is installed, False otherwise
    """
    try:
        result = subprocess.run(
            [tool_name, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def ensure_tools_installed(
    tools: list[str], install_missing: bool, verbose: bool, skip_check: bool = False
) -> None:
    """Ensure all required tools are installed.

    Args:
        tools: List of tool names to check
        install_missing: If True, install missing tools automatically
        verbose: Enable verbose output
        skip_check: If True, skip tool installation check
    """
    logger = logging.getLogger(__name__)

    if skip_check:
        logger.debug("Skipping tool check (--no-tool-check)")
        return

    table = Table(title="Tool Check", show_header=True, header_style="bold magenta")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Action", style="yellow")

    missing_tools = []

    for tool in tools:
        is_installed = check_tool_installed(tool)

        if is_installed:
            table.add_row(tool, "[green]✓ Installed[/green]", "[dim]None[/dim]")
            logger.debug(f"Tool {tool} is already installed")
        else:
            table.add_row(tool, "[red]✗ Missing[/red]", "[dim]Will install[/dim]")
            missing_tools.append(tool)
            logger.warning(f"Tool {tool} is not installed")

    console.print(table)

    if not missing_tools:
        console.print("[green]All required tools are installed[/green]")
        return

    if not install_missing:
        console.print("[yellow]Warning: Missing tools found[/yellow]")
        console.print("[dim]Run with --install-tools to install missing tools automatically[/dim]")
        console.print()
        raise click.ClickException(
            f"Missing tools: {', '.join(missing_tools)}. Use --install-tools to install."
        )

    console.print()
    console.print("[cyan]Installing missing tools with uv...[/cyan]")
    console.print()

    failed_tools = []
    for tool in missing_tools:
        if not install_tool_with_uv(tool, verbose):
            failed_tools.append(tool)

    if failed_tools:
        console.print()
        console.print(
            f"[red]Failed to install {len(failed_tools)} tool(s): {', '.join(failed_tools)}[/red]"
        )
        raise click.ClickException("Tool installation failed")


def format_security_assessment(assessment: Any) -> None:
    """Format and print security assessment to terminal.

    Args:
        assessment: SecurityAssessment with review results
    """
    severity_colors: dict[str, str] = {
        "critical": "red",
        "high": "bright_red",
        "medium": "yellow",
        "low": "blue",
    }

    decision_colors: dict[str, str] = {
        "approve": "green",
        "needs_changes": "yellow",
        "block": "red",
    }

    console.print(Panel.fit("[bold cyan]Security Review Assessment[/bold cyan]"))

    console.print()

    console.print(
        f"[bold]Overall Severity:[/bold] [{severity_colors[assessment.overall_severity]}]{assessment.overall_severity}[/{severity_colors[assessment.overall_severity]}]"
    )
    console.print(f"[bold]Total Findings:[/bold] {assessment.total_findings}")
    console.print()

    if assessment.critical_count > 0:
        console.print(f"[red]  Critical: {assessment.critical_count}[/red]")
    if assessment.high_count > 0:
        console.print(f"[bright_red]  High: {assessment.high_count}[/bright_red]")
    if assessment.medium_count > 0:
        console.print(f"[yellow]  Medium: {assessment.medium_count}[/yellow]")
    if assessment.low_count > 0:
        console.print(f"[blue]  Low: {assessment.low_count}[/blue]")

    console.print()
    decision_color = decision_colors[assessment.merge_recommendation]
    decision_emoji: dict[str, str] = {
        "approve": "✅",
        "needs_changes": "⚠️",
        "block": "🛑",
    }

    console.print(
        f"[bold]Merge Recommendation:[/bold] [{decision_color}]{decision_emoji[assessment.merge_recommendation]} {assessment.merge_recommendation.upper()}[/{decision_color}]"
    )
    console.print()
    console.print(f"[dim]{assessment.summary}[/dim]")

    if assessment.notes:
        console.print()
        console.print("[bold]Notes:[/bold]")
        for note in assessment.notes:
            console.print(f"[dim]  • {note}[/dim]")

    if assessment.findings:
        console.print()
        console.print(Panel.fit("[bold cyan]Detailed Findings[/bold cyan]"))

        for i, finding in enumerate(assessment.findings, 1):
            console.print()
            console.print(f"[bold magenta]Finding #{i}:[/bold magenta]")

            console.print(f"  [cyan]ID:[/cyan] {finding.id}")
            console.print(
                f"  [{severity_colors[finding.severity]}]Severity:[/{severity_colors[finding.severity]}] {finding.severity}"
            )
            console.print(f"  [bold]Title:[/bold] {finding.title}")
            console.print(f"  [dim]Description:[/dim] {finding.description}")
            console.print(f"  [dim]Evidence:[/dim]")
            console.print(f"    [dim]{finding.evidence}[/dim]")

            if finding.file_path:
                console.print(f"  [dim]File:[/dim] {finding.file_path}")
                if finding.line_number:
                    console.print(f"  [dim]Line:[/dim] {finding.line_number}")

            if finding.recommendation:
                console.print(f"  [dim]Recommendation:[/dim] {finding.recommendation}")


@click.group()
def fsm_security():
    """FSM-based security review with subagent delegation."""
    pass


def main():
    """Main entry point for FSM CLI."""
    return fsm_security()


@fsm_security.command()
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
    "--max-iterations",
    type=int,
    default=5,
    help="Maximum review iterations (default: 5)",
)
@click.option(
    "--install-tools",
    is_flag=True,
    help="Install missing tools using uv tool install",
)
@click.option(
    "--no-tool-check",
    is_flag=True,
    help="Skip tool installation check",
)
@click.option(
    "--output",
    type=click.Choice(["terminal", "json"]),
    default="terminal",
    help="Output format (default: terminal)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
def review(
    repo_root: Path,
    base_ref: str,
    head_ref: str,
    max_iterations: int,
    install_tools: bool,
    no_tool_check: bool,
    output: Literal["terminal", "json"],
    verbose: bool,
) -> None:
    """Run FSM-based security review with subagent delegation.

    This command performs a comprehensive security review using:
    - Finite State Machine (FSM) for lifecycle management
    - Subagent delegation for investigation (no investigation by main agent)
    - Dynamic todo creation based on exploration
    - Iterative review with additional task generation
    - Final security assessment
    - LLM-powered analysis (when configured)

    Required tools (can be installed automatically with --install-tools):
    - git: For diff and changed files
    - uv: For tool installation (if using --install-tools)

    Optional LLM configuration:
    - Requires dawn-kestrel account configuration with API key
    - LLM enhances analysis, pattern detection, and assessment generation
    """

    async def run_review() -> None:
        setup_logging(verbose)

        console.print("[bold cyan]FSM-based Security Review[/bold cyan]")
        console.print()

        console.print(f"[dim]Repository:[/dim] {repo_root}")
        console.print(f"[dim]Base ref:[/dim] {base_ref}")
        console.print(f"[dim]Head ref:[/dim] {head_ref}")
        console.print()

        # Tools that might be needed
        required_tools = ["git"]

        # Ensure tools are installed
        try:
            ensure_tools_installed(required_tools, install_tools, verbose, no_tool_check)
        except click.ClickException:
            raise

        console.print()

        # Import here to avoid circular imports
        from dawn_kestrel.agents.orchestrator import AgentOrchestrator
        from dawn_kestrel.agents.runtime import AgentRuntime
        from dawn_kestrel.agents.registry import AgentRegistry

        # Create real runtime with registry and base directory
        registry = AgentRegistry()
        runtime = AgentRuntime(agent_registry=registry, base_dir=repo_root)
        orchestrator = AgentOrchestrator(runtime)

        # Create session ID
        session_id = f"fsm_security_review_{asyncio.get_event_loop().time()}"

        # Import security reviewer
        try:
            from dawn_kestrel.agents.review.fsm_security import SecurityReviewerAgent
        except ImportError as e:
            console.print(f"[yellow]Warning: Could not import SecurityReviewerAgent: {e}[/yellow]")
            console.print(
                "[dim]Make sure dawn_kestrel.agents.review.fsm_security module exists[/dim]"
            )
            raise click.ClickException("Could not import SecurityReviewerAgent")

        llm_client = None
        try:
            from dawn_kestrel.llm import LLMClient
            from dawn_kestrel.core.settings import settings

            default_account = settings.get_default_account()
            if default_account:
                provider_id = default_account.provider_id
                model = default_account.model
                api_key = default_account.api_key.get_secret_value()

                llm_client = LLMClient(
                    provider_id=provider_id,
                    model=model,
                    api_key=api_key,
                )
                if verbose:
                    console.print(f"[dim]LLM client initialized: {provider_id} / {model}[/dim]")
            else:
                console.print(
                    "[yellow]Warning: No default account configured - LLM features disabled[/yellow]"
                )
                console.print("[dim]Configure account with: dawn-kestrel account add[/dim]")
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to initialize LLM client: {e}[/yellow]")
            console.print("[dim]Continuing without LLM features[/dim]")

        # Create security reviewer agent
        reviewer = SecurityReviewerAgent(
            orchestrator=orchestrator,
            session_id=session_id,
            llm_client=llm_client,
        )

        # Set max iterations
        reviewer.max_iterations = max_iterations

        # Run security review
        try:
            assessment = await reviewer.run_review(
                repo_root=str(repo_root),
                base_ref=base_ref,
                head_ref=head_ref,
            )

            # Display results
            console.print()
            if output == "terminal":
                format_security_assessment(assessment)
            elif output == "json":
                import json

                assessment_data = {
                    "overall_severity": assessment.overall_severity,
                    "total_findings": assessment.total_findings,
                    "critical_count": assessment.critical_count,
                    "high_count": assessment.high_count,
                    "medium_count": assessment.medium_count,
                    "low_count": assessment.low_count,
                    "merge_recommendation": assessment.merge_recommendation,
                    "summary": assessment.summary,
                    "notes": assessment.notes,
                    "findings": [
                        {
                            "id": f.id,
                            "severity": f.severity,
                            "title": f.title,
                            "description": f.description,
                            "evidence": f.evidence,
                            "file_path": f.file_path,
                            "line_number": f.line_number,
                            "recommendation": f.recommendation,
                        }
                        for f in assessment.findings
                    ],
                }

                console.print(json.dumps(assessment_data, indent=2))

            console.print()
            console.print("[green]✓ Security review completed successfully[/green]")

        except Exception as e:
            console.print()
            console.print(f"[red]✗ Security review failed: {e}[/red]")
            if verbose:
                import traceback

                console.print()
                console.print("[red]Traceback:[/red]")
                console.print(traceback.format_exc())
            raise click.ClickException(str(e))

    try:
        asyncio.run(run_review())
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]⚠ Review interrupted by user[/yellow]")
        sys.exit(130)
    except click.ClickException:
        raise
    except Exception as e:
        console.print()
        console.print(f"[red]Unexpected error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)


@fsm_security.command()
@click.argument("tool_name", required=True)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output from uv",
)
def install_tool(tool_name: str, verbose: bool) -> None:
    """Install a security tool using uv.

    Installs the specified tool using `uv tool install`.
    Useful for pre-installing tools before running a review.

    Examples:
        dawn-kestrel fsm-security install-tool bandit
        dawn-kestrel fsm-security install-tool semgrep
    """
    console.print(f"[cyan]Installing {tool_name} with uv...[/cyan]")
    console.print()

    if not install_tool_with_uv(tool_name, verbose):
        sys.exit(1)

    console.print()
    console.print(f"[green]✓ {tool_name} installed successfully[/green]")


@fsm_security.command()
def check_tools():
    """Check which security tools are installed.

    Displays status of common security tools used by the FSM reviewer:
    - bandit: Python SAST scanner
    - semgrep: Static analysis tool
    - safety: Dependency vulnerability checker
    - git: Version control (required)
    - uv: Package manager (for tool installation)
    """
    logger = logging.getLogger(__name__)

    console.print("[bold cyan]Tool Installation Check[/bold cyan]")
    console.print()

    tools_to_check = [
        "bandit",
        "semgrep",
        "safety",
        "git",
        "uv",
    ]

    table = Table(title="Tool Status", show_header=True, header_style="bold magenta")
    table.add_column("Tool", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")

    installed_count = 0
    for tool in tools_to_check:
        is_installed = check_tool_installed(tool)
        version = "unknown"

        if is_installed:
            installed_count += 1
            try:
                result = subprocess.run(
                    [tool, "--version"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                version = result.stdout.strip().split("\n")[0]
                logger.debug(f"Tool {tool} version: {version}")
            except Exception:
                version = "installed"

        table.add_row(
            tool,
            f"[green]✓ Installed[/green]" if is_installed else f"[red]✗ Missing[/red]",
            version,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Installed: {installed_count}/{len(tools_to_check)} tools[/dim]")

    if installed_count < len(tools_to_check):
        console.print()
        console.print("[yellow]Tip: Install missing tools with:[/yellow]")
        console.print("[cyan]  dawn-kestrel fsm-security install-tool <tool-name>[/cyan]")
        console.print("[cyan]  dawn-kestrel fsm-security review --install-tools[/cyan]")


if __name__ == "__main__":
    fsm_security()
