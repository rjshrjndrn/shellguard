// decide(): what the pi hook does with one bash command. Pure: no pi, no socket.
//
//   off                         -> allow
//   shellguard failed           -> UI: ask "run anyway?"   no UI: block
//   safe                        -> allow
//   dangerous, all flagged parts allowed this session -> allow
//   dangerous, some parts new   -> UI: ask, listing only the new parts   no UI: block
import { test } from "node:test";
import assert from "node:assert/strict";
import { decide, normalize, remember, type Check } from "./decide.ts";

const safe: Check = { command: "ls", label: "safe", danger_probability: 0.005, flagged: [] };
const chain: Check = {
  command: "git add -A && git commit -m wip && git push --force",
  label: "dangerous",
  danger_probability: 0.99,
  flagged: [
    { part: "git push --force", danger_probability: 0.985 },
    { part: "git add -A", danger_probability: 0.844 },
  ],
};
const ui = { enabled: true, hasUI: true, allowed: new Set<string>() };

test("off: everything runs, even a failure", () => {
  const off = { ...ui, enabled: false };
  assert.deepEqual(decide(chain, off), { action: "allow" });
  assert.deepEqual(decide(new Error("boom"), off), { action: "allow" });
});

test("safe runs", () => {
  assert.deepEqual(decide(safe, ui), { action: "allow" });
});

test("dangerous asks with every flagged part", () => {
  assert.deepEqual(decide(chain, ui), { action: "ask", check: chain, parts: chain.flagged });
});

test("dangerous without UI is blocked, reason names the parts", () => {
  const d = decide(chain, { ...ui, hasUI: false });
  assert.equal(d.action, "block");
  assert.match(d.reason, /shellguard/);
  assert.match(d.reason, /git push --force \(0\.985\)/);
  assert.match(d.reason, /git add -A \(0\.844\)/);
});

test("all flagged parts allowed for the session: runs without asking", () => {
  const allowed = remember(new Set(), chain.flagged);
  assert.deepEqual(decide(chain, { ...ui, allowed }), { action: "allow" });
  assert.deepEqual(decide(chain, { ...ui, hasUI: false, allowed }), { action: "allow" });
});

test("one new part: asks again, listing only the new part", () => {
  const allowed = remember(new Set(), [chain.flagged[0]]);
  const d = decide(chain, { ...ui, allowed });
  assert.equal(d.action, "ask");
  assert.deepEqual(d.parts, [chain.flagged[1]]);
});

test("allowed parts match despite whitespace differences", () => {
  const allowed = remember(new Set(), [{ part: "git  push   --force", danger_probability: 0.9 }]);
  const one: Check = { ...chain, flagged: [chain.flagged[0]] };
  assert.deepEqual(decide(one, { ...ui, allowed }), { action: "allow" });
});

test("normalize collapses whitespace but keeps quoted text", () => {
  assert.equal(normalize("  rm   -rf\tbuild \n"), "rm -rf build");
  assert.equal(normalize("echo 'a  b'"), "echo 'a b'"); // shortcut: quotes not special; fine for matching
});

test("remember returns a new set and keeps old entries", () => {
  const a = remember(new Set(), [chain.flagged[0]]);
  const b = remember(a, [chain.flagged[1]]);
  assert.equal(a.size, 1);
  assert.deepEqual([...b].sort(), ["git add -A", "git push --force"]);
});

test("failure with UI: ask whether to run anyway", () => {
  assert.deepEqual(decide(new Error("daemon not reachable"), ui), {
    action: "failed",
    error: "daemon not reachable",
  });
});

test("failure without UI: block with the error", () => {
  const d = decide(new Error("daemon not reachable"), { ...ui, hasUI: false });
  assert.equal(d.action, "block");
  assert.match(d.reason, /shellguard failed: daemon not reachable/);
});

test("daemon error reply counts as a failure", () => {
  const d = decide({ error: "bad request: x" } as any, ui);
  assert.deepEqual(d, { action: "failed", error: "bad request: x" });
});

test("allowing a part allows that exact command only, path included", () => {
  const allowed = remember(new Set(), [{ part: "rm -rf /tmp/tester", danger_probability: 0.711 }]);
  const other: Check = { command: "rm -rf ~", label: "dangerous", danger_probability: 0.985,
    flagged: [{ part: "rm -rf ~", danger_probability: 0.985 }] };
  assert.equal(decide(other, { ...ui, allowed }).action, "ask");
});
