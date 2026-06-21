"""Pulls the latest site content from the GitHub repo."""

import subprocess
from pathlib import Path


class GitRepoUpdater:
    """Single responsibility: know whether the local clone of the content
    repo is behind origin, and pull if so. Knows nothing about Docker or Hugo."""

    def __init__(self, repo_path: Path, branch: str = "main"):
        self._repo_path = repo_path
        self._branch = branch

    def _run_git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(self._repo_path), *args],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    def fetch(self) -> None:
        self._run_git("fetch", "origin", self._branch)

    def has_remote_changes(self) -> bool:
        local_sha = self._run_git("rev-parse", "HEAD")
        remote_sha = self._run_git("rev-parse", f"origin/{self._branch}")
        return local_sha != remote_sha

    def pull(self) -> None:
        self._run_git("pull", "--ff-only", "origin", self._branch)
