// Claude Code PreToolUse hook for Bash. Reuses the pi hook's client (daemon) and decide().
//
//   stdin event ─▶ commandOf ─▶ client.check ─▶ decide ─▶ toReply ─▶ stdout JSON (or nothing)
//
// Never answers "allow": staying silent hands the call to Claude Code's own permission
// flow; "ask" puts shellguard's reason in Claude Code's confirmation prompt.
// No session memory here (a new process per call): Claude Code's "don't ask again" covers it.
import { fileURLToPath } from "node:url";
import { check, defaultSocket } from "../pi/client.ts";
import { decide, type Decision } from "../pi/decide.ts";

export type Reply = {
  hookSpecificOutput: {
    hookEventName: "PreToolUse";
    permissionDecision: "ask";
    permissionDecisionReason: string;
  };
  systemMessage?: string;
};

export function commandOf(event: unknown): string | null {
  if (!event || typeof event !== "object") return null;
  const e = event as { tool_name?: unknown; tool_input?: { command?: unknown } };
  if (e.tool_name !== "Bash") return null;
  const cmd = e.tool_input?.command;
  return typeof cmd === "string" && cmd.trim() ? cmd : null;
}

const ask = (reason: string, systemMessage?: string): Reply => ({
  hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "ask", permissionDecisionReason: reason },
  ...(systemMessage ? { systemMessage } : {}),
});

export function toReply(d: Decision): Reply | null {
  switch (d.action) {
    case "allow":
      return null;
    case "ask": {
      const list = d.parts.map((f) => `${f.part} (${f.danger_probability})`).join("; ");
      return ask(`shellguard flagged this command as dangerous: ${list}`);
    }
    case "failed":
      return ask(
        `shellguard could not check this command: ${d.error}`,
        `⚠ shellguard unavailable (${d.error}); command not checked`,
      );
    case "block": // only without a UI; Claude Code always has someone to ask
      return ask(d.reason);
  }
}

async function readStdin(): Promise<string> {
  let s = "";
  for await (const chunk of process.stdin) s += chunk;
  return s;
}

async function main() {
  let event: unknown;
  try {
    event = JSON.parse(await readStdin());
  } catch {
    return; // not our business: let Claude Code carry on
  }
  const command = commandOf(event);
  if (command === null) return;

  const result = await check(command, {
    socket: process.env.SHELLGUARD_SOCKET || defaultSocket(),
    command: (process.env.SHELLGUARD_CMD || "shellguard").split(" ").filter(Boolean),
  }).catch((e: Error) => e);
  const reply = toReply(decide(result, { enabled: true, hasUI: true, allowed: new Set() }));
  if (reply) process.stdout.write(JSON.stringify(reply) + "\n");
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) await main();
