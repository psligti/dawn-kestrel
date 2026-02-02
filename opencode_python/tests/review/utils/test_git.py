"""Tests for Git utility functions."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from git import Repo as GitRepo, Diff, Commit, Tree, Blob
from git.exc import InvalidGitRepositoryError, NoSuchPathError

from opencode_python.agents.review.utils.git import (
    get_changed_files,
    get_diff,
    get_repo_tree,
    GitError,
    InvalidRefError,
    RepositoryNotFoundError,
)


@pytest.fixture
def repo_root(tmp_path: Path) -> str:
    return str(tmp_path)


@pytest.fixture
def mock_repo() -> Mock:
    return Mock(spec=GitRepo)


@pytest.fixture
def mock_commit() -> Mock:
    return Mock(spec=Commit)


@pytest.fixture
def mock_tree() -> Mock:
    return Mock(spec=Tree)


@pytest.fixture
def mock_blob() -> Mock:
    blob = Mock(spec=Blob)
    blob.path = "src/module.py"
    blob.name = "module.py"
    blob.hexsha = "abc123"
    blob.type = "blob"
    blob.size = 100
    return blob


class TestGetChangedFiles:
    async def test_get_changed_files_success(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "feature-branch"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_commit.diff.return_value = [
            Mock(spec=Diff, a_path="file1.py", b_path="file1.py", change_type="M"),
            Mock(spec=Diff, a_path=None, b_path="file2.py", change_type="A"),
            Mock(spec=Diff, a_path="file3.py", b_path=None, change_type="D"),
        ]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_changed_files(repo_root, base_ref, head_ref)

            assert isinstance(result, list)
            assert len(result) == 3
            assert "file1.py" in result
            assert "file2.py" in result
            assert "file3.py" in result

    async def test_get_changed_files_empty_diff(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "main"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_commit.diff.return_value = []

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_changed_files(repo_root, base_ref, head_ref)

            assert result == []

    async def test_get_changed_files_invalid_ref(self, repo_root: str, mock_repo: Mock):
        base_ref = "nonexistent-ref"
        head_ref = "main"

        mock_repo.commit.side_effect = ValueError("Invalid reference")

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            with pytest.raises(InvalidRefError, match="Invalid Git reference"):
                await get_changed_files(repo_root, base_ref, head_ref)

    async def test_get_changed_files_repo_not_found(self, repo_root: str):
        base_ref = "main"
        head_ref = "feature-branch"

        with patch("opencode_python.agents.review.utils.git.GitRepo") as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repository")

            with pytest.raises(RepositoryNotFoundError, match="Not a git repository"):
                await get_changed_files(repo_root, base_ref, head_ref)

    async def test_get_changed_files_path_not_found(self):
        base_ref = "main"
        head_ref = "feature-branch"

        with patch("opencode_python.agents.review.utils.git.GitRepo") as mock_repo_class:
            mock_repo_class.side_effect = NoSuchPathError("Path does not exist")

            with pytest.raises(RepositoryNotFoundError, match="Path does not exist"):
                await get_changed_files("/nonexistent/path", base_ref, head_ref)

    async def test_get_changed_files_binary_files_excluded(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "feature-branch"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_commit.diff.return_value = [
            Mock(spec=Diff, a_path="file.py", b_path="file.py", change_type="M"),
            Mock(spec=Diff, a_path="image.png", b_path="image.png", change_type="M"),
            Mock(spec=Diff, a_path="data.bin", b_path="data.bin", change_type="A"),
        ]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_changed_files(repo_root, base_ref, head_ref)

            assert "file.py" in result
            assert "image.png" not in result
            assert "data.bin" not in result

    async def test_get_changed_files_submodules_included(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "feature-branch"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_commit.diff.return_value = [
            Mock(spec=Diff, a_path="file.py", b_path="file.py", change_type="M"),
            Mock(spec=Diff, a_path="submodule/", b_path="submodule/", change_type="M"),
        ]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_changed_files(repo_root, base_ref, head_ref)

            assert len(result) == 2


class TestGetDiff:
    async def test_get_diff_success(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "feature-branch"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_diff = Mock(spec=Diff)
        mock_diff.diff = b"@@ -1,3 +1,4 @@\n+new line"
        mock_commit.diff.return_value = [mock_diff]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_diff(repo_root, base_ref, head_ref)

            assert isinstance(result, str)
            assert "new line" in result

    async def test_get_diff_empty(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "main"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_commit.diff.return_value = []

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_diff(repo_root, base_ref, head_ref)

            assert result == ""

    async def test_get_diff_invalid_ref(self, repo_root: str, mock_repo: Mock):
        base_ref = "invalid-ref"
        head_ref = "main"

        mock_repo.commit.side_effect = ValueError("Invalid reference")

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            with pytest.raises(InvalidRefError, match="Invalid Git reference"):
                await get_diff(repo_root, base_ref, head_ref)

    async def test_get_diff_multiple_files(self, repo_root: str, mock_repo: Mock, mock_commit: Mock):
        base_ref = "main"
        head_ref = "feature-branch"

        mock_repo.commit.side_effect = [mock_commit, mock_commit]
        mock_diff1 = Mock(spec=Diff)
        mock_diff1.diff = b"file1 changes"
        mock_diff2 = Mock(spec=Diff)
        mock_diff2.diff = b"file2 changes"
        mock_commit.diff.return_value = [mock_diff1, mock_diff2]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_diff(repo_root, base_ref, head_ref)

            assert "file1 changes" in result
            assert "file2 changes" in result


class TestGetRepoTree:
    async def test_get_repo_tree_success(self, repo_root: str, mock_repo: Mock, mock_tree: Mock, mock_blob: Mock):
        mock_repo.tree.return_value = mock_tree
        mock_tree.traverse.return_value = [mock_blob]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_repo_tree(repo_root)

            assert isinstance(result, str)
            assert "module.py" in result

    async def test_get_repo_tree_empty_repo(self, repo_root: str, mock_repo: Mock, mock_tree: Mock):
        mock_repo.tree.return_value = mock_tree
        mock_tree.traverse.return_value = []

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_repo_tree(repo_root)

            assert result == ""

    async def test_get_repo_tree_nested_structure(self, repo_root: str, mock_repo: Mock, mock_tree: Mock):
        mock_repo.tree.return_value = mock_tree

        blob1 = Mock(spec=Blob)
        blob1.path = "src/core.py"
        blob1.type = "blob"

        blob2 = Mock(spec=Blob)
        blob2.path = "tests/test_core.py"
        blob2.type = "blob"

        mock_tree.traverse.return_value = [blob1, blob2]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_repo_tree(repo_root)

            assert "core.py" in result
            assert "test_core.py" in result

    async def test_get_repo_tree_repo_not_found(self, repo_root: str):
        with patch("opencode_python.agents.review.utils.git.GitRepo") as mock_repo_class:
            mock_repo_class.side_effect = InvalidGitRepositoryError("Not a git repository")

            with pytest.raises(RepositoryNotFoundError, match="Not a git repository"):
                await get_repo_tree(repo_root)

    async def test_get_repo_tree_with_directories(self, repo_root: str, mock_repo: Mock, mock_tree: Mock):
        mock_repo.tree.return_value = mock_tree

        blob = Mock(spec=Blob)
        blob.path = "src/utils/helper.py"
        blob.type = "blob"

        mock_tree.traverse.return_value = [blob]

        with patch("opencode_python.agents.review.utils.git.GitRepo", return_value=mock_repo):
            result = await get_repo_tree(repo_root)

            assert "helper.py" in result


class TestCustomExceptions:
    def test_git_error_is_exception(self):
        assert issubclass(GitError, Exception)

    def test_invalid_ref_error_inherits_git_error(self):
        assert issubclass(InvalidRefError, GitError)

    def test_repository_not_found_error_inherits_git_error(self):
        assert issubclass(RepositoryNotFoundError, GitError)

    def test_custom_exceptions_can_be_raised(self):
        with pytest.raises(GitError):
            raise GitError("Generic git error")

        with pytest.raises(InvalidRefError):
            raise InvalidRefError("Invalid ref")

        with pytest.raises(RepositoryNotFoundError):
            raise RepositoryNotFoundError("Repo not found")
