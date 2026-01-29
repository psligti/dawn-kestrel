# OpenCode Surface Area Inventory (SAI)

## Purpose
Authoritative list of every user-touchable surface in OpenCode CLI and TUI, serving as the foundation for achieving complete feature parity in Python.

## Document Structure
This directory contains comprehensive surface area inventories organized by category:

- `01_cli_commands.md` - CLI commands, flags, options, aliases
- `02_tui_surface.md` - TUI screens, navigation, keybindings
- `03_session_management.md` - Session lifecycle, storage, export/import
- `04_tools_and_agents.md` - Built-in tools, tool framework, agents
- `05_git_integration.md` - Git integration features
- `06_config_settings.md` - Configuration, environment variables, permissions
- `07_ai_integration.md` - AI providers, streaming, tokens
- `08_lsp_integration.md` - Language server protocol
- `09_output_logging.md` - Output formats, exit codes, errors
- `10_review_loop.md` - Linters, test runners, formatters
- `11_ptm.md` - Parity Traceability Matrix (main document)

## Completion Status
✅ **Completed** - All surface area exploration completed
📋 **Status**: In progress - Synthesizing complete SAI from all explore agent results

## Usage
This inventory serves two purposes:
1. **Discovery**: Complete mapping of "what exists" in TypeScript OpenCode
2. **Verification**: Checklist to ensure nothing is missed in Python implementation
3. **Implementation**: Blueprint for building feature-complete Python version

## Definition of "Nothing Can Be Missed"
Parity is not "core features." Parity is everything the user can touch:
- Any command / subcommand / alias
- Any flag, env var, config option, default, or precedence rule
- Any interactive prompt / selection / confirm / cancel behavior
- Any screen/panel in the TUI
- Any keybinding / shortcut / mouse behavior
- Any output format (human + machine)
- Any exit code, error text class, or logging level
- Any stateful behavior (sessions, resume, history, compaction, cache)
- Any tool integration hook (git, tests, formatters, linters, shells)
- Any permission / safety gate ("are you sure", destructive actions)
- Any help UX (help text, examples, completions)
- Any edge-case semantics (missing files, conflicts, partial failures)

## Approach
The Ralph Loop will:
1. **Comprehensively map** every touchable surface via parallel explore agents
2. **Create structured SAI documents** for each category
3. **Build PTM** mapping each SAI item to implementation and test status
4. **Implement missing features** following SAI guidance
5. **Verify completeness** via PTM coverage audit

## Next Steps
See `/11_ptm.md` for the complete Parity Traceability Matrix once all SAI documents are synthesized.
