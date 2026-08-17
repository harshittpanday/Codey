from __future__ import annotations

from pathlib import Path

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from .models import CommitFileRecord, CommitRecord


class GitRepositoryError(RuntimeError):
    """Raised when Git information cannot be read safely."""


def discover_repository(path: Path) -> Path | None:
    try:
        repo = Repo(path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return None
    if repo.bare:
        return None
    return Path(repo.working_tree_dir).resolve()


def open_repository(root: Path) -> Repo:
    try:
        repo = Repo(root)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise GitRepositoryError(f"Not a Git repository: {root}") from exc
    if repo.bare:
        raise GitRepositoryError("Bare Git repositories are not supported")
    return repo


def collect_commits(repo: Repo, limit: int | None = None) -> tuple[list[CommitRecord], list[CommitFileRecord]]:
    commits: list[CommitRecord] = []
    files: list[CommitFileRecord] = []
    commits_iter = repo.iter_commits(max_count=limit) if limit else repo.iter_commits()

    for commit in commits_iter:
        author = commit.author
        commits.append(
            CommitRecord(
                sha=commit.hexsha,
                author_name=author.name or "Unknown",
                author_email=author.email or "",
                timestamp=commit.committed_datetime,
                message=commit.message.strip(),
                parents=tuple(parent.hexsha for parent in commit.parents),
            )
        )

        parent = commit.parents[0] if commit.parents else None
        if parent is None:
            diffs = commit.diff(None, create_patch=False)
        else:
            diffs = parent.diff(commit, create_patch=False)

        for diff in diffs:
            path = diff.b_path or diff.a_path
            if not path:
                continue
            change_type = {
                "A": "added",
                "M": "modified",
                "D": "deleted",
                "R": "renamed",
                "C": "copied",
            }.get(diff.change_type, diff.change_type)
            additions = 0
            deletions = 0
            try:
                stats = commit.stats.files.get(path, {})
                additions = int(stats.get("insertions", 0))
                deletions = int(stats.get("deletions", 0))
            except (TypeError, ValueError):
                pass
            files.append(
                CommitFileRecord(
                    commit_sha=commit.hexsha,
                    path=path,
                    change_type=change_type,
                    additions=additions,
                    deletions=deletions,
                )
            )

    return commits, files
