"""Manages the lifecycle of the site's Docker container: build image,
stop the old container, start the new one."""

import subprocess
from pathlib import Path


class DockerContainerManager:
    """Single responsibility: own the Docker image/container lifecycle for
    the portfolio site. Knows nothing about git or Hugo."""

    def __init__(self, repo_path: Path, image_name: str,
                 container_name: str, host_port: int = 8080,
                 container_port: int = 8080):
        self._repo_path = repo_path
        self._image_name = image_name
        self._container_name = container_name
        self._host_port = host_port
        self._container_port = container_port

    def build_image(self) -> None:
        subprocess.run(
            ["docker", "build", "-t", self._image_name, str(self._repo_path)],
            check=True,
        )

    def stop_existing(self) -> None:
        # check=False: it's fine if the container didn't exist yet.
        subprocess.run(["docker", "rm", "-f", self._container_name], check=False)

    def start_new(self) -> None:
        subprocess.run([
            "docker", "run", "-d",
            "--name", self._container_name,
            "--read-only",
            "--tmpfs", "/data", "--tmpfs", "/config",
            "-p", f"{self._host_port}:{self._container_port}",
            "--restart", "unless-stopped",
            self._image_name,
        ], check=True)

    def redeploy(self) -> None:
        self.build_image()
        self.stop_existing()
        self.start_new()
