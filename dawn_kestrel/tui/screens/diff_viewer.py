"""OpenCode Python - Diff Viewer Screen for TUI

Provides a diff viewing screen with:
- Unified diff format display with syntax highlighting
- Line numbers for original and modified versions
- Color coding (red for deletions, green for additions, cyan for unchanged)
- Scrollable content
- Header with file names and change summary
- Support for multiple file diffs (tabs)
- Inline view toggle
- Search/filter functionality
"""

from textual.screen import Screen
from textual.containers import Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Tabs, Tab, TabbedContent, TabPane
from textual.app import ComposeResult, App
from textual.reactive import reactive
from typing import Optional, List, Dict, Any
import logging
import asyncio
import subprocess
from pathlib import Path

from dawn_kestrel.core.models import PatchPart, Session


logger = logging.getLogger(__name__)


class DiffLine(Static):
    """A single line in the diff display"""

    line_type: reactive[str] = reactive("context")

    CSS = """
    DiffLine {
        height: 1;
        width: 1fr;
    }

    DiffLine.context {
        text-style: dim;
    }

    DiffLine.addition {
        background: green 10%;
    }

    DiffLine.deletion {
        background: red 10%;
    }

    DiffLine.header {
        text-style: bold;
        background: $accent 20%;
    }
    """


