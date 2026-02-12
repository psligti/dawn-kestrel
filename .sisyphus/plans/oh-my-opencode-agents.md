# Oh-My-OpenCode Agents with FSM and Builder Patterns

## TL;DR

> **Quick Summary**: Create 11 bolt_merlin agents with embedded FSM lifecycle management and a fluent AgentBuilder pattern. Each agent has a nested FSM structure: main lifecycle FSM (idle→running→completed/failed) plus workflow sub-FSM (intake→plan→[act→synthesize→check]*→done).
>
> **Deliverables**:
> - New AgentConfig dataclass wrapping Agent + FSMs
> - New AgentBuilder with fluent API (.with_name(), .with_prompt(), .with_fsm(), etc.)
> - AgentLifecycleFSM for state management
> - AgentWorkflowFSM for workflow phase orchestration
> - All 11 bolt_merlin agents recreated using AgentBuilder
> - Comprehensive test suite with 80%+ coverage
>
> **Estimated Effort**: Large (complex multi-component integration)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: AgentConfig → AgentLifecycleFSM → AgentWorkflowFSM → AgentBuilder → Agent Factories → Tests

---

## Context

### Original Request
Create the agents that are found in oh-my-opencode. Use the FSM pattern and the builder design patterns.

### Interview Summary
**Key Discussions & User Decisions**:
- **Agent Scope**: All 11 bolt_merlin agents (orchestrator, master_orchestrator, planner, autonomous_worker, consultant, pre_planning, plan_validator, librarian, explore, frontend_ui_engineer, multimodal_looker)
- **FSM Architecture**: Nested FSM approach
  - Main lifecycle FSM: idle → running → paused → completed/failed/cancelled
  - Nested workflow sub-FSM (when running): intake → plan → [act → synthesize → check]* → done
  - Workflow loop: act→synthesize→check repeats until check decides done
- **Builder Pattern**: Hybrid approach
  - AgentBuilder for agent configuration (name, description, permissions, prompt, etc.)
  - .with_fsm(fsm_builder) method to attach FSM built with existing FSMBuilder
- **Test Strategy**: TDD with pytest (RED-GREEN-REFACTOR)
- **Workflow FSM**: SAME for all 11 agents - act→synthesize→check→plan loop continues until check says done

**Research Findings**:
- Existing FSM framework: `dawn_kestrel/core/fsm.py` with FSMBuilder, FSMImpl, FSMContext, TransitionConfig
- Existing WorkflowFSM: `dawn_kestrel/agents/workflow_fsm.py` shows intake→plan→act→synthesize→check→done pattern
- Agent dataclass: `dawn_kestrel/agents/builtin.py` with name, description, mode, permission, etc.
- bolt_merlin agents: `dawn_kestrel/agents/bolt_merlin/` directory with 11 agent subdirectories

