// The popup as plain data: keys -> choice, state -> lines. index.ts adds pi + colours.
//
//   ⚠ shellguard flagged a dangerous command (0.99)
//     git add -A && git push --force
//     flagged:  git push --force  0.985
//               git add -A        0.844
//
//   ▸ Allow once                enter
//     Allow for this session    s
//     Deny                      d / esc
import type { Check, Flagged } from "./decide.ts";

export type Choice = "once" | "session" | "deny";
export type Key = "enter" | "escape" | "up" | "down" | string;
type Option = { choice: Choice; label: string; key: string; hint: string };
export type Menu = { title: string; body: string[]; options: Option[]; selected: number };

const ONCE: Option = { choice: "once", label: "Allow once", key: "", hint: "enter" };
const SESSION: Option = { choice: "session", label: "Allow for this session", key: "s", hint: "s" };
const DENY: Option = { choice: "deny", label: "Deny", key: "d", hint: "d / esc" };

/** `parts` = flagged parts not yet allowed; the rest of check.flagged is shown as allowed. */
export function askMenu(check: Check, parts: Flagged[]): Menu {
  const body = check.command.split("\n").map((l) => "  " + l);
  const isNew = new Set(parts.map((f) => f.part));
  const rows = [...parts, ...check.flagged.filter((f) => !isNew.has(f.part))];
  const isWhole = rows.length === 1 && rows[0].part === check.command;
  if (!isWhole) {
    const w = Math.max(...rows.map((f) => f.part.length));
    rows.forEach((f, i) => {
      const tag = isNew.has(f.part) ? "" : "  (allowed this session)";
      body.push(`  ${i === 0 ? "flagged:" : "        "}  ${f.part.padEnd(w)}  ${f.danger_probability}${tag}`);
    });
  }
  return {
    title: `⚠ shellguard flagged a dangerous command (${check.danger_probability})`,
    body,
    options: [ONCE, SESSION, DENY],
    selected: 0,
  };
}

export function failedMenu(error: string): Menu {
  return {
    title: `⚠ shellguard failed: ${error}`,
    body: ["  The command was not checked."],
    options: [{ ...ONCE, label: "Run anyway" }, DENY],
    selected: 0,
  };
}

export function press(menu: Menu, key: Key): { done: Choice } | { menu: Menu } {
  if (key === "enter") return { done: menu.options[menu.selected].choice };
  if (key === "escape") return { done: "deny" };
  if (key === "up" || key === "down") {
    const step = key === "up" ? -1 : 1;
    const selected = Math.min(Math.max(menu.selected + step, 0), menu.options.length - 1);
    return { menu: { ...menu, selected } };
  }
  const hit = menu.options.find((o) => o.key && o.key === key);
  return hit ? { done: hit.choice } : { menu };
}

export function render(menu: Menu): string[] {
  const w = Math.max(...menu.options.map((o) => o.label.length));
  return [
    menu.title,
    ...menu.body,
    "",
    ...menu.options.map((o, i) => `${i === menu.selected ? "▸" : " "} ${o.label.padEnd(w)}  ${o.hint}`),
  ];
}
