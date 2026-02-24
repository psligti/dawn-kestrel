import pytest

from dawn_kestrel.prompts.loader import (
    clear_cache,
    get_prompt_path,
    list_prompts,
    load_prompt,
)


class TestLoadPrompt:
    def test_load_fsm_intake_prompt(self) -> None:
        prompt = load_prompt("fsm/intake")
        assert "INTAKE" in prompt
        assert "{user_message}" in prompt
        assert "{schema}" in prompt

    def test_load_fsm_plan_prompt(self) -> None:
        prompt = load_prompt("fsm/plan")
        assert "PLAN" in prompt
        assert "{context_summary}" in prompt
        assert "{schema}" in prompt

    def test_load_fsm_act_prompt(self) -> None:
        prompt = load_prompt("fsm/act")
        assert "ACT" in prompt
        assert "SINGLE ACTION CONSTRAINT" in prompt
        assert "{current_todo_id}" in prompt
        assert "{description}" in prompt

    def test_load_fsm_synthesize_prompt(self) -> None:
        prompt = load_prompt("fsm/synthesize")
        assert "SYNTHESIZE" in prompt
        assert "{current_todo_id}" in prompt
        assert "{act_summary}" in prompt

    def test_load_fsm_check_prompt(self) -> None:
        prompt = load_prompt("fsm/check")
        assert "CHECK" in prompt
        assert "{current_todo_id}" in prompt
        assert "{iterations_consumed}" in prompt
        assert "{stagnation_count}" in prompt

    def test_load_fsm_reason_prompt(self) -> None:
        """Test that REASON state prompt exists and has required variables."""
        prompt = load_prompt("fsm/reason")
        assert "REASON" in prompt
        assert "{context_summary}" in prompt
        assert "{schema}" in prompt

    def test_reason_prompt_contains_thought_action(self) -> None:
        """Test that REASON prompt contains ReAct pattern elements."""
        prompt = load_prompt("fsm/reason")
        assert "Thought" in prompt
        assert "Action" in prompt
        assert "next state" in prompt  # "Choose the next state" in template
        assert "ReAct" in prompt

    def test_load_nonexistent_prompt_raises_error(self) -> None:
        with pytest.raises(FileNotFoundError) as exc_info:
            load_prompt("nonexistent/prompt")
        assert "Prompt file not found" in str(exc_info.value)

    def test_caching_works(self) -> None:
        clear_cache()
        prompt1 = load_prompt("fsm/intake")
        prompt2 = load_prompt("fsm/intake")
        assert prompt1 is prompt2

    def test_clear_cache_works(self) -> None:
        load_prompt("fsm/intake")
        clear_cache()
        prompt = load_prompt("fsm/intake")
        assert "INTAKE" in prompt

    def test_prompt_formatting(self) -> None:
        prompt = load_prompt("fsm/intake")
        formatted = prompt.format(schema="TEST_SCHEMA", user_message="Test user message")
        assert "Test user message" in formatted
        assert "TEST_SCHEMA" in formatted


class TestListPrompts:
    def test_list_all_fsm_prompts(self) -> None:
        prompts = list_prompts("fsm")
        assert "fsm/intake" in prompts
        assert "fsm/plan" in prompts
        assert "fsm/act" in prompts
        assert "fsm/synthesize" in prompts
        assert "fsm/check" in prompts
        assert "fsm/reason" in prompts
        assert len(prompts) == 6

    def test_list_all_prompts(self) -> None:
        prompts = list_prompts()
        assert len(prompts) >= 6
        for p in ["fsm/intake", "fsm/plan", "fsm/act", "fsm/synthesize", "fsm/check", "fsm/reason"]:
            assert p in prompts

    def test_list_nonexistent_category(self) -> None:
        prompts = list_prompts("nonexistent")
        assert prompts == []


class TestGetPromptPath:
    def test_get_fsm_intake_path(self) -> None:
        path = get_prompt_path("fsm/intake")
        assert path.name == "intake.md"
        assert "fsm" in str(path)

    def test_get_nonexistent_path_raises_error(self) -> None:
        with pytest.raises(FileNotFoundError):
            get_prompt_path("nonexistent/prompt")


class TestPromptSections:
    @pytest.mark.parametrize(
        "phase,expected_sections",
        [
            ("intake", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
            ("plan", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
            ("act", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
            ("synthesize", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
            ("check", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
            ("reason", ["## GOAL", "## INPUT", "## OUTPUT", "## VALIDATION", "## CONSTRAINTS"]),
        ],
    )
    def test_prompt_has_required_sections(self, phase: str, expected_sections: list[str]) -> None:
        from pathlib import Path

        prompt_path = (
            Path(__file__).parent.parent.parent / "dawn_kestrel" / "prompts" / "fsm" / f"{phase}.md"
        )
        content = prompt_path.read_text()

        for section in expected_sections:
            assert section in content, f"Missing section '{section}' in {phase}.md"
