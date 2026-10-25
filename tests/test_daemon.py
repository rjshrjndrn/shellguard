"""shellguard --serve: one shared daemon, model loaded once, JSON lines over a unix socket.

  request  {"command": "cd /tmp && rm -rf build"}\n
  response {"command": ..., "label": ..., "danger_probability": ..., "flagged": [...]}\n

Lifecycle rules (each one a test below):
- an exclusive flock on <sock>.lock is the single-instance guard; a second daemon exits
- the lock holder removes a leftover socket file before binding
- socket dir 0700, socket 0600: only this user can talk to it
- exits when idle, when the model file changes (retrain/reinstall), or when its socket
  file is removed/replaced (otherwise it would be an unreachable orphan)
"""
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from shellguard.daemon import default_socket, request, serve


def fake(commands):
    table = {"chmod -R 777 build": 0.82, "cd /tmp && chmod -R 777 build": 0.62}
    return [table.get(c, 0.01) for c in commands]


@pytest.fixture
def tmp():
    # unix socket paths max ~104 bytes on macOS; pytest's tmp_path is too long
    d = Path(tempfile.mkdtemp(dir="/tmp", prefix="sg"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


class Daemon:
    def __init__(self, tmp, **kw):
        self.sock = tmp / "run" / "sock"
        self.model = tmp / "model.bin"
        self.model.write_bytes(b"v1")
        self.result = None
        kw = {"model_path": self.model, "idle": 30, "poll": 0.05, "score": fake, **kw}
        self.thread = threading.Thread(target=self._run, args=(kw,), daemon=True)
        self.thread.start()
        wait_for(lambda: connectable(self.sock))  # not exists(): a leftover file exists too

    def _run(self, kw):
        self.result = serve(self.sock, **kw)

    def ask(self, command):
        return request(self.sock, command, timeout=2)

    def wait_exit(self, timeout=3):
        self.thread.join(timeout)
        assert not self.thread.is_alive(), "daemon did not exit"
        return self.result


def connectable(sock):
    with socket.socket(socket.AF_UNIX) as s:
        try:
            s.connect(str(sock))
            return True
        except OSError:
            return False


def wait_for(cond, timeout=3):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def test_scores_over_socket(tmp):
    d = Daemon(tmp)
    out = d.ask("cd /tmp && chmod -R 777 build")
    assert out == {"command": "cd /tmp && chmod -R 777 build", "label": "dangerous", "danger_probability": 0.82,
                   "flagged": [{"part": "chmod -R 777 build", "danger_probability": 0.82}]}
    assert d.ask("ls")["label"] == "safe"


def test_several_requests_on_one_connection(tmp):
    d = Daemon(tmp)
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(str(d.sock))
        f = s.makefile("rw")
        for cmd in ["ls", "rm -rf build", "pwd"]:
            f.write(json.dumps({"command": cmd}) + "\n")
            f.flush()
            assert json.loads(f.readline())["command"] == cmd


@pytest.mark.parametrize("line", ["not json", '{"cmd": "ls"}', '{"command": 3}', '{"command": "  "}'])
def test_bad_request_gets_error_and_daemon_keeps_serving(tmp, line):
    d = Daemon(tmp)
    with socket.socket(socket.AF_UNIX) as s:
        s.connect(str(d.sock))
        f = s.makefile("rw")
        f.write(line + "\n")
        f.flush()
        assert "error" in json.loads(f.readline())
    assert d.ask("ls")["label"] == "safe"


def test_only_this_user_can_connect(tmp):
    d = Daemon(tmp)
    assert stat.S_IMODE(d.sock.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(d.sock.stat().st_mode) == 0o600


def test_second_daemon_exits_and_first_keeps_serving(tmp):
    d = Daemon(tmp)
    assert serve(d.sock, model_path=d.model, idle=30, poll=0.05, score=fake) == "already running"
    assert d.ask("ls")["label"] == "safe"


def test_leftover_socket_file_is_replaced(tmp):
    sock = tmp / "run" / "sock"
    sock.parent.mkdir(mode=0o700)
    s = socket.socket(socket.AF_UNIX)
    s.bind(str(sock))
    s.close()  # crashed daemon: file stays, nobody listens
    with pytest.raises(OSError):
        request(sock, "ls", timeout=1)
    d = Daemon(tmp)
    assert d.ask("ls")["label"] == "safe"


def test_exits_when_idle(tmp):
    d = Daemon(tmp, idle=0.3)
    assert d.wait_exit() == "idle"
    assert not d.sock.exists()


def test_requests_keep_it_alive(tmp):
    d = Daemon(tmp, idle=0.4)
    for _ in range(6):
        time.sleep(0.15)
        d.ask("ls")
    assert d.thread.is_alive()


@pytest.mark.parametrize("change", ["rewrite", "delete"])
def test_exits_when_model_file_changes(tmp, change):
    d = Daemon(tmp)
    if change == "rewrite":
        d.model.write_bytes(b"v2 retrained")
    else:
        d.model.unlink()
    assert d.wait_exit() == "model changed"


def test_exits_when_socket_file_is_removed(tmp):
    d = Daemon(tmp)
    d.sock.unlink()
    assert d.wait_exit() == "socket gone"


def test_exit_releases_lock_so_next_daemon_starts(tmp):
    d = Daemon(tmp, idle=0.2)
    d.wait_exit()
    d2 = Daemon(tmp)
    assert d2.ask("ls")["label"] == "safe"


def test_default_socket_is_in_user_cache():
    assert default_socket() == Path.home() / ".cache" / "shellguard" / "sock"


def test_cli_serve_with_real_model(tmp):
    sock = tmp / "run" / "sock"
    p = subprocess.Popen([sys.executable, "-m", "shellguard", "--serve", "--socket", str(sock), "--idle", "20"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    try:
        wait_for(lambda: sock.exists(), timeout=10)
        out = request(sock, "cd /tmp && rm -rf build && ls", timeout=10)  # first call waits for model load
        assert [f["part"] for f in out["flagged"]] == ["rm -rf build"]
        t = time.perf_counter()
        for _ in range(50):
            request(sock, "git push --force origin main", timeout=2)
        ms = (time.perf_counter() - t) / 50 * 1000
        print(f"\nwarm round trip: {ms:.2f} ms")
        assert ms < 5
    finally:
        p.terminate()
        p.wait(5)