### Metis Review
**Identified Gaps (addressed in plan)**:
- **Data Structure Decision**: New AgentConfig class wrapping Agent + FSMs (safest approach, doesn't modify existing Agent)
- **Nested FSM Architecture**: Two separate FSM instances (lifecycle_fsm + workflow_fsm) for clean separation
- **FSM Instantiation**: At agent creation time (per-instance, not shared)
- **Workflow FSM Customization**: All agents use SAME workflow FSM structure
- **Scope Boundaries**: No FSM-as-a-Service, no dynamic state definition, no FSM visualization

**Guardrails from Metis Review**:
- ❌ **MUST NOT**: Create FSM-as-a-Service infrastructure
- ❌ **MUST NOT**: Add dynamic state machine definition at runtime
- ❌ **MUST NOT**: Add FSM visualization tools
- ❌ **MUST NOT**: Modify existing Agent dataclass (create wrapper)
- ❌ **MUST NOT**: Add FSM persistence (in-memory only)
- ✅ **MUST**: Create new AgentConfig class wrapping Agent + FSMs
- ✅ **MUST**: Use two separate FSM instances (lifecycle + workflow)
- ✅ **MUST**: All agents use same workflow FSM structure
- ✅ **MUST**: Follow existing FSMBuilder pattern

---

## Work Objectives

### Core Objective
Create 11 bolt_merlin agents with embedded FSM lifecycle management using nested FSM architecture (lifecycle FSM + workflow FSM) and a fluent AgentBuilder pattern that integrates with the existing FSMBuilder.

### Concrete Deliverables
- `dawn_kestrel/agents/agent_config.py` - AgentConfig dataclass and AgentBuilder
- `dawn_kestrel/agents/agent_lifecycle_fsm.py` - AgentLifecycleFSM class
- `dawn_kestrel/agents/agent_workflow_fsm.py` - AgentWorkflowFSM class
- `dawn_kestrel/agents/bolt_merlin/` - Updated agent factory functions using AgentBuilder
- `tests/agents/test_agent_config.py` - AgentConfig and AgentBuilder tests
- `tests/agents/test_agent_lifecycle_fsm.py` - AgentLifecycleFSM tests
- `tests/agents/test_agent_workflow_fsm.py` - AgentWorkflowFSM tests
- `tests/agents/test_bolt_merlin_fsm.py` - Integration tests for all 11 agents

### Definition of Done
- [ ] AgentConfig dataclass created with Agent + FSMs
- [ ] AgentBuilder fluent API with all required methods
- [ ] AgentLifecycleFSM with idle→running→paused→completed/failed/cancelled
- [ ] AgentWorkflowFSM with intake→plan→[act→synthesize→check]*→done loop
- [ ] All 11 agent factory functions updated to use AgentBuilder
- [ ] All tests passing (80%+ coverage)
- [ ] Integration with existing AgentRuntime verified

### Must Have
- **AgentConfig wrapper**: New class wrapping Agent + lifecycle_fsm + workflow_fsm
- **AgentBuilder fluent API**: .with_name(), .with_description(), .with_mode(), .with_permission(), .with_prompt(), .with_temperature(), .with_options(), .with_lifecycle_fsm(), .with_workflow_fsm(), .build()
- **AgentLifecycleFSM**: States: idle, running, paused, completed, failed, cancelled
- **AgentWorkflowFSM**: States: intake, plan, act, synthesize, check, done with loop
- **All 11 agents**: Recreated using AgentBuilder with embedded FSMs
- **Result-based errors**: All operations return Result[T]
- **TDD approach**: Tests written first

### Must NOT Have (Guardrails)
- ❌ FSM-as-a-Service infrastructure
- ❌ Dynamic state machine definition at runtime
- ❌ FSM visualization tools
- ❌ Modification of existing Agent dataclass
- ❌ FSM persistence (in-memory only)
- ❌ Separate workflow FSM per agent type (same structure for all)
- ❌ FSM observability beyond basic logging

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest with pytest-asyncio)
- **Automated tests**: YES (TDD - RED-GREEN-REFACTOR)
- **Framework**: pytest with pytest-asyncio

### If TDD Enabled

Each TODO follows RED-GREEN-REFACTOR:

