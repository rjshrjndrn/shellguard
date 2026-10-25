"""Shared daemon: load the model once, answer check() over a unix socket.

  shellguard --serve        # ~/.cache/shellguard/sock, one JSON line in, one out

  agent A ─┐                      ┌────────────────────────────┐
  agent B ─┼── ~/.cache/shellguard/sock ──▶│ serve(): check() per line   │
  agent C ─┘                      └────────────────────────────┘

Single instance: an exclusive flock on <sock>.lock. Whoever holds it owns the socket
path, so it may remove a leftover socket file from a crashed daemon. The kernel drops
the lock when the process dies, so a crash never blocks the next start.

Exits on its own (clients respawn it) when:
- idle for `idle` seconds                    -> no orphan forever
- the model file changed or vanished         -> retrain/reinstall picks up the new model
- its socket file was removed or replaced    -> it would be unreachable
"""
import fcntl
import json
import os
import socket
import socketserver
import threading
import time
from collections.abc import Callable
from pathlib import Path


def default_socket() -> Path:
    return Path.home() / ".cache" / "shellguard" / "sock"


def request(sock: Path, command: str, timeout: float = 1.0) -> dict:
    """Client side: one request, one response. Raises OSError if no daemon answers."""
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(timeout)
        s.connect(str(sock))
        s.sendall((json.dumps({"command": command}) + "\n").encode())
        data = b""
        while not data.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                raise ConnectionError("daemon closed the connection")
            data += chunk
    return json.loads(data)


def _file_id(path: Path):
    try:
        st = path.stat()
        return st.st_ino, st.st_mtime_ns, st.st_size
    except FileNotFoundError:
        return None


def serve(sock: Path, model_path: Path | None = None, idle: float = 1800, poll: float = 1.0,
          score: Callable[[list[str]], list[float]] | None = None) -> str:
    """Run until a stop condition; return why ("idle", "model changed", ...)."""
    from shellguard.check import _model_scorer, check
    from shellguard.model_a import MODEL_PATH

    model_path = model_path or MODEL_PATH
    score = score or _model_scorer
    sock.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(sock.parent, 0o700)

    lock = open(sock.with_name(sock.name + ".lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return "already running"

    scoring = threading.Lock()  # one model, one caller at a time; checks are ~1 ms
    last = [time.monotonic()]

    def answer(line: bytes) -> dict:
        try:
            command = json.loads(line)["command"]
            if not isinstance(command, str) or not command.strip():
                raise ValueError("command must be a non-empty string")
        except (ValueError, KeyError, TypeError) as e:
            return {"error": f"bad request: {e}"}
        with scoring:
            return {"command": command, **check(command, score)}

    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            for line in self.rfile:
                last[0] = time.monotonic()
                self.wfile.write((json.dumps(answer(line)) + "\n").encode())
                self.wfile.flush()
                last[0] = time.monotonic()

    model_id = _file_id(model_path)
    sock.unlink(missing_ok=True)  # we hold the lock: any socket file is a leftover
    server = socketserver.ThreadingUnixStreamServer(str(sock), Handler)
    server.daemon_threads = True
    os.chmod(sock, 0o600)
    sock_id = _file_id(sock)
    threading.Thread(target=server.serve_forever, args=(poll,), daemon=True).start()
    if score is _model_scorer:  # load the model now, not on the first request
        with scoring:
            score(["ls"])

    reason = ""
    while not reason:
        time.sleep(poll)
        if _file_id(sock) != sock_id:
            reason = "socket gone"
        elif _file_id(model_path) != model_id:
            reason = "model changed"
        elif time.monotonic() - last[0] > idle:
            reason = "idle"

    server.shutdown()
    server.server_close()
    if reason != "socket gone":
        sock.unlink(missing_ok=True)
    lock.close()  # releases the flock
    return reason
