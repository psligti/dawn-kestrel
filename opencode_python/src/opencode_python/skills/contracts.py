"""Skill contracts - prompt templates and output schemas"""
from __future__ import annotations

from typing import Dict, Any, List
import pydantic as pd


class PlanningOutput(pd.BaseModel):
    """Structured output for planning skill"""

    tasks: List[str] = pd.Field(default_factory=list)
    """List of tasks in the plan"""

    dependencies: Dict[str, List[str]] = pd.Field(default_factory=dict)
    """Task dependencies: task_id -> [dependent_task_ids]"""

    priority: Dict[str, str] = pd.Field(default_factory=dict)
    """Task priorities: task_id -> priority level"""

    estimated_time: Dict[str, str] = pd.Field(default_factory=dict)
    """Estimated time for each task"""

    model_config = pd.ConfigDict(extra="forbid")


class RefactorOutput(pd.BaseModel):
    """Structured output for refactor skill"""

    changes: List[Dict[str, Any]] = pd.Field(default_factory=list)
    """List of refactor changes, each with file, line, old_code, new_code"""

    improvements: List[str] = pd.Field(default_factory=list)
    """List of improvement descriptions"""

    warnings: List[str] = pd.Field(default_factory=list)
    """List of warnings about potential issues"""

    model_config = pd.ConfigDict(extra="forbid")


class TestGenerationOutput(pd.BaseModel):
    """Structured output for test generation skill"""

    test_files: List[Dict[str, Any]] = pd.Field(default_factory=list)
    """List of test files to create with path and content"""

    test_cases: List[Dict[str, Any]] = pd.Field(default_factory=list)
    """List of test cases with description and assertions"""

    coverage_analysis: Dict[str, Any] = pd.Field(default_factory=dict)
    """Coverage analysis results"""

    model_config = pd.ConfigDict(extra="forbid")


class DocsOutput(pd.BaseModel):
    """Structured output for documentation skill"""

    updated_files: List[Dict[str, Any]] = pd.Field(default_factory=list)
    """List of files that need documentation updates"""

    new_docs: List[Dict[str, Any]] = pd.Field(default_factory=list)
    """List of new documentation to create"""

    api_documentation: Dict[str, Any] = pd.Field(default_factory=dict)
    """API documentation in structured format"""

    model_config = pd.ConfigDict(extra="forbid")


class SkillContract:
    """Skill contract with prompt template and output schema"""

    def __init__(self, prompt_template: str, output_model: type[pd.BaseModel]):
        self.prompt_template = prompt_template
        self.output_model = output_model

    @property
    def output_schema(self) -> Dict[str, Any]:
        """Get the output schema as a dictionary"""
        return self.output_model.model_json_schema()

    def format_prompt(self, **kwargs: Any) -> str:
        """Format the prompt template with provided variables"""
        return self.prompt_template.format(**kwargs)


PLANNING_PROMPT = """You are a planning specialist. Analyze the following task and create a detailed plan.

Task: {task}

Context:
{context}

Create a structured plan with:
1. Clear, actionable tasks
2. Dependencies between tasks
3. Priority levels (high/medium/low)
4. Estimated time for each task

Output in JSON format matching the PlanningOutput schema."""


REFACTOR_PROMPT = """You are a refactoring specialist. Analyze the following code and suggest improvements.

Code:
{code}

Context:
{context}

Identify:
1. Code quality issues
2. Potential bugs
3. Performance improvements
4. Readability enhancements

Output in JSON format matching the RefactorOutput schema."""


TESTS_PROMPT = """You are a test generation specialist. Analyze the following code and create comprehensive tests.

Code:
{code}

Context:
{context}

Create:
1. Unit tests for all functions
2. Edge case tests
3. Integration tests if applicable
4. Mock tests for external dependencies

Output in JSON format matching the TestsOutput schema."""


DOCS_PROMPT = """You are a documentation specialist. Analyze the following code and create/update documentation.

Code:
{code}

Context:
{context}

Create:
1. Function/class docstrings
2. API documentation
3. Usage examples
4. Type hints where missing

Output in JSON format matching the DocsOutput schema."""


# Predefined skill contracts
PLANNING_CONTRACT = SkillContract(PLANNING_PROMPT, PlanningOutput)
REFACTOR_CONTRACT = SkillContract(REFACTOR_PROMPT, RefactorOutput)
TESTS_CONTRACT = SkillContract(TESTS_PROMPT, TestGenerationOutput)
DOCS_CONTRACT = SkillContract(DOCS_PROMPT, DocsOutput)
