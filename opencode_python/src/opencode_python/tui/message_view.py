"""OpenCode Python - Message and Part rendering for TUI"""
from __future__ import annotations

from typing import Any, Iterator

from textual.containers import Container, Vertical, Horizontal  # type: ignore[import-not-found]
from textual.widgets import Static, Markdown, Button, Input  # type: ignore[import-not-found]
from textual.app import ComposeResult  # type: ignore[import-not-found]
from textual.reactive import reactive  # type: ignore[import-not-found]
import logging

logger = logging.getLogger(__name__)


class MessagePartView(Container):  # type: ignore[misc]
    """Display a message part (text, tool, file, etc.)"""

    CSS = """
    MessagePartView {
        margin: 0 1;
    }
    
    .part-header {
        text-style: bold;
        margin-bottom: 0;
    }
    
    .part-content {
        padding: 0 1;
        margin-bottom: 1;
    }
    
    .tool-status-pending {
        color: yellow;
    }
    
    .tool-status-running {
        color: cyan;
    }
    
    .tool-status-completed {
        color: green;
    }
    
    .tool-status-error {
        color: red;
    }
    """

    def __init__(self, part_data: dict[str, Any]):
        super().__init__()
        self.part_data = part_data
        self.part_type = part_data.get("part_type", "text")

    def compose(self) -> ComposeResult:
        if self.part_type == "text":
            text = self.part_data.get("text", "")
            yield Static(text, classes="part-content")
        
        elif self.part_type == "tool":
            tool_name = self.part_data.get("tool", "unknown")
            state = self.part_data.get("state", {})
            status = state.get("status", "unknown") if isinstance(state, dict) else "unknown"
            
            status_class = f"tool-status-{status}"
            status_emoji = {
                "pending": "⏳",
                "running": "▶️",
                "completed": "✅",
                "error": "❌",
                "unknown": "❓",
            }.get(status, "❓")
            
            yield Static(f"[bold cyan]{status_emoji} {tool_name}[/bold cyan]", classes="part-header")
            yield Static(f"[dim]Status: [{status_class}]{status}[/][/dim]", classes="part-content")
            
            if isinstance(state, dict):
                input_data = state.get("input", {})
                if input_data:
                    yield Static(f"[dim]Input: {input_data}[/dim]", classes="part-content")
                
                output = state.get("output", "")
                if output:
                    yield Static(f"[dim]Output:[/dim]", classes="part-header")
                    lines = output.split("\n")[:10]
                    for line in lines:
                        yield Static(f"[dim]  {line}[/dim]", classes="part-content")
                    if len(output.split("\n")) > 10:
                        output_lines = output.split('\n')
                        yield Static(f"[dim]... ({len(output_lines)} more lines)[/dim]", classes="part-content")
            
        elif self.part_type == "file":
            filename = self.part_data.get("filename", "")
            mime = self.part_data.get("mime", "")
            yield Static(f"[bold green]📎 {filename}[/bold green] [dim]({mime})[/dim]", classes="part-header")
        
        elif self.part_type == "reasoning":
            text = self.part_data.get("text", "")
            yield Static(f"[bold yellow]💭 Thinking[/bold yellow]", classes="part-header")
            yield Static(f"[dim]{text}[/dim]", classes="part-content")
        
        elif self.part_type == "snapshot":
            snapshot_id = self.part_data.get("snapshot", "")
            yield Static(f"[bold magenta]📸 Snapshot:[/bold magenta] {snapshot_id}", classes="part-header")
        
        elif self.part_type == "patch":
            files = self.part_data.get("files", [])
            files_count = len(files)
            patch_hash = self.part_data.get("hash", "")
            yield Static(f"[bold blue]🔧 Patch:[/bold blue] {files_count} files [dim]({patch_hash[:8]})[/dim]", classes="part-header")
            if files:
                for file in files[:5]:
                    yield Static(f"[dim]  • {file}[/dim]", classes="part-content")
                if len(files) > 5:
                    yield Static(f"[dim]  ... and {len(files) - 5} more[/dim]", classes="part-content")
        
        elif self.part_type == "agent":
            agent_name = self.part_data.get("name", "")
            yield Static(f"[bold purple]🤖 Agent:[/bold purple] {agent_name}", classes="part-header")
        
        elif self.part_type == "subtask":
            session_id = self.part_data.get("session_id", "")
            category = self.part_data.get("category", "")
            yield Static(f"[bold purple]📋 Subtask:[/bold purple] {category}", classes="part-header")
            yield Static(f"[dim]{session_id}[/dim]", classes="part-content")
        
        elif self.part_type == "retry":
            attempt = self.part_data.get("attempt", 1)
            yield Static(f"[bold orange]🔄 Retry:[/bold orange] Attempt {attempt}", classes="part-header")
        
        elif self.part_type == "compaction":
            auto = self.part_data.get("auto", False)
            yield Static(f"[bold cyan]📦 Compaction:[/bold cyan] {'Auto' if auto else 'Manual'}", classes="part-header")


