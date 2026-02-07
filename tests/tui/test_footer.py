"""Footer widget tests - TDD phase tests"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

# Import footer module (will fail initially - RED phase)
try:
    from dawn_kestrel.tui.widgets.footer import SessionFooter
    FOOTER_EXISTS = True
except ImportError:
    FOOTER_EXISTS = False
    SessionFooter = None  # type: ignore


class TestSessionFooter:
    """SessionFooter widget tests"""

    def test_footer_exists(self):
        """SessionFooter should be importable"""
        assert FOOTER_EXISTS, "SessionFooter module not found"
        assert SessionFooter is not None, "SessionFooter class not found"

    def test_footer_is_widget(self):
        """SessionFooter should be a Textual widget"""
        from textual.widget import Widget
        assert issubclass(SessionFooter, Widget), "SessionFooter should extend Widget"

    def test_footer_has_status_property(self):
        """SessionFooter should accept status"""
        footer = SessionFooter(status="Syncing...")
        assert footer.status == "Syncing..."

    def test_footer_has_tokens_property(self):
        """SessionFooter should accept tokens"""
        footer = SessionFooter(tokens="1000 tokens")
        assert footer.tokens == "1000 tokens"

    def test_footer_has_cost_property(self):
        """SessionFooter should accept cost"""
        footer = SessionFooter(cost="$0.50")
        assert footer.cost == "$0.50"

    def test_footer_has_model_property(self):
        """SessionFooter should accept model"""
        footer = SessionFooter(model="gpt-4")
        assert footer.model == "gpt-4"

    def test_footer_default_values(self):
        """SessionFooter should have sensible default values"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        footer = SessionFooter()
        assert footer.status == ""
        assert footer.tokens == ""
        assert footer.cost == ""
        assert footer.model is None

    @pytest.mark.asyncio
    async def test_footer_displays_keyboard_hints(self):
        """SessionFooter should display keyboard hints"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter()
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            footer = app._footer
            # Should show keyboard hints
            assert "q:" in footer.content
            assert "/:" in footer.content
            assert "Enter:" in footer.content
            assert "Escape:" in footer.content

    @pytest.mark.asyncio
    async def test_footer_displays_status(self):
        """SessionFooter should display status messages"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter(status="Loading...")
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            footer = app._footer
            # Should show status
            assert "Loading..." in footer.content

    @pytest.mark.asyncio
    async def test_footer_displays_metadata(self):
        """SessionFooter should display metadata"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter(
                    tokens="5000 tokens",
                    cost="$2.50",
                    model="gpt-4"
                )
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            footer = app._footer
            # Should show metadata
            assert "5000 tokens" in footer.content
            assert "$2.50" in footer.content
            assert "model: gpt-4" in footer.content

    @pytest.mark.asyncio
    async def test_footer_update_status(self):
        """SessionFooter should update when status changes"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter(status="Initial")
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            footer = app._footer
            # Update status
            footer.status = "Updated"
            # Verify update
            assert "Updated" in footer.content

    @pytest.mark.asyncio
    async def test_footer_read_only(self):
        """SessionFooter should be read-only display only"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter(
                    status="Test",
                    tokens="100 tokens"
                )
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            footer = app._footer
            # Footer should be display-only (no input widgets)
            from textual.widgets import Input
            inputs = footer.query(Input)
            assert len(inputs) == 0, "Footer should not contain Input widgets"

    @pytest.mark.asyncio
    async def test_footer_integrates_with_app(self):
        """SessionFooter should integrate with Textual app"""
        if not FOOTER_EXISTS:
            pytest.skip("SessionFooter not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._footer = SessionFooter(
                    status="Test Status",
                    model="test-model"
                )
                yield self._footer

        app = TestApp()
        async with app.run_test() as pilot:
            # Footer should be queryable in app
            footer = app.query_one(SessionFooter)
            assert footer is not None
            assert footer.status == "Test Status"
            assert footer.model == "test-model"
