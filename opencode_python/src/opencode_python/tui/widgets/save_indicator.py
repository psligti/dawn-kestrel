"""OpenCode Python - Save Indicator Widget"""
from __future__ import annotations

from textual.widgets import Static
from textual.reactive import reactive
import asyncio


class SaveIndicator(Static):
    """Non-intrusive save status indicator"""

    CSS = """
    SaveIndicator {
        width: auto;
        height: 1;
        content-align: center middle;
        padding: 0 2;
    }

    .saving {
        color: $warning;
        text-style: bold;
    }

    .saved {
        color: $success;
        text-style: bold;
    }

    .error {
        color: $error;
        text-style: bold;
    }

    .hidden {
        visibility: hidden;
    }
    """

    status = reactive[str]("", init=False)
    visible = reactive[bool](True, init=False)

    def __init__(self) -> None:
        super().__init__()
        self._hide_task: asyncio.Task | None = None
        self.status = ""
        self.visible = True

    def watch_status(self, old_status: str, new_status: str) -> None:
        if new_status == "saving":
            self.update("[saving]Saving...[/saving]")
        elif new_status == "saved":
            self.update("[saved]Saved[/saved]")
            self._schedule_hide()
        elif new_status == "error":
            self.update("[error]Save Error[/error]")
        else:
            self.update("")

    def watch_visible(self, old_visible: bool, new_visible: bool) -> None:
        if not new_visible:
            self.add_class("hidden")
        else:
            self.remove_class("hidden")

    def set_saving(self) -> None:
        self.status = "saving"
        self.visible = True

    def set_saved(self) -> None:
        self.status = "saved"
        self.visible = True

    def set_error(self) -> None:
        self.status = "error"
        self.visible = True

    def _schedule_hide(self) -> None:
        if self._hide_task:
            self._hide_task.cancel()

        async def _hide() -> None:
            await asyncio.sleep(2)
            self.visible = False

        self._hide_task = asyncio.create_task(_hide())
