"""make hook-pi / unhook-pi: install the pi extension by copying hooks/pi/.

`-o install` tells make to treat the global `uv tool install` as already done, so these
tests never touch the real shellguard install or ~/.pi.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "hooks" / "pi"


def make(*args, **env):
    extra = [f"{k}={v}" for k, v in env.items()]
    return subprocess.run(["make", "-s", "-o", "install", *args, *extra], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)


def test_hook_pi_copies_extension_without_tests(tmp_path):
    dest = tmp_path / "extensions" / "shellguard"
    r = make("hook-pi", PI_EXT=dest)
    assert r.returncode == 0, r.stderr
    want = sorted(p.name for p in SRC.glob("*.ts") if not p.name.endswith(".test.ts"))
    assert sorted(p.name for p in dest.iterdir()) == want
    assert "index.ts" in want
    for name in want:
        assert (dest / name).read_bytes() == (SRC / name).read_bytes()


def test_hook_pi_again_replaces_stale_files(tmp_path):
    dest = tmp_path / "shellguard"
    dest.mkdir()
    (dest / "old.ts").write_text("stale")
    (dest / "index.ts").write_text("stale")
    assert make("hook-pi", PI_EXT=dest).returncode == 0
    assert not (dest / "old.ts").exists()
    assert (dest / "index.ts").read_bytes() == (SRC / "index.ts").read_bytes()


def test_unhook_pi_removes_extension(tmp_path):
    dest = tmp_path / "shellguard"
    make("hook-pi", PI_EXT=dest)
    r = make("unhook-pi", PI_EXT=dest, SG_SOCK=tmp_path / "no-daemon" / "sock")
    assert r.returncode == 0, r.stderr
    assert not dest.exists()


def test_unhook_pi_when_not_installed_is_fine(tmp_path):
    r = make("unhook-pi", PI_EXT=tmp_path / "nothing", SG_SOCK=tmp_path / "no-daemon" / "sock")
    assert r.returncode == 0, r.stderr


def test_unhook_pi_stops_daemon_by_removing_its_socket(tmp_path):
    # the daemon exits on its own within ~1 s once its socket file is gone
    sock = tmp_path / "run" / "sock"
    sock.parent.mkdir()
    sock.write_text("")
    make("unhook-pi", PI_EXT=tmp_path / "x", SG_SOCK=sock)
    assert not sock.exists()


def test_hook_targets_listed_in_help():
    out = make("help").stdout
    assert "hook-pi" in out and "unhook-pi" in out
