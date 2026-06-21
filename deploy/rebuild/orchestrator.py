"""Composes GitRepoUpdater and DockerContainerManager into the single
rebuild-on-change workflow that cron/systemd actually triggers."""

import logging

from .git_updater import GitRepoUpdater
from .container_manager import DockerContainerManager

logger = logging.getLogger(__name__)


class RebuildOrchestrator:
    """Single responsibility: sequence the steps (check for changes -> pull
    -> redeploy) and decide whether to act. Does not know HOW git pulls or
    HOW Docker builds — only WHEN to call each collaborator."""

    def __init__(self, git_updater: GitRepoUpdater,
                 container_manager: DockerContainerManager):
        self._git_updater = git_updater
        self._container_manager = container_manager

    def run_once(self) -> bool:
        """Returns True if a redeploy happened, False if already up to date."""
        self._git_updater.fetch()
        if not self._git_updater.has_remote_changes():
            logger.info("No remote changes; skipping rebuild.")
            return False

        logger.info("Remote changes detected; pulling and redeploying.")
        self._git_updater.pull()
        self._container_manager.redeploy()
        logger.info("Redeploy complete.")
        return True
