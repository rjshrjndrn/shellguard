// What the pi hook does with one bash command. Pure: no pi, no socket, so it is testable.
//
//   off                      -> allow
//   shellguard failed        -> "failed" (UI asks: run anyway?)   no UI: block
//   safe                     -> allow
//   dangerous, every flagged part allowed this session  -> allow
//   dangerous, some new parts -> "ask" with only the new parts     no UI: block

export type Flagged = { part: string; danger_probability: number };
export type Check = {
  command: string;
  label: "safe" | "dangerous";
  danger_probability: number;
  flagged: Flagged[];
};
export type State = { enabled: boolean; hasUI: boolean; allowed: Set<string> };
export type Decision =
  | { action: "allow" }
  | { action: "ask"; check: Check; parts: Flagged[] }
  | { action: "failed"; error: string }
  | { action: "block"; reason: string };

/** Key for "allowed this session": same command modulo whitespace. */
export function normalize(part: string): string {
  return part.trim().split(/\s+/).join(" ");
}

export function remember(allowed: Set<string>, parts: Flagged[]): Set<string> {
  return new Set([...allowed, ...parts.map((f) => normalize(f.part))]);
}

export function decide(result: Check | { error: string } | Error, state: State): Decision {
  if (!state.enabled) return { action: "allow" };

  if (result instanceof Error || "error" in result) {
    const error = result instanceof Error ? result.message : result.error;
    return state.hasUI
      ? { action: "failed", error }
      : { action: "block", reason: `shellguard failed: ${error}. Blocked because no one can confirm.` };
  }

  if (result.label === "safe") return { action: "allow" };

  const parts = result.flagged.filter((f) => !state.allowed.has(normalize(f.part)));
  if (parts.length === 0) return { action: "allow" };
  if (state.hasUI) return { action: "ask", check: result, parts };

  const list = parts.map((f) => `${f.part} (${f.danger_probability})`).join("; ");
  return { action: "block", reason: `shellguard flagged this command as dangerous: ${list}` };
}
