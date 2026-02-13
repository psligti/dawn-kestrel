"""Dawn Kestrel CLI interface."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, cast

import click  # type: ignore[import-not-found]
import pendulum  # type: ignore[import-not-found]
from rich.console import Console  # type: ignore[import-not-found]
from rich.table import Table  # type: ignore[import-not-found]

console = Console(force_terminal=True, stderr=False)


@click.command()
@click.option(
    "--directory",
    "-d",
    type=click.Path(),
    help="Project directory (default: current directory)",
)
def connect(directory: str | None) -> None:
    """Configure dawn-kestrel for this project.

    Interactive wizard to set up provider credentials and account configuration.
    Settings are saved to .dawn-kestrel/config.toml in the project directory.
    """
    from dawn_kestrel.cli.commands import connect_command

    if directory:
        try:
            import os

            os.chdir(directory)
        except Exception as e:
            console.print(f"[red]Error: Failed to change directory: {e}[/red]")
            sys.exit(1)

    try:
        asyncio.run(connect_command())
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Configuration cancelled.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        console.print()
        console.print("[dim]Traceback:[/dim]")
        console.print(traceback.format_exc())
        sys.exit(1)


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
        from dawn_kestrel.cli.handlers import (
            CLIIOHandler,
            CLINotificationHandler,
            CLIProgressHandler,
        )
        from dawn_kestrel.core.repositories import (
            MessageRepositoryImpl,
            PartRepositoryImpl,
            SessionRepositoryImpl,
        )
        from dawn_kestrel.core.services.session_service import DefaultSessionService
        from dawn_kestrel.core.settings import settings
        from dawn_kestrel.storage.store import (
            MessageStorage,
            PartStorage,
            SessionStorage,
        )

        storage_dir = settings.storage_dir_path()
        session_storage = SessionStorage(storage_dir)
        message_storage = MessageStorage(storage_dir)
        part_storage = PartStorage(storage_dir)

        session_repo = SessionRepositoryImpl(session_storage)
        message_repo = MessageRepositoryImpl(message_storage)
        part_repo = PartRepositoryImpl(part_storage)

        if directory:
            work_dir = Path(directory).expanduser()
        else:
            work_dir = Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            part_repo=part_repo,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        result = await service.list_sessions()

        if result.is_err():
            err_result = cast(Any, result)
            console.print(f"[red]Error: {err_result.error}[/red]")
            sys.exit(1)

        sessions = result.unwrap()

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
    from dawn_kestrel.core.settings import settings

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
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "jsonl", "jsonl.gz"]),
    default="json",
    help="Export format",
)
def export_session(session_id: str, output: str | None, format: str) -> None:
    """Export a session to file"""

    async def _export() -> None:
        from dawn_kestrel.cli.handlers import (
            CLIIOHandler,
            CLINotificationHandler,
            CLIProgressHandler,
        )
        from dawn_kestrel.core.repositories import (
            MessageRepositoryImpl,
            PartRepositoryImpl,
            SessionRepositoryImpl,
        )
        from dawn_kestrel.core.services.session_service import DefaultSessionService
        from dawn_kestrel.core.session import SessionManager
        from dawn_kestrel.core.settings import settings
        from dawn_kestrel.session.export_import import ExportImportManager
        from dawn_kestrel.snapshot.index import GitSnapshot
        from dawn_kestrel.storage.store import (
            MessageStorage,
            PartStorage,
            SessionStorage,
        )

        storage_dir = settings.storage_dir_path()
        session_storage = SessionStorage(storage_dir)
        message_storage = MessageStorage(storage_dir)
        part_storage = PartStorage(storage_dir)

        session_repo = SessionRepositoryImpl(session_storage)
        message_repo = MessageRepositoryImpl(message_storage)
        part_repo = PartRepositoryImpl(part_storage)

        work_dir = Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            part_repo=part_repo,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        result = await service.get_session(session_id)

        if result.is_err():
            err_result = cast(Any, result)
            console.print(f"[red]Error: {err_result.error}[/red]")
            sys.exit(1)

        session = result.unwrap()
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            return

        git_snapshot = GitSnapshot(storage_dir, work_dir.name)
        session_manager = SessionManager(session_storage, work_dir)
        manager = ExportImportManager(session_manager, git_snapshot)

        try:
            result = await manager.export_session(
                session_id=session_id,
                output_path=Path(output) if output else None,
                format=format,
            )

            console.print("[green]Export complete![/green]")
            console.print("[dim]  Path: {}".format(result["path"]))
            console.print("[dim]  Format: {}".format(result["format"]))
            console.print("[dim]  Messages: {}".format(result["message_count"]))
        except (ValueError, FileNotFoundError, Exception) as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    run_async(_export())


@click.command()
@click.argument("import_path", type=click.Path(exists=True))
@click.option("--project-id", "-p", type=click.STRING, help="Project ID for multi-project repos")
def import_session(import_path: str, project_id: str | None) -> None:
    """Import a session from file"""

    async def _import() -> None:
        from dawn_kestrel.cli.handlers import (
            CLIIOHandler,
            CLINotificationHandler,
            CLIProgressHandler,
        )
        from dawn_kestrel.core.repositories import (
            MessageRepositoryImpl,
            PartRepositoryImpl,
            SessionRepositoryImpl,
        )
        from dawn_kestrel.core.services.session_service import DefaultSessionService
        from dawn_kestrel.core.session import SessionManager
        from dawn_kestrel.core.settings import settings
        from dawn_kestrel.session.export_import import ExportImportManager
        from dawn_kestrel.snapshot.index import GitSnapshot
        from dawn_kestrel.storage.store import (
            MessageStorage,
            PartStorage,
            SessionStorage,
        )

        storage_dir = settings.storage_dir_path()
        session_storage = SessionStorage(storage_dir)
        message_storage = MessageStorage(storage_dir)
        part_storage = PartStorage(storage_dir)

        session_repo = SessionRepositoryImpl(session_storage)
        message_repo = MessageRepositoryImpl(message_storage)
        part_repo = PartRepositoryImpl(part_storage)

        work_dir = Path.cwd()

        io_handler = CLIIOHandler()
        progress_handler = CLIProgressHandler()
        notification_handler = CLINotificationHandler()

        service = DefaultSessionService(
            session_repo=session_repo,
            message_repo=message_repo,
            part_repo=part_repo,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        session_manager = SessionManager(session_storage, work_dir)
        git_snapshot = GitSnapshot(storage_dir, work_dir.name)
        manager = ExportImportManager(session_manager, git_snapshot)

        try:
            result = await manager.import_session(
                import_path=Path(import_path),
                project_id=project_id,
            )

            console.print("[green]Import complete![/green]")
            console.print("[dim]  Session ID: {}".format(result["session_id"]))
            console.print("[dim]  Messages imported: {}".format(result["message_count"]))
        except (ValueError, FileNotFoundError, Exception) as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)

    run_async(_import())


@click.command()
def tui() -> None:
    """Launch Textual TUI interface"""
    import warnings

    warnings.warn(
        "CLI → TUI launch is deprecated. "
        "Use 'python -m dawn_kestrel.tui.app' directly instead. "
        "This feature will be removed in version 0.2.0.",
        DeprecationWarning,
        stacklevel=2,
    )

    from dawn_kestrel.tui.app import OpenCodeTUI

    app = OpenCodeTUI()
    app.run()


cast(Any, cli).add_command(list_sessions)
cast(Any, cli).add_command(run)
cast(Any, cli).add_command(export_session)
cast(Any, cli).add_command(import_session)
cast(Any, cli).add_command(tui)
cast(Any, cli).add_command(connect)
