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

const SHORT = 3; // commands up to this many lines are printed; longer ones are in the chat

/** First line of a multi-line part, plus how many lines were left out. */
function oneLine(part: string): { head: string; more: string } {
  const lines = part.split("\n");
  return { head: lines[0], more: lines.length > 1 ? `  (+${lines.length - 1} lines)` : "" };
}

/** `parts` = flagged parts not yet allowed; the rest of check.flagged is shown as allowed.
 *  Height stays small whatever the command: long commands are not printed (pi shows them
 *  in the chat above) and every flagged part is one line. */
export function askMenu(check: Check, parts: Flagged[]): Menu {
  const cmdLines = check.command.split("\n");
  const short = cmdLines.length <= SHORT;
  const body = short ? cmdLines.map((l) => "  " + l) : [];
  const isNew = new Set(parts.map((f) => f.part));
  const rows = [...parts, ...check.flagged.filter((f) => !isNew.has(f.part))];
  const isWhole = rows.length === 1 && rows[0].part === check.command;
  if (!(isWhole && short)) {
    const heads = rows.map((f) => oneLine(f.part));
    const w = Math.max(...heads.map((h) => h.head.length));
    rows.forEach((f, i) => {
      const tag = isNew.has(f.part) ? "" : "  (allowed this session)";
      const label = i === 0 ? "flagged:" : "        ";
      body.push(`  ${label}  ${heads[i].head.padEnd(w)}  ${f.danger_probability}${heads[i].more}${tag}`);
    });
  }
  if (!short) body.push(`  command:  ${cmdLines.length} lines, shown in full in the chat above`);
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

/** Reply to /shellguard <arg>: on/off confirm the switch, status (or bare) also lists session allows. */
export function commandText(arg: string, enabled: boolean, allowed: Set<string>): string {
  const state = `shellguard is ${enabled ? "on" : "off"}`;
  if (arg === "on" || arg === "off" || !allowed.size) return state;
  return `${state}\nallowed this session:\n${[...allowed].map((p) => `  ${p}`).join("\n")}`;
}
