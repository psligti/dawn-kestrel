# Plan: Fix Python SDK Issues

**Created**: 2026-01-30
**Status**: Ready for implementation
**Based on**: SDK_GAPS_AND_NEXT_STEPS.md analysis + comprehensive codebase exploration

---

## TL;DR

Fix **3 critical bugs** blocking SDK functionality, then implement **6 missing core features**:

**Critical Fixes** (must do first):
1. Fix `SessionStorage()` initialization in SDK client
2. Fix `AgentExecutor` fake Session objects
3. Fix `ToolExecutionManager` empty tool_registry

**Core Features** (after bugs fixed):
4. Agent Registry - Register custom agents
5. Skill Injection - Inject skills into system prompts
6. Context Builder - Public API for building agent context

**Future Phases** (documented but not in this plan):
- Memory System
- Multi-Agent Orchestration
- Tool Execution History Storage

---

## Execution Strategy

### Wave 1: Critical Bug Fixes (Week 1)
**Goal**: Unblock all SDK usage by fixing runtime errors

| Task | Depends On | Files |
|------|------------|--------|
| 1. Fix SessionStorage init | None | sdk/client.py |
| 2. Fix AgentExecutor Session objects | None | agents/__init__.py |
| 3. Fix ToolExecutionManager tool_registry | None | ai_session.py, agents/__init__.py |

**Critical Path**: Task 1 → Task 2 → Task 3

---

### Wave 2: Agent Registry (Week 2)
**Goal**: Enable custom agent registration and retrieval

| Task | Depends On | Files |
|------|------------|--------|
| 4. Create AgentRegistry class | None | agents/registry.py |
| 5. Add register_agent to SDK client | None | sdk/client.py |
| 6. Add get_agent/list_agents to SDK client | None | sdk/client.py |
| 7. Integrate AgentRegistry with AgentManager | Task 4 | agents/__init__.py |

**Critical Path**: Task 4 → Task 5,6 → Task 7

---

### Wave 3: Skill Injection (Week 3)
**Goal**: Automatically inject skills into agent system prompts

| Task | Depends On | Files |
|------|------------|--------|
| 8. Create SkillInjector class | None | skills/injector.py |
| 9. Modify AISession to use SkillInjector | Task 8 | ai_session.py |
| 10. Add skill discovery to agent execution | Task 8 | agents/__init__.py |

**Critical Path**: Task 8 → Task 9 → Task 10

---

### Wave 4: Context Builder (Week 4)
**Goal**: Expose internal context building as public API

| Task | Depends On | Files |
|------|------------|--------|
| 11. Create ContextBuilder class | None | context/builder.py |
| 12. Integrate with AISession | Task 11 | ai_session.py |
| 13. Add to SDK client API | Task 11,12 | sdk/client.py |

**Critical Path**: Task 11 → Task 12 → Task 13

**Parallel Speedup**: ~30% (independent components)

---

## Detailed TODOs

---

### WAVE 1: CRITICAL BUG FIXES

#### Task 1: Fix SessionStorage initialization in SDK client

**What to do**:
Fix `OpenCodeAsyncClient.__init__()` to pass `base_dir` to `SessionStorage`

**Location**: `opencode_python/src/opencode_python/sdk/client.py:53`

**Current Code**:
```python
storage = SessionStorage()  # ❌ TypeError - missing base_dir
project_dir = self.config.project_dir or Path.cwd()
```

**New Code**:
```python
from opencode_python.core.settings import get_storage_dir

storage_dir = self.config.storage_path or get_storage_dir()
storage = SessionStorage(storage_dir)
project_dir = self.config.project_dir or Path.cwd()
```

**Why This Fix**:
- `SessionStorage.__init__` requires `base_dir: Path` parameter
- `SDKConfig.storage_path` is defined but never used
- `get_storage_dir()` provides default `~/.local/share/opencode-python`
- Aligns with CLI/TUI initialization patterns

**References**:
- `opencode_python/core/settings.py:50-55` - get_storage_dir() function
- `opencode_python/core/config.py:40` - storage_path in SDKConfig
- `opencode_python/cli/main.py:53` - Correct pattern example
- `custom_agent_app_example.py:338-341` - Example workaround

**Acceptance Criteria**:
- [ ] SDK client can be instantiated without TypeError
- [ ] SessionStorage is created with valid base_dir
- [ ] storage_path from config is respected when provided
- [ ] Falls back to get_storage_dir() when storage_path is None

