"""OpenCode Python - Context Browser Screen for TUI

Provides a context browsing screen with:
- Tabbed interface for different context views
- Files tab: File tree view with icons, expand/collapse folders
- Modified tab: List of modified files from git status
- LSP tab: Language server symbols (outline, functions, classes)
- Todo tab: Todo list items from TodoRead tool
- Diff tab: Summary of file changes
"""

from textual.screen import Screen
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Button, Tabs, Tab, TabbedContent, TabPane, Input, Tree
from textual.app import ComposeResult
from textual.reactive import reactive
from textual import on
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import logging
import asyncio
import subprocess
from pathlib import Path

from opencode_python.core.models import Session

if TYPE_CHECKING:
    from textual.widgets import Tree


logger = logging.getLogger(__name__)


class ContextBrowser(Screen):
    """Context browsing screen for OpenCode TUI"""

    CSS = """
    #context-screen {
        layout: vertical;
    }

    #context-header {
        height: 2;
        dock: top;
        padding: 0 1;
        border-bottom: solid $primary;
    }

    #context-tabs {
        height: 1;
    }

    #context-content {
        height: 1fr;
    }

    #context-footer {
        height: 2;
        dock: bottom;
        padding: 0 1;
        border-top: solid $primary;
    }

    .file-item {
        height: 1;
        padding: 0 1;
        cursor: pointer;
    }

    .file-item:hover {
        background: $accent 20%;
    }

    .folder-item {
        text-style: bold;
    }

    .modified-item {
        color: yellow;
    }

    .todo-item {
        height: 2;
        padding: 0 1;
        border-bottom: solid $text-muted 10%;
    }

    .todo-item.pending {
        border-left: thick yellow;
    }

    .todo-item.completed {
        border-left: thick green;
    }

    .lsp-symbol {
        padding: 0 1;
    }

    .lsp-function {
        color: cyan;
    }

    .lsp-class {
        color: yellow;
        text-style: bold;
    }

    .lsp-variable {
        color: green;
    }

    .file-tree {
        width: 1fr;
    }

    #search-input {
        width: 1fr;
    }

    #open-btn {
        width: 15;
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
        ("f", "focus_search", "Search"),
        ("1", "goto_tab(0)", "Files"),
        ("2", "goto_tab(1)", "Modified"),
        ("3", "goto_tab(2)", "LSP"),
        ("4", "goto_tab(3)", "Todo"),
        ("5", "goto_tab(4)", "Diff"),
    ]

    session: Optional[Session] = None
    current_tab: reactive[int] = reactive(0)
    selected_file: reactive[str] = reactive("")
    search_query: reactive[str] = reactive("")

    def __init__(self, session: Session, **kwargs):
        super().__init__(**kwargs)
        self.session = session
        self.file_tree_data: List[Dict[str, Any]] = []
        self.modified_files: List[Dict[str, Any]] = []
        self.lsp_symbols: List[Dict[str, Any]] = []
        self.todo_items: List[Dict[str, Any]] = []
        self.diff_summary: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        """Build the context browser UI"""
        with Vertical(id="context-screen"):
            yield Static("[bold]Context Browser[/bold]", id="context-header")

            yield Input(placeholder="Search...", id="search-input")

            with TabbedContent(id="context-content"):
                with TabPane("Files", id="files-pane"):
                    yield Tree("Root", id="file-tree")

                with TabPane("Modified", id="modified-pane"):
                    yield ScrollableContainer(id="modified-list")

                with TabPane("LSP", id="lsp-pane"):
                    yield ScrollableContainer(id="lsp-list")

                with TabPane("Todo", id="todo-pane"):
                    yield ScrollableContainer(id="todo-list")

                with TabPane("Diff", id="diff-pane"):
                    yield ScrollableContainer(id="diff-list")

            with Horizontal(id="context-footer"):
                yield Static("", id="status-text")
                yield Button("Open", variant="primary", id="open-btn")

    def on_mount(self) -> None:
        """Called when screen is mounted"""
        logger.info(f"ContextBrowser mounted for session {self.session.id}")
        self.app.title = "Context Browser"
        asyncio.create_task(self._load_context_data())

    async def _load_context_data(self) -> None:
        """Load context data for all tabs"""
        try:
            await asyncio.gather(
                self._load_file_tree(),
                self._load_modified_files(),
                self._load_lsp_symbols(),
                self._load_todos(),
                self._load_diff_summary(),
            )
            logger.info("Context data loaded successfully")

        except Exception as e:
            logger.error(f"Error loading context data: {e}")
            self.notify(f"[red]Error loading context: {e}[/red]")

    async def _load_file_tree(self) -> None:
        """Load file tree structure"""
        try:
            work_dir = Path(self.session.directory) if self.session.directory else Path.cwd()

            tree_widget = self.query_one("#file-tree", Tree)
            tree_widget.root.expand()

            def add_path_to_tree(path: Path, parent_node: TreeNode):
                """Recursively add path to tree"""
                for child in sorted(path.iterdir()):
                    if child.name.startswith("."):
                        continue

                    node_label = self._get_file_icon(child) + " " + child.name

                    if child.is_dir():
                        dir_node = parent_node.add(node_label, data={"path": str(child), "type": "dir"})
                        add_path_to_tree(child, dir_node)
                    else:
                        parent_node.add(node_label, data={"path": str(child), "type": "file"})

            add_path_to_tree(work_dir, tree_widget.root)

        except Exception as e:
            logger.error(f"Error loading file tree: {e}")

    def _get_file_icon(self, path: Path) -> str:
        """Get emoji icon for file type"""
        if path.is_dir():
            return "📁"

        suffix = path.suffix.lower()
        icon_map = {
            ".py": "🐍",
            ".js": "📜",
            ".ts": "📘",
            ".tsx": "⚛️",
            ".jsx": "⚛️",
            ".md": "📝",
            ".txt": "📄",
            ".json": "📋",
            ".yaml": "📋",
            ".yml": "📋",
            ".toml": "📋",
            ".css": "🎨",
            ".html": "🌐",
            ".sh": "💻",
            ".bash": "💻",
            ".zsh": "💻",
            ".rs": "🦀",
            ".go": "🐹",
            ".java": "☕",
            ".cpp": "⚙️",
            ".c": "⚙️",
            ".h": "⚙️",
            ".hpp": "⚙️",
        }

        return icon_map.get(suffix, "📄")

    async def _load_modified_files(self) -> None:
        """Load modified files from git status"""
        try:
            work_dir = Path(self.session.directory) if self.session.directory else Path.cwd()

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            modified_list = self.query_one("#modified-list", ScrollableContainer)
            modified_list.remove_children()

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                status_code = line[:2]
                file_path = line[3:].strip()

                status_map = {
                    "M": "Modified",
                    "A": "Added",
                    "D": "Deleted",
                    "R": "Renamed",
                    "C": "Copied",
                    "??": "Untracked",
                }

                status = "Unknown"
                if status_code[0] in status_map:
                    status = status_map[status_code[0]]
                elif status_code[1] in status_map:
                    status = status_map[status_code[1]]

                file_widget = Static(
                    f"[{status_color(status)}]{status}[/]: {file_path}",
                    classes=["file-item", "modified-item"],
                )
                file_widget.data = {"path": file_path, "status": status}
                await modified_list.mount(file_widget)

                self.modified_files.append({"path": file_path, "status": status})

        except subprocess.TimeoutExpired:
            logger.error("Git status timeout")
        except Exception as e:
            logger.error(f"Error loading modified files: {e}")

    async def _load_lsp_symbols(self) -> None:
        """Load LSP symbols (placeholder for now)"""
        try:
            lsp_list = self.query_one("#lsp-list", ScrollableContainer)
            lsp_list.remove_children()

            placeholder = Static(
                "[dim]LSP symbols not yet implemented.[/dim]\n"
                "[dim]This tab will show functions, classes, and variables.[/dim]"
            )
            await lsp_list.mount(placeholder)

        except Exception as e:
            logger.error(f"Error loading LSP symbols: {e}")

    async def _load_todos(self) -> None:
        """Load todo list items"""
        try:
            todo_list = self.query_one("#todo-list", ScrollableContainer)
            todo_list.remove_children()

            placeholder = Static(
                "[dim]Todo list not yet connected to TodoRead tool.[/dim]\n"
                "[dim]This tab will show active and completed todos.[/dim]"
            )
            await todo_list.mount(placeholder)

        except Exception as e:
            logger.error(f"Error loading todos: {e}")

    async def _load_diff_summary(self) -> None:
        """Load diff summary for changed files"""
        try:
            work_dir = Path(self.session.directory) if self.session.directory else Path.cwd()

            diff_list = self.query_one("#diff-list", ScrollableContainer)
            diff_list.remove_children()

            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.stdout.strip():
                for line in result.stdout.splitlines():
                    diff_widget = Static(line, classes=["file-item"])
                    await diff_list.mount(diff_widget)
            else:
                placeholder = Static("[dim]No changes detected.[/dim]")
                await diff_list.mount(placeholder)

        except subprocess.TimeoutExpired:
            logger.error("Git diff stat timeout")
        except Exception as e:
            logger.error(f"Error loading diff summary: {e}")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection"""
        node_data = event.node.data
        if node_data and node_data.get("type") == "file":
            self.selected_file = node_data.get("path", "")
            status_text = self.query_one("#status-text", Static)
            status_text.update(f"Selected: {self.selected_file}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input"""
        self.search_query = event.value
        asyncio.create_task(self._apply_search())

    async def _apply_search(self) -> None:
        """Apply search filter to current tab"""
        tab_index = self.current_tab

        if tab_index == 0:
            self._filter_file_tree()
        elif tab_index == 1:
            await self._filter_modified_files()
        elif tab_index == 3:
            await self._filter_todos()

    def _filter_file_tree(self) -> None:
        """Filter file tree based on search query"""
        tree_widget = self.query_one("#file-tree", Tree)

        def should_show_node(node: TreeNode) -> bool:
            """Check if node should be shown"""
            node_label = node.label.lower()
            if self.search_query.lower() in node_label:
                return True

            node_data = node.data
            if node_data:
                path = node_data.get("path", "").lower()
                if self.search_query.lower() in path:
                    return True

            return False

        for node in tree_widget.root.children:
            node.set_visible(should_show_node(node))

    async def _filter_modified_files(self) -> None:
        """Filter modified files based on search query"""
        modified_list = self.query_one("#modified-list", ScrollableContainer)

        for child in modified_list.children:
            if hasattr(child, "data"):
                file_path = child.data.get("path", "").lower()
                child.set_visible(self.search_query.lower() in file_path)

    async def _filter_todos(self) -> None:
        """Filter todos based on search query"""
        todo_list = self.query_one("#todo-list", ScrollableContainer)

        for child in todo_list.children:
            text = str(child.renderable).lower() if hasattr(child, "renderable") else ""
            child.set_visible(self.search_query.lower() in text)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab activation"""
        self.current_tab = event.tab_index
        status_text = self.query_one("#status-text", Static)
        tab_names = ["Files", "Modified", "LSP", "Todo", "Diff"]
        status_text.update(f"View: {tab_names[self.current_tab]}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "open-btn":
            asyncio.create_task(self._open_selected())

    async def _open_selected(self) -> None:
        """Open selected file"""
        if self.selected_file:
            self.notify(f"[cyan]Opening: {self.selected_file}[/cyan]")
            try:
                import subprocess
                import os
                editor = os.environ.get("EDITOR", "vi")
                subprocess.run([editor, self.selected_file], timeout=60)
            except Exception as e:
                logger.error(f"Error opening file: {e}")
                self.notify(f"[red]Error opening file: {e}[/red]")
        else:
            self.notify("[yellow]No file selected[/yellow]")

    def action_focus_search(self) -> None:
        """Focus on search input"""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

    def action_goto_tab(self, tab_index: int) -> None:
        """Go to specific tab"""
        tabbed_content = self.query_one(TabbedContent)
        if tab_index < len(tabbed_content.panes):
            tabbed_content.active = tab_index


def status_color(status: str) -> str:
    """Get color for git status"""
    color_map = {
        "Modified": "yellow",
        "Added": "green",
        "Deleted": "red",
        "Renamed": "cyan",
        "Copied": "cyan",
        "Untracked": "gray",
    }
    return color_map.get(status, "white")
