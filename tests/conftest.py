from typing import Any

import pytest


def pytest_ignore_collect(collection_path: Any, config: Any) -> bool:
    path_str = str(collection_path)
    return "/tests/review/" in path_str


@pytest.fixture
def app():
    pytest.skip("TUI support has been removed from dawn-kestrel")
