## Textual implementation plan

### Target widget tree (vertical stack + overlays)

- `App`
    - `Screen(MainScreen)`
        - `TopBar` (fixed height)
        - `ConversationTimeline` (fills)
        - `ComposerBar` (auto-grow up to N lines)
        - `BottomStatusBar` (fixed height)
        - `CommandPaletteOverlay` (hidden by default)
        - `RightDrawerOverlay` (hidden by default)

Key point: **no permanent split panes**. The drawer/palette **overlay** the timeline.

---

## 1) CSS tokens for rounded corners + contrast-driven theming

Textual supports CSS variables and `border-radius`. Make your themes swap **variables only**.

### Required CSS variables
- Surfaces: `--surface-base`, `--surface-panel`, `--surface-raised`
- Text: `--text-primary`, `--text-secondary`, `--text-tertiary`
- Borders: `--border-normal`, `--border-focus`
- Accents: `--accent-primary`, `--accent-secondary`
- States: `--success`, `--warning`, `--error`, `--info`
- Radii: `--r-panel`, `--r-control`, `--r-pill`
- Spacing: `--pad-sm`, `--pad-md`

### Base CSS (shape language + legend headers)
~~~css
/* app.tcss */
Screen {
  background: var(--surface-base);
  color: var(--text-primary);
}

/* Rounded corners everywhere */
.panel {
  background: var(--surface-panel);
  border: round var(--border-normal);
  border-radius: var(--r-panel);
  padding: var(--pad-md);
}

.control {
  border: round var(--border-normal);
  border-radius: var(--r-control);
}

.chip {
  background: var(--surface-raised);
  border: round var(--border-normal);
  border-radius: var(--r-pill);
  padding: 0 1;
  color: var(--text-secondary);
}

/* Focus should pop (2 cues: color + border) */
*:focus {
  border: round var(--border-focus);
}

/* Legend header that sits "in the border" look */
.legend-header {
  height: 1;
  margin: 0 0 1 0;
  color: var(--text-secondary);
}
.legend-header .title {
  color: var(--text-primary);
  text-style: bold;
}
~~~

### Theme switching rule
Each theme = a `dict` of variable values. Switching theme = `self.set_class(...)` or inject CSS variables by loading theme `.tcss` or updating a `ThemeManager` that calls `app.set_css_variables(theme)` (you can implement this helper).

**Acceptance:** no hard-coded colors in widget CSS (only vars).

---

## 2) Component mapping to Textual widgets

### Top bar
**Goal:** session + agent + model/provider/account + run/stop + tiny progress.

Textual widgets:
- `Horizontal` container
- `Static` for session label
- custom `Chip` widgets (Static with `.chip` class)
- `Button` run/stop

Checklist:
- [ ] Fixed height (1–3 rows)
- [ ] All controls rounded (`border-radius`)
- [ ] Status chips use semantic colors (success/warn/error)

---

### Conversation timeline (primary workspace)
Use a **scrollable container** that renders message “cards”.

Textual widgets:
- `VerticalScroll`
- inside: `MessageCard` widgets (custom `Widget` or `Container`)
    - header row (`Horizontal`)
    - body (`Markdown` or `Static` with rich text)
    - optional footer row (actions visible on focus)

Message types:
- `UserMessageCard`
- `AgentMessageCard`
- `ToolRunCard` (summary row + `Collapsible` details)
- `ThinkingCard` (collapsed by default)
- `QuestionCard` (needs-response highlight)

Textual primitives to use:
- `Collapsible` for thinking/tool details
- `Markdown` (Textual has Markdown rendering) for content
- `OptionList` is good for nav lists, but for timeline stick to custom cards inside `VerticalScroll`

Clutter reduction rules implemented in timeline:
- [ ] Thinking collapsed by default
- [ ] Tool details collapsed by default (expand on error optional)
- [ ] Metadata hidden behind expand (timings/tokens)

---

### Composer (reactive input, auto-grow)
Textual widget:
- `TextArea` (or `Input` for single-line; you want multi-line → `TextArea`)
- Wrap in a `Container` with send button and optional chips.

Auto-grow approach:
- On `TextArea` change event, compute line count and set container height to `min(max_lines, line_count + padding)`.
- Keep timeline height flexible so composer growth doesn’t break layout.

Checklist:
- [ ] Auto-grow up to N lines
- [ ] Draft persists when palette/drawer opens (don’t replace widget)
- [ ] Submit keybind(s): Enter/Ctrl+Enter configurable

---

### Bottom status bar
Textual widgets:
- `Horizontal`
- `Static` left: session/workspace
- `Static` middle: last warning/error summary
- `Static` right: key hints

