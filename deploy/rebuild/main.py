"""CLI entrypoint invoked by cron/systemd. Wires concrete paths/names into
the classes above and runs one rebuild cycle.

Update REPO_PATH below to match where this repo is actually cloned on the
VM (the README's manual deployment checklist clones it to /opt/mindloop).
"""

import logging
import sys
from pathlib import Path

from .container_manager import DockerContainerManager
from .git_updater import GitRepoUpdater
from .orchestrator import RebuildOrchestrator

REPO_PATH = Path("/opt/mindloop")
IMAGE_NAME = "mindloop-portfolio:latest"
CONTAINER_NAME = "mindloop-portfolio"
HOST_PORT = 8080


def main() -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    )

    git_updater = GitRepoUpdater(repo_path=REPO_PATH)
    container_manager = DockerContainerManager(
        repo_path=REPO_PATH, image_name=IMAGE_NAME,
        container_name=CONTAINER_NAME, host_port=HOST_PORT,
    )
    orchestrator = RebuildOrchestrator(git_updater, container_manager)

    try:
        orchestrator.run_once()
    except Exception:
        logging.exception("Rebuild cycle failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
