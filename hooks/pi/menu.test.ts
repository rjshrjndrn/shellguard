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
import { askMenu, commandText, failedMenu, press, render } from "./menu.ts";
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

// Long commands (scripts, heredocs) must not push the flagged parts and the options off
// screen: the popup never prints more than SHORT lines of the command, and each flagged
// part is one line with a (+N lines) note. pi shows the full command in the chat above.
const script = (n: number) => ["python3 - <<'EOF'", ...Array.from({ length: n - 2 }, (_, i) => `x = ${i}`), "EOF"].join("\n");

test("multi-line flagged part shows its first line and how many more", () => {
  const part = script(28);
  const c: Check = { ...check, command: `ls && ${part}`, flagged: [{ part, danger_probability: 0.688 }] };
  const lines = render(askMenu(c, c.flagged));
  assert.ok(lines.some((l) => /flagged:\s+python3 - <<'EOF'\s+0\.688\s+\(\+27 lines\)$/.test(l)), lines.join("\n"));
  assert.ok(!lines.some((l) => l.includes("x = 5")));
});

test("long command is not printed; the popup says where to read it", () => {
  const c: Check = { ...check, command: script(60), flagged: [{ part: "rm -rf build", danger_probability: 0.8 }] };
  const lines = render(askMenu(c, c.flagged));
  assert.ok(!lines.some((l) => l.includes("x = 5")));
  assert.ok(lines.some((l) => /command:\s+60 lines, shown in full in the chat above/.test(l)), lines.join("\n"));
});

test("long command that is itself the only flagged part still names it once", () => {
  const cmd = script(40);
  const c: Check = { ...check, command: cmd, flagged: [{ part: cmd, danger_probability: 0.9 }] };
  const lines = render(askMenu(c, c.flagged));
  assert.equal(lines.filter((l) => l.includes("python3 - <<'EOF'")).length, 1, lines.join("\n"));
  assert.ok(lines.some((l) => /\(\+39 lines\)/.test(l)));
});

test("popup height does not grow with the command", () => {
  const h = (n: number) => {
    const c: Check = { ...check, command: script(n), flagged: [{ part: script(n), danger_probability: 0.9 }, check.flagged[0]] };
    return render(askMenu(c, c.flagged)).length;
  };
  assert.equal(h(4), h(300));
});

test("short command (up to 3 lines) is still shown in full", () => {
  const c: Check = { ...check, command: "cd /tmp\nrm -rf build\nls", flagged: [{ part: "rm -rf build", danger_probability: 0.8 }] };
  const lines = render(askMenu(c, c.flagged));
  for (const l of ["cd /tmp", "rm -rf build", "ls"]) assert.ok(lines.some((x) => x.trim() === l), l);
  assert.ok(!lines.some((l) => l.includes("command:")));
});

// /shellguard on | off | status: on/off just confirm the switch; status also lists session allows.
const allowed = new Set(["rm -r /tmp/tester", "git push --force"]);

test("off says only that shellguard is off, even with session allows", () => {
  assert.equal(commandText("off", false, allowed), "shellguard is off");
});

test("on says only that shellguard is on", () => {
  assert.equal(commandText("on", true, allowed), "shellguard is on");
});

test("status lists what was allowed this session", () => {
  assert.equal(
    commandText("status", true, allowed),
    "shellguard is on\nallowed this session:\n  rm -r /tmp/tester\n  git push --force",
  );
});

test("bare /shellguard behaves like status", () => {
  assert.equal(commandText("", false, allowed), commandText("status", false, allowed));
});

test("status with nothing allowed is just the state", () => {
  assert.equal(commandText("status", false, new Set()), "shellguard is off");
});
