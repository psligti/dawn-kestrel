# AGENTS MODULE

**Package:** `dawn_kestrel/agents/`

Multi-agent orchestration system with lifecycle management, plugin discovery, and Bolt Merlin subagents.

## OVERVIEW

```
agents/
├── __init__.py          # AgentManager, AgentExecutor
├── state.py             # AgentState enum, AgentStateMachine
├── agent_config.py      # AgentConfig wrapper, AgentBuilder
├── builtin.py           # Agent dataclass, built-in agents
├── registry.py          # CRUD + JSON persistence
├── workflow.py          # Phase output contracts (Pydantic)
├── bolt_merlin/         # Specialized subagents
└── review/              # BaseReviewerAgent + contracts
```

## AGENT TYPES

| Type | File | Purpose |
|------|------|---------|
| `Agent` | builtin.py | Core dataclass (name, mode, permission, prompt) |
| `AgentConfig` | agent_config.py | Wrapper with lifecycle_fsm, workflow_fsm, metadata |
| `AgentManager` | __init__.py | Lifecycle coordination, event publishing |
| `AgentExecutor` | __init__.py | Execution engine with tool filtering |
| `AgentRegistry` | registry.py | CRUD + plugin discovery + JSON persistence |
| `BaseReviewerAgent` | review/base.py | Abstract base for PR review agents |

## LIFECYCLE STATES

```
IDLE → INITIALIZING → READY → RUNNING → COMPLETED
                         ↓         ↓
                      FAILED   PAUSED → RUNNING
```

| State | Meaning |
|-------|---------|
| IDLE | Initialized, not started |
| INITIALIZING | Setting up internal state |
| READY | Ready to process |
| RUNNING | Actively processing |
| PAUSED | Suspended (resumable) |
| COMPLETED | Finished successfully |
| FAILED | Error encountered |

## BUILDER PATTERN

```python
from dawn_kestrel.agents.agent_config import AgentBuilder

config = (AgentBuilder()
    .with_name("my-agent")
    .with_description("Custom agent")
    .with_mode("subagent")
    .with_permission([{"permission": "read", "action": "allow"}])
    .with_prompt("You are a code reviewer")
    .with_default_fsms()
    .build()
    .unwrap())
```

## BUILT-IN AGENTS

| Name | Mode | Purpose |
|------|------|---------|
| `build` | primary | Default agent, full tool permissions |
| `plan` | primary | Planning mode, disallows edit/write |
| `general` | subagent | Multi-step tasks, parallel work |
| `explore` | subagent | Fast codebase exploration (grep, glob, read) |

## BOLT MERLIN SUBAGENTS

| Agent | Factory Function | Purpose |
|-------|------------------|---------|
| Orchestrator (Sisyphus) | `create_orchestrator_agent()` | Main delegation coordinator |
| Master Orchestrator | `create_master_orchestrator_agent()` | Top-level coordination |
| Planner (Prometheus) | `create_planner_agent()` | Strategic planning |
| Autonomous Worker (Hephaestus) | `create_autonomous_worker_agent()` | Deep autonomous execution |
| Consultant (Oracle) | `create_consultant_agent()` | Read-only consultation |
| Pre-Planning (Metis) | `create_pre_planning_agent()` | Pre-planning analysis |
| Plan Validator (Momus) | `create_plan_validator_agent()` | Plan validation |
| Librarian | `create_librarian_agent()` | Docs/codebase search |
| Explore | `create_explore_agent()` | Fast exploration |
| Frontend UI/UX | `create_frontend_ui_ux_skill()` | UI/UX engineering |
| Multimodal Looker | `create_multimodal_looker_agent()` | PDF/image analysis |

## WORKFLOW PHASES

Each phase outputs a Pydantic model with `extra="forbid"`:

| Phase | Output Model | Purpose |
|-------|--------------|---------|
| Intake | `IntakeOutput` | Intent, constraints, initial evidence |
| Plan | `PlanOutput` | Prioritized todo list, strategy |
| Act | `ActOutput` | Single tool execution, artifacts |
| Synthesize | `SynthesizeOutput` | Merged findings, updated todos |
| Check | `CheckOutput` | Routing decision (act/reason/done) |

## NOTES

- Plugin discovery via entry points (`load_agents()`)
- Permission rules use glob patterns with allow/deny actions
- Event publishing on state transitions via `bus.publish()`
- Registry supports JSON persistence to `storage/agent/`