Checklist:
- [ ] Fixed height
- [ ] Minimal text (tertiary)
- [ ] Always visible

---

## 3) Command palette overlay (Ctrl+K)
This should be an overlay modal that steals focus.

Textual widgets:
- `ModalScreen` (recommended)
    - `Container.panel` (raised surface)
    - `Input.control` (query)
    - `OptionList` (results)
    - optional preview pane later

Data model:
- `CommandItem(id, title, kind, handler, keywords)`
- kinds: `action`, `entity:model`, `entity:session`, `entity:agent`, `nav:message`

Checklist:
- [ ] Fuzzy search (rapid)
- [ ] Executes selection and closes
- [ ] Restores prior focus

---

## 4) Right drawer overlay with vertical tabs (Ctrl+D)
Use a slide-in overlay. In Textual:
- either a `Container` with `dock: right;` and toggle `display: none/block`
- or a `ModalScreen` anchored right (if you want to block interactions behind it)

Structure:
- Drawer container (rounded panel)
    - Left edge: vertical tabs (`OptionList` or custom buttons stacked)
    - Right side: active tab content

Tabs:
- Todos (list)
- Tools (list)
- Agents (list + status chips)
- Sessions (list)
- Navigator (conversation index)

Navigator behavior:
- Selecting a row calls `timeline.scroll_to_widget(message_card)` and highlights it.

Checklist:
- [ ] Drawer overlays 30–45% width
- [ ] Vertical tab selector always visible
- [ ] Selecting an item jumps timeline (doesn’t switch main view)

---

## 5) Focus model + key bindings (Textual-friendly)
Define global bindings in `App.BINDINGS`:

Recommended:
- `ctrl+k` → open palette
- `ctrl+d` → toggle drawer
- `esc` → close palette/drawer (if open) else blur/cancel
- `ctrl+j / ctrl+k` → timeline navigation (optional)
- `ctrl+enter` → send message (safe default)

Focus order:
1. Composer TextArea (default focus)
2. Timeline (when user navigates)
3. Drawer lists (when open)
4. Palette input/list (when open)

Checklist:
- [ ] Opening palette stores previous focus and restores on close
- [ ] Drawer open does not destroy composer draft
- [ ] Focus ring/border uses `--border-focus`

---

## 6) Textual component checklist (concrete)

### Core widgets
- [ ] `TopBar(Widget)`
- [ ] `ConversationTimeline(VerticalScroll)`
- [ ] `MessageCard(Widget)` + variants
- [ ] `ComposerBar(Widget)` with `TextArea`
- [ ] `BottomStatusBar(Widget)`
- [ ] `CommandPalette(ModalScreen)` with `Input` + `OptionList`
- [ ] `RightDrawer(Widget)` with vertical tabs + content pane

### State + data contracts
- [ ] `SessionState` (active session id/name, provider/account/model, agent)
- [ ] `TimelineItem` union: user/agent/tool/thinking/question/system
- [ ] `ToolRunResult` with severity + summary + expandable details
- [ ] `DrawerTabState` (active tab + selected item)
- [ ] `Theme` (token map)

### Styling constraints
- [ ] Every widget has rounded corners via CSS vars
- [ ] No square buttons/inputs/tabs anywhere
- [ ] Selection/focus uses at least **two cues**
- [ ] Legend headers implemented as a consistent pattern across panels

---

## 7) Starter skeleton (Textual code)

~~~python
# app.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Button, TextArea, Input, OptionList, Collapsible, Markdown


@dataclass(frozen=True)
class CommandItem:
  id: str
  title: str
  keywords: str
  run: Callable[[], None]


class CommandPalette(ModalScreen[None]):
  BINDINGS = [("escape", "dismiss", "Close")]

  def __init__(self, items: List[CommandItem]) -> None:
    super().__init__()
    self._items = items
    self._filtered: List[CommandItem] = items

  def compose(self) -> ComposeResult:
    with Container(classes="panel palette"):
      yield Static("Command Palette", classes="legend-header title")
      yield Input(placeholder="Type to search…", id="cp_query", classes="control")
      yield OptionList(id="cp_list", classes="control")

  def on_mount(self) -> None:
    self.query_one("#cp_query", Input).focus()
    self._refresh_list()

  def _refresh_list(self) -> None:
    ol = self.query_one("#cp_list", OptionList)
    ol.clear_options()
    for item in self._filtered[:50]:
      ol.add_option(item.title, id=item.id)

  def on_input_changed(self, event: Input.Changed) -> None:
    q = event.value.strip().lower()
    if not q:
      self._filtered = self._items
    else:
      self._filtered = [
        it for it in self._items
        if q in it.title.lower() or q in it.keywords.lower()
      ]
    self._refresh_list()

  def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
    sel_id = event.option.id
    if not sel_id:
      return
    item = next((it for it in self._items if it.id == sel_id), None)
    if item:
      item.run()
    self.dismiss()


