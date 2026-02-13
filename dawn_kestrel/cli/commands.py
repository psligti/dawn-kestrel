"""Interactive CLI commands for dawn-kestrel."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

console = Console()


async def connect_command() -> None:
    """Interactive command to connect to an AI provider.

    Guides user through provider selection, account configuration,
    and saves credentials to .dawn-kestrel/config.toml.
    """

    console.print("[bold cyan]Dawn Kestrel - Interactive Configuration[/bold cyan]")
    console.print()

    from dawn_kestrel.core.config_toml import (
        get_project_config_path,
        load_config,
        save_config,
        update_config_with_account,
    )
    from dawn_kestrel.core.provider_settings import AccountConfig
    from dawn_kestrel.providers.base import ProviderID

    provider_id = None
    account_name = None
    api_key = None
    model = None

    config_path = get_project_config_path()

    if config_path.exists():
        existing_config = load_config(config_path)
        console.print(f"[dim]Existing config found at: {config_path}[/dim]")

        accounts = existing_config.get("accounts", {})
        if accounts:
            console.print("[dim]Existing accounts:[/dim]")
            for name, data in accounts.items():
                provider = data.get("provider_id", "unknown")
                is_default = " (default)" if data.get("is_default") else ""
                console.print(f"  [dim]• {name} ({provider}){is_default}[/dim]")

            if Confirm.ask("Use an existing account?", default=True):
                account_name = Prompt.ask(
                    "Which account?",
                    choices=list(accounts.keys()),
                )
                account_data = accounts[account_name]
                provider_id = ProviderID(account_data["provider_id"])
                model = account_data.get("model", "")
                console.print()
                console.print(f"[green]✓ Using existing account: {account_name}[/green]")
                console.print()

    if provider_id is None:
        console.print("[bold]1. Select Provider[/bold]")
        console.print()

        providers = [
            "anthropic",
            "openai",
            "zai",
            "zai_coding_plan",
            "github-copilot",
        ]

        console.print("[dim]Use ↑/↓ arrow keys to navigate, Enter to select[/dim]")
        console.print()

        provider_choice = Prompt.ask(
            "Which provider?",
            choices=providers,
            default="anthropic",
        )

        provider_map = {
            "anthropic": ProviderID.ANTHROPIC,
            "openai": ProviderID.OPENAI,
            "zai": ProviderID.Z_AI,
            "zai_coding_plan": ProviderID.Z_AI_CODING_PLAN,
            "github-copilot": ProviderID.GITHUB_COPILOT,
        }

        provider_id = provider_map.get(provider_choice)
        console.print(f"  [cyan]Provider: {provider_choice}[/cyan]")
        console.print()

    if account_name is None:
        account_name = Prompt.ask("Account name (e.g., personal, work)", default="default")
        console.print(f"  [cyan]Account name: {account_name}[/cyan]")
        console.print()

    if api_key is None:
        if provider_id == ProviderID.GITHUB_COPILOT:
            console.print("[yellow]GitHub Copilot OAuth Authentication[/yellow]")
            console.print("[dim]Using GitHub OAuth 2.0 Device Code Flow[/dim]")
            console.print()

            if not Confirm.ask("Continue with OAuth?", default=True):
                api_key = Prompt.ask("Enter your GitHub Personal Access Token", password=True)
            else:
                from dawn_kestrel.providers.oauth_github_copilot import GitHubOAuthClient

                console.print("[cyan]Step 1: Requesting device code from GitHub...[/cyan]")

                client = GitHubOAuthClient()

                try:
                    device_response = client.request_device_code()

                except RuntimeError as e:
                    console.print(f"[red]✗ Failed to get device code: {e}[/red]")
                    sys.exit(1)

                user_code = device_response.get("user_code", "")
                verification_uri = device_response.get("verification_uri", "")

                if not verification_uri:
                    console.print("[red]✗ No verification URL returned[/red]")
                    sys.exit(1)

                console.print()
                console.print(f"[dim]Verification URL: {verification_uri}[/dim]")
                console.print(f"[dim]Enter code: {user_code}[/dim]")
                console.print()
                console.print("[cyan]Step 2: Waiting for authorization...[/cyan]")
                console.print("[dim](Opening browser...)[/dim]")
                console.print()

                try:
                    import webbrowser

                    webbrowser.open(verification_uri)
                except Exception:
                    console.print(
                        "[yellow]⚠ Could not open browser. Please open the URL manually.[/yellow]"
                    )

                console.print()
                console.print("[bold]Step 3: Exchanging code for access token...[/bold]")
                console.print("[dim](Polling GitHub... This may take up to 90 seconds)[/dim]")
                console.print()

                try:
                    tokens = await client.poll_for_token(device_response)
                except RuntimeError as e:
                    console.print(f"[red]✗ Token exchange/polling failed: {e}[/red]")
                    sys.exit(1)

                if "access_token" in tokens:
                    api_key = tokens["access_token"]
                    console.print("[green]✓ Access token obtained[/green]")
                else:
                    console.print(f"[red]✗ Failed to get token: {tokens}[/red]")
                    sys.exit(1)

                console.print()
                console.print("[cyan]Step 2: Requesting device code from GitHub...[/cyan]")

                client = GitHubOAuthClient(client_id=client_id)

                try:
                    device_response = client.request_device_code(
                        scopes=["read:org", "codespace", "copilot"],
                    )

                except RuntimeError as e:
                    console.print(f"[red]✗ Failed to get device code: {e}[/red]")
                    sys.exit(1)

                user_code = device_response.get("user_code", "")
                verification_uri = device_response.get("verification_uri", "")

                if not verification_uri:
                    console.print("[red]✗ No verification URL returned[/red]")
                    sys.exit(1)

                console.print()
                console.print(f"[dim]Please visit: {verification_uri}[/dim]")
                console.print(f"[dim]Enter code: {user_code}[/dim]")
                console.print()
                console.print("[cyan]Step 3: Waiting for authorization...[/cyan]")

                console.print()
                console.print("[bold]Step 4: Exchanging code for access token...[/bold]")
                console.print(
                    "[dim](Waiting up to 15 minutes for you to authorize on GitHub)[/dim]"
                )
                console.print()

                try:
                    tokens = await client.poll_for_token(device_response)
                except RuntimeError as e:
                    console.print(f"[red]✗ Token exchange/polling failed: {e}[/red]")
                    sys.exit(1)

                if "access_token" in tokens:
                    api_key = tokens["access_token"]
                    console.print("[green]✓ Access token obtained[/green]")
                else:
                    console.print(f"[red]✗ Failed to get token: {tokens}[/red]")
                    sys.exit(1)

                user_code = device_response.get("user_code", "")
                verification_uri = device_response.get("verification_uri", "")

                if not verification_uri:
                    console.print("[red]✗ No verification URL returned[/red]")
                    sys.exit(1)

                console.print()
                console.print(f"[dim]Please visit: {verification_uri}[/dim]")
                console.print(f"[dim]Enter code: {user_code}[/dim]")
                console.print()
                console.print("[cyan]Step 3: Waiting for device code...[/cyan]")

                device_code = Prompt.ask("Enter device code", default="")

                if not device_code:
                    console.print("[red]✗ No code entered. Authentication cancelled.[/red]")
                    sys.exit(1)

                console.print()
                console.print("[cyan]Step 4: Exchanging code for access token...[/cyan]")

                try:
                    tokens = client.exchange_device_code(device_code)
                except RuntimeError as e:
                    console.print(f"[red]✗ Token exchange failed: {e}[/red]")
                    sys.exit(1)

                if "access_token" in tokens:
                    api_key = tokens["access_token"]
                    console.print("[green]✓ Access token obtained[/green]")
                else:
                    console.print(f"[red]✗ Failed to get token: {tokens}[/red]")
                    sys.exit(1)

                if not verification_url:
                    console.print("[red]✗ No verification URL returned[/red]")
                    sys.exit(1)

                console.print()
                console.print(f"[dim]Verification URL: {verification_url}[/dim]")
                console.print()
                console.print("[cyan]Step 2: Opening browser...[/cyan]")

                try:
                    import webbrowser

                    webbrowser.open(verification_url)
                except ImportError:
                    console.print("[yellow]⚠ webbrowser not available. Open URL manually.[/yellow]")
                except Exception:
                    console.print("[yellow]⚠ Could not open browser. Open URL manually.[/yellow]")

                console.print()
                console.print("[bold]Step 3: Enter the device code from GitHub[/bold]")
                console.print("[dim](After authorizing on GitHub, you'll see a code)[/dim]")
                console.print()

                device_code = Prompt.ask("Device code", default="")

                if not device_code:
                    console.print("[red]✗ No code entered. Authentication cancelled.[/red]")
                    sys.exit(1)

                console.print()
                console.print("[cyan]Step 4: Exchanging code for access token...[/cyan]")

                try:
                    tokens = client.exchange_code_for_token(device_code)
                except RuntimeError as e:
                    console.print(f"[red]✗ Token exchange failed: {e}[/red]")
                    sys.exit(1)

                if "access_token" in tokens:
                    api_key = tokens["access_token"]
                    console.print("[green]✓ Access token obtained[/green]")

                    if "expires_in" in tokens:
                        expires_minutes = int(tokens["expires_in"]) / 60
                        console.print(f"[dim]  Expires in: {expires_minutes} minutes[/dim]")
                else:
                    console.print(f"[red]✗ Failed to get token: {tokens}[/red]")
                    sys.exit(1)

        else:
            console.print(f"[cyan]Enter your {provider_id.value} API key:[/cyan]")
            api_key = Prompt.ask("API key", password=True)
            console.print()

    if model is None:
        default_models = {
            ProviderID.ANTHROPIC: "claude-sonnet-4-20250514",
            ProviderID.OPENAI: "gpt-5",
            ProviderID.Z_AI: "glm-4.7",
            ProviderID.Z_AI_CODING_PLAN: "glm-4.7",
            ProviderID.GITHUB_COPILOT: "claude-haiku",
        }

        default_model = default_models.get(provider_id, "")
        model = Prompt.ask("Default model", default=default_model)

        if model:
            console.print(f"  [cyan]Model: {model}[/cyan]")
            console.print()

    config_data = load_config(config_path) if config_path.exists() else {}

    account_config = AccountConfig(
        account_name=account_name,
        provider_id=provider_id,
        api_key=api_key,
        model=model,
        is_default=True,
    )

    config_data = update_config_with_account(config_data, account_config, account_name)

    saved_path = save_config(config_data, config_path)

    console.print()
    console.print(f"[green]✓ Configuration saved to: {saved_path}[/green]")
    console.print()
    console.print("[dim]Your configuration is now active for this directory.[/dim]")
    console.print()
    console.print("[cyan]Next steps:[/cyan]")
    console.print("  [dim]• Use 'dawn-kestrel run' to chat[/dim]")
    console.print("  [dim]• Use 'dawn-kestrel tui' for TUI mode[/dim]")
