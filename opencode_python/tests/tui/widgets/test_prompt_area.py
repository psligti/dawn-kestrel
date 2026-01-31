"""PromptArea widget tests"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import TextArea

# Import prompt_area module
try:
    from opencode_python.tui.widgets.prompt_area import PromptArea
    PROMPT_AREA_EXISTS = True
except ImportError:
    PROMPT_AREA_EXISTS = False
    PromptArea = None  # type: ignore


class TestPromptArea:
    """PromptArea widget tests"""

    def test_prompt_area_exists(self):
        """PromptArea should be importable"""
        assert PROMPT_AREA_EXISTS, "PromptArea module not found"
        assert PromptArea is not None, "PromptArea class not found"

    def test_prompt_area_extends_textarea(self):
        """PromptArea should extend TextArea"""
        assert issubclass(PromptArea, TextArea), "PromptArea should extend TextArea"

    def test_prompt_area_has_submitted_message(self):
        """PromptArea should have Submitted message class"""
        assert hasattr(PromptArea, "Submitted"), "PromptArea should have Submitted message"

    def test_prompt_area_can_be_instantiated(self):
        """PromptArea should be instantiable"""
        prompt_area = PromptArea()
        assert prompt_area is not None

    def test_prompt_area_accepts_placeholder(self):
        """PromptArea should accept placeholder text"""
        prompt_area = PromptArea(placeholder="Enter your prompt...")
        assert prompt_area is not None

    def test_prompt_area_accepts_id(self):
        """PromptArea should accept widget ID"""
        prompt_area = PromptArea(id="test-prompt")
        assert prompt_area.id == "test-prompt"

    async def test_prompt_area_displays_placeholder(self):
        """PromptArea should display placeholder when empty"""
        if not PROMPT_AREA_EXISTS:
            pytest.skip("PromptArea not yet implemented")

        prompt = PromptArea(placeholder="Type your message here...")
        # Placeholder should be set
        assert prompt.placeholder == "Type your message here..."

    @pytest.mark.asyncio
    async def test_prompt_area_accepts_text_input(self):
        """PromptArea should accept multi-line text input"""
        if not PROMPT_AREA_EXISTS:
            pytest.skip("PromptArea not yet implemented")

        prompt = PromptArea()
        # Set text
        prompt.text = "Hello, World!\nThis is a test."
        # Verify text was set
        assert prompt.text == "Hello, World!\nThis is a test."

    def test_prompt_area_has_on_key_handler(self):
        """PromptArea should have on_key method for handling key events"""
        if not PROMPT_AREA_EXISTS:
            pytest.skip("PromptArea not yet implemented")

        prompt = PromptArea()
        assert hasattr(prompt, "on_key"), "PromptArea should have on_key method"

    def test_prompt_area_submitted_message_takes_text(self):
        """Submitted message should accept text parameter"""
        if not PROMPT_AREA_EXISTS:
            pytest.skip("PromptArea not yet implemented")

        message = PromptArea.Submitted("test text")
        assert message.text == "test text"

    def test_prompt_area_css_defined(self):
        """PromptArea should have DEFAULT_CSS defined"""
        if not PROMPT_AREA_EXISTS:
            pytest.skip("PromptArea not yet implemented")

        assert hasattr(PromptArea, "DEFAULT_CSS"), "PromptArea should have DEFAULT_CSS"
        css = PromptArea.DEFAULT_CSS
        assert "height: auto" in css, "PromptArea CSS should have auto height"
        assert "max-height: 50vh" in css, "PromptArea CSS should have max-height of 50vh"
