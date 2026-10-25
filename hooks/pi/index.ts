// shellguard for pi: check every bash command before it runs.
//
//   tool_call(bash) ─▶ client.check() ─▶ daemon (~1 ms) ─▶ decide()
//                                                          ├ allow  → runs
//                                                          ├ ask    → popup: once / session / deny
//                                                          ├ failed → popup: run anyway / deny
//                                                          └ block  → no UI: reason goes to the model
//
//   /shellguard on | off | status      (session only; resets when pi restarts)
//
// Installed by `make hook-pi` (copies hooks/pi/ to ~/.pi/agent/extensions/shellguard/).
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";
import { matchesKey, truncateToWidth } from "@earendil-works/pi-tui";
import { check } from "./client.ts";
import { decide, remember } from "./decide.ts";
import { type Choice, type Menu, press, render } from "./menu.ts";
import { askMenu, failedMenu } from "./menu.ts";

export default function (pi: ExtensionAPI) {
  let enabled = true;
  let allowed = new Set<string>();

  const status = (ctx: ExtensionContext) =>
    ctx.ui.setStatus("shellguard", enabled ? undefined : ctx.ui.theme.fg("warning", "shellguard: off"));

  async function popup(ctx: ExtensionContext, start: Menu): Promise<Choice> {
    return ctx.ui.custom<Choice>((tui, theme, _kb, done) => {
      let menu = start;
      return {
        render(width: number) {
          const [title, ...rest] = render(menu);
          return [
            theme.fg("warning", theme.bold(title)),
            ...rest.map((l) => (l.startsWith("▸") ? theme.fg("accent", l) : l)),
          ].map((l) => truncateToWidth(l, width));
        },
        handleInput(data: string) {
          const key = ["enter", "escape", "up", "down"].find((k) => matchesKey(data, k as any)) ?? data;
          const r = press(menu, key);
          if ("done" in r) return done(r.done);
          menu = r.menu;
          tui.requestRender();
        },
        invalidate() {},
      };
    });
  }

  pi.on("session_start", async (_e, ctx) => {
    status(ctx);
    check("true").catch(() => {}); // start the daemon now, so the first real command is warm
  });

  pi.on("tool_call", async (event, ctx) => {
    if (!enabled || !isToolCallEventType("bash", event)) return;
    const command = event.input.command;
    const result = await check(command).catch((e: Error) => e);
    const d = decide(result, { enabled, hasUI: ctx.hasUI, allowed });

    if (d.action === "allow") return;
    if (d.action === "block") return { block: true, reason: d.reason };

    const choice = await popup(ctx, d.action === "ask" ? askMenu(d.check, d.parts) : failedMenu(d.error));
    if (choice === "session" && d.action === "ask") allowed = remember(allowed, d.parts);
    if (choice === "deny") return { block: true, reason: "Blocked by the user (shellguard)." };
  });

  pi.registerCommand("shellguard", {
    description: "shellguard on | off | status",
    getArgumentCompletions: (prefix: string) =>
      ["on", "off", "status"].filter((a) => a.startsWith(prefix)).map((a) => ({ value: a, label: a })),
    handler: async (args, ctx) => {
      const arg = args.trim();
      if (arg === "on" || arg === "off") {
        enabled = arg === "on";
        status(ctx);
      } else if (arg && arg !== "status") {
        return ctx.ui.notify("usage: /shellguard on | off | status", "warning");
      }
      const list = [...allowed].map((p) => `  ${p}`).join("\n");
      ctx.ui.notify(
        `shellguard is ${enabled ? "on" : "off"}` + (allowed.size ? `\nallowed this session:\n${list}` : ""),
        "info",
      );
    },
  });
}
