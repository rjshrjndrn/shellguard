// client.check(): ask the shared daemon; start it if nobody answers.
//
//   connect ~/.cache/shellguard/sock ── ok ──▶ one JSON line out, one in
//        │ ENOENT / ECONNREFUSED (not running, or a crashed one left its file)
//        ▼
//   spawn `<command> --serve --socket <sock>` detached, retry until startTimeoutMs
//   (a spawned daemon that exits, e.g. "already running" while an old one shuts
//    down, is spawned again; the daemon's flock keeps it to one)
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, mkdirSync, unlinkSync, existsSync } from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { check, defaultSocket } from "./client.ts";

const PY = path.resolve(import.meta.dirname, "../../.venv/bin/python");
const SG = [PY, "-m", "shellguard"];
const dirs: string[] = [];

function tmpSock(): string {
  const d = mkdtempSync("/tmp/sgc"); // unix socket paths max ~104 bytes on macOS
  dirs.push(d);
  return path.join(d, "run", "sock");
}

after(() => {
  // removing the socket makes any daemon we started exit ("socket gone")
  for (const d of dirs) rmSync(d, { recursive: true, force: true });
});

function fakeServer(sock: string, onLine: (s: net.Socket, line: string) => void): Promise<net.Server> {
  mkdirSync(path.dirname(sock), { recursive: true });
  const srv = net.createServer((s) => s.once("data", (b) => onLine(s, b.toString())));
  return new Promise((res) => srv.listen(sock, () => res(srv)));
}

test("default socket matches the daemon's", () => {
  assert.equal(defaultSocket(), path.join(os.homedir(), ".cache", "shellguard", "sock"));
});

test("no daemon: starts one, then answers warm in a few ms", async () => {
  const sock = tmpSock();
  const out = await check("cd /tmp && rm -rf build && ls", { socket: sock, command: SG, startTimeoutMs: 20000 });
  assert.ok(!("error" in out));
  assert.equal(out.label, "dangerous");
  assert.deepEqual(out.flagged.map((f) => f.part), ["rm -rf build"]);

  const ms: number[] = [];
  for (let i = 0; i < 50; i++) {
    const t = performance.now();
    await check("git push --force origin main", { socket: sock, command: SG });
    ms.push(performance.now() - t);
  }
  ms.sort((a, b) => a - b);
  console.log(`warm check from node: p50 ${ms[25].toFixed(2)} ms, p95 ${ms[47].toFixed(2)} ms`);
  assert.ok(ms[25] < 5, `p50 ${ms[25]} ms`);
});

test("leftover socket file from a crashed daemon: replaced", async () => {
  const sock = tmpSock();
  mkdirSync(path.dirname(sock), { recursive: true, mode: 0o700 });
  spawnSync(PY, ["-c", "import socket,sys; socket.socket(socket.AF_UNIX).bind(sys.argv[1])", sock]);
  assert.ok(existsSync(sock));
  const out = await check("ls", { socket: sock, command: SG, startTimeoutMs: 20000 });
  assert.ok(!("error" in out) && out.label === "safe");
});

test("daemon went away mid-session: next check brings a new one", async () => {
  const sock = tmpSock();
  await check("ls", { socket: sock, command: SG, startTimeoutMs: 20000 });
  // old daemon notices within ~1 s and exits, still holding its lock meanwhile:
  // the first respawn says "already running" and must be retried
  unlinkSync(sock);
  const out = await check("ls", { socket: sock, command: SG, startTimeoutMs: 20000 });
  assert.ok(!("error" in out) && out.label === "safe");
});

test("shellguard not installed: fails fast with a clear error", async () => {
  const t = performance.now();
  await assert.rejects(
    check("ls", { socket: tmpSock(), command: ["/nonexistent/shellguard"], startTimeoutMs: 20000 }),
    /cannot start shellguard/,
  );
  assert.ok(performance.now() - t < 2000);
});

test("daemon never answers: times out", async () => {
  const sock = tmpSock();
  const srv = await fakeServer(sock, () => {});
  const t = performance.now();
  await assert.rejects(check("ls", { socket: sock, command: SG, timeoutMs: 300 }), /timed out/);
  assert.ok(performance.now() - t < 1500);
  srv.close();
});

test("daemon hangs up: error", async () => {
  const sock = tmpSock();
  const srv = await fakeServer(sock, (s) => s.destroy());
  await assert.rejects(check("ls", { socket: sock, command: SG }), /closed/);
  srv.close();
});

test("daemon error reply is passed through for decide()", async () => {
  const sock = tmpSock();
  const srv = await fakeServer(sock, (s) => s.end('{"error": "bad request: x"}\n'));
  assert.deepEqual(await check("ls", { socket: sock, command: SG }), { error: "bad request: x" });
  srv.close();
});
