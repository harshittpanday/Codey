from __future__ import annotations

import sys
from pathlib import Path

# If this file is executed directly or if src/codey is at sys.path[0],
# importing 'git' would resolve to this file (git.py) instead of GitPython.
_file_path = Path(__file__).resolve()
_codey_dir = _file_path.parent
_src_dir = _codey_dir.parent

if sys.path and Path(sys.path[0]).resolve() == _codey_dir:
    sys.path.pop(0)
    if str(_src_dir) not in sys.path:
        sys.path.insert(0, str(_src_dir))

from git import NULL_TREE, Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError

try:
    from .models import CommitFileRecord, CommitRecord
except ImportError:
    from codey.models import CommitFileRecord, CommitRecord


class GitRepositoryError(RuntimeError):
    """Raised when a Git repository cannot be accessed."""


def discover_repository(path: Path) -> Path | None:
    """Return the Git repository root if one exists."""
    try:
        repo = Repo(path, search_parent_directories=True)
        if repo.working_tree_dir:
            return Path(repo.working_tree_dir).resolve()
        return None
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None


def open_repository(path: Path) -> Repo:
    """Open the Git repository containing path."""
    try:
        return Repo(path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise GitRepositoryError(
            f"No Git repository found for {path}"
        ) from exc


def collect_commits(
    repo: Repo,
    limit: int | None = None,
) -> list[CommitRecord]:
    """Collect commit history and changed-file statistics."""
    commits: list[CommitRecord] = []

    iterator = (
        repo.iter_commits(max_count=limit)
        if limit is not None
        else repo.iter_commits()
    )

    for commit in iterator:
        changed: list[CommitFileRecord] = []

        if commit.parents:
            parent = commit.parents[0]
            diffs = parent.diff(commit, create_patch=True)
        else:
            diffs = commit.diff(
                NULL_TREE,
                create_patch=True,
            )

        for diff in diffs:
            patch = diff.diff

            if isinstance(patch, bytes):
                patch = patch.decode("utf-8", errors="replace")

            path = diff.b_path or diff.a_path or ""
            if patch:
                additions = sum(
                    1
                    for line in patch.splitlines()
                    if line.startswith("+") and not line.startswith("+++")
                )
                deletions = sum(
                    1
                    for line in patch.splitlines()
                    if line.startswith("-") and not line.startswith("---")
                )
            else:
                additions = 0
                deletions = 0

            changed.append(
                CommitFileRecord(
                    path=path,
                    additions=additions,
                    deletions=deletions,
                )
            )

        commits.append(
            CommitRecord(
                sha=commit.hexsha,
                author=str(commit.author),
                timestamp=commit.committed_datetime.isoformat(),
                message=commit.message.strip(),
                parents=tuple(parent.hexsha for parent in commit.parents),
                files=tuple(changed),
            )
        )

    return commits
    