// Claude Code PreToolUse hook: one process per Bash call, reusing the pi client + decide.
//
//   stdin {"tool_name":"Bash","tool_input":{"command":"..."}}
//     │ commandOf          not Bash / no command ──▶ print nothing, exit 0
//     ▼
//   client.check ──▶ decide ──▶ toReply
//     allow   ──▶ print nothing (Claude Code's own permission flow decides)
//     ask     ──▶ permissionDecision "ask", reason = flagged parts
//     failed  ──▶ "ask" + systemMessage "shellguard unavailable"
//   never "allow": that would skip Claude Code's own permission checks
import { test, after } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, existsSync } from "node:fs";
import path from "node:path";
import { commandOf, toReply } from "./hook.ts";
import type { Check } from "../pi/decide.ts";

const HOOK = path.resolve(import.meta.dirname, "hook.ts");
const PY = path.resolve(import.meta.dirname, "../../.venv/bin/python");
const dirs: string[] = [];
after(() => {
  for (const d of dirs) rmSync(d, { recursive: true, force: true }); // socket gone -> daemon exits
});

const dangerous: Check = {
  command: "mkdir -p /tmp/t && rm -r /tmp/t",
  label: "dangerous",
  danger_probability: 0.467,
  flagged: [{ part: "rm -r /tmp/t", danger_probability: 0.467 }],
};

// --- commandOf: which events we check -------------------------------------------------

test("Bash event gives its command", () => {
  assert.equal(commandOf({ tool_name: "Bash", tool_input: { command: "rm -rf /" } }), "rm -rf /");
});

test("other tools, empty or junk input give null", () => {
  assert.equal(commandOf({ tool_name: "Read", tool_input: { file_path: "/etc/passwd" } }), null);
  assert.equal(commandOf({ tool_name: "Bash", tool_input: { command: "   " } }), null);
  assert.equal(commandOf({ tool_name: "Bash", tool_input: {} }), null);
  assert.equal(commandOf(null), null);
  assert.equal(commandOf("nope"), null);
});

// --- toReply: decide() -> Claude Code hook JSON ------------------------------------------

test("allow prints nothing", () => {
  assert.equal(toReply({ action: "allow" }), null);
});

test("ask -> permissionDecision ask with the flagged parts as reason", () => {
  const r = toReply({ action: "ask", check: dangerous, parts: dangerous.flagged })!;
  assert.equal(r.hookSpecificOutput.hookEventName, "PreToolUse");
  assert.equal(r.hookSpecificOutput.permissionDecision, "ask");
  assert.match(r.hookSpecificOutput.permissionDecisionReason, /shellguard/);
  assert.match(r.hookSpecificOutput.permissionDecisionReason, /rm -r \/tmp\/t \(0\.467\)/);
  assert.equal(r.systemMessage, undefined);
});

test("failed -> ask, plus a systemMessage saying the command was not checked", () => {
  const r = toReply({ action: "failed", error: "daemon did not start" })!;
  assert.equal(r.hookSpecificOutput.permissionDecision, "ask");
  assert.match(r.hookSpecificOutput.permissionDecisionReason, /daemon did not start/);
  assert.match(r.systemMessage!, /shellguard unavailable/);
  assert.match(r.systemMessage!, /not checked/);
});

test("block (no UI) still maps to ask: Claude Code always has someone to ask", () => {
  const r = toReply({ action: "block", reason: "x" })!;
  assert.equal(r.hookSpecificOutput.permissionDecision, "ask");
});

test("never allow", () => {
  const decisions = [
    { action: "allow" },
    { action: "ask", check: dangerous, parts: dangerous.flagged },
    { action: "failed", error: "e" },
    { action: "block", reason: "r" },
  ] as const;
  for (const d of decisions) assert.notEqual(toReply(d)?.hookSpecificOutput.permissionDecision, "allow");
});

// --- end to end: node hook.ts < event, against a real daemon on a temp socket -----------

function run(event: unknown, cmd = `${PY} -m shellguard`) {
  const d = mkdtempSync("/tmp/sgh"); // unix socket paths max ~104 bytes on macOS
  dirs.push(d);
  const sock = path.join(d, "sock");
  const r = spawnSync("node", [HOOK], {
    input: typeof event === "string" ? event : JSON.stringify(event),
    env: { ...process.env, SHELLGUARD_SOCKET: sock, SHELLGUARD_CMD: cmd },
    encoding: "utf8",
    timeout: 20000,
  });
  return { ...r, sock };
}

const bash = (command: string) => ({ hook_event_name: "PreToolUse", tool_name: "Bash", tool_input: { command } });

test("e2e: dangerous chain -> ask naming the dangerous part", () => {
  const r = run(bash("mkdir -p /tmp/tester && ls -ld /tmp/tester && rm -r /tmp/tester"));
  assert.equal(r.status, 0, r.stderr);
  const out = JSON.parse(r.stdout);
  assert.equal(out.hookSpecificOutput.permissionDecision, "ask");
  assert.match(out.hookSpecificOutput.permissionDecisionReason, /rm -r \/tmp\/tester/);
});

test("e2e: safe command -> no output, exit 0", () => {
  const r = run(bash("ls -la"));
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "");
});

test("e2e: non-Bash tool -> no output, daemon not even started", () => {
  const r = run({ tool_name: "Read", tool_input: { file_path: "/etc/passwd" } });
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "");
  assert.equal(existsSync(r.sock), false);
});

test("e2e: garbage stdin -> no output, exit 0", () => {
  const r = run("not json");
  assert.equal(r.status, 0, r.stderr);
  assert.equal(r.stdout, "");
});

test("e2e: shellguard cannot start -> ask + systemMessage, exit 0", () => {
  const r = run(bash("ls"), "/nonexistent/shellguard");
  assert.equal(r.status, 0, r.stderr);
  const out = JSON.parse(r.stdout);
  assert.equal(out.hookSpecificOutput.permissionDecision, "ask");
  assert.match(out.systemMessage, /shellguard unavailable/);
});

// --- latency: Claude Code waits on this before every Bash call --------------------------

test("e2e: with the daemon warm, a check takes < 150 ms (median of 5)", () => {
  const d = mkdtempSync("/tmp/sgh");
  dirs.push(d);
  const env = { ...process.env, SHELLGUARD_SOCKET: path.join(d, "sock"), SHELLGUARD_CMD: `${PY} -m shellguard` };
  const once = () => {
    const t = performance.now();
    const r = spawnSync("node", [HOOK], { input: JSON.stringify(bash("git status")), env, encoding: "utf8" });
    assert.equal(r.status, 0, r.stderr);
    return performance.now() - t;
  };
  once(); // cold: starts the daemon (~1.5 s)
  const ms = Array.from({ length: 5 }, once).sort((a, b) => a - b);
  console.log(`hook latency ms: ${ms.map((x) => x.toFixed(0)).join(" ")}`);
  assert.ok(ms[2] < 150, `median ${ms[2].toFixed(0)} ms`);
});
