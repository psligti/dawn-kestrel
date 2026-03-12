# Dawn Kestrel Skills Guide

Skills are the primary extensibility mechanism for agent projects. This guide covers skill authoring, registration, and usage.

---

## What is a Skill?

A **skill** is a reusable capability that can be loaded by agents at runtime. Skills:
- Extend agent behavior without code changes
- Can be project-specific or shared globally
- Are discovered automatically from predefined paths
- Can be chained and composed

---

## Skill Discovery

Skills are discovered from these paths (in order):

```
./skills/                          # Project-specific skills
~/.dawn-kestrel/skills/            # User skills
~/.opencode/skill/                 # OpenCode compatibility
~/.claude/skills/                  # Claude compatibility
```

### File Structure

```
skills/
├── code-review/
│   ├── __init__.py               # Skill implementation
│   └── skill.md                  # Skill documentation/prompt
├── testing/
│   ├── __init__.py
│   └── skill.md
└── deployment/
    ├── __init__.py
    └── skill.md
```

---

## Creating a Skill

### Basic Structure

```python
# skills/my_skill/__init__.py
from __future__ import annotations
from typing import Any, Dict
from dawn_kestrel.skills import Skill, SkillContext, SkillResult

class MySkill(Skill):
    """A reusable skill for [purpose]."""
    
    @property
    def name(self) -> str:
        return "my_skill"
    
    @property
    def description(self) -> str:
        return "Brief description of what this skill does"
    
    @property
    def triggers(self) -> list[str]:
        """Keywords that suggest this skill should be used."""
        return ["my keyword", "specific phrase"]
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill logic."""
        
        # Access agent runtime
        runtime = context.runtime
        
        # Access session
        session_id = context.session_id
        
        # Access tools
        tools = context.tools
        
        # Your skill logic here
        result = await self._do_work(context)
        
        return SkillResult(
            success=True,
            output=result,
            metadata={"tokens_used": 100}
        )
    
    async def _do_work(self, context: SkillContext) -> Dict[str, Any]:
        """Internal skill logic."""
        # Implementation details
        return {"status": "complete"}
```

### Skill Prompt (Optional)

```markdown
<!-- skills/my_skill/skill.md -->
# My Skill

This skill performs [specific task].

## When to Use
- Condition 1
- Condition 2

## How It Works
1. Step 1
2. Step 2

## Examples
[Example usage patterns]
```

---

## Built-in Skills

### Council Skill

Multi-agent consultation for comprehensive analysis.

```python
from dawn_kestrel.skills import CouncilSkill

skill = CouncilSkill()

result = await skill.execute(SkillContext(
    question="Should we use microservices or monolith?",
    council_members=["consultant", "architect", "performance"],
    runtime=runtime,
))
```

**Triggers:**
- "consult multiple agents"
- "get multiple perspectives"
- "council analysis"

### Git-Master Skill

Git operations with safety guards.

```python
from dawn_kestrel.skills import GitMasterSkill

skill = GitMasterSkill()
result = await skill.execute(SkillContext(
    operation="commit",
    message="feat: add new feature",
    files=["src/main.py"],
))
```

**Triggers:**
- "commit", "rebase", "squash"
- "who wrote", "when was X added"

### Playwright Skill

Browser automation via MCP.

```python
from dawn_kestrel.skills import PlaywrightSkill

skill = PlaywrightSkill()
result = await skill.execute(SkillContext(
    action="screenshot",
    url="https://example.com",
))
```

**Triggers:**
- "open browser", "take screenshot"
- "click on", "fill form"

---

## Registering Skills

### Via Entry Points

```toml
# pyproject.toml
[project.entry-points."dawn_kestrel.skills"]
my_skill = "my_package.skills:MySkill"
```

### Via Registry

```python
from dawn_kestrel.skills import SkillRegistry

registry = SkillRegistry()
registry.register(MySkill())

# Discover and load
skills = registry.discover(["./skills", "~/.dawn-kestrel/skills"])
```

---

## Using Skills in Agents

### Agent Configuration

```python
from dawn_kestrel.agents import AgentBuilder

config = (AgentBuilder()
    .with_name("my_agent")
    .with_skills(["code-review", "testing"])
    .build())
```

### Runtime Skill Loading

```python
from dawn_kestrel.skills import SkillLoader

loader = SkillLoader()
skill = loader.load("my_skill")

result = await skill.execute(context)
```

---

## Skill Patterns

### 1. Wrapper Skill

Wraps a tool with additional logic:

```python
class SafeBashSkill(Skill):
    """Bash with safety checks."""
    
    @property
    def name(self) -> str:
        return "safe_bash"
    
    async def execute(self, context: SkillContext) -> SkillResult:
        command = context.params.get("command")
        
        # Safety check
        if self._is_dangerous(command):
            return SkillResult(
                success=False,
                error="Dangerous command blocked"
            )
        
        # Execute
        result = await context.tools.bash(command)
        
        return SkillResult(success=True, output=result)
```

### 2. Composite Skill

Combines multiple skills:

```python
class CodeQualitySkill(Skill):
    """Combines lint, test, and coverage."""
    
    @property
    def name(self) -> str:
        return "code_quality"
    
    async def execute(self, context: SkillContext) -> SkillResult:
        results = {}
        
        # Run lint
        lint_result = await context.skills.get("lint").execute(context)
        results["lint"] = lint_result
        
        # Run tests
        test_result = await context.skills.get("test").execute(context)
        results["test"] = test_result
        
        # Calculate coverage
        coverage = await context.skills.get("coverage").execute(context)
        results["coverage"] = coverage
        
        return SkillResult(
            success=all(r.success for r in results.values()),
            output=results
        )
```