**Task Structure:**
1. **RED**: Write failing test first
   - Test file: `tests/agents/test_agent_config.py`
   - Test command: `pytest tests/agents/test_agent_config.py -k test_name`
   - Expected: FAIL (test exists, implementation doesn't)
2. **GREEN**: Implement minimum code to pass
   - Command: `pytest tests/agents/test_agent_config.py -k test_name`
   - Expected: PASS
3. **REFACTOR**: Clean up while keeping green
   - Command: `pytest tests/agents/test_agent_config.py -k test_name`
   - Expected: PASS (still)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

**Verification Tool by Deliverable Type:**

| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Library/Module** | Bash (pytest) | Import, create instances, assert behavior |
| **FSM Logic** | Bash (pytest) | Transition states, assert valid/invalid transitions |
| **Builder API** | Bash (pytest) | Build agents, assert configuration correct |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: AgentConfig dataclass
├── Task 2: AgentLifecycleFSM core
└── Task 3: AgentWorkflowFSM core

Wave 2 (After Wave 1):
├── Task 4: AgentBuilder fluent API
└── Task 5: AgentBuilder FSM integration

Wave 3 (After Wave 2):
├── Task 6: orchestrator agent with FSM
├── Task 7: master_orchestrator agent with FSM
├── Task 8: planner agent with FSM
├── Task 9: autonomous_worker agent with FSM
├── Task 10: consultant agent with FSM
├── Task 11: pre_planning agent with FSM
├── Task 12: plan_validator agent with FSM
├── Task 13: librarian agent with FSM
├── Task 14: explore agent with FSM
├── Task 15: frontend_ui_engineer agent with FSM
└── Task 16: multimodal_looker agent with FSM

Wave 4 (After Wave 3):
└── Task 17: Integration tests for all agents

Critical Path: Task 1 → Task 4 → Task 5 → Task 6 → Task 17
Parallel Speedup: ~60% faster than sequential
```

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2, 3 | task(category="unspecified-high", run_in_background=false) |
| 2 | 4, 5 | task(category="unspecified-high", run_in_background=false) |
| 3 | 6-16 | task(category="quick", run_in_background=false) - can parallelize |
| 4 | 17 | task(category="unspecified-high", run_in_background=false) |

---

## TODOs

- [x] 1. Create AgentConfig Dataclass

  **What to do**:
  - Create AgentConfig dataclass in `dawn_kestrel/agents/agent_config.py`
  - Fields: agent (Agent), lifecycle_fsm (Optional[FSM]), workflow_fsm (Optional[FSM]), metadata (dict)
  - Add from_agent() class method to create from existing Agent
  - Import Result pattern for type-safe returns

  **Must NOT do**:
  - Modify existing Agent dataclass
  - Add persistence fields

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Dataclass design requires careful architecture decisions
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: Tasks 4, 5, 6-16
  - **Blocked By**: None

  **References**:
  - `dawn_kestrel/agents/builtin.py:Agent` (lines 8-24) - Existing Agent dataclass to wrap
  - `dawn_kestrel/core/fsm.py:FSM` (lines 36-88) - FSM protocol to reference

  **Acceptance Criteria**:
  - [ ] AgentConfig dataclass created with agent, lifecycle_fsm, workflow_fsm fields
  - [ ] from_agent() class method creates AgentConfig from existing Agent
  - [ ] pytest tests/agents/test_agent_config.py::TestAgentConfig::test_agent_config_creates_from_agent → PASS

  **Commit**: YES (groups with 2, 3)
  - Message: `feat(agents): add AgentConfig dataclass`
  - Files: dawn_kestrel/agents/agent_config.py, tests/agents/test_agent_config.py

- [x] 2. Create AgentLifecycleFSM

  **What to do**:
  - Create AgentLifecycleFSM class in `dawn_kestrel/agents/agent_lifecycle_fsm.py`
  - Use existing FSMBuilder to build lifecycle FSM
  - States: idle, running, paused, completed, failed, cancelled
  - Valid transitions:
    - idle → running, cancelled
    - running → paused, completed, failed, cancelled
    - paused → running, cancelled
    - completed → idle (reset)
    - failed → idle (reset)
    - cancelled → idle (reset)
  - Add entry/exit hooks for logging
  - Add factory function create_lifecycle_fsm()

  **Must NOT do**:
  - Add persistence
  - Add visualization

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: FSM design requires careful state transition logic
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3)
  - **Blocks**: Tasks 4, 5, 6-16
  - **Blocked By**: None

  **References**:
  - `dawn_kestrel/core/fsm.py:FSMBuilder` (lines 467-739) - FSMBuilder to use
  - `dawn_kestrel/core/agent_fsm.py:AgentFSMImpl` (lines 77-193) - Reference implementation
  - `dawn_kestrel/core/agent_fsm.py:VALID_STATES, VALID_TRANSITIONS` (lines 104-121) - State definitions to follow

  **Acceptance Criteria**:
  - [ ] AgentLifecycleFSM creates FSM with idle, running, paused, completed, failed, cancelled states
  - [ ] Valid transitions match specification
  - [ ] pytest tests/agents/test_agent_lifecycle_fsm.py::TestAgentLifecycleFSM → PASS

  **Commit**: YES (groups with 1, 3)
  - Message: `feat(agents): add AgentLifecycleFSM`
  - Files: dawn_kestrel/agents/agent_lifecycle_fsm.py, tests/agents/test_agent_lifecycle_fsm.py

- [x] 3. Create AgentWorkflowFSM

  **What to do**:
  - Create AgentWorkflowFSM class in `dawn_kestrel/agents/agent_workflow_fsm.py`
  - Use existing FSMBuilder to build workflow FSM
  - States: intake, plan, act, synthesize, check, done
  - Valid transitions:
    - intake → plan
    - plan → act
    - act → synthesize
    - synthesize → check
    - check → plan (loop) OR check → done (exit)
    - done → intake (reset for next task)
  - Add entry hooks for phase execution
  - Add check phase hook that returns continue/done decision
  - Add factory function create_workflow_fsm()

  **Must NOT do**:
  - Add persistence
  - Customize per agent type

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Workflow FSM design requires careful loop logic
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2)
  - **Blocks**: Tasks 4, 5, 6-16
  - **Blocked By**: None

  **References**:
  - `dawn_kestrel/agents/workflow_fsm.py:WorkflowFSM` - Reference implementation of workflow FSM
  - `dawn_kestrel/core/fsm.py:FSMBuilder` (lines 467-739) - FSMBuilder to use

  **Acceptance Criteria**:
  - [ ] AgentWorkflowFSM creates FSM with intake, plan, act, synthesize, check, done states
  - [ ] Loop transition check → plan works correctly
  - [ ] Exit transition check → done works correctly
  - [ ] pytest tests/agents/test_agent_workflow_fsm.py::TestAgentWorkflowFSM → PASS

  **Commit**: YES (groups with 1, 2)
  - Message: `feat(agents): add AgentWorkflowFSM`
  - Files: dawn_kestrel/agents/agent_workflow_fsm.py, tests/agents/test_agent_workflow_fsm.py

- [x] 4. Create AgentBuilder Fluent API

  **What to do**:
  - Create AgentBuilder class in `dawn_kestrel/agents/agent_config.py`
  - Fluent methods:
    - .with_name(name: str) → AgentBuilder
    - .with_description(description: str) → AgentBuilder
    - .with_mode(mode: str) → AgentBuilder
    - .with_permission(permissions: List[Dict]) → AgentBuilder
    - .with_prompt(prompt: str) → AgentBuilder
    - .with_temperature(temperature: float) → AgentBuilder
    - .with_options(options: Dict) → AgentBuilder
    - .with_native(native: bool) → AgentBuilder
  - All methods return self for chaining
  - Validate configuration before building

  **Must NOT do**:
  - Add more than 10 builder methods
  - Build FSM in this task (separate task)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Builder API design requires careful fluent method chaining
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 5)
  - **Blocks**: Tasks 6-16
  - **Blocked By**: Task 1 (needs AgentConfig)

  **References**:
  - `dawn_kestrel/context/builder.py:ContextBuilder` - Existing builder pattern to follow
  - `dawn_kestrel/core/fsm.py:FSMBuilder` - Reference for fluent API design

  **Acceptance Criteria**:
  - [ ] AgentBuilder with all fluent methods implemented
  - [ ] Method chaining works correctly
  - [ ] pytest tests/agents/test_agent_config.py::TestAgentBuilder → PASS

  **Commit**: YES (groups with 5)
  - Message: `feat(agents): add AgentBuilder fluent API`
  - Files: dawn_kestrel/agents/agent_config.py, tests/agents/test_agent_config.py

- [x] 5. Add FSM Integration to AgentBuilder

  **What to do**:
  - Add .with_lifecycle_fsm(fsm: FSM) → AgentBuilder
  - Add .with_workflow_fsm(fsm: FSM) → AgentBuilder
  - Add .with_default_fsms() → AgentBuilder (creates default lifecycle + workflow FSMs)
  - Update .build() to return Result[AgentConfig] with FSMs attached
  - Validate FSM configuration

  **Must NOT do**:
  - Create FSMs directly in builder (use factory functions)
  - Allow FSM customization per agent type

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: FSM integration requires careful coordination
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Task 4)
  - **Blocks**: Tasks 6-16
  - **Blocked By**: Tasks 2, 3 (needs FSM factory functions), Task 4 (needs AgentBuilder)

  **References**:
  - `dawn_kestrel/agents/agent_lifecycle_fsm.py:create_lifecycle_fsm` - Factory function to use
  - `dawn_kestrel/agents/agent_workflow_fsm.py:create_workflow_fsm` - Factory function to use

  **Acceptance Criteria**:
  - [ ] .with_lifecycle_fsm() and .with_workflow_fsm() methods work
  - [ ] .with_default_fsms() creates default FSMs
  - [ ] .build() returns AgentConfig with FSMs attached
  - [ ] pytest tests/agents/test_agent_config.py::TestAgentBuilderFSM → PASS

  **Commit**: YES (groups with 4)
  - Message: `feat(agents): add FSM integration to AgentBuilder`
  - Files: dawn_kestrel/agents/agent_config.py, tests/agents/test_agent_config.py

- [x] 6. Recreate orchestrator Agent with FSM

  **What to do**:
  - Update `dawn_kestrel/agents/bolt_merlin/orchestrator/__init__.py`
  - Use AgentBuilder to create orchestrator AgentConfig
  - Keep existing ORCHESTRATOR_PROMPT unchanged
  - Add .with_default_fsms() to attach FSMs
  - Update factory function: create_orchestrator_agent() → AgentConfig

  **Must NOT do**:
  - Modify the prompt content
  - Change existing permissions

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple refactoring to use new builder
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 7-16)
  - **Blocked By**: Tasks 4, 5 (needs AgentBuilder)

  **References**:
  - `dawn_kestrel/agents/bolt_merlin/orchestrator/__init__.py` - Existing agent to update
  - `dawn_kestrel/agents/agent_config.py:AgentBuilder` - Builder to use

  **Acceptance Criteria**:
  - [ ] create_orchestrator_agent() returns AgentConfig with FSMs
  - [ ] AgentConfig.agent has correct name, prompt, permissions
  - [ ] pytest tests/agents/test_bolt_merlin_fsm.py::test_orchestrator_agent_with_fsm → PASS

  **Commit**: YES (groups with 7-16)
  - Message: `feat(agents): recreate orchestrator with AgentBuilder and FSM`
  - Files: dawn_kestrel/agents/bolt_merlin/orchestrator/__init__.py

- [x] 7-16. Recreate Remaining 10 Agents with FSM

  **Agents to update (same pattern as Task 6)**:
  - Task 7: master_orchestrator
  - Task 8: planner
  - Task 9: autonomous_worker
  - Task 10: consultant
  - Task 11: pre_planning
  - Task 12: plan_validator
  - Task 13: librarian
  - Task 14: explore
  - Task 15: frontend_ui_engineer
  - Task 16: multimodal_looker

  **What to do for each**:
  - Update factory function to return AgentConfig
  - Use AgentBuilder with .with_default_fsms()
  - Keep existing prompts unchanged
  - Keep existing permissions unchanged

  **Acceptance Criteria (for each)**:
  - [ ] Factory function returns AgentConfig with FSMs
  - [ ] Existing tests still pass
  - [ ] New test verifies FSM attachment

  **Commit**: YES (groups with 6)
  - Message: `feat(agents): recreate all bolt_merlin agents with AgentBuilder and FSM`
  - Files: dawn_kestrel/agents/bolt_merlin/*/__init__.py

- [ ] 17. Create Integration Tests

  **What to do**:
  - Create `tests/agents/test_bolt_merlin_fsm.py`
  - Test all 11 agents have FSMs attached
  - Test lifecycle FSM transitions
  - Test workflow FSM loop (act→synthesize→check→plan)
  - Test workflow FSM exit (check→done)
  - Test FSM state on agent failure

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration tests require understanding of full system
  - **Skills**: None needed

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Tasks 6-16 (needs all agents)

  **Acceptance Criteria**:
  - [ ] All 11 agents tested for FSM attachment
  - [ ] Lifecycle FSM transitions tested
  - [ ] Workflow FSM loop tested
  - [ ] pytest tests/agents/test_bolt_merlin_fsm.py → PASS (all tests)
  - [ ] Coverage ≥ 80%

  **Commit**: YES
  - Message: `test(agents): add integration tests for bolt_merlin agents with FSM`
  - Files: tests/agents/test_bolt_merlin_fsm.py

---

## Commit Strategy

| After Task | Message | Files |
|------------|---------|-------|
| 1-3 | `feat(agents): add AgentConfig, AgentLifecycleFSM, AgentWorkflowFSM` | agent_config.py, agent_lifecycle_fsm.py, agent_workflow_fsm.py |
| 4-5 | `feat(agents): add AgentBuilder with FSM integration` | agent_config.py |
| 6-16 | `feat(agents): recreate all bolt_merlin agents with AgentBuilder and FSM` | bolt_merlin/*/\_\_init\_\_.py |
| 17 | `test(agents): add integration tests for bolt_merlin agents with FSM` | test_bolt_merlin_fsm.py |

---

## Success Criteria

### Verification Commands
```bash
# Run all agent tests
pytest tests/agents/ -v

# Run with coverage
pytest tests/agents/ --cov=dawn_kestrel/agents --cov-report=term-missing

# Verify all agents can be imported
python -c "from dawn_kestrel.agents.bolt_merlin import *; print('All agents imported successfully')"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (80%+ coverage)
- [ ] All 11 agents return AgentConfig with FSMs
- [ ] Integration with existing AgentRuntime verified
