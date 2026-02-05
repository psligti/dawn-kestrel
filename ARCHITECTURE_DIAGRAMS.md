# OpenCode Python SDK - Architecture Diagrams

This document contains comprehensive mermaid diagrams for the OpenCode Python SDK architecture, workflows, and data flows.

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Component Relationships](#component-relationships)
3. [Agent Lifecycle](#agent-lifecycle)
4. [Tool Execution Flow](#tool-execution-flow)
5. [Session Message Flow](#session-message-flow)
6. [PR Review Workflow](#pr-review-workflow)
7. [Storage Hierarchy](#storage-hierarchy)
8. [Event-Driven Architecture](#event-driven-architecture)
9. [Permission System](#permission-system)
10. [Multi-Agent Orchestration](#multi-agent-orchestration)

---

## High-Level Architecture

### Overall System Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        App[Application]
        AgentExecutor[Agent Executor]
        PRReviewOrchestrator[PR Review Orchestrator]
    end

    subgraph "Agent Layer"
        BuildAgent[Build Agent<br/>Default, full access]
        PlanAgent[Plan Agent<br/>Read-only planning]
        GeneralAgent[General Agent<br/>Multi-step parallel]
        ExploreAgent[Explore Agent<br/>Codebase search]
        ReviewAgents[Review Subagents<br/>Architecture, Security,<br/>Documentation, etc.]
    end

    subgraph "Tool Layer"
        ToolRegistry[Tool Registry]
        BuiltinTools[Built-in Tools<br/>bash, read, write,<br/>grep, glob]
        AdditionalTools[Additional Tools<br/>edit, list, task,<br/>webfetch, etc.]
    end

    subgraph "Core Layer"
        SessionManager[Session Manager]
        EventBus[Event Bus]
        AgentManager[Agent Manager]
    end

    subgraph "Storage Layer"
        SessionStorage[Session Storage]
        MessageStorage[Message Storage]
        PartStorage[Part Storage]
    end

    subgraph "Models"
        Session[Session Model]
        Message[Message Model]
        Part[Part Types]
        Agent[Agent Model]
        Tool[Tool Model]
    end

    App --> AgentExecutor
    App --> PRReviewOrchestrator
    
    AgentExecutor --> BuildAgent
    AgentExecutor --> PlanAgent
    AgentExecutor --> GeneralAgent
    AgentExecutor --> ExploreAgent
    
    PRReviewOrchestrator --> ReviewAgents
    
    BuildAgent --> ToolRegistry
    PlanAgent --> ToolRegistry
    GeneralAgent --> ToolRegistry
    ExploreAgent --> ToolRegistry
    ReviewAgents --> ToolRegistry
    
    ToolRegistry --> BuiltinTools
    ToolRegistry --> AdditionalTools
    
    AgentExecutor --> SessionManager
    PRReviewOrchestrator --> SessionManager
    SessionManager --> EventBus
    AgentExecutor --> AgentManager
    
    SessionManager --> SessionStorage
    SessionManager --> MessageStorage
    SessionManager --> PartStorage
    
    BuiltinTools --> EventBus
    AdditionalTools --> EventBus
    AgentManager --> EventBus
    
    SessionStorage --> Session
    MessageStorage --> Message
    PartStorage --> Part
    ToolRegistry --> Tool
    AgentManager --> Agent

    style App fill:#e1f5ff
    style AgentExecutor fill:#fff4e1
    style PRReviewOrchestrator fill:#fff4e1
    style EventBus fill:#f3e5f5
```

---

## Component Relationships

### Entity-Relationship Diagram

```mermaid
erDiagram
    Session ||--o{ Message : contains
    Session ||--o{ Agent : managed_by
    Session {
        string id PK
        string slug
        string project_id
        string directory
        string title
        string version
        string parent_id FK
        datetime time_created
        datetime time_updated
        int message_count
        float total_cost
    }
    Message ||--o{ Part : contains
    Message {
        string id PK
        string session_id FK
        string role
        string text
        json time
        json token_usage
    }
    Part {
        string id PK
        string message_id FK
        string session_id FK
        string part_type
        json data
    }
    Agent ||--o{ AgentState : has_state
    Agent {
        string name PK
        string description
        string mode
        json permission
        bool native
    }
    AgentState {
        string session_id PK, FK
        string agent_name FK
        string status
        float time_started
        float time_finished
    }
    Tool {
        string id PK
        string description
        json parameters
    }
    ToolRegistry ||--o{ Tool : registers
```

---

## Agent Lifecycle

### State Machine

```mermaid
stateDiagram-v2
    [*] --> Initializing: initialize_agent(agent, session)
    
    Initializing --> Ready: set_agent_ready(session_id)
    note right of Ready
        Agent initialized
        Ready to execute tasks
    end note
    
    Ready --> Executing: execute_agent(agent_name, user_message)
    note right of Executing
        Processing user request
        Executing tools
    end note
    
    Executing --> Ready: Task complete successfully
    Executing --> Error: Exception occurred
    
    Error --> Ready: Recovery / Retry
    note right of Error
        Error logged
        Agent state updated
    end note
    
    Executing --> Cleanup: cleanup_agent(session_id)
    Ready --> Cleanup: cleanup_agent(session_id)
    
    Cleanup --> [*]: Agent terminated
    note right of Cleanup
        State cleaned up
        Events emitted
    end note
```

### Agent Execution Sequence

```mermaid
sequenceDiagram
    participant User
    participant AgentExecutor
    participant AgentManager
    participant ToolManager
    participant SessionManager
    participant AISession
    participant EventBus

    User->>AgentExecutor: execute_agent(agent_name, user_message, session_id)
    AgentExecutor->>AgentManager: get_agent_by_name(agent_name)
    AgentManager-->>AgentExecutor: Agent object
    
    AgentExecutor->>SessionManager: get_session(session_id)
    SessionManager-->>AgentExecutor: Session object
    
    AgentExecutor->>AgentManager: initialize_agent(agent, session)
    AgentManager->>EventBus: publish(AGENT_INITIALIZED)
    
    AgentExecutor->>AgentManager: set_agent_ready(session_id)
    AgentManager->>EventBus: publish(AGENT_READY)
    
    AgentExecutor->>AgentManager: set_agent_executing(session_id)
    AgentManager->>EventBus: publish(AGENT_EXECUTING)
    
    AgentExecutor->>ToolManager: get_allowed_tools(agent.permission)
    ToolManager-->>AgentExecutor: List of tool names
    
    AgentExecutor->>AISession: process_message(user_message, tools, options)
    
    loop Tool Execution
        AISession->>ToolManager: execute(tool_name, args)
        ToolManager-->>AISession: ToolResult
    end
    
    AISession-->>AgentExecutor: Response with parts and metadata
    
    alt Success
        AgentExecutor->>AgentManager: cleanup_agent(session_id)
        AgentManager->>EventBus: publish(AGENT_CLEANUP)
        AgentExecutor-->>User: {response, parts, status: "completed"}
    else Error
        AgentExecutor->>AgentManager: set_agent_error(session_id, error)
        AgentManager->>EventBus: publish(AGENT_ERROR)
        AgentExecutor-->>User: {response, status: "error"}
    end
```

---

## Tool Execution Flow

### Tool Execution Sequence Diagram

```mermaid
sequenceDiagram
    participant Agent
    participant AgentExecutor
    participant ToolRegistry
    participant PermissionFilter
    participant Tool
    participant EventBus
    participant Context

    Agent->>AgentExecutor: execute_agent(agent_name, user_message)
    AgentExecutor->>ToolRegistry: get_all_tools()
    ToolRegistry-->>AgentExecutor: {bash: BashTool, read: ReadTool, ...}
    
    AgentExecutor->>PermissionFilter: filter_tools(agent.permission)
    
    Note over PermissionFilter
        Agent permission rules:
        - allow/deny patterns
        - tool name matching
    end Note
    
    PermissionFilter-->>AgentExecutor: [bash, read, glob, ...] (allowed tools)
    
    loop For each tool in execution
        AgentExecutor->>Tool: execute(args, ctx)
        
        Note over Context
            ToolContext:
            - session_id
            - message_id
            - agent
            - abort signal
        end Note
        
        Tool->>Tool: validate(args)
        Tool->>Tool: perform operation
        Tool->>EventBus: publish(TOOL_EXECUTED)
        
        alt Success
            Tool-->>AgentExecutor: ToolResult(output, metadata)
        else Error
            Tool->>EventBus: publish(TOOL_ERROR, error)
            Tool-->>AgentExecutor: ToolResult(error: "...")
        end
    end
    
    AgentExecutor-->>Agent: Final response with all tool results
```

---

## Session Message Flow

### Message Creation and Retrieval

```mermaid
sequenceDiagram
    participant User
    participant SessionManager
    participant SessionStorage
    participant MessageStorage
    participant PartStorage
    participant EventBus

    Note over User, EventBus: Create Session
    User->>SessionManager: create(title, version, summary)
    SessionManager->>SessionStorage: create_session(session)
    SessionStorage-->>SessionManager: success
    SessionManager->>EventBus: publish(SESSION_CREATED)
    SessionManager-->>User: Session object
    
    Note over User, EventBus: Create User Message
    User->>SessionManager: create_message(session_id, role="user", text)
    SessionManager->>MessageStorage: create_message(session_id, message)
    MessageStorage-->>SessionManager: success
    SessionManager->>EventBus: publish(SESSION_MESSAGE_CREATED)
    
    Note over User, EventBus: Add Part to Message
    User->>SessionManager: add_part(TextPart(...))
    SessionManager->>PartStorage: create_part(message_id, part)
    PartStorage-->>SessionManager: success
    SessionManager->>EventBus: publish(MESSAGE_PART_UPDATED)
    
    Note over User, EventBus: List Messages
    User->>SessionManager: list_messages(session_id)
    SessionManager->>MessageStorage: list_messages(session_id)
    MessageStorage-->>SessionManager: [message1, message2, ...]
    
    Note over User, EventBus: Load Part for Message
    User->>PartStorage: list_parts(message_id)
    PartStorage-->>User: [part1, part2, ...]
    
    Note over User, EventBus: Get Session Export
    User->>SessionManager: get_export_data(session_id)
    SessionManager->>SessionStorage: get_session(session_id)
    SessionManager->>MessageStorage: list_messages(session_id)
    SessionManager-->>User: {session, messages: [...]}
```

---

## PR Review Workflow

### Multi-Subagent PR Review

```mermaid
flowchart TD
    Start([Start PR Review]) --> Input[Receive PR<br/>changed_files, diff, refs]
    
    Input --> Parse[Parse Diff<br/>Identify changes]
    Parse --> Summarize[Summarize Change Intent]
    Summarize --> RiskAssess[Assess Risk Level]
    
    RiskAssess --> Subagents[Execute Required Subagents]
    
    Subagents --> Architecture[Architecture Review Agent]
    Subagents --> Security[Security Review Agent]
    Subagents --> Documentation[Documentation Review Agent]
    Subagents --> Telemetry[Telemetry/Metrics Review Agent]
    Subagents --> Linting[Linting Review Agent]
    Subagents --> UnitTests[Unit Tests Review Agent]
    
    Architecture --> Findings1[Generate Findings]
    Security --> Findings2[Generate Findings]
    Documentation --> Findings3[Generate Findings]
    Telemetry --> Findings4[Generate Findings]
    Linting --> Findings5[Generate Findings]
    UnitTests --> Findings6[Generate Findings]
    
    Findings1 --> Aggregate[Aggregate Results]
    Findings2 --> Aggregate
    Findings3 --> Aggregate
    Findings4 --> Aggregate
    Findings5 --> Aggregate
    Findings6 --> Aggregate
    
    Aggregate --> ToolPlan[Generate Tool Plan]
    Aggregate --> Dedupe[Dedupe & Merge Findings]
    
    ToolPlan --> MergeGate[Apply Merge Gate Policy]
    Dedupe --> MergeGate
    
    MergeGate --> Decision[Generate Final Decision]
    
    Decision --> Approved{Approve?}
    
    Approved -->|approve| Success([Merge Approved])
    Approved -->|approve_with_warnings| Warning([Merge Approved<br/>with warnings])
    Approved -->|merge_with_warnings| MergeWarn([Merge with Warnings<br/>Review required])
    Approved -->|needs_changes| Failed([Needs Changes<br/>Before merge])
    Approved -->|block| Blocked([Blocked<br/>Critical issues])
    
    style Start fill:#90EE90
    style Success fill:#90EE90
    style Warning fill:#FFD700
    style MergeWarn fill:#FFA500
    style Failed fill:#FF6B6B
    style Blocked fill:#FF0000
```

### PR Review Sequence Diagram

```mermaid
sequenceDiagram
    participant User
    participant Orchestrator
    participant BaseReviewAgent
    participant ArchitectureAgent
    participant SecurityAgent
    participant DocumentationAgent
    participant LintingAgent
    participant UnitTestsAgent

    User->>Orchestrator: review_pr(changed_files, diff, repo_root, refs)
    
    Orchestrator->>Orchestrator: parse_diff()
    Orchestrator->>Orchestrator: identify_change_intent()
    Orchestrator->>Orchestrator: assess_risk_level()
    
    Orchestrator->>ArchitectureAgent: review()
    ArchitectureAgent->>ArchitectureAgent: scope_review()
    ArchitectureAgent->>ArchitectureAgent: run_checks()
    ArchitectureAgent->>ArchitectureAgent: generate_findings()
    ArchitectureAgent->>ArchitectureAgent: make_merge_gate_decision()
    ArchitectureAgent-->>Orchestrator: ReviewOutput
    
    Orchestrator->>SecurityAgent: review()
    SecurityAgent-->>Orchestrator: ReviewOutput
    
    Orchestrator->>DocumentationAgent: review()
    DocumentationAgent-->>Orchestrator: ReviewOutput
    
    Orchestrator->>LintingAgent: review()
    LintingAgent-->>Orchestrator: ReviewOutput
    
    Orchestrator->>UnitTestsAgent: review()
    UnitTestsAgent-->>Orchestrator: ReviewOutput
    
    Orchestrator->>Orchestrator: aggregate_results()
    Orchestrator->>Orchestrator: dedupe_findings()
    Orchestrator->>Orchestrator: generate_tool_plan()
    Orchestrator->>Orchestrator: apply_merge_gate_policy()
    
    Orchestrator-->>User: OrchestratorOutput
    Note right of User
        Contains:
        - Summary
        - Tool Plan
        - Rollup
        - Findings
        - Merge Gate
    end Note
```

---

## Storage Hierarchy

### File System Structure

```mermaid
graph LR
    Storage[Storage Base Directory<br/>/path/to/storage]
    
    Storage --> Sessions[sessions.json]
    
    Storage --> Messages[messages/]
    Messages --> Session1[session_id_1/]
    Messages --> Session2[session_id_2/]
    Messages --> Session3[session_id_3/]
    
    Session1 --> Msg1[msg_id_1.json]
    Session1 --> Msg2[msg_id_2.json]
    Session1 --> Msg3[msg_id_3.json]
    
    Session2 --> Msg4[msg_id_4.json]
    Session2 --> Msg5[msg_id_5.json]
    
    Storage --> Parts[parts/]
    Parts --> Msg1Parts[msg_id_1/]
    Parts --> Msg2Parts[msg_id_2/]
    Parts --> Msg3Parts[msg_id_3/]
    Parts --> Msg4Parts[msg_id_4/]
    
    Msg1Parts --> Part1[part_id_1.json]
    Msg1Parts --> Part2[part_id_2.json]
    Msg1Parts --> Part3[part_id_3.json]
    
    Msg2Parts --> Part4[part_id_4.json]
    
    style Storage fill:#e1f5ff
    style Sessions fill:#f3e5f5
    style Messages fill:#fff4e1
    style Parts fill:#ffe1f5
```

### Data Flow

```mermaid
graph TB
    subgraph "Application"
        SessionManager[Session Manager]
    end
    
    subgraph "Storage"
        SessionStorage[Session Storage]
        MessageStorage[Message Storage]
        PartStorage[Part Storage]
    end
    
    subgraph "Files"
        SessionsFile[sessions.json]
        MessagesDir[messages/]
        PartsDir[parts/]
        MessageFiles[msg_*.json]
        PartFiles[part_*.json]
    end
    
    SessionManager -->|create/update| SessionStorage
    SessionManager -->|read| SessionStorage
    
    SessionStorage -->|JSON| SessionsFile
    
    SessionManager -->|create/list/delete| MessageStorage
    MessageStorage -->|JSON| MessagesDir
    MessagesDir --> MessageFiles
    
    SessionManager -->|create/list| PartStorage
    PartStorage -->|JSON| PartsDir
    PartsDir --> PartFiles
    
    style SessionManager fill:#e1f5ff
    style SessionStorage fill:#f3e5f5
    style MessageStorage fill:#fff4e1
    style PartStorage fill:#ffe1f5
```

---

## Event-Driven Architecture

### Event Flow

```mermaid
graph TB
    subgraph "Event Emitters"
        AgentManager[Agent Manager]
        SessionManager[Session Manager]
        ToolExecutor[Tool Executor]
        TaskManager[Task Manager]
    end
    
    subgraph "Event Bus"
        EventBus[Event Bus]
    end
    
    subgraph "Event Subscribers"
        Logger[Logger]
        Metrics[Metrics Collector]
        UI[UI Components]
        Notifications[Notifications]
        Analytics[Analytics]
    end
    
    AgentManager -->|publish| EventBus
    SessionManager -->|publish| EventBus
    ToolExecutor -->|publish| EventBus
    TaskManager -->|publish| EventBus
    
    EventBus -->|subscribe| Logger
    EventBus -->|subscribe| Metrics
    EventBus -->|subscribe| UI
    EventBus -->|subscribe| Notifications
    EventBus -->|subscribe| Analytics
    
    style EventBus fill:#f3e5f5
    stroke-width 4px
```

### Event Types and Flow

```mermaid
sequenceDiagram
    participant Emitter
    participant EventBus
    participant Subscriber1
    participant Subscriber2
    participant Subscriber3

    Emitter->>EventBus: publish("agent.ready", {session_id, agent_name})
    
    par Broadcast to Subscribers
        EventBus->>Subscriber1: callback(Event)
        and
        EventBus->>Subscriber2: callback(Event)
        and
        EventBus->>Subscriber3: callback(Event)
    end
    
    Subscriber1-->>EventBus: success
    Subscriber2-->>EventBus: error (logged)
    Subscriber3-->>EventBus: success
    
    EventBus-->>Emitter: publish complete
```

### Event Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Published: emit(event_name, data)
    Published --> Dispatching: Get subscribers
    Dispatching --> Notifying: For each subscriber
    Notifying --> Executing: Call callback
    Executing --> Completed: Success
    Executing --> ErrorLogged: Exception
    ErrorLogged --> Notifying: Continue
    Completed --> Notifying: Next subscriber
    Notifying --> Done: All subscribers processed
    Done --> [*]
```

---

## Permission System

### Permission Evaluation Flow

```mermaid
flowchart TD
    Start([Check Tool Permission]) --> Input[Get tool_name and permissions]
    Input --> Iterate{For each permission rule}
    
    Iterate -->|Next Rule| Evaluate{Pattern Match?}
    
    Evaluate -->|Yes| CheckAction{Action Type?}
    Evaluate -->|No| Iterate
    
    CheckAction -->|deny| Deny[Deny Access<br/>return False]
    CheckAction -->|allow| Allow[Allow Access<br/>return True]
    
    Deny --> End([Permission Denied])
    Allow --> End([Permission Granted])
    
    Iterate -->|No more rules| Default{Default Action?}
    Default -->|allow| End
    Default -->|deny| Deny
    
    style Deny fill:#FF6B6B
    style Allow fill:#90EE90
    style End fill:#90EE90
```

### Agent-Tool Permission Matrix

```mermaid
graph TB
    subgraph "Agents"
        BuildAgent[Build Agent<br/>Mode: primary]
        PlanAgent[Plan Agent<br/>Mode: primary]
        GeneralAgent[General Agent<br/>Mode: subagent]
        ExploreAgent[Explore Agent<br/>Mode: subagent]
    end
    
    subgraph "Tools"
        Bash[bash]
        Read[read]
        Write[write]
        Edit[edit]
        Glob[glob]
        Grep[grep]
        Webfetch[webfetch]
        Websearch[websearch]
        Codesearch[codesearch]
        TodoRead[todoread]
        TodoWrite[todowrite]
    end
    
    BuildAgent -->|✓ Allow| Bash
    BuildAgent -->|✓ Allow| Read
    BuildAgent -->|✓ Allow| Write
    BuildAgent -->|✓ Allow| Edit
    BuildAgent -->|✓ Allow| Glob
    BuildAgent -->|✓ Allow| Grep
    BuildAgent -->|✓ Allow| Webfetch
    BuildAgent -->|✓ Allow| Websearch
    BuildAgent -->|✓ Allow| Codesearch
    BuildAgent -->|✓ Allow| TodoRead
    BuildAgent -->|✓ Allow| TodoWrite
    
    PlanAgent -->|✓ Allow| Bash
    PlanAgent -->|✓ Allow| Read
    PlanAgent -->|✗ Deny| Write
    PlanAgent -->|✗ Deny| Edit
    PlanAgent -->|✓ Allow| Glob
    PlanAgent -->|✓ Allow| Grep
    PlanAgent -->|✓ Allow| Webfetch
    PlanAgent -->|✓ Allow| Websearch
    PlanAgent -->|✓ Allow| Codesearch
    PlanAgent -->|✓ Allow| TodoRead
    PlanAgent -->|✓ Allow| TodoWrite
    
    GeneralAgent -->|✓ Allow| Bash
    GeneralAgent -->|✓ Allow| Read
    GeneralAgent -->|✓ Allow| Write
    GeneralAgent -->|✓ Allow| Edit
    GeneralAgent -->|✓ Allow| Glob
    GeneralAgent -->|✓ Allow| Grep
    GeneralAgent -->|✓ Allow| Webfetch
    GeneralAgent -->|✓ Allow| Websearch
    GeneralAgent -->|✓ Allow| Codesearch
    GeneralAgent -->|✗ Deny| TodoRead
    GeneralAgent -->|✗ Deny| TodoWrite
    
    ExploreAgent -->|✓ Allow| Bash
    ExploreAgent -->|✓ Allow| Read
    ExploreAgent -->|✗ Deny| Write
    ExploreAgent -->|✗ Deny| Edit
    ExploreAgent -->|✓ Allow| Glob
    ExploreAgent -->|✓ Allow| Grep
    ExploreAgent -->|✓ Allow| Webfetch
    ExploreAgent -->|✓ Allow| Websearch
    ExploreAgent -->|✓ Allow| Codesearch
    ExploreAgent -->|✗ Deny| TodoRead
    ExploreAgent -->|✗ Deny| TodoWrite
    
    style BuildAgent fill:#90EE90
    style PlanAgent fill:#FFD700
    style GeneralAgent fill:#87CEEB
    style ExploreAgent fill:#DDA0DD
```

---

## Multi-Agent Orchestration

### Agent Delegation Flow

```mermaid
sequenceDiagram
    participant User
    participant PrimaryAgent[Primary Agent<br/>build/plan]
    participant AgentExecutor
    participant TaskTool[Task Tool]
    participant Subagent1[Subagent 1<br/>explore]
    participant Subagent2[Subagent 2<br/>general]
    participant EventBus

    User->>PrimaryAgent: User request
    PrimaryAgent->>TaskTool: Task(delegate_task(...))
    
    TaskTool->>AgentExecutor: execute_agent("explore", ...)
    
    par Parallel Execution
        AgentExecutor->>Subagent1: execute()
        Subagent1->>EventBus: publish(AGENT_EXECUTING)
        Subagent1->>Subagent1: perform task
        Subagent1->>EventBus: publish(AGENT_CLEANUP)
        Subagent1-->>AgentExecutor: result1
    and
        AgentExecutor->>Subagent2: execute()
        Subagent2->>EventBus: publish(AGENT_EXECUTING)
        Subagent2->>Subagent2: perform task
        Subagent2->>EventBus: publish(AGENT_CLEANUP)
        Subagent2-->>AgentExecutor: result2
    end
    
    AgentExecutor->>TaskTool: return results
    TaskTool->>PrimaryAgent: return results
    PrimaryAgent->>PrimaryAgent: aggregate and process
    PrimaryAgent-->>User: Final response
```

### Agent Interaction Patterns

```mermaid
graph TB
    subgraph "User Request"
        Request[Complex User Request]
    end
    
    subgraph "Primary Agent"
        Primary[Primary Agent<br/>Decomposes task]
    end
    
    subgraph "Subagent Pool"
        Explore[Explore Agent<br/>Codebase search]
        General[General Agent<br/>Multi-step tasks]
        Oracle[Oracle Agent<br/>Architecture/Debugging]
        Librarian[Librarian Agent<br/>External research]
    end
    
    subgraph "Tool Execution"
        ToolRegistry[Tool Registry]
        Tools[23 Tools]
    end
    
    Request --> Primary
    
    Primary -->|delegate| Explore
    Primary -->|delegate| General
    Primary -->|consult| Oracle
    Primary -->|research| Librarian
    
    Explore --> ToolRegistry
    General --> ToolRegistry
    Oracle --> ToolRegistry
    Librarian --> ToolRegistry
    
    ToolRegistry --> Tools
    
    Explore -->|results| Primary
    General -->|results| Primary
    Oracle -->|analysis| Primary
    Librarian -->|research| Primary
    
    Primary -->|final response| Request
    
    style Primary fill:#e1f5ff
    style Explore fill:#f3e5f5
    style General fill:#fff4e1
    style Oracle fill:#ffe1f5
    style Librarian fill:#f0e1ff
```

---

## Data Models

### Message Part Types

```mermaid
graph TB
    Message[Message]
    
    Message --> TextPart[TextPart<br/>Plain text content]
    Message --> FilePart[FilePart<br/>File attachments]
    Message --> ToolPart[ToolPart<br/>Tool execution results]
    Message --> ReasoningPart[ReasoningPart<br/>LLM thinking process]
    Message --> SnapshotPart[SnapshotPart<br/>Git snapshots]
    Message --> PatchPart[PatchPart<br/>File patch summaries]
    Message --> AgentPart[AgentPart<br/>Agent delegation]
    Message --> SubtaskPart[SubtaskPart<br/>Subtask invocation]
    Message --> RetryPart[RetryPart<br/>Retry attempts]
    Message --> CompactionPart[CompactionPart<br/>Session compaction marker]
    
    style TextPart fill:#90EE90
    style FilePart fill:#87CEEB
    style ToolPart fill:#FFD700
    style ReasoningPart fill:#DDA0DD
    style SnapshotPart fill:#FFA500
    style PatchPart fill:#F08080
    style AgentPart fill:#20B2AA
    style SubtaskPart fill:#9370DB
    style RetryPart fill:#FF6347
    style CompactionPart fill:#708090
```

---

## Summary

The OpenCode Python SDK follows a modular, event-driven architecture with clear separation of concerns:

- **Application Layer**: User-facing applications and orchestrators
- **Agent Layer**: Built-in and custom agents for different tasks
- **Tool Layer**: Extensible tool system with permission-based access
- **Core Layer**: Session management, event bus, and agent lifecycle
- **Storage Layer**: JSON-based persistence for all data
- **Models**: Type-safe Pydantic models for all data structures

Key features:
- **Async-first design** for concurrent operations
- **Event-driven communication** for loose coupling
- **Permission-based access control** for security
- **Multi-agent orchestration** for complex tasks
- **Modular tool system** with 23 built-in tools
- **PR Review system** with specialized subagents
