from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _build_stub(path: Path) -> Path:
    path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "docker $@" >>"${DOCKER_LOG}"
if [ "$1" = "compose" ]; then
  echo "compose:$2" >>"${DOCKER_LOG}"
fi
printf 'stub-%s\n' "$*"
"""
    )
    path.chmod(0o755)
    return path


def test_activation_script_runs_and_invokes_docker(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "setup" / "activate.sh"
    template = repo_root / "config" / ".env.example"

    vibe_root = tmp_path / "vibe-root"
    config_dir = vibe_root / "config"
    config_dir.mkdir(parents=True)
    shutil.copy(template, config_dir / ".env.example")

    tools_dir = vibe_root / "tools"
    tools_dir.mkdir(parents=True)
    builder = tools_dir / "build-project-images.sh"
    builder.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
echo "stub-build" >>"${DOCKER_LOG}"
"""
    )
    builder.chmod(0o755)

    docker_log = tmp_path / "docker.log"
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    _build_stub(stub_dir / "docker")

    env = os.environ.copy()
    env.update(
        {
            "VIBE_ROOT_DIR": str(vibe_root),
            "PATH": f"{stub_dir}:{env['PATH']}",
            "DOCKER_LOG": str(docker_log),
        }
    )

    responses = "\n".join(
        [
            "/srv/data",  # data dir
            "9100",  # api port
            "vibe.local",  # domain
            "client-key",  # api key
            "master-key",  # master key
            "db-secret",  # db password
            "alerts@vibe.local",  # alerts email
            "0.0.0.0",  # api host binding
            "y",  # start docker compose
        ]
    )

    result = subprocess.run(
        ["bash", str(script)],
        input=f"{responses}\n",
        text=True,
        env=env,
        cwd=repo_root,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Launching docker compose stack" in result.stdout
    assert vibe_root.joinpath(".env").exists()
    assert config_dir.joinpath(".env").exists()

    env_content = vibe_root.joinpath(".env").read_text()
    assert "API_PORT=9100" in env_content
    assert "DOMAIN=vibe.local" in env_content
    assert "API_KEY=client-key" in env_content
    assert "MASTER_API_KEY=master-key" in env_content
    assert "DB_PASSWORD=db-secret" in env_content
    assert "ADMIN_ALERT_EMAIL=alerts@vibe.local" in env_content
    assert "DATA_DIR=/srv/data" in env_content
    assert "GITHUB_SECRETS_PATH=/data/github-secrets.bin" in env_content
    assert any(line.startswith("GITHUB_SECRETS_KEY=") for line in env_content.splitlines())

    docker_calls = docker_log.read_text().strip().splitlines()
    assert any(line.startswith("docker compose up") for line in docker_calls)
    assert any(line.startswith("docker compose ps") for line in docker_calls)
    assert "stub-build" in docker_calls
