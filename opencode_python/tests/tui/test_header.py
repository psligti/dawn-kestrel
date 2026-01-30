"""Header widget tests - TDD phase tests"""
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

# Import header module (will fail initially - RED phase)
try:
    from opencode_python.tui.widgets.header import SessionHeader
    HEADER_EXISTS = True
except ImportError:
    HEADER_EXISTS = False
    SessionHeader = None  # type: ignore

class TestSessionHeader:
    """SessionHeader widget tests"""

    def test_header_exists(self):
        """SessionHeader should be importable"""
        assert HEADER_EXISTS, "SessionHeader module not found"
        assert SessionHeader is not None, "SessionHeader class not found"

    def test_header_is_widget(self):
        """SessionHeader should be a Textual widget"""
        from textual.widget import Widget
        assert issubclass(SessionHeader, Widget), "SessionHeader should extend Widget"

    def test_header_has_session_title_property(self):
        """SessionHeader should accept session title"""
        header = SessionHeader(session_title="Test Session")
        assert header.session_title == "Test Session"

    def test_header_has_parent_session_property(self):
        """SessionHeader should accept parent session ID"""
        header = SessionHeader(session_title="Test", parent_session_id="parent-123")
        assert header.parent_session_id == "parent-123"

    def test_header_has_model_property(self):
        """SessionHeader should accept model name"""
        header = SessionHeader(session_title="Test", model="gpt-4")
        assert header.model == "gpt-4"

    @pytest.mark.asyncio
    async def test_header_displays_session_title(self):
        """SessionHeader should display session title"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(session_title="My Test Session")
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Check that title is displayed
            assert "My Test Session" in header.content

    @pytest.mark.asyncio
    async def test_header_displays_breadcrumb_no_parent(self):
        """SessionHeader should show session title when no parent"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(session_title="Main Session")
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Should show just session title
            assert "Main Session" in header.content
            # Should NOT show parent indicator
            assert "Parent" not in header.content

    @pytest.mark.asyncio
    async def test_header_displays_breadcrumb_with_parent(self):
        """SessionHeader should show parent session path when parent exists"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(
                    session_title="Child Session",
                    parent_session_id="parent-123"
                )
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Should show session title
            assert "Child Session" in header.content
            # Should show parent indicator
            assert "parent" in header.content.lower()

    @pytest.mark.asyncio
    async def test_header_displays_model(self):
        """SessionHeader should display model information"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(
                    session_title="Test Session",
                    model="gpt-4"
                )
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Should show model information
            assert "gpt-4" in header.content

    @pytest.mark.asyncio
    async def test_header_update_session_title(self):
        """SessionHeader should update when session title changes"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(session_title="Original Title")
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Update title
            header.session_title = "Updated Title"
            await pilot.pause()
            # Verify update
            assert "Updated Title" in header.content

    @pytest.mark.asyncio
    async def test_header_update_model(self):
        """SessionHeader should update when model changes"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(
                    session_title="Test",
                    model="gpt-3.5-turbo"
                )
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Update model
            header.model = "gpt-4"
            await pilot.pause()
            # Verify update
            assert "gpt-4" in header.content

    @pytest.mark.asyncio
    async def test_header_read_only_title(self):
        """SessionHeader title should be read-only display only"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(session_title="Read Only")
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            header = app._header
            # Header should be display-only (no input widgets)
            from textual.widgets import Input
            inputs = header.query(Input)
            assert len(inputs) == 0, "Header should not contain Input widgets"

    @pytest.mark.asyncio
    async def test_header_integrates_with_app(self):
        """SessionHeader should integrate with OpenCodeTUI app"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        class TestApp(App):
            def compose(self) -> ComposeResult:
                self._header = SessionHeader(
                    session_title="Integration Test",
                    model="test-model"
                )
                yield self._header

        app = TestApp()
        async with app.run_test() as pilot:
            # Header should be queryable in app
            header = app.query_one(SessionHeader)
            assert header is not None
            assert header.session_title == "Integration Test"
            assert header.model == "test-model"

    def test_header_default_values(self):
        """SessionHeader should have sensible default values"""
        if not HEADER_EXISTS:
            pytest.skip("SessionHeader not yet implemented")

        header = SessionHeader()
        assert header.session_title == ""
        assert header.parent_session_id is None
        assert header.model is None