### 3. Delegation Skill

Delegates to subagents:

```python
class DeepAnalysisSkill(Skill):
    """Delegates to specialized agents."""
    
    @property
    def name(self) -> str:
        return "deep_analysis"
    
    async def execute(self, context: SkillContext) -> SkillResult:
        from dawn_kestrel.delegation import DelegationEngine
        
        engine = DelegationEngine(context.config.delegation)
        
        children = [
            {"agent": "security", "prompt": "Analyze security"},
            {"agent": "performance", "prompt": "Analyze performance"},
        ]
        
        result = await engine.delegate(
            agent_name="orchestrator",
            prompt="Deep analysis",
            session_id=context.session_id,
            children=children,
        )
        
        return SkillResult(
            success=result.success,
            output=result.results
        )
```

---

## Skill Best Practices

### 1. Single Responsibility

Each skill should do one thing well:

```
✅ Good: "Run pytest and parse results"
❌ Bad: "Run tests, lint, format, and deploy"
```

### 2. Explicit Triggers

Define clear trigger phrases:

```python
@property
def triggers(self) -> list[str]:
    return [
        "run tests", "pytest", "test coverage",
        "check tests pass"
    ]
```

### 3. Meaningful Errors

Return actionable error messages:

```python
if not test_file.exists():
    return SkillResult(
        success=False,
        error=f"Test file not found: {test_file}",
        suggestions=[
            "Create the test file",
            "Check the file path"
        ]
    )
```

### 4. Context Awareness

Use context signals for conditional behavior:

```python
async def execute(self, context: SkillContext) -> SkillResult:
    if "ci_env" in context.signals:
        # CI-specific behavior
        pass
    elif "interactive" in context.signals:
        # Interactive behavior
        pass
```

### 5. Progress Reporting

Report progress for long-running skills:

```python
async def execute(self, context: SkillContext) -> SkillResult:
    await context.report_progress("Starting analysis...", 0)
    
    # Phase 1
    await context.report_progress("Analyzing security...", 25)
    
    # Phase 2
    await context.report_progress("Analyzing performance...", 50)
    
    # Phase 3
    await context.report_progress("Generating report...", 75)
    
    await context.report_progress("Complete", 100)
```

---

## Testing Skills

### Unit Testing

```python
import pytest
from dawn_kestrel.skills import SkillContext
from my_package.skills import MySkill

@pytest.fixture
def skill():
    return MySkill()

@pytest.fixture
def context():
    return SkillContext(
        runtime=MockRuntime(),
        session_id="test-session",
        params={"input": "test"}
    )

async def test_skill_executes(skill, context):
    result = await skill.execute(context)
    assert result.success
    assert result.output is not None

async def test_skill_handles_error(skill, context):
    context.params = {}  # Missing required param
    result = await skill.execute(context)
    assert not result.success
    assert "error" in result.error.lower()
```

### Integration Testing

```python
async def test_skill_in_agent():
    from dawn_kestrel.agents import AgentRuntime
    
    runtime = AgentRuntime()
    runtime.register_skill(MySkill())
    
    result = await runtime.execute(
        agent_name="test_agent",
        user_message="Use my skill to process this"
    )
    
    assert result.success
```

---

## Skill Distribution

### Local Skills

Project-specific skills in `./skills/`:

```
my-project/
├── skills/
│   └── project-specific/
│       ├── __init__.py
│       └── skill.md
└── ...
```

### Package Skills

Distribute via Python package:

```toml
# pyproject.toml
[project.entry-points."dawn_kestrel.skills"]
my_skill = "my_package.skills:MySkill"
```

### Global Skills

User-wide skills in `~/.dawn-kestrel/skills/`:

```
~/.dawn-kestrel/skills/
├── personal-workflow/
│   ├── __init__.py
│   └── skill.md
└── company-standards/
    ├── __init__.py
    └── skill.md
```

---

## Advanced Topics

### Skill Configuration

```python
class ConfigurableSkill(Skill):
    """Skill with runtime configuration."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    async def execute(self, context: SkillContext) -> SkillResult:
        timeout = self.config.get("timeout", 30)
        max_retries = self.config.get("max_retries", 3)
        
        # Use configuration
        ...
```

### Skill Dependencies

```python
class DependentSkill(Skill):
    """Skill that requires other skills."""
    
    @property
    def dependencies(self) -> list[str]:
        return ["git", "bash"]
    
    async def execute(self, context: SkillContext) -> SkillResult:
        # Ensure dependencies are available
        for dep in self.dependencies:
            if not context.skills.has(dep):
                return SkillResult(
                    success=False,
                    error=f"Missing dependency: {dep}"
                )
        
        # Use dependencies
        git_result = await context.skills.get("git").execute(...)
        ...
```

### Skill Middleware

```python
class LoggingMiddleware:
    """Log all skill executions."""
    
    async def before(self, skill: Skill, context: SkillContext):
        logger.info(f"Starting skill: {skill.name}")
    
    async def after(self, skill: Skill, context: SkillContext, result: SkillResult):
        logger.info(f"Completed skill: {skill.name} (success={result.success})")

# Register middleware
registry.add_middleware(LoggingMiddleware())
```

---

## See Also

- [FEATURE_ANALYSIS.md](./FEATURE_ANALYSIS.md) - Feature extraction priorities
- [SPECS/](./SPECS/) - Technical specifications
- [PRD/](./PRD/) - Product requirements