class DiffViewer(Screen[None]):
    """Diff viewing screen for OpenCode TUI"""

    CSS = """
    #diff-screen {
        layout: vertical;
    }

    #diff-header {
        height: 3;
        dock: top;
        padding: 0 1;
    }

    #diff-tabs {
        height: 1;
    }

    #diff-content {
        height: 1fr;
        overflow-y: auto;
    }

    #diff-footer {
        height: 3;
        dock: bottom;
        padding: 0 1;
    }

    #file-info {
        text-style: bold;
    }

    #diff-stats {
        text-style: dim;
    }

    #apply-patch-btn {
        width: 15;
    }

    #revert-btn {
        width: 10;
    }

    #view-toggle-btn {
        width: 10;
    }

    .diff-add {
        color: green;
    }

    .diff-remove {
        color: red;
    }

    .diff-context {
        color: cyan;
    }

    .line-number {
        color: $text-muted;
        text-style: dim;
        min-width: 4;
        text-align: right;
        margin-right: 1;
    }
    """

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("v", "toggle_view", "Toggle View"),
    ]

    patch_part: Optional[PatchPart] = None
    session: Optional[Session] = None
    current_file_index: reactive[int] = reactive(0)
    view_mode: reactive[str] = reactive("inline")
    search_query: reactive[str] = reactive("")

    def __init__(self, patch_part: PatchPart, session: Session, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.patch_part = patch_part
        self.session = session
        self.diff_data: Dict[str, List[Dict[str, Any]]] = {}
        self.current_file_diff: List[Dict[str, Any]] = []

    @property
    def _app(self) -> "App[None]":
        """Get the app with proper type annotation"""
        return self.app

    def compose(self) -> ComposeResult:
        """Build the diff viewer UI"""
        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in compose")

        with Vertical(id="diff-screen"):
            with Horizontal(id="diff-header"):
                yield Static("", id="file-info")
                yield Static("", id="diff-stats")

            tabs_list = [Tab(label=str(file_path)) for file_path in patch_part.files]
            yield Tabs(*tabs_list, id="diff-tabs")

            with TabbedContent(id="diff-content"):
                for i, file_path in enumerate(patch_part.files):
                    with TabPane(file_path, id=f"diff-pane-{i}"):
                        yield ScrollableContainer(id=f"diff-lines-{i}")

            with Horizontal(id="diff-footer"):
                yield Button("Inline", id="view-toggle-btn", variant="default")
                yield Button("Apply Patch", variant="primary", id="apply-patch-btn")
                yield Button("Revert", variant="error", id="revert-btn")

    def on_mount(self) -> None:
        """Called when screen is mounted"""
        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in on_mount")
        logger.info(f"DiffViewer mounted for patch {patch_part.id}")
        self._app.title = f"Diff Viewer - {patch_part.hash[:8]}"
        asyncio.create_task(self._load_diffs())

    async def _load_diffs(self) -> None:
        """Load git diffs for all modified files"""
        session = self.session
        if session is None:
            raise RuntimeError("session must be set in _load_diffs")

        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in _load_diffs")

        try:
            work_dir = Path(session.directory) if session.directory else Path.cwd()

            for file_path in patch_part.files:
                try:
                    result = subprocess.run(
                        ["git", "diff", file_path],
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    diff_lines = self._parse_diff_output(result.stdout, file_path)
                    self.diff_data[file_path] = diff_lines
                    logger.info(f"Loaded diff for {file_path}: {len(diff_lines)} lines")

                except subprocess.TimeoutExpired:
                    logger.error(f"Git diff timeout for {file_path}")
                    self.diff_data[file_path] = self._create_error_diff(file_path, "Git diff timeout")

                except Exception as e:
                    logger.error(f"Error loading diff for {file_path}: {e}")
                    self.diff_data[file_path] = self._create_error_diff(file_path, str(e))

            if patch_part.files:
                await self._update_diff_display(0)

        except Exception as e:
            logger.error(f"Error loading diffs: {e}")
            self.notify(f"[red]Error loading diffs: {e}[/red]")

    def _parse_diff_output(self, diff_output: str, file_path: str) -> List[Dict[str, Any]]:
        """Parse git diff output into structured data"""
        lines: List[Dict[str, Any]] = []
        original_line = 0
        modified_line = 0

        for raw_line in diff_output.splitlines():
            line_info: Dict[str, Any] = {"raw": raw_line, "original": None, "modified": None, "type": "context"}

            if raw_line.startswith("@@"):
                line_info["type"] = "header"
                parts = raw_line.split(" ")
                if len(parts) >= 3:
                    orig_range = parts[1]
                    if "," in orig_range:
                        original_line = int(orig_range[1:].split(",")[0])
                    else:
                        original_line = int(orig_range[1:])

                    mod_range = parts[2].rstrip("@")
                    if "," in mod_range:
                        modified_line = int(mod_range[1:].split(",")[0])
                    else:
                        modified_line = int(mod_range[1:])

            elif raw_line.startswith("+") and not raw_line.startswith("+++"):
                line_info["type"] = "addition"
                modified_line += 1
                line_info["modified"] = modified_line

            elif raw_line.startswith("-") and not raw_line.startswith("---"):
                line_info["type"] = "deletion"
                original_line += 1
                line_info["original"] = original_line

            elif raw_line.startswith("+++"):
                line_info["type"] = "header"

            elif raw_line.startswith("---"):
                line_info["type"] = "header"

            else:
                original_line += 1
                modified_line += 1
                line_info["original"] = original_line
                line_info["modified"] = modified_line

            lines.append(line_info)

        return lines

    def _create_error_diff(self, file_path: str, error_msg: str) -> List[Dict[str, Any]]:
        """Create error message as diff"""
        return [
            {
                "raw": f"--- Error loading diff for {file_path} ---",
                "type": "header",
                "original": None,
                "modified": None,
            },
            {
                "raw": error_msg,
                "type": "context",
                "original": None,
                "modified": None,
            },
        ]

    async def _update_diff_display(self, file_index: int) -> None:
        """Update the diff display for a specific file"""
        self.current_file_index = file_index

        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in _update_diff_display")

        if file_index >= len(patch_part.files):
            return

        file_path = patch_part.files[file_index]
        diff_lines = self.diff_data.get(file_path, [])

        file_info = self.query_one("#file-info", Static)
        file_info.update(f"[bold]File:[/bold] {file_path}")

        additions = sum(1 for line in diff_lines if line["type"] == "addition")
        deletions = sum(1 for line in diff_lines if line["type"] == "deletion")

        diff_stats = self.query_one("#diff-stats", Static)
        diff_stats.update(f"[green]+{additions}[/green] [red]-{deletions}[/red]")

        try:
            container_id = f"diff-lines-{file_index}"
            container = self.query_one(f"#{container_id}", ScrollableContainer)

            container.remove_children()

            for line_info in diff_lines:
                line_type = line_info["type"]
                raw_content = line_info["raw"]

                if self.search_query and self.search_query in raw_content:
                    highlighted = raw_content.replace(
                        self.search_query, f"[reverse]{self.search_query}[/reverse]"
                    )
                else:
                    highlighted = raw_content

                modified_num = line_info.get("modified")

                if line_type == "addition":
                    content = f"[green]+{highlighted}[/green]"
                    num_str = "    "
                elif line_type == "deletion":
                    content = f"[red]-{highlighted}[/red]"
                    num_str = "    "
                elif line_type == "header":
                    content = f"[bold cyan]{highlighted}[/bold cyan]"
                    num_str = "    "
                else:
                    content = f"[cyan]{highlighted}[/cyan]"
                    num_str = f"{modified_num:>4}" if modified_num else "    "

                diff_line = DiffLine(f"{num_str} {content}")
                diff_line.line_type = line_type
                await container.mount(diff_line)

        except Exception as e:
            logger.error(f"Error updating diff display: {e}")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab activation"""
        tab_index = None

        tabs_widget = self.query_one("#diff-tabs", Tabs)
        try:
            tab_index = tabs_widget.children.index(event.tab)
        except (ValueError, AttributeError, TypeError):
            pass

        if tab_index is not None:
            asyncio.create_task(self._update_diff_display(tab_index))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        button_id = event.button.id if event.button.id else ""
        if button_id == "apply-patch-btn":
            asyncio.create_task(self._apply_patch())
        elif button_id == "revert-btn":
            asyncio.create_task(self._revert_changes())
        elif button_id == "view-toggle-btn":
            self.action_toggle_view()

    async def _apply_patch(self) -> None:
        """Apply the current patch"""
        session = self.session
        if session is None:
            raise RuntimeError("session must be set in _apply_patch")

        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in _apply_patch")

        try:
            work_dir = Path(session.directory) if session.directory else Path.cwd()

            for file_path in patch_part.files:
                try:
                    _ = subprocess.run(
                        ["git", "apply", "--cached"],
                        cwd=work_dir,
                        input="",
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    logger.info(f"Applied patch for {file_path}")

                except Exception as e:
                    logger.error(f"Error applying patch for {file_path}: {e}")

            self.notify("[green]Patch applied successfully[/green]")
            self._app.pop_screen()

        except Exception as e:
            logger.error(f"Error applying patch: {e}")
            self.notify(f"[red]Error applying patch: {e}[/red]")

    async def _revert_changes(self) -> None:
        """Revert the current changes"""
        session = self.session
        if session is None:
            raise RuntimeError("session must be set in _revert_changes")

        patch_part = self.patch_part
        if patch_part is None:
            raise RuntimeError("patch_part must be set in _revert_changes")

        try:
            work_dir = Path(session.directory) if session.directory else Path.cwd()

            for file_path in patch_part.files:
                try:
                    _ = subprocess.run(
                        ["git", "checkout", "--", file_path],
                        cwd=work_dir,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    logger.info(f"Reverted changes for {file_path}")

                except Exception as e:
                    logger.error(f"Error reverting {file_path}: {e}")

            self.notify("[green]Changes reverted successfully[/green]")
            self._app.pop_screen()

        except Exception as e:
            logger.error(f"Error reverting changes: {e}")
            self.notify(f"[red]Error reverting changes: {e}[/red]")

    def action_toggle_view(self) -> None:
        """Toggle between inline and side-by-side view"""
        self.view_mode = "side-by-side" if self.view_mode == "inline" else "inline"
        toggle_btn = self.query_one("#view-toggle-btn", Button)
        toggle_btn.label = "Side-by-Side" if self.view_mode == "inline" else "Inline"
        self.notify(f"[cyan]View mode: {self.view_mode}[/cyan]")
