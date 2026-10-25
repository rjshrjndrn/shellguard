"""`uv tool install .` must give a working `shellguard`, run from any directory.

Proves the trained model travels inside the package instead of being looked up in the
repo's models/ folder (which does not exist next to an installed copy).
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("install")
    sh = lambda *a: subprocess.run(a, check=True, capture_output=True, text=True, timeout=300)
    sh("uv", "build", "--wheel", "-o", str(tmp / "dist"), str(ROOT))
    sh("uv", "venv", "-q", "--python", "3.12", str(tmp / "venv"))
    wheel = next((tmp / "dist").glob("*.whl"))
    sh("uv", "pip", "install", "-q", "--python", str(tmp / "venv" / "bin" / "python"), str(wheel))
    return tmp / "venv" / "bin" / "shellguard", tmp


def test_installed_cli_runs_outside_the_repo(installed):
    exe, cwd = installed
    r = subprocess.run([str(exe), "rm -rf ~"], cwd=cwd, capture_output=True, text=True, timeout=60)
    assert r.stderr == ""  # a crash also exits 1, so check this first
    assert r.returncode == 1
    assert json.loads(r.stdout)["label"] == "dangerous"
