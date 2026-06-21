"""Runs the Hugo build to produce the static site output.

Not wired into RebuildOrchestrator: the Docker image's build stage already
runs Hugo, so the orchestrator never needs to build twice. This class exists
as a clean, independent abstraction for local preview tooling or a future
non-Docker deploy path.
"""

import subprocess
from pathlib import Path


class HugoSiteBuilder:
    """Single responsibility: invoke `hugo` against the repo and report
    success/failure. Knows nothing about git or Docker."""

    def __init__(self, repo_path: Path, output_dir: Path):
        self._repo_path = repo_path
        self._output_dir = output_dir

    def build(self) -> None:
        subprocess.run(
            [
                "hugo", "--minify", "--gc",
                "--source", str(self._repo_path),
                "--destination", str(self._output_dir),
            ],
            check=True,
        )
