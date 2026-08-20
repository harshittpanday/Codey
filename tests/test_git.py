from pathlib import Path
import pytest
from git import Repo
from codey.git import (
    GitRepositoryError,
    collect_commits,
    discover_repository,
    open_repository,
)


def test_discover_repository_valid(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)

    sub_dir = repo_dir / "subdir"
    sub_dir.mkdir()

    discovered = discover_repository(sub_dir)
    assert discovered == repo_dir.resolve()


def test_discover_repository_invalid(tmp_path: Path) -> None:
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    assert discover_repository(non_repo) is None


def test_open_repository_valid(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)

    repo = open_repository(repo_dir)
    assert repo.working_tree_dir == str(repo_dir.resolve())


def test_open_repository_invalid_raises(tmp_path: Path) -> None:
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()

    with pytest.raises(GitRepositoryError):
        open_repository(non_repo)


def test_collect_commits_with_root_and_limit(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)

    # Initial commit (root commit)
    f1 = repo_dir / "file1.txt"
    f1.write_text("hello\nworld\n", encoding="utf-8")
    repo.index.add(["file1.txt"])
    c1 = repo.index.commit("Initial commit")

    # Second commit
    f2 = repo_dir / "file2.txt"
    f2.write_text("another file\n", encoding="utf-8")
    f1.write_text("hello\nmodified world\n", encoding="utf-8")
    repo.index.add(["file1.txt", "file2.txt"])
    c2 = repo.index.commit("Second commit")

    commits = collect_commits(repo)
    assert len(commits) == 2

    # Verify latest commit (c2)
    assert commits[0].sha == c2.hexsha
    assert commits[0].message == "Second commit"
    assert commits[0].parents == (c1.hexsha,)
    assert isinstance(commits[0].timestamp, str)
    assert len(commits[0].files) == 2

    # Verify root commit (c1)
    assert commits[1].sha == c1.hexsha
    assert commits[1].message == "Initial commit"
    assert commits[1].parents == ()
    assert len(commits[1].files) == 1
    assert commits[1].files[0].path == "file1.txt"
    assert commits[1].files[0].additions == 2

    # Verify limit parameter
    limited = collect_commits(repo, limit=1)
    assert len(limited) == 1
    assert limited[0].sha == c2.hexsha
