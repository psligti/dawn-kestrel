"""
CLI command for AI interactions.

Provides unified interface for AI sessions, model selection,
and configuration management across all providers.
"""

import click
from typing import Optional
import pendulum
from pydantic import SecretStr
from rich.table import Table
from rich.console import Console

from ..ai_session import AISession
from ..core.settings import settings
from ..core.session import SessionManager


console = Console()


@click.group()
def model():
    """Model selection and configuration"""
    pass


@model.command()
def list_models():
    """List all available models from providers"""
    import asyncio
    from ..providers import get_available_models, ProviderID

    anthropic_key = settings.api_keys.get("anthropic", SecretStr(""))
    openai_key = settings.api_keys.get("openai", SecretStr(""))

    if not anthropic_key and not openai_key:
        console.print("[yellow]No API key configured. Set OPENCODE_PYTHON_ANTHROPIC_API_KEY or OPENCODE_PYTHON_OPENAI_API_KEY[/yellow]")
        return

    console.print("\n[bold]Available Models:[/bold]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Family", style="blue")
    table.add_column("Input Cost", style="yellow")
    table.add_column("Output Cost", style="yellow")
    table.add_column("Context", style="magenta")
    table.add_column("Status", style="dim")

    async def fetch_models():
        models = []
        if anthropic_key:
            for model_info in await get_available_models(ProviderID.ANTHROPIC, anthropic_key.get_secret_value()):
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
        if openai_key:
            for model_info in await get_available_models(ProviderID.OPENAI, openai_key.get_secret_value()):
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
        return models

    asyncio.run(fetch_models())
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
    import asyncio
    from pathlib import Path
    from opencode_python.storage.store import SessionStorage
    from ..core.models import Session

    provider_id = provider or "anthropic"
    api_key = settings.api_keys.get(provider_id, settings.api_keys.get("openai"))

    if not api_key or not api_key.get_secret_value():
        console.print("[yellow]No API key configured. Set OPENCODE_PYTHON_ANTHROPIC_API_KEY or OPENCODE_PYTHON_OPENAI_API_KEY[/yellow]")
        return

    if session:
        console.print(f"[dim]Resuming session: {session}[/dim]")

    console.print(f"[cyan]Processing message with {model or 'default model'}...[/cyan]")
    console.print(f"[dim]'{message}'[/dim]")
    console.print()

    async def process():
        # Setup storage and session manager
        storage_dir = Path(settings.storage_dir).expanduser()
        storage = SessionStorage(storage_dir)
        project_dir = Path.cwd()
        session_mgr = SessionManager(storage, project_dir)

        # Get or create session
        if session:
            session_obj = await session_mgr.get_session(session)
            if not session_obj:
                console.print(f"[red]Session not found: {session}[/red]")
                return
        else:
            # Create a new session
            session_obj = await session_mgr.create(
                title=f"Session - {pendulum.now().format('YYYY-MM-DD HH:mm')}"
            )

        # Create AISession
        model_name = model or settings.model_default
        ai_session = AISession(
            session=session_obj,
            provider_id=provider_id,
            model=model_name,
            api_key=api_key.get_secret_value(),
            session_manager=session_mgr
        )

        # Process message
        await ai_session.process_message(message)
        console.print(f"[green]Message processed successfully[/green]")

    asyncio.run(process())


@click.command()
def new_session():
    """Create a new AI session"""
    import asyncio
    from pathlib import Path
    from opencode_python.storage.store import SessionStorage
    from ..core.settings import settings

    from ..core.session import SessionManager

    async def create():
        storage_dir = Path(settings.storage_dir).expanduser()
        storage = SessionStorage(storage_dir)
        project_dir = Path.cwd()
        session_mgr = SessionManager(storage, project_dir)

        title = f"New session - {pendulum.now().format('YYYY-MM-DD HH:mm')}"
        session = await session_mgr.create(title=title)

        console.print(f"[green]Created session: {session.id}[/green]")
        console.print(f"[dim]Slug: {session.slug}[/dim]")
        console.print()

    asyncio.run(create())


@click.command()
def list_sessions():
    """List all sessions"""
    import asyncio
    from pathlib import Path
    from opencode_python.storage.store import SessionStorage
    from rich.table import Table

    async def list():
        storage_dir = Path(settings.storage_dir).expanduser()
        storage = SessionStorage(storage_dir)
        project_dir = Path.cwd()
        session_mgr = SessionManager(storage, project_dir)

        sessions = await session_mgr.list_all()

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
                str(session_info.message_count),
                f"${session_info.total_cost:.2f}",
                "idle"
            )

        console.print(table)

    asyncio.run(list())


@click.command()
@click.argument("session_id")
def export_session(session_id: str):
    """Export session to JSON"""
    import asyncio
    import json
    from pathlib import Path
    from opencode_python.storage.store import SessionStorage

    async def export():
        storage_dir = Path(settings.storage_dir).expanduser()
        storage = SessionStorage(storage_dir)
        project_dir = Path.cwd()
        session_mgr = SessionManager(storage, project_dir)

        session_data = await session_mgr.get_export_data(session_id)

        output_path = Path(f"{session_id}.json")
        with open(output_path, "w") as f:
            json.dump(session_data, f, indent=2)

        console.print(f"[green]Exported session to: {output_path}[/green]")

    asyncio.run(export())


@click.command()
@click.argument("file_path")
def import_session(file_path: str):
    """Import session from JSON file"""
    import asyncio
    import json
    from pathlib import Path
    from opencode_python.storage.store import SessionStorage

    async def import_():
        storage_dir = Path(settings.storage_dir).expanduser()
        storage = SessionStorage(storage_dir)
        project_dir = Path.cwd()
        session_mgr = SessionManager(storage, project_dir)

        if not Path(file_path).exists():
            console.print(f"[red]File not found: {file_path}[/red]")
            return

        with open(file_path, "r") as f:
            session_data = json.load(f)

        session = await session_mgr.import_data(session_data)

        console.print(f"[green]Imported session: {session.id}[/green]")
        console.print(f"[dim]Messages: {session.message_count}[/dim]")

    asyncio.run(import_())
