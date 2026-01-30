"""OpenCode Python - Agent Selection Screen for TUI

Provides a screen for selecting agent profiles:
- Displays available agent profiles in DataTable
- Shows description and capabilities for selected profile
- Validates prerequisites and shows warnings
"""

from typing import List, Optional
import logging

from textual.screen import Screen
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static, Button
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer
from textual import on
from textual.message import Message

from opencode_python.agents import AgentProfile, check_prerequisites


logger = logging.getLogger(__name__)


class ProfileSelected(Message):
    """Event emitted when a profile is selected"""

    def __init__(self, profile: AgentProfile) -> None:
        self.profile = profile
        super().__init__()


class AgentSelectionScreen(Screen):
    """Agent profile selection screen"""

    BINDINGS = [
        ("escape", "pop_screen", "Back"),
        ("ctrl+c", "quit", "Quit"),
        ("enter", "confirm_selection", "Select"),
    ]

    def __init__(
        self,
        profiles: List[AgentProfile],
        available_skills: Optional[List[str]] = None,
        available_tools: Optional[List[str]] = None,
        available_providers: Optional[List[str]] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.profiles = profiles
        self.available_skills = available_skills or []
        self.available_tools = available_tools or []
        self.available_providers = available_providers or []
        self.selected_profile: Optional[AgentProfile] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="agent-selection-screen"):
            with Horizontal(id="agent-selection-content"):
                with Vertical(id="agent-list-panel"):
                    yield Static("Select Agent Profile", id="agent-list-title")
                    yield DataTable(id="agent-table")

                with Vertical(id="agent-details-panel"):
                    yield Static("Profile Details", id="agent-details-title")
                    yield Static("Select a profile to view details", id="agent-details-description")
                    yield Static("", id="agent-details-capabilities")
                    yield Static("", id="agent-details-prerequisites")

            with Horizontal(id="agent-selection-actions"):
                yield Button("Cancel", id="btn-cancel", variant="default")
                yield Button("Select", id="btn-select", variant="primary", disabled=True)

    def on_mount(self) -> None:
        data_table = self.query_one(DataTable)

        data_table.add_column("Name", width=20)
        data_table.add_column("Category", width=15)
        data_table.add_column("Description", width=40)

        for profile in self.profiles:
            prereq_check = check_prerequisites(
                profile,
                self.available_skills,
                self.available_tools,
                self.available_providers
            )

            row_key = profile.id

            data_table.add_row(
                f"[bold]{profile.name}[/bold]",
                profile.category,
                profile.description[:50] + "..." if len(profile.description) > 50 else profile.description,
                key=row_key,
            )

            if not prereq_check["satisfied"]:
                missing_count = len(prereq_check["missing"])
                data_table.add_row(
                    f"[red]⚠️ {profile.name}[/red]",
                    profile.category,
                    f"[red]{missing_count} missing prerequisites[/red]",
                    key=row_key,
                )

        data_table.cursor_type = "row"

    def on_data_table_row_selected(self, event) -> None:
        data_table = self.query_one(DataTable)

        try:
            cursor_coordinate = data_table.cursor_coordinate
            row_key, _ = data_table.coordinate_to_cell_key(cursor_coordinate)

            if row_key is not None:
                profile_id = str(row_key)
                profile = self._find_profile_by_id(profile_id)

                if profile:
                    self._update_profile_details(profile)
                    self.selected_profile = profile
                    self.query_one(Button, "#btn-select").disabled = False
        except Exception as e:
            logger.error(f"Error selecting profile: {e}")

    def _update_profile_details(self, profile: AgentProfile) -> None:
        description_widget = self.query_one(Static, "#agent-details-description")
        capabilities_widget = self.query_one(Static, "#agent-details-capabilities")
        prereq_widget = self.query_one(Static, "#agent-details-prerequisites")

        description_widget.update(
            f"[bold]{profile.name}[/bold]\n\n{profile.description}"
        )

        capabilities_text = "[bold]Capabilities:[/bold]\n" + "\n".join(
            f"  • {cap}" for cap in profile.capabilities
        )
        capabilities_widget.update(capabilities_text)

        prereq_check = check_prerequisites(
            profile,
            self.available_skills,
            self.available_tools,
            self.available_providers
        )

        if prereq_check["satisfied"]:
            prereq_text = "[green]✓ All prerequisites satisfied[/green]"
        else:
            missing_items = prereq_check["missing"]
            prereq_text = "[red]⚠️ Missing prerequisites:[/red]\n"
            prereq_text += "\n".join(
                f"  • {item.type}: {item.name}" for item in missing_items
            )
        prereq_widget.update(prereq_text)

    def action_confirm_selection(self) -> None:
        if self.selected_profile:
            prereq_check = check_prerequisites(
                self.selected_profile,
                self.available_skills,
                self.available_tools,
                self.available_providers
            )

            if not prereq_check["satisfied"]:
                self.app.push_screen(
                    self._create_prerequisite_warning_modal()
                )
            else:
                self.post_message(ProfileSelected(self.selected_profile))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.app.pop_screen()
        elif event.button.id == "btn-select":
            self.action_confirm_selection()
        elif event.button.id == "btn-prereq-continue":
            self.post_message(ProfileSelected(self.selected_profile))
            self.app.pop_screen()

    def _find_profile_by_id(self, profile_id: str) -> Optional[AgentProfile]:
        for profile in self.profiles:
            if profile.id == profile_id:
                return profile
        return None

    def _create_prerequisite_warning_modal(self) -> Screen:
        prereq_check = check_prerequisites(
            self.selected_profile,
            self.available_skills,
            self.available_tools,
            self.available_providers
        )

        missing_text = "\n".join(
            f"  • {item.type}: {item.name}" for item in prereq_check["missing"]
        )

        modal_content = f"""[bold]Missing Prerequisites[/bold]

The selected agent profile requires the following:

{missing_text}

You can:
1. Enable the missing skills/tools and continue
2. Choose a different agent profile

Continue anyway?
"""

        from textual.widgets import ModalScreen

        modal = ModalScreen(modal_content)
        modal._buttons = [
            Button("Choose Different Agent", id="btn-prereq-cancel", variant="default"),
            Button("Continue Anyway", id="btn-prereq-continue", variant="primary"),
        ]

        return modal
