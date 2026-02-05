"""OpenCode Python CLI Interface"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click
import pendulum
from rich.console import Console
from rich.table import Table

from opencode_python.core.settings import (
    settings,
    get_storage_dir,
    get_config_dir,
    get_cache_dir,
)
from opencode_python.core.session import SessionManager
from opencode_python.session.export_import import ExportImportManager
from opencode_python.storage.store import SessionStorage
from opencode_python.cli.handlers import (
    CLIIOHandler,
    CLIProgressHandler,
    CLINotificationHandler,
)
from opencode_python.core.services.session_service import DefaultSessionService

console = Console()


def run_async(coro: Any) -> None:
    """Helper to run async function in sync context"""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        sys.exit(0)


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """OpenCode Python - CLI + TUI for AI-assisted development"""
    pass


@click.command()
@click.option("--directory", "-d", type=click.Path(), help="Project directory")
def list_sessions(directory: str | None) -> None:
    """List all sessions in a project"""
    async def _list() -> None:
        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)

        work_dir = Path(directory).expanduser() if directory else Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            storage=storage,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        sessions = await service.list_sessions()

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Created", style="dim")

        for session in sessions:
            created = pendulum.from_timestamp(session.time_created).format("YYYY-MM-DD HH:mm")
            table.add_row(session.id, session.title, created)

        console.print(table)

    run_async(_list())


@click.command()
@click.argument("message", nargs=-1)
@click.option("--agent", "-a", default="build", help="Agent to use")
@click.option("--model", "-m", help="Model to use")
def run(message: tuple[str, ...], agent: str, model: str | None) -> None:
    """Run OpenCode with a message (non-interactive mode)"""

    if settings.debug:
        console.print("[dim]Running in debug mode[/dim]")

    console.print("[cyan]Agent:[/cyan] {}".format(agent))
    console.print("[cyan]Model:[/cyan] {}".format(model))
    console.print("[cyan]Message:[/cyan] {}".format(message))

    console.print("[dim]\n--- Session started ---[/dim]")
    console.print("[dim]Use 'opencode tui' to launch TUI mode.[/dim]")


@click.command()
@click.argument("session_id", type=click.STRING)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--format", "-f", type=click.Choice(['json', 'jsonl', 'jsonl.gz']), default="json", help="Export format")
def export_session(session_id: str, output: str | None, format: str) -> None:
    """Export a session to file"""
    async def _export() -> None:
        from opencode_python.snapshot.index import GitSnapshot

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        work_dir = Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            storage=storage,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        session = await service.get_session(session_id)
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            return

        git_snapshot = GitSnapshot(storage_dir, work_dir.name)
        session_manager = SessionManager(storage, work_dir)
        manager = ExportImportManager(session_manager, git_snapshot)

        result = await manager.export_session(
            session_id=session_id,
            output_path=Path(output) if output else None,
            format=format,
        )

        console.print("[green]Export complete![/green]")
        console.print("[dim]  Path: {}".format(result['path']))
        console.print("[dim]  Format: {}".format(result['format']))
        console.print("[dim]  Messages: {}".format(result['message_count']))

    run_async(_export())


@click.command()
@click.argument("import_path", type=click.Path(exists=True))
@click.option("--project-id", "-p", type=click.STRING, help="Project ID for multi-project repos")
def import_session(import_path: str, project_id: str | None) -> None:
    """Import a session from file"""
    async def _import() -> None:
        from opencode_python.snapshot.index import GitSnapshot
        from opencode_python.storage.store import MessageStorage

        storage_dir = get_storage_dir()
        storage = SessionStorage(storage_dir)
        work_dir = Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            storage=storage,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        session_manager = SessionManager(storage, work_dir)
        git_snapshot = GitSnapshot(storage_dir, work_dir.name)
        manager = ExportImportManager(session_manager, git_snapshot)

        result = await manager.import_session(
            import_path=Path(import_path),
            project_id=project_id,
        )

        console.print("[green]Import complete![/green]")
        console.print("[dim]  Session ID: {}".format(result['session_id']))
        console.print("[dim]  Messages imported: {}".format(result['message_count']))

    run_async(_import())


@click.command()
def tui() -> None:
    """Launch Textual TUI interface"""
    import warnings

    warnings.warn(
        "CLI → TUI launch is deprecated. "
        "Use 'python -m opencode_python.tui.app' directly instead. "
        "This feature will be removed in version 0.2.0.",
        DeprecationWarning,
        stacklevel=2,
    )

    from opencode_python.tui.app import OpenCodeTUI
    app = OpenCodeTUI()
    app.run()


cli.add_command(list_sessions)
cli.add_command(run)
cli.add_command(export_session)
cli.add_command(import_session)
cli.add_command(tui)

from opencode_python.agents.review.cli import review, generate_docs
cli.add_command(review)
cli.add_command(generate_docs)