**Verification**:
```python
# Test in test_sdk_async_client.py
async def test_client_initialization():
    client = OpenCodeAsyncClient()
    assert client._service.storage is not None
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 2: Fix AgentExecutor fake Session objects

**What to do**:
Modify `AgentExecutor.execute_agent()` to use real Session from storage or accept Session object

**Location**: `opencode_python/src/opencode_python/agents/__init__.py:190-198, 232-240`

**Current Code**:
```python
session = Session(
    id=session_id,
    slug=session_id,
    project_id="",  # ❌ Empty
    directory="",   # ❌ Empty
    title="",      # ❌ Empty
    version="1.0",
    metadata={}
)
```

**New Code** (Option 1 - Accept Session object):
```python
async def execute_agent(
    self,
    agent_name: str,
    user_message: str,
    session: Session,  # ← Accept Session object, not session_id
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # Use real session directly
    await self.agent_manager.initialize_agent(agent, session)

    result = await self._run_agent_logic(agent, user_message, session, options)

    await self.agent_manager.cleanup_agent(session.id)
    return result
```

**OR** (Option 2 - Fetch from session_manager):
```python
async def execute_agent(
    self,
    agent_name: str,
    user_message: str,
    session_id: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    # Fetch real session from storage
    session = await self.session_manager.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    await self.agent_manager.initialize_agent(agent, session)
    result = await self._run_agent_logic(agent, user_message, session, options)
    await self.agent_manager.cleanup_agent(session.id)
    return result
```

**Why This Fix**:
- Session metadata (project_id, directory, title) is preserved
- Integrates with actual session storage
- Enables context-aware agent execution

**References**:
- `opencode_python/core/services/session_service.py` - SessionService interface
- `opencode_python/storage/store.py:77-114` - SessionStorage.get_session()

**Acceptance Criteria**:
- [ ] execute_agent() uses real Session object
- [ ] Session metadata (project_id, directory, title) is preserved
- [ ] Integration with session storage works
- [ ] No more empty Session fields

**Verification**:
```python
async def test_agent_executor_real_session():
    executor = AgentExecutor(session_manager=mock_session_manager)
    agent = get_agent_by_name("build")

    # Create a real session
    session = Session(
        id="test_id",
        slug="test_id",
        project_id="test_project",
        directory="/test/dir",
        title="Test Session",
        version="1.0",
        metadata={}
    )

    result = await executor.execute_agent("build", "test", session)

    # Verify session metadata is used
    assert result.get("session_project_id") == "test_project"
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 3: Fix ToolExecutionManager empty tool_registry

**What to do**:
Modify `ToolExecutionManager` to accept pre-populated ToolRegistry or import from tools/registry

**Location**: Multiple files:
- `opencode_python/src/opencode_python/ai/tool_execution.py:26` - ToolExecutionManager.__init__
- `opencode_python/src/opencode_python/ai_session.py:46` - AISession creates ToolExecutionManager
- `opencode_python/src/opencode_python/agents/__init__.py:158` - AgentExecutor receives tool_manager

**Current Code** (tool_execution.py:26):
```python
def __init__(self, session_id: str):
    self.session_id = session_id
    self.active_calls: Dict[str, ToolContext] = {}
    self.tool_registry = ToolRegistry()  # ❌ Creates EMPTY registry
```

**New Code** (Option 1 - Accept ToolRegistry parameter):
```python
def __init__(self, session_id: str, tool_registry: ToolRegistry = None):
    self.session_id = session_id
    self.active_calls: Dict[str, ToolContext] = {}
    self.tool_registry = tool_registry or ToolRegistry()  # Accept external registry
```

**New Code** (Option 2 - Import pre-populated registry):
```python
from opencode_python.tools.registry import create_complete_registry

class ToolExecutionManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.active_calls: Dict[str, ToolContext] = {}
        # Use pre-populated registry with all 23 tools
        self.tool_registry = create_complete_registry()
```

**Update AISession** (ai_session.py:46):
```python
from opencode_python.tools.registry import create_complete_registry

def __init__(
    self,
    session: Session,
    provider_id: str,
    model: str,
    api_key: Optional[str] = None,
    session_manager=None
):
    # ...
    # Create ToolExecutionManager with pre-populated registry
    tool_registry = await create_complete_registry()
    self.tool_manager = ToolExecutionManager(session.id, tool_registry)
    # ...
```

**Why This Fix**:
- `tools/registry.ToolRegistry` pre-populates all 23 tools in __init__
- Current code creates empty registry, causing tool lookups to fail
- Aligns with existing tool infrastructure

**References**:
- `opencode_python/src/opencode_python/tools/registry.py:46-77` - Pre-populated ToolRegistry
- `opencode_python/src/opencode_python/tools/__init__.py:39-72` - create_complete_registry()
- `opencode_python/src/opencode_python/tools/framework.py:16-34` - ToolRegistry interface

**Acceptance Criteria**:
- [ ] ToolExecutionManager has access to all 23 tools
- [ ] AISession._get_tool_definitions() returns non-empty dict
- [ ] Tool lookups succeed (no "tool not found" errors)
- [ ] AgentExecutor._filter_tools_for_agent() works without AttributeError

**Verification**:
```python
async def test_tool_registry_populated():
    tool_registry = await create_complete_registry()
    assert len(tool_registry.tools) == 23  # All tools present

    manager = ToolExecutionManager("test_id", tool_registry)
    bash_tool = manager.tool_registry.get("bash")
    assert bash_tool is not None
```

**Parallelization**:
- **Task 3a**: Modify ToolExecutionManager.__init__ - Independent
- **Task 3b**: Update AISession - Depends on 3a

---

### WAVE 2: AGENT REGISTRY

#### Task 4: Create AgentRegistry class

**What to do**:
Create new `AgentRegistry` class for managing custom agent definitions

**Location**: `opencode_python/src/opencode_python/agents/registry.py` (NEW FILE)

**New File**: `agents/registry.py`
```python
"""
Agent Registry - Manage custom agent definitions
"""
from __future__ import annotations
from typing import Dict, List, Optional
import logging

from .builtin import Agent, get_agent_by_name as get_builtin_agent


logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for custom and built-in agents"""

    def __init__(self) -> None:
        self._custom_agents: Dict[str, Agent] = {}
        self._builtin_agents = get_all_builtin_agents()

    async def register_agent(self, agent: Agent) -> None:
        """Register a custom agent

        Args:
            agent: Agent definition to register

        Raises:
            ValueError: If agent with same name already exists
        """
        name = agent.name.lower()
        if name in self._custom_agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        if name in self._builtin_agents:
            raise ValueError(f"Cannot override built-in agent '{agent.name}'")

        self._custom_agents[name] = agent
        logger.info(f"Registered custom agent: {agent.name}")

    async def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name (case-insensitive)

        Args:
            name: Agent name to retrieve

        Returns:
            Agent object or None if not found
        """
        name_lower = name.lower()

        # Check custom agents first
        if name_lower in self._custom_agents:
            return self._custom_agents[name_lower]

        # Check built-in agents
        if name_lower in self._builtin_agents:
            return self._builtin_agents[name_lower]

        return None

    async def list_agents(self) -> List[Agent]:
        """List all available agents (custom + built-in)

        Returns:
            List of all registered agents
        """
        # Combine custom and built-in agents
        # Custom agents override built-ins with same name (checked at registration)
        all_agents = dict(self._builtin_agents)
        all_agents.update(self._custom_agents)
        return list(all_agents.values())

    async def remove_agent(self, name: str) -> bool:
        """Remove a custom agent

        Args:
            name: Agent name to remove

        Returns:
            True if removed, False if not found (built-in)
        """
        name_lower = name.lower()

        if name_lower in self._custom_agents:
            del self._custom_agents[name_lower]
            logger.info(f"Removed custom agent: {name}")
            return True

        # Cannot remove built-in agents
        if name_lower in self._builtin_agents:
            logger.warning(f"Cannot remove built-in agent: {name}")
            return False

        return False


def get_all_builtin_agents() -> Dict[str, Agent]:
    """Get all built-in agents by name

    Returns:
        Dict mapping lowercase names to Agent objects
    """
    from .builtin import get_all_agents
    agents = get_all_agents()
    return {agent.name.lower(): agent for agent in agents}


def create_agent_registry() -> AgentRegistry:
    """Factory function to create AgentRegistry"""
    return AgentRegistry()


__all__ = [
    "AgentRegistry",
    "create_agent_registry",
]
```

**Why This Class**:
- Enables registration of custom agents beyond built-ins
- Prevents overriding built-in agents
- Provides unified access to all agents
- Supports removal of custom agents

**Acceptance Criteria**:
- [ ] AgentRegistry class created
- [ ] register_agent() prevents duplicate names
- [ ] register_agent() prevents overriding built-ins
- [ ] get_agent() finds both custom and built-in agents
- [ ] list_agents() returns combined list
- [ ] remove_agent() works for custom agents only

**Verification**:
```python
async def test_agent_registry():
    registry = create_agent_registry()

    custom_agent = Agent(
        name="custom_bot",
        description="Custom test agent",
        mode="subagent",
        permission=[{"permission": "*", "pattern": "*", "action": "allow"}]
    )

    await registry.register_agent(custom_agent)

    # Should find custom agent
    agent = await registry.get_agent("custom_bot")
    assert agent.name == "custom_bot"

    # Should still find built-in
    build_agent = await registry.get_agent("build")
    assert build_agent is not None

    # Cannot override built-in
    try:
        await registry.register_agent(build_agent)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 5: Add agent registration to SDK client

**What to do**:
Add `register_agent()` method to `OpenCodeAsyncClient` and `OpenCodeSyncClient`

**Location**: `opencode_python/src/opencode_python/sdk/client.py`

**New Code** (client.py - add after create_session method):
```python
from opencode_python.agents.registry import create_agent_registry
from opencode_python.agents.builtin import Agent

class OpenCodeAsyncClient:
    def __init__(
        self,
        config: Optional[SDKConfig] = None,
        io_handler: Optional[Any] = None,
        progress_handler: Optional[Any] = None,
        notification_handler: Optional[Any] = None,
    ):
        # ... existing code ...

        # Fix Task 1: Pass base_dir to SessionStorage
        storage_dir = self.config.storage_path or get_storage_dir()
        storage = SessionStorage(storage_dir)
        project_dir = self.config.project_dir or Path.cwd()

        self._service = DefaultSessionService(
            storage=storage,
            project_dir=project_dir,
            io_handler=io_handler,
            progress_handler=progress_handler,
            notification_handler=notification_handler,
        )

        # NEW: Initialize agent registry
        self._agent_registry = create_agent_registry()

    # ... existing methods ...

    async def register_agent(self, agent: Agent) -> None:
        """Register a custom agent

        Args:
            agent: Agent definition to register

        Raises:
            ValueError: If agent with same name already exists
            SessionError: If registration fails
        """
        try:
            await self._agent_registry.register_agent(agent)
        except ValueError as e:
            raise SessionError(f"Failed to register agent: {e}") from e

    async def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name

        Args:
            name: Agent name to retrieve

        Returns:
            Agent object or None if not found
        """
        try:
            return await self._agent_registry.get_agent(name)
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to get agent: {e}") from e

    async def list_agents(self) -> list[Agent]:
        """List all available agents (custom + built-in)

        Returns:
            List of all registered agents
        """
        try:
            return await self._agent_registry.list_agents()
        except Exception as e:
            if isinstance(e, OpenCodeError):
                raise
            raise SessionError(f"Failed to list agents: {e}") from e
```

**Also update `OpenCodeSyncClient`** (client.py - sync wrapper):
```python
class OpenCodeSyncClient:
    def __init__(self, config: Optional[SDKConfig] = None, ...):
        # ... existing code ...
        self._async_client = OpenCodeAsyncClient(config=config, ...)
        # Agent registry already initialized in async client

    def register_agent(self, agent: Agent) -> None:
        """Register a custom agent (sync wrapper)"""
        return asyncio.run(self._async_client.register_agent(agent))

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name (sync wrapper)"""
        return asyncio.run(self._async_client.get_agent(name))

    def list_agents(self) -> list[Agent]:
        """List all agents (sync wrapper)"""
        return asyncio.run(self._async_client.list_agents())
```

**References**:
- `opencode_python/agents/registry.py` - AgentRegistry class (Task 4)
- `opencode_python/agents/builtin.py:8-25` - Agent dataclass
- `custom_agent_app_example.py:148-172` - Custom agent definition example

**Acceptance Criteria**:
- [ ] OpenCodeAsyncClient has _agent_registry attribute
- [ ] register_agent() method exists and works
- [ ] get_agent() method exists and works
- [ ] list_agents() method exists and works
- [ ] OpenCodeSyncClient has sync wrappers

**Verification**:
```python
async def test_sdk_agent_registration():
    client = OpenCodeAsyncClient()

    # Register custom agent
    custom_agent = Agent(
        name="test_bot",
        description="Test agent",
        mode="subagent",
        permission=[]
    )

    await client.register_agent(custom_agent)

    # Retrieve it
    agent = await client.get_agent("test_bot")
    assert agent.name == "test_bot"

    # List all agents (custom + built-in)
    agents = await client.list_agents()
    assert len(agents) == 5  # 4 built-in + 1 custom
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 6: Integrate AgentRegistry with AgentManager

**What to do**:
Modify `AgentManager` to use `AgentRegistry` for agent lookups

**Location**: `opencode_python/src/opencode_python/agents/__init__.py`

**Current Code** (agents/__init__.py:129-135):
```python
async def get_all_agents(self) -> List[Agent]:
    """Get all available agents"""
    return get_all_agents()

async def get_agent_by_name(self, name: str) -> Optional[Agent]:
    """Get an agent by name (case-insensitive)"""
    return get_agent_by_name(name)
```

**New Code**:
```python
from opencode_python.agents.registry import create_agent_registry

class AgentManager:
    def __init__(self, session_storage=None, config=None):
        self.session_storage = session_storage
        self.config = config or {}
        self._active_sessions: Dict[str, AgentState] = {}
        self._agent_states: Dict[str, AgentState] = {}

        # NEW: Initialize agent registry
        self._agent_registry = create_agent_registry()

    async def initialize_agent(
        self,
        agent: Agent,
        session: Session
    ) -> AgentState:
        """Initialize an agent for a session

        Args:
            agent: Agent to initialize
            session: Session object

        Returns:
            AgentState with status="initializing"
        """
        agent_state = AgentState(
            session_id=session.id,
            agent_name=agent.name,
            status="initializing",
            time_started=None,
            time_finished=None,
            error=None,
            messages_count=0,
            tools_used=[]
        )

        self._agent_states[session.id] = agent_state

        await bus.publish(Events.AGENT_INITIALIZED, {
            "session_id": session.id,
            "agent_name": agent.name,
            "agent_mode": agent.mode
        })

        logger.info(f"Agent {agent.name} initialized for session {session.id}")

        return agent_state

    async def get_all_agents(self) -> List[Agent]:
        """Get all available agents (custom + built-in)

        Returns:
            List of all registered agents
        """
        return await self._agent_registry.list_agents()

    async def get_agent_by_name(self, name: str) -> Optional[Agent]:
        """Get an agent by name (case-insensitive)

        Args:
            name: Agent name to retrieve

        Returns:
            Agent object or None if not found
        """
        return await self._agent_registry.get_agent(name)
```

**Why This Change**:
- AgentManager now uses AgentRegistry for all agent lookups
- Supports both custom and built-in agents
- Provides unified agent discovery mechanism

**References**:
- `opencode_python/agents/registry.py` - AgentRegistry class (Task 4)
- `opencode_python/agents/__init__.py:129-149` - AgentManager class

**Acceptance Criteria**:
- [ ] AgentManager uses AgentRegistry
- [ ] get_all_agents() returns custom + built-in agents
- [ ] get_agent_by_name() checks AgentRegistry first
- [ ] Backward compatibility maintained (no breaking changes)

**Verification**:
```python
async def test_agent_manager_registry():
    storage = MockStorage()
    manager = AgentManager(session_storage=storage)

    # Should find both custom and built-in agents
    agents = await manager.get_all_agents()
    assert len(agents) == 4  # All built-in agents

    # Register custom agent
    custom_agent = Agent(
        name="custom_test",
        description="Custom agent",
        mode="subagent",
        permission=[]
    )

    await manager._agent_registry.register_agent(custom_agent)

    # Should find custom agent
    agent = await manager.get_agent_by_name("custom_test")
    assert agent.name == "custom_test"
```

**Parallelization**:
- Depends on Task 4 (AgentRegistry creation)

---

### WAVE 3: SKILL INJECTION

#### Task 8: Create SkillInjector class

**What to do**:
Create `SkillInjector` class to automatically inject skills into agent system prompts

**Location**: `opencode_python/src/opencode_python/skills/injector.py` (NEW FILE)

**New File**: `skills/injector.py`
```python
"""
Skill Injector - Inject loaded skills into agent system prompts
"""
from __future__ import annotations
from typing import List, Optional
import logging

from .loader import SkillLoader, Skill
from ..agents.builtin import Agent


logger = logging.getLogger(__name__)


class SkillInjector:
    """Inject skills into agent system prompts"""

    def __init__(self, base_dir):
        """Initialize skill loader

        Args:
            base_dir: Base directory for skill discovery
        """
        self.skill_loader = SkillLoader(base_dir)
        self._skill_cache: Optional[List[Skill]] = None

    async def load_skills(self) -> List[Skill]:
        """Load all available skills

        Returns:
            List of discovered skills
        """
        if self._skill_cache is None:
            self._skill_cache = self.skill_loader.discover_skills()
        return self._skill_cache

    async def get_relevant_skills(
        self,
        agent: Agent,
        query: Optional[str] = None
    ) -> List[Skill]:
        """Get skills relevant to agent or query

        Args:
            agent: Agent to check skill relevance for
            query: Optional query string for semantic matching

        Returns:
            List of relevant skills
        """
        skills = await self.load_skills()

        # Filter by agent relevance (could be enhanced)
        # For now, return all skills
        # TODO: Implement semantic matching based on agent description
        return skills

    def build_system_prompt(
        self,
        agent: Agent,
        skills: List[Skill]
    ) -> str:
        """Build system prompt with skills injected

        Args:
            agent: Agent to build prompt for
            skills: Skills to inject

        Returns:
            System prompt with skills section
        """
        base_prompt = agent.prompt or f"You are {agent.name}, an AI agent."

        if not skills:
            return base_prompt

        skills_section = "\n\nYou have access to the following skills:\n\n"
        for skill in skills:
            skills_section += f"- {skill.name}: {skill.description}\n"
            skills_section += f"  Content:\n{skill.content}\n\n"

        return base_prompt + skills_section


def create_skill_injector(base_dir) -> SkillInjector:
    """Factory function to create SkillInjector

    Args:
        base_dir: Base directory for skill discovery

    Returns:
        SkillInjector instance
    """
    return SkillInjector(base_dir)


__all__ = [
    "SkillInjector",
    "create_skill_injector",
]
```

**Why This Class**:
- Automatically loads skills from SKILL.md files
- Provides skill relevance filtering (extensible)
- Injects skills into system prompts in standard format
- Caches skills for performance

**References**:
- `opencode_python/skills/loader.py:32-137` - SkillLoader class
- `opencode_python/agents/builtin.py:22` - Agent.prompt field

**Acceptance Criteria**:
- [ ] SkillInjector class created
- [ ] load_skills() discovers all skills
- [ ] build_system_prompt() injects skills into agent prompt
- [ ] get_relevant_skills() provides filtering mechanism

**Verification**:
```python
async def test_skill_injector():
    injector = create_skill_injector(Path.cwd())

    skills = await injector.load_skills()
    assert len(skills) >= 0  # Should find some skills

    agent = Agent(
        name="test_agent",
        description="Test agent",
        mode="subagent",
        permission=[],
        prompt="You are a helpful assistant."
    )

    prompt = injector.build_system_prompt(agent, skills)

    assert "following skills:" in prompt
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 9: Modify AISession to use SkillInjector

**What to do**:
Integrate `SkillInjector` into `AISession` to automatically include skills in prompts

**Location**: `opencode_python/src/opencode_python/ai_session.py`

**New Code** (ai_session.py - modify __init__ and _build_llm_messages):
```python
from opencode_python.skills.injector import create_skill_injector
from opencode_python.agents.builtin import Agent

class AISession:
    def __init__(
        self,
        session: Session,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        session_manager=None,
        agent: Optional[Agent] = None  # NEW: Agent for skill injection
    ):
        self.session = session
        self.provider_id = provider_id
        self.model = model
        self.session_manager = session_manager
        self.agent = agent  # NEW

        api_key_value = api_key or settings.api_keys.get(provider_id)
        provider_enum = ProviderID(provider_id) if isinstance(provider_id, str) else provider_id
        self.provider = get_provider(provider_enum, str(api_key_value) if api_key_value else "")
        self.model_info: Optional[ModelInfo] = None
        self.tool_manager = ToolExecutionManager(session.id)

        # NEW: Initialize skill injector
        self._skill_injector = create_skill_injector(session.directory)

    async def _build_llm_messages(
        self,
        messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Build LLM-format messages from OpenCode messages

        Args:
            messages: List of OpenCode messages

        Returns:
            List of messages in LLM format
        """
        llm_messages = []

        # NEW: Build system prompt with skills
        if self.agent:
            skills = await self._skill_injector.load_skills()
            relevant_skills = await self._skill_injector.get_relevant_skills(self.agent)
            system_prompt = self._skill_injector.build_system_prompt(self.agent, relevant_skills)
            llm_messages.append({"role": "system", "content": system_prompt})

        for msg in messages:
            if msg.role == "user":
                content = msg.text or ""
                llm_messages.append({"role": "user", "content": content})
            elif msg.role == "assistant":
                content: str = ""
                for part in msg.parts:
                    if isinstance(part, TextPart) and hasattr(part, "text"):
                        content += part.text
                llm_messages.append({"role": "assistant", "content": content})

        return llm_messages
```

**Also update AgentExecutor** (agents/__init__.py - modify _run_agent_logic):
```python
async def _run_agent_logic(
    self,
    agent,
    user_message: str,
    session_id: str,
    options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    await self.agent_manager.set_agent_executing(session_id)

    tools = self._filter_tools_for_agent(agent)

    try:
        from opencode_python.ai_session import AISession
        from opencode_python.core.models import Session

        # NEW: Pass agent to AISession for skill injection
        ai_session = AISession(
            session=session,
            provider_id=options.get("provider", "anthropic") if options else "anthropic",
            model=options.get("model", "claude-sonnet-4-20250514") if options else "claude-sonnet-4-20250514",
            session_manager=self.session_manager,
            agent=agent  # NEW
        )

        response = await ai_session.process_message(
            user_message=user_message,
            options={
                "temperature": agent.temperature,
                "top_p": agent.top_p
            }
        )

        return {
            "response": response.text or "",
            "parts": response.parts or [],
            "agent": agent.name,
            "status": "completed",
            "metadata": response.metadata or {}
        }

    except Exception as e:
        logger.error(f"Agent execution failed: {e}")
        await self.agent_manager.set_agent_error(session_id, str(e))

        return {
            "response": f"Error: {str(e)}",
            "parts": [],
            "agent": agent.name,
            "status": "error",
            "metadata": {"error": str(e)}
        }
```

**Why This Change**:
- Skills are automatically loaded from SKILL.md files
- Skills are injected into system prompts
- No need for manual skill tool calls
- Agent.prompt field is now used

**References**:
- `opencode_python/skills/injector.py` - SkillInjector class (Task 8)
- `opencode_python/skills/loader.py` - SkillLoader class
- `opencode_python/agents/builtin.py:22` - Agent.prompt field

**Acceptance Criteria**:
- [ ] AISession accepts agent parameter
- [ ] AISession initializes SkillInjector
- [ ] _build_llm_messages() adds system message with skills
- [ ] AgentExecutor passes agent to AISession
- [ ] Skills are automatically injected (no manual tool calls needed)

**Verification**:
```python
async def test_skill_injection():
    # Create test session
    session = Session(
        id="test_session",
        slug="test_session",
        project_id="test_project",
        directory="/test/dir",
        title="Test Session",
        version="1.0",
        metadata={}
    )

    agent = Agent(
        name="test_agent",
        description="Test agent",
        mode="subagent",
        permission=[],
        prompt="You are a test assistant."
    )

    ai_session = AISession(
        session=session,
        provider_id="anthropic",
        model="claude-sonnet-4-20250514",
        agent=agent  # NEW
    )

    messages = await ai_session._build_llm_messages([])
    system_messages = [m for m in messages if m["role"] == "system"]

    assert len(system_messages) == 1
    assert "following skills:" in system_messages[0]["content"]
```

**Parallelization**:
- Task 9a: Modify AISession - Depends on Task 8
- Task 9b: Modify AgentExecutor - Depends on Task 8, 9a

---

#### Task 10: Add skill discovery to agent execution

**What to do**:
Integrate skill loading and injection into agent execution flow

**Location**: `opencode_python/src/opencode_python/agents/__init__.py`

**Already Done**: Task 9b (AgentExecutor._run_agent_logic) already passes agent to AISession

**Acceptance Criteria**:
- [ ] AgentExecutor loads relevant skills
- [ ] Skills are passed to AISession via agent parameter
- [ ] Skills appear in system prompt

**Verification**: Already covered by Task 9

---

### WAVE 4: CONTEXT BUILDER

#### Task 11: Create ContextBuilder class

**What to do**:
Create `ContextBuilder` class to expose internal context building as public API

**Location**: `opencode_python/src/opencode_python/context/builder.py` (NEW FILE)

**New File**: `context/builder.py`
```python
"""
Context Builder - Build agent execution context from components
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
import logging

from opencode_python.core.models import Session, Message, Agent, Tool
from opencode_python.agents.builtin import Agent as AgentType
from opencode_python.tools.framework import ToolRegistry
from opencode_python.skills.loader import SkillLoader, Skill


logger = logging.getLogger(__name__)


class AgentContext:
    """Complete context for agent execution"""
    system_prompt: str
    tools: Dict[str, Tool]
    messages: List[Message]
    skills: List[Skill]
    memories: List[Any]  # Future: MemoryEntry
    session: Session
    agent: AgentType


class ContextBuilder:
    """Build agent execution context from components"""

    def __init__(
        self,
        base_dir,
        tool_registry: Optional[ToolRegistry] = None,
        skill_loader: Optional[SkillLoader] = None
    ):
        """Initialize context builder

        Args:
            base_dir: Base directory for skill discovery
            tool_registry: Optional ToolRegistry for tools
            skill_loader: Optional SkillLoader for skills
        """
        self.base_dir = base_dir
        self.tool_registry = tool_registry or ToolRegistry()
        self.skill_loader = skill_loader or SkillLoader(base_dir)

    async def build_context(
        self,
        session: Session,
        agent: AgentType,
        skills: Optional[List[Skill]] = None,
        memories: Optional[List[Any]] = None  # Future: MemoryEntry list
    ) -> AgentContext:
        """Build complete context for agent execution

        Args:
            session: Session object
            agent: Agent to execute
            skills: Optional skills to include
            memories: Optional memories to include (future)

        Returns:
            Complete agent context
        """
        # Load skills if not provided
        if skills is None and self.skill_loader:
            skills = self.skill_loader.discover_skills()

        # Build system prompt
        system_prompt = self._build_system_prompt(agent, skills)

        # Get tools
        tools = await self._get_tools()

        # Get message history
        messages = await self._get_messages(session)

        return AgentContext(
            system_prompt=system_prompt,
            tools=tools,
            messages=messages,
            skills=skills or [],
            memories=memories or [],
            session=session,
            agent=agent
        )

    def _build_system_prompt(
        self,
        agent: AgentType,
        skills: List[Skill]
    ) -> str:
        """Build system prompt from agent and skills

        Args:
            agent: Agent to build prompt for
            skills: Skills to inject

        Returns:
            System prompt with skills
        """
        base_prompt = agent.prompt or f"You are {agent.name}, an AI agent."

        if not skills:
            return base_prompt

        skills_section = "\n\nYou have access to the following skills:\n\n"
        for skill in skills:
            skills_section += f"- {skill.name}: {skill.description}\n"
            skills_section += f"  Content:\n{skill.content}\n\n"

        return base_prompt + skills_section

    async def _get_tools(self) -> Dict[str, Tool]:
        """Get available tools

        Returns:
            Dictionary of tool_id -> Tool
        """
        return await self.tool_registry.get_all()

    async def _get_messages(self, session: Session) -> List[Message]:
        """Get message history from session

        Returns:
            List of messages in session
        """
        if not self.tool_registry:
            return []

        # Get session storage from tool registry
        storage = getattr(self.tool_registry, "_storage", None)
        if storage:
            return await storage.list_messages(session.id)

        # Fallback: No message history available
        return []


def create_context_builder(base_dir) -> ContextBuilder:
    """Factory function to create ContextBuilder

    Args:
        base_dir: Base directory for skill/tool discovery

    Returns:
        ContextBuilder instance
    """
    return ContextBuilder(base_dir)


__all__ = [
    "ContextBuilder",
    "AgentContext",
    "create_context_builder",
]
```

**Why This Class**:
- Exposes internal context building as public API
- Integrates tools, skills, messages, and memories
- Flexible architecture for custom use cases
- Backward compatible with existing AISession

**References**:
- `opencode_python/ai_session.py:265-281` - _build_llm_messages (internal)
- `opencode_python/tools/framework.py:10-34` - ToolRegistry
- `opencode_python/skills/loader.py` - SkillLoader

**Acceptance Criteria**:
- [ ] ContextBuilder class created
- [ ] build_context() creates AgentContext with all components
- [ ] _build_system_prompt() integrates skills
- [ ] _get_tools() uses ToolRegistry
- [ ] _get_messages() uses session storage

**Verification**:
```python
async def test_context_builder():
    storage = MockStorage()
    registry = MockToolRegistry()
    builder = ContextBuilder("/test", tool_registry=registry)

    session = Session(
        id="test_session",
        slug="test_session",
        project_id="test_project",
        directory="/test/dir",
        title="Test Session",
        version="1.0",
        metadata={}
    )

    agent = Agent(
        name="test_agent",
        description="Test agent",
        mode="subagent",
        permission=[],
        prompt="You are a test assistant."
    )

    context = await builder.build_context(session, agent)

    assert context.system_prompt is not None
    assert "You are test_agent" in context.system_prompt
    assert context.session == session
    assert context.agent == agent
```

**Parallelization**:
- Can run independently (no dependencies)

---

#### Task 12: Integrate ContextBuilder with AISession

**What to do**:
Add method to `AISession` to use `ContextBuilder` for external context building

**Location**: `opencode_python/src/opencode_python/ai_session.py`

**New Code** (ai_session.py - add new method):
```python
from opencode_python.context.builder import create_context_builder, AgentContext

class AISession:
    def __init__(
        self,
        session: Session,
        provider_id: str,
        model: str,
        api_key: Optional[str] = None,
        session_manager=None,
        agent: Optional[Agent] = None
    ):
        # ... existing initialization ...

        # NEW: Initialize context builder
        self._context_builder = create_context_builder(session.directory)

    # ... existing methods ...

    async def build_context(
        self,
        agent: Optional[Agent] = None,
        skills: Optional[List[Skill]] = None,
        memories: Optional[List[Any]] = None
    ) -> AgentContext:
        """Build complete context for agent execution

        Args:
            agent: Agent to build context for (uses session agent if None)
            skills: Skills to include
            memories: Memories to include

        Returns:
            Complete agent context
        """
        agent_to_use = agent or self.agent

        return await self._context_builder.build_context(
            session=self.session,
            agent=agent_to_use,
            skills=skills,
            memories=memories
        )
```

**Why This Method**:
- Provides public API for context building
- Separates context building logic from AISession internals
- Enables custom context construction
- Backward compatible with existing _build_llm_messages()

**Acceptance Criteria**:
- [ ] AISession has _context_builder attribute
- [ ] build_context() method exists
- [ ] Uses agent parameter or falls back to session.agent
- [ ] Supports custom skills and memories

**Verification**:
```python
async def test_aISession_context_builder():
    session = Session(
        id="test_session",
        slug="test_session",
        project_id="test_project",
        directory="/test/dir",
        title="Test Session",
        version="1.0",
        metadata={}
    )

    ai_session = AISession(
        session=session,
        provider_id="anthropic",
        model="claude-sonnet-4-20250514"
    )

    agent = Agent(
        name="test_agent",
        description="Test agent",
        mode="subagent",
        permission=[]
    )

    context = await ai_session.build_context(agent=agent)

    assert context.session == session
    assert context.agent == agent
    assert "You are test_agent" in context.system_prompt
```

**Parallelization**:
- Depends on Task 11 (ContextBuilder creation)

---

#### Task 13: Add ContextBuilder to SDK client API

**What to do**:
Expose `build_context()` method through SDK client

**Location**: `opencode_python/src/opencode_python/sdk/client.py`

**New Code** (client.py - add after list_sessions method):
```python
from opencode_python.context.builder import AgentContext

class OpenCodeAsyncClient:
    # ... existing code ...

    async def build_context(
        self,
        session_id: str,
        agent_name: Optional[str] = None,
        skills: Optional[List[Any]] = None,
        memories: Optional[List[Any]] = None
    ) -> AgentContext:
        """Build agent execution context

        Args:
            session_id: Session ID to build context for
            agent_name: Optional agent name (uses session agent if None)
            skills: Optional skills to include
            memories: Optional memories to include

        Returns:
            Complete agent context
        """
        # Get session
        session = await self.get_session(session_id)
        if not session:
            raise SessionError(f"Session {session_id} not found")

        # Get agent
        agent = None
        if agent_name:
            agent = await self.get_agent(agent_name)
        if not agent:
            raise SessionError(f"Agent {agent_name} not found")

        # Use AISession to build context
        # Need to access _service._session_manager to create AISession
        from opencode_python.ai_session import AISession
        ai_session = AISession(
            session=session,
            provider_id=self._config.provider_id or "anthropic",
            model=self._config.model or "claude-sonnet-4-20250514",
            session_manager=self._service._session_manager,
            agent=agent
        )

        return await ai_session.build_context(
            agent=agent,
            skills=skills,
            memories=memories
        )
```

**Also update `OpenCodeSyncClient`** (client.py - sync wrapper):
```python
class OpenCodeSyncClient:
    # ... existing code ...

    def build_context(
        self,
        session_id: str,
        agent_name: Optional[str] = None,
        skills: Optional[List[Any]] = None,
        memories: Optional[List[Any]] = None
    ) -> AgentContext:
        """Build agent execution context (sync wrapper)"""
        return asyncio.run(self._async_client.build_context(
            session_id, agent_name, skills, memories
        ))
```

**Why This Method**:
- Exposes context building through SDK client API
- Provides high-level interface for users
- Integrates with existing session/agent management

**Acceptance Criteria**:
- [ ] OpenCodeAsyncClient has build_context() method
- [ ] OpenCodeSyncClient has build_context() method
- [ ] Method validates session_id and agent_name
- [ ] Method uses AISession.build_context() internally

**Verification**:
```python
async def test_sdk_context_builder():
    client = OpenCodeAsyncClient()

    session = await client.create_session("Test")

    agent = await client.get_agent("build")

    context = await client.build_context(
        session_id=session.id,
        agent_name="build"
    )

    assert context.session == session
    assert context.agent.name == "build"
```

**Parallelization**:
- Depends on Tasks 11, 12

---

## Testing Strategy

### Unit Tests (Each Task)

Add to `tests/test_sdk_{feature}.py`:

```python
# test_sdk_storage_fix.py
def test_session_storage_initialization():
    client = OpenCodeAsyncClient()
    assert client._service.storage is not None

# test_agent_registry.py
async def test_agent_registration():
    registry = create_agent_registry()
    custom_agent = Agent(name="custom", ...)
    await registry.register_agent(custom_agent)
    agent = await registry.get_agent("custom")
    assert agent is not None

# test_skill_injection.py
async def test_skill_injector():
    injector = create_skill_injector(Path.cwd())
    skills = await injector.load_skills()
    assert isinstance(skills, list)

# test_context_builder.py
async def test_context_builder():
    builder = create_context_builder(Path.cwd())
    session = Session(id="test", ...)
    agent = Agent(name="test", ...)
    context = await builder.build_context(session, agent)
    assert context.system_prompt is not None
```

### Integration Tests

```python
# test_end_to_end_agent_execution.py
async def test_complete_agent_execution():
    client = OpenCodeAsyncClient()

    # Register custom agent
    custom_agent = Agent(name="custom_bot", ...)
    await client.register_agent(custom_agent)

    # Create session
    session = await client.create_session("Test")

    # Execute agent (would fail without Task 3 fix)
    result = await client.execute_agent(
        agent_name="custom_bot",
        session_id=session.id,
        user_message="Hello"
    )

    assert result["status"] == "completed"
```

### Test Commands

```bash
# Run all tests
pytest tests/test_sdk_*.py -v

# Run specific test suites
pytest tests/test_sdk_storage_fix.py -v
pytest tests/test_agent_registry.py -v
pytest tests/test_skill_injection.py -v
pytest tests/test_context_builder.py -v
pytest tests/test_integration.py -v
```

---

## Success Criteria

### Wave 1: Critical Bug Fixes
- [ ] SDK client initializes without TypeError
- [ ] SessionStorage created with valid base_dir
- [ ] AgentExecutor uses real Session objects
- [ ] ToolExecutionManager has all 23 tools
- [ ] AgentExecutor._filter_tools_for_agent() works
- [ ] Tool lookups succeed
- [ ] All existing tests pass

### Wave 2: Agent Registry
- [ ] AgentRegistry class created
- [ ] Custom agents can be registered
- [ ] get_agent() finds custom agents
- [ ] list_agents() returns combined list
- [ ] Cannot override built-in agents
- [ ] AgentManager uses AgentRegistry
- [ ] SDK client has register_agent/get_agent/list_agents

### Wave 3: Skill Injection
- [ ] SkillInjector class created
- [ ] Skills automatically loaded from SKILL.md
- [ ] Skills injected into system prompts
- [ ] AISession accepts agent parameter
- [ ] System messages contain skills
- [ ] Agent.prompt field is used

### Wave 4: Context Builder
- [ ] ContextBuilder class created
- [ ] build_context() creates AgentContext
- [ ] Components: system_prompt, tools, messages, skills
- [ ] Public API exposed through SDK client
- [ ] Can build context for custom scenarios

---

## Migration Notes

### Breaking Changes

None - all changes are additive

### Backward Compatibility

✅ **Fully backward compatible**
- Existing code continues to work
- All changes are additive
- No API changes (only additions)

### Deprecations

None

---

## Risk Assessment

### Low Risk

**Wave 1: Critical Bug Fixes**
- Straightforward bug fixes
- Well-understood problem space
- Clear acceptance criteria
- **Risk**: LOW

**Wave 2: Agent Registry**
- Simple CRUD operations
- No dependencies on other waves
- Clear testing strategy
- **Risk**: LOW

**Wave 3: Skill Injection**
- Well-defined patterns from existing code
- Integrates with existing AISession
- No breaking changes
- **Risk**: LOW

**Wave 4: Context Builder**
- Exposes existing functionality
- Adds flexibility without breaking changes
- **Risk**: LOW

---

## Commit Strategy

### Commit Wave 1
```bash
# Fix critical bugs
git add opencode_python/src/opencode_python/sdk/client.py
git add opencode_python/src/opencode_python/agents/__init__.py
git add opencode_python/src/opencode_python/ai/tool_execution.py
git commit -m "fix: Fix 3 critical bugs blocking SDK usage

- Fix SessionStorage initialization with base_dir parameter
- Fix AgentExecutor fake Session objects
- Fix ToolExecutionManager empty tool_registry"
```

### Commit Wave 2
```bash
# Add agent registry
git add opencode_python/src/opencode_python/agents/registry.py
git add opencode_python/src/opencode_python/sdk/client.py
git add opencode_python/src/opencode_python/agents/__init__.py
git commit -m "feat: Add AgentRegistry for custom agent management

- Create AgentRegistry class
- Add register_agent/get_agent/list_agents to SDK client
- Integrate with AgentManager"
```

### Commit Wave 3
```bash
# Add skill injection
git add opencode_python/src/opencode_python/skills/injector.py
git add opencode_python/src/opencode_python/ai_session.py
git add opencode_python/src/opencode_python/agents/__init__.py
git commit -m "feat: Add SkillInjector for automatic skill injection

- Create SkillInjector class
- Integrate with AISession for system prompt injection
- Update AgentExecutor to pass agent for skill loading"
```

### Commit Wave 4
```bash
# Add context builder
git add opencode_python/src/opencode_python/context/builder.py
git add opencode_python/src/opencode_python/ai_session.py
git add opencode_python/src/opencode_python/sdk/client.py
git commit -m "feat: Add ContextBuilder for public API

- Create ContextBuilder class
- Integrate with AISession
- Expose through SDK client API"
```

---

## Rollback Plan

If any wave fails:

**Wave 1 (Critical Bugs)**:
- Revert to working state before wave
- Investigate failure
- Create hotfix patch

**Wave 2-4 (Features)**:
- Revert new features only
- Keep bug fixes (if successful)
- Re-implement with different approach

---

## References

### Files Modified

**Wave 1**:
- `opencode_python/src/opencode_python/sdk/client.py`
- `opencode_python/src/opencode_python/agents/__init__.py`
- `opencode_python/src/opencode_python/ai/tool_execution.py`

**Wave 2**:
- `opencode_python/src/opencode_python/agents/registry.py` (NEW)
- `opencode_python/src/opencode_python/sdk/client.py`
- `opencode_python/src/opencode_python/agents/__init__.py`

**Wave 3**:
- `opencode_python/src/opencode_python/skills/injector.py` (NEW)
- `opencode_python/src/opencode_python/ai_session.py`
- `opencode_python/src/opencode_python/agents/__init__.py`

**Wave 4**:
- `opencode_python/src/opencode_python/context/builder.py` (NEW)
- `opencode_python/src/opencode_python/ai_session.py`
- `opencode_python/src/opencode_python/sdk/client.py`

### New Files Created

```
opencode_python/src/opencode_python/agents/registry.py
opencode_python/src/opencode_python/skills/injector.py
opencode_python/src/opencode_python/context/builder.py
```

---

## Open Questions

1. **Skill relevance**: Should skills be filtered by agent type or description?
2. **Skill caching**: Should skills be cached across sessions?
3. **Memory future**: Should ContextBuilder accept MemoryEntry type?
4. **Testing**: What test framework should be used?
5. **Documentation**: Should we add docstrings for new classes?

---

## Next Steps

1. ✅ Plan created and ready for implementation
2. ⬜ Execute Wave 1: Fix critical bugs
3. ⬜ Execute Wave 2: Agent registry
4. ⬜ Execute Wave 3: Skill injection
5. ⬜ Execute Wave 4: Context builder
6. ⬜ Run full test suite
7. ⬜ Update documentation
8. ⬜ Release with 4 waves of commits

**Total Estimated Time**: 4 weeks

**Ready to begin implementation!**
