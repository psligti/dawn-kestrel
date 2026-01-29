"""
CLI command for AI interactions.

Provides unified interface for AI sessions, model selection,
and configuration management across all providers.
"""

import click
from typing import Optional
import pendulum
from rich.table import Table
from rich.console import Console

from ..ai_session import AISession
from ..core.settings import settings
from opencode_python.session import SessionManager


console = Console()


@click.group()
def model():
    """Model selection and configuration"""
    pass


@model.command()
def list_models():
    """List all available models from providers"""
    api_key = settings.api_keys.get("anthropic", settings.api_keys.get("openai"))
    
    if not api_key:
        console.print("[yellow]No API key configured. Set OPENCODE_PYTHON_ANTHROPIC_API_KEY or OPENCODE_PYTHON_OPENAI_API_KEY[/yellow]")
        return
    
    console.print("\n[bold]Available Models:[/bold]")
    
    from ..providers import get_available_models, ProviderID
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Family", style="blue")
    table.add_column("Input Cost", style="yellow")
    table.add_column("Output Cost", style="yellow")
    table.add_column("Context", style="magenta")
    table.add_column("Status", style="dim")
    
    models = []
    for model_info in get_available_models():
        context_str = f"{model_info.limit.context:,}"
        table.add_row(
            model_info.provider_id.value,
            model_info.name,
            model_info.family,
            f"${model_info.cost.input:,}M",
            f"${model_info.cost.output:,}M",
            context_str,
            model_info.status
        )
        models.append(model_info)
    
    table.add_section(models)
    console.print(table)


@model.command()
def set_default(provider: str, model: str):
    """Set default model for provider"""
    pass


@click.command()
@click.argument("message", required=False, default="")
@click.option("--model", "-m", default=None, help="Model to use")
@click.option("--provider", "-p", default=None, help="AI provider")
@click.option("--session", "-s", default=None, help="Resume existing session")
def run(message: str, model: Optional[str], provider: Optional[str], session: Optional[str]):
    """Run a message through AI session"""
    api_key = settings.api_keys.get(provider or "anthropic", settings.api_keys.get("openai"))
    
    if not api_key:
        console.print("[yellow]No API key configured. Set OPENCODE_PYTHON_ANTHROPIC_API_KEY or OPENCODE_PYTHON_OPENAI_API_KEY[/yellow]")
        return
    
    if session:
        console.print(f"[dim]Resuming session: {session}[/dim]")
    
    console.print(f"[cyan]Processing message with {model or 'default model'}...[/cyan]")
    console.print(f"[dim]'{message}'[/dim]")
    console.print()
    
    session = AISession(directory=".")
    session.process_message(message, model=model)


@click.command()
def new_session():
    """Create a new AI session"""
    import pendulum
    from ..core.settings import settings
    
    from ..core.session import SessionManager
    
    session_mgr = SessionManager()
    slug = SessionManager.generate_slug()
    
    session = session_mgr.create(
        directory=settings.project_directory,
        title=f"New session - {pendulum.now().format('YYYY-MM-DD HH:mm')}"
    )
    
    console.print(f"[green]Created session: {session.id}[/green]")
    console.print(f"[dim]Slug: {session.slug}[/dim]")
    console.print()


@click.command()
def list_sessions():
    """List all sessions"""
    from ..core.session import SessionManager
    from rich.table import Table
    from rich.console import Console
    
    session_mgr = SessionManager()
    sessions = session_mgr.list_all()
    
    console = Console()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="green")
    table.add_column("Updated", style="blue")
    table.add_column("Messages", style="yellow")
    table.add_column("Cost", style="magenta")
    table.add_column("Status", style="dim")
    
    for session_info in sessions:
        table.add_row(
            session_info.id[:8],
            session_info.title[:30],
            pendulum.from_timestamp(session_info.time_updated).diff_for_humans(),
            session_info.message_count,
            f"${session_info.total_cost:.2f}",
            "idle"
        )
    
    console.add_section(table)
    console.print()


@click.command()
def export_session(session_id: str):
    """Export session to JSON"""
    import json
    from ..core.session import SessionManager
    from pathlib import Path
    
    session_mgr = SessionManager()
    session_data = session_mgr.get_export_data(session_id)
    
    output_path = Path(f"{session_id}.json")
    with open(output_path, "w") as f:
        json.dump(session_data, f, indent=2)
    
    console.print(f"[green]Exported session to: {output_path}[/green]")


@click.command()
def import_session(file_path: str):
    """Import session from JSON file"""
    import json
    from ..core.session import SessionManager
    from pathlib import Path
    
    session_mgr = SessionManager()
    
    if not Path(file_path).exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return
    
    with open(file_path, "r") as f:
        session_data = json.load(f)
    
    session = session_mgr.import_data(session_data)
    
    console.print(f"[green]Imported session: {session.id}[/green]")
    console.print(f"[dim]Messages: {session.message_count}[/dim]")
