"""Skills panel screen - TUI interface for managing skills"""
from __future__ import annotations

from typing import Optional
import logging

from textual.screen import Screen
from textual.containers import Vertical, Horizontal
from textual.widgets import DataTable, Button, Label, Footer
from textual.app import ComposeResult
from textual.binding import Binding

from opencode_python.skills.registry import registry


logger = logging.getLogger(__name__)


class SkillsPanelScreen(Screen):
    """Skills panel for browsing and managing skills"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("t", "toggle_skill", "Toggle"),
        ("r", "refresh_skills", "Refresh"),
    ]

    def __init__(self, session_id: str, **kwargs):
        """Initialize SkillsPanelScreen

        Args:
            session_id: ID of the session to manage skills for
        """
        super().__init__(**kwargs)
        self.session_id = session_id

    def compose(self) -> ComposeResult:
        """Build the skills panel screen UI"""
        with Vertical(id="skills-panel-screen"):
            yield Label(f"Skills for Session: {self.session_id[:8]}...", id="header")
            yield DataTable(id="skills-table")
            yield Label("[dim]Press T to toggle, R to refresh, ESC to back[/dim]", id="footer")

    def on_mount(self) -> None:
        """Called when screen is mounted - populate DataTable"""
        self._populate_skills_table()

    def _populate_skills_table(self) -> None:
        """Populate skills table with all registered skills"""
        data_table = self.query_one(DataTable)

        # Clear existing data
        data_table.clear()

        # Add columns
        data_table.add_column("ID", width=15)
        data_table.add_column("Name", width=20)
        data_table.add_column("Category", width=15)
        data_table.add_column("Enabled", width=10)
        data_table.add_column("Blocked", width=10)

        # Get all skills and their states
        skills = registry.list_skills()
        for skill in skills:
            state = registry.get_skill_state(self.session_id, skill.id)

            is_enabled = state.is_enabled if state else skill.is_enabled_by_default
            is_blocked = state.is_blocked if state else False
            blocked_reason = state.block_reason if state and state.is_blocked else ""

            status = "[green]Yes[/green]" if is_enabled else "[red]No[/red]"
            blocked = "[red]Yes[/red]" if is_blocked else "[dim]No[/dim]"

            data_table.add_row(
                skill.id,
                skill.name,
                skill.category or "[dim]-[/dim]",
                status,
                blocked,
                key=skill.id,
            )

        # Set cursor type to row
        data_table.cursor_type = "row"

    def action_toggle_skill(self) -> None:
        """Toggle the currently selected skill"""
        data_table = self.query_one(DataTable)
        cursor_row = data_table.cursor_row

        if cursor_row < 0:
            return

        skill_id = data_table.get_row_at(cursor_row)[0]
        state = registry.get_skill_state(self.session_id, skill_id)

        if state:
            if state.is_blocked:
                self.notify(f"Cannot toggle blocked skill '{skill_id}'", severity="error")
                return

            if state.is_enabled:
                success = registry.disable_skill(self.session_id, skill_id)
            else:
                success = registry.enable_skill(self.session_id, skill_id)
        else:
            skill = registry.get_skill(skill_id)
            if skill:
                success = registry.enable_skill(self.session_id, skill_id)

        if success:
            self._populate_skills_table()
            self.notify(f"Toggled skill '{skill_id}'")
        else:
            self.notify(f"Failed to toggle skill '{skill_id}'", severity="error")

    def action_refresh_skills(self) -> None:
        """Refresh the skills table"""
        self._populate_skills_table()
        self.notify("Skills refreshed")

    def on_data_table_row_selected(self, event) -> None:
        """Handle row selection in skills table"""
        skill_id = event.row_key
        skill = registry.get_skill(skill_id)
        state = registry.get_skill_state(self.session_id, skill_id)

        if skill:
            info_text = f"[bold]{skill.name}[/bold]\n\n"
            info_text += f"{skill.description}\n\n"
            info_text += f"Category: {skill.category or 'N/A'}\n"
            info_text += f"Default enabled: {'Yes' if skill.is_enabled_by_default else 'No'}\n"

            if state and state.is_blocked:
                info_text += f"\n[red]BLOCKED:[/red] {state.block_reason}"
            elif state and not state.is_enabled:
                info_text += "\n[dim]Currently disabled[/dim]"
            elif state:
                info_text += "\n[green]Currently enabled[/green]"
                if state.use_count > 0:
                    info_text += f" (used {state.use_count} time{'s' if state.use_count != 1 else ''})"

            self.notify(info_text, title=skill.name)
