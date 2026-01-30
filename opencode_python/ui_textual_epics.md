UI concept

Always visible
  • Top bar: provider/account/model, session, status, Run
  • Main session view: conversation timeline + tool runs + diffs inline (the “truth”)
  • Prompt composer: bottom input

Drawer (toggleable)

A right-side drawer that slides in over ~30–45% width. It has tabs/sections:
  1.  Todos (from plan / backlog / “next actions”)
  2.  Subagents (each subagent status + last result)
  3.  Quick navigator (the “conversation index”)

No “view switching” in the workspace anymore — the drawer is how you jump around.

⸻

Drawer contents (specific behaviors)

1) Todos section

Each todo item has:
  • status (queued/in-progress/done/blocked)
  • owner (agent/subagent)
  • short title
  • link target (jump to the timeline entry where it was created/updated)

Interactions:
  • Enter = jump to its most recent timeline anchor
  • r = run the todo (or “ask agent to execute this”)
  • x = mark done (with confirmation / audit)

2) Subagents section

List of subagents:
  • name (e.g., security, qa, docs, readability)
  • status indicator (idle/running/failed/complete)
  • last run timestamp + summary line
  • Enter = open subagent details panel (still inside drawer) and/or jump to its latest output in the main timeline
  • R = rerun subagent

3) Quick conversation navigator

This is the key piece you described:

A compact index of timeline “events”, each row shows:
  • speaker: User or Agent or Subagent:<name>
  • short description: first sentence or generated summary
  • type pill: msg, plan, tool, diff, result, error

Interaction:
  • Up/Down moves highlight
  • Enter jumps the main view to that event (scroll + focus)
  • f filters (User only, Agent only, Subagent only, errors only, tool runs only)
  • s search by text

⸻

User stories + gherkins (drawer model)

Epic 1 — Drawer as the control center

Story 1.1 — Toggle drawer
  • As a developer, I want to open/close a drawer, so I can access navigation and controls without changing the main view.

Feature: Right-side drawer
  Scenario: Open and close drawer
    Given I am viewing an active session
    When I press "Ctrl+D"
    Then the drawer should open on the right
    And focus should move into the drawer
    When I press "Esc"
    Then the drawer should close
    And focus should return to the prompt composer

Story 1.2 — Drawer does not replace the main session
  • As a developer, I want the main session view to remain the source of truth, so the drawer is only a helper.

Feature: Drawer is auxiliary
  Scenario: Main timeline remains visible
    Given the drawer is open
    Then the main session timeline should remain visible
    And the prompt composer should remain visible


⸻

Epic 2 — Todos in the drawer

Story 2.1 — See todos extracted from plan
  • As a developer, I want todos listed in the drawer, so I can track next actions and progress.

Feature: Todos drawer section
  Scenario: Show todos
    Given I have an active session
    And the agent has produced at least one todo item
    When I open the drawer
    And I select the "Todos" section
    Then I should see a list of todos
    And each todo should show status, title, and last updated time

Story 2.2 — Jump to todo anchor in timeline
  • As a developer, I want selecting a todo to jump the main view, so I can see context and outcomes.

Feature: Todo navigation
  Scenario: Jump to todo in timeline
    Given the drawer is open on "Todos"
    When I highlight a todo and press "Enter"
    Then the main timeline should scroll to the todo's anchor entry
    And the selected entry should be visibly highlighted


⸻

Epic 3 — Subagents in the drawer

Story 3.1 — Show subagent status + last summary
  • As a developer, I want to see each subagent’s status and last result summary, so I know what ran and what failed.

Feature: Subagent list
  Scenario: Display subagent status
    Given I have configured subagents for the session
    When I open the drawer
    And I select the "Subagents" section
    Then I should see all subagents
    And each subagent should show status and a one-line summary of the last run

Story 3.2 — Jump to latest subagent output
  • As a developer, I want selecting a subagent to jump to its latest output, so I can review it quickly.

Feature: Subagent navigation
  Scenario: Jump to latest output
    Given the drawer is open on "Subagents"
    And the "security" subagent has run at least once
    When I select "security" and press "Enter"
    Then the main timeline should scroll to the latest "security" result entry


⸻

Epic 4 — Quick conversation navigator

Story 4.1 — Show compact conversation index
  • As a developer, I want a quick navigator list that shows who spoke and a short summary, so I can jump around the session fast.

Feature: Quick conversation navigator
  Scenario: Render conversation index
    Given I have an active session with messages and tool events
    When I open the drawer
    And I select the "Navigator" section
    Then I should see an indexed list of timeline events
    And each row should include speaker and a short description

Story 4.2 — Move highlight, jump main timeline
  • As a developer, I want moving and selecting items to jump the main view, so navigation is instant.

Feature: Navigator jumping
  Scenario: Jump to selected event
    Given the drawer is open on "Navigator"
    When I move the highlight to an event
    And I press "Enter"
    Then the main timeline should scroll to that event
    And that event should be highlighted in the main view

Story 4.3 — Filter navigator
  • As a developer, I want filters (User/Agent/Subagent/Errors/Tools), so I can reduce noise.

Feature: Navigator filters
  Scenario: Filter to errors only
    Given the drawer is open on "Navigator"
    When I apply the filter "Errors"
    Then only error events should be listed
    And the result count should update


⸻

Keybindings (Posting-inspired, minimal)
  • Ctrl+P command palette (global)
  • Ctrl+D toggle drawer
  • Ctrl+O jump mode (now: prompt, timeline, drawer, top bar)
  • F1 help (contextual)
  • F3 pager/inspector (focused content)
  • F4 external editor (focused text / prompt)

⸻

Implementation “contract” (so it stays clean)
  • Main timeline entries must have:
  • event_id
  • speaker (user/agent/subagent:name)
  • type (msg/plan/tool/diff/result/error)
  • summary (one-liner used by navigator)
  • anchor (scroll target)
  • Todos must have:
  • todo_id, status, title, owner, anchor_event_id
  • Subagents must have:
  • name, status, last_run_event_id, last_summary

If you want, I’ll rewrite the whole earlier set into a single “Drawer-first UX epic” and keep the rest of the system (providers/accounts/sessions/skills/tools/themes) as overlays + palette actions that feed into this timeline + drawer model.