class MessageView(Container):  # type: ignore[misc]
    """Display a complete message with all parts"""

    CSS = """
    MessageView {
        padding: 1;
        margin-bottom: 1;
        border: solid $primary;
    }
    
    MessageView.user {
        background: $primary 5%;
        border-color: green;
    }
    
    MessageView.assistant {
        background: $primary 10%;
        border-color: blue;
    }
    
    MessageView.system {
        background: $primary 5%;
        border-color: gray;
    }
    
    .message-header {
        padding: 0 0 1 0;
        margin-bottom: 1;
    }
    
    .role-badge {
        padding: 0 1;
        border: solid;
        border-radius: 1;
    }
    
    .role-badge.user {
        border: green;
        color: green;
    }
    
    .role-badge.assistant {
        border: blue;
        color: blue;
    }
    
    .role-badge.system {
        border: gray;
        color: gray;
    }
    
    .timestamp {
        color: $text-muted;
        text-style: dim;
        margin-left: 1;
    }
    
    .streaming-indicator {
        color: cyan;
        text-style: italic;
    }
    """

    def __init__(self, message_data: dict[str, Any]):
        super().__init__()
        self.message_data = message_data
        self.role = message_data.get("role", "user")

    def compose(self) -> ComposeResult:
        is_streaming = self.message_data.get("is_streaming", False)
        
        role_color = {
            "user": "green",
            "assistant": "blue",
            "system": "gray",
        }.get(self.role, "white")
        
        role_emoji = {
            "user": "👤",
            "assistant": "🤖",
            "system": "⚙️",
        }.get(self.role, "❓")
        
        timestamp = self._format_timestamp()
        
        with Horizontal(classes="message-header"):
            yield Static(f"[{role_color}]{role_emoji} {self.role.upper()}[/]", classes=f"role-badge {self.role}")
            yield Static(timestamp, classes="timestamp")
        
        if is_streaming:
            yield Static("[cyan]✍️ Thinking...[/cyan]", classes="streaming-indicator")
        
        parts = self.message_data.get("parts", [])
        
        if parts:
            for part_data in parts:
                part_view = MessagePartView(part_data)
                yield part_view
        else:
            yield Static("[dim italic]No content[/dim italic]")

    def _format_timestamp(self) -> str:
        """Format timestamp for display"""
        time_data = self.message_data.get("time", {})
        if isinstance(time_data, dict):
            created = time_data.get("created") or time_data.get("updated")
        else:
            created = None
        
        if created:
            try:
                import pendulum  # type: ignore[import-not-found]
                dt = pendulum.from_timestamp(created)
                return dt.strftime("HH:mm:ss")
            except Exception:
                return str(created)[:8]
        
        return ""

    def _compose_content(self) -> ComposeResult:
        """Compose message content for streaming updates"""
        return self.compose()
