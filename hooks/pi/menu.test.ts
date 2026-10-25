// The popup, minus pi: which choice a key picks, and the lines it shows.
//
//   ⚠ shellguard flagged a dangerous command (0.99)
//     git add -A && git push --force
//     flagged:  git push --force  0.985
//               git add -A        0.844
//
//   ▸ Allow once                enter
//     Allow for this session    s
//     Deny                      d / esc
import { test } from "node:test";
import assert from "node:assert/strict";
import { askMenu, failedMenu, press, render } from "./menu.ts";
import type { Check } from "./decide.ts";

const check: Check = {
  command: "git add -A && git push --force",
  label: "dangerous",
  danger_probability: 0.99,
  flagged: [
    { part: "git push --force", danger_probability: 0.985 },
    { part: "git add -A", danger_probability: 0.844 },
  ],
};

test("ask menu: enter allows once by default", () => {
  assert.deepEqual(press(askMenu(check, check.flagged), "enter"), { done: "once" });
});

test("ask menu: s = session, d = deny, esc = deny", () => {
  const m = askMenu(check, check.flagged);
  assert.deepEqual(press(m, "s"), { done: "session" });
  assert.deepEqual(press(m, "d"), { done: "deny" });
  assert.deepEqual(press(m, "escape"), { done: "deny" });
});

test("ask menu: arrows move, enter picks the highlighted option", () => {
  let m = askMenu(check, check.flagged);
  m = press(m, "down").menu!;
  assert.deepEqual(press(m, "enter"), { done: "session" });
  m = press(m, "down").menu!;
  assert.deepEqual(press(m, "enter"), { done: "deny" });
  m = press(m, "down").menu!; // clamps at the bottom
  assert.deepEqual(press(m, "enter"), { done: "deny" });
  m = press(press(press(m, "up").menu!, "up").menu!, "up").menu!; // clamps at the top
  assert.deepEqual(press(m, "enter"), { done: "once" });
});

test("other keys do nothing", () => {
  const m = askMenu(check, check.flagged);
  assert.deepEqual(press(m, "x"), { menu: m });
});

test("failed menu: run anyway or deny, no session option", () => {
  const m = failedMenu("daemon did not start");
  assert.deepEqual(press(m, "enter"), { done: "once" });
  assert.deepEqual(press(m, "s"), { menu: m });
  assert.deepEqual(press(m, "d"), { done: "deny" });
  assert.deepEqual(press(press(m, "down").menu!, "enter"), { done: "deny" });
});

test("ask menu renders command, every new flagged part and the key hints", () => {
  const lines = render(askMenu(check, check.flagged)).join("\n");
  assert.match(lines, /shellguard.*0\.99/);
  assert.match(lines, /git add -A && git push --force/);
  assert.match(lines, /git push --force\s+0\.985/);
  assert.match(lines, /git add -A\s+0\.844/);
  assert.match(lines, /▸ Allow once\s+enter/);
  assert.match(lines, / {2}Allow for this session\s+s/);
  assert.match(lines, / {2}Deny\s+d \/ esc/);
});

test("parts already allowed this session are shown, marked, after the new ones", () => {
  // only git add -A is new; git push --force was allowed earlier
  const lines = render(askMenu(check, [check.flagged[1]]));
  const add = lines.findIndex((l) => /git add -A\s+0\.844$/.test(l));
  const push = lines.findIndex((l) => /git push --force\s+0\.985\s+\(allowed this session\)$/.test(l));
  assert.ok(add >= 0 && push > add, lines.join("\n"));
});

test("whole command flagged: no separate flagged list", () => {
  const one: Check = { ...check, command: "rm -rf ~", flagged: [{ part: "rm -rf ~", danger_probability: 0.985 }] };
  const lines = render(askMenu(one, one.flagged)).join("\n");
  assert.doesNotMatch(lines, /flagged:/);
});

test("highlight follows the arrow", () => {
  const m = press(askMenu(check, check.flagged), "down").menu!;
  assert.match(render(m).join("\n"), /▸ Allow for this session/);
});

test("failed menu renders the error", () => {
  const lines = render(failedMenu("daemon did not start")).join("\n");
  assert.match(lines, /shellguard failed: daemon did not start/);
  assert.match(lines, /▸ Run anyway\s+enter/);
});

test("multi-line commands are shown line by line", () => {
  const ml: Check = { ...check, command: "cat <<EOF > f\nrm -rf ~\nEOF", flagged: [{ part: "x", danger_probability: 0.5 }] };
  const lines = render(askMenu(ml, ml.flagged));
  assert.ok(lines.some((l) => l.trim() === "rm -rf ~"));
});