class MessageCard(Container):
  def __init__(self, role: str, content_md: str, *, collapsible_title: Optional[str] = None) -> None:
    super().__init__(classes="panel message-card")
    self.role = role
    self.content_md = content_md
    self.collapsible_title = collapsible_title

  def compose(self) -> ComposeResult:
    with Horizontal(classes="legend-header"):
      yield Static(self.role, classes="title")
      yield Static("", classes="spacer")
      # status chips go here
    if self.collapsible_title:
      with Collapsible(title=self.collapsible_title, collapsed=True):
        yield Markdown(self.content_md)
    else:
      yield Markdown(self.content_md)


class RightDrawer(Container):
  DEFAULT_CSS = """
  RightDrawer {
    dock: right;
    width: 40%;
    display: none;
  }
  RightDrawer.-open { display: block; }
  """

  def __init__(self) -> None:
    super().__init__(classes="panel drawer")
    self.active_tab = "Navigator"

  def compose(self) -> ComposeResult:
    with Horizontal():
      # Vertical tabs
      with Container(id="drawer_tabs"):
        yield OptionList("Todos", "Tools", "Agents", "Sessions", "Navigator", id="drawer_tab_list", classes="control")
      # Content pane
      with Container(id="drawer_content"):
        yield Static("Drawer Content", id="drawer_title", classes="legend-header title")
        yield OptionList(id="drawer_list", classes="control")

  def open(self) -> None:
    self.add_class("-open")
    self.query_one("#drawer_tab_list", OptionList).focus()

  def close(self) -> None:
    self.remove_class("-open")


class MainScreen(Screen):
  def compose(self) -> ComposeResult:
    yield Container(
      Static("Top Bar", id="top_bar", classes="panel"),
      VerticalScroll(id="timeline"),
      Container(id="composer", classes="panel"),
      Static("Status Bar", id="status_bar", classes="panel"),
      RightDrawer(),
      id="root",
    )

  def on_mount(self) -> None:
    timeline = self.query_one("#timeline", VerticalScroll)
    timeline.mount(MessageCard("User", "Hello agent."))
    timeline.mount(MessageCard("Agent", "I can help.", collapsible_title=None))
    timeline.mount(MessageCard("Thinking", "Internal reasoning…", collapsible_title="▸ Thinking (hidden)"))

    composer = self.query_one("#composer", Container)
    with composer:
      yield Horizontal(
        TextArea(id="composer_input", classes="control"),
        Button("Send", id="send_btn", classes="control"),
      )

    self.query_one("#composer_input", TextArea).focus()


class AgentTUI(App):
  CSS_PATH = "app.tcss"
  BINDINGS = [
    ("ctrl+k", "command_palette", "Command Palette"),
    ("ctrl+d", "toggle_drawer", "Drawer"),
    ("escape", "escape", "Back"),
  ]

  def __init__(self) -> None:
    super().__init__()
    self._drawer_open = False

  def on_mount(self) -> None:
    self.push_screen(MainScreen())

  def action_command_palette(self) -> None:
    items = [
      CommandItem("open_drawer", "Open Drawer", "drawer nav", lambda: self.action_toggle_drawer()),
      # add model/provider/account/session/agent commands here
    ]
    self.push_screen(CommandPalette(items))

  def action_toggle_drawer(self) -> None:
    drawer = self.screen.query_one(RightDrawer)
    self._drawer_open = not self._drawer_open
    if self._drawer_open:
      drawer.open()
    else:
      drawer.close()

  def action_escape(self) -> None:
    # Close drawer first, otherwise let Textual handle focus/cancel
    if self._drawer_open:
      self.action_toggle_drawer()
      return

if __name__ == "__main__":
  AgentTUI().run()
~~~

This is intentionally minimal: it establishes the **shell + overlays** pattern and gives you the right “places” to flesh out.

---

## 8) Gherkin alignment to Textual behaviors (quick addendum)
A few Textual-specific acceptance checks you’ll want to enforce:

- **Palette** uses `ModalScreen` and must:
    - steal focus on open
    - restore focus on dismiss
- **Drawer** must:
    - not destroy composer input widget
    - overlay right side without changing the main layout
- **Rounded corners** must:
    - apply to `Button`, `Input`, `TextArea`, `OptionList`, `Container` frames
