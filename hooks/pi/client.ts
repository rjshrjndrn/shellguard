// Talk to the shared shellguard daemon; start it if nobody answers.
//
//   connect sock ── ok ──▶ {"command"}\n  →  {"label", "danger_probability", "flagged"}\n
//        │ ENOENT / ECONNREFUSED
//        ▼
//   spawn `shellguard --serve --socket sock` detached (outlives this pi session,
//   shared with others), retry until startTimeoutMs. The daemon's flock keeps it
//   to one, so racing spawns are harmless.
import { spawn } from "node:child_process";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import type { Check } from "./decide.ts";

export type Options = {
  socket?: string;
  command?: string[]; // how to run shellguard
  timeoutMs?: number; // one request to a running daemon
  startTimeoutMs?: number; // whole check when the daemon must be started (model load ~1-2 s)
};

export function defaultSocket(): string {
  return path.join(os.homedir(), ".cache", "shellguard", "sock");
}

class NotRunning extends Error {}

function ask(sock: string, command: string, timeoutMs: number): Promise<Check | { error: string }> {
  return new Promise((resolve, reject) => {
    let data = "";
    const s = net.createConnection(sock);
    const fail = (e: Error) => {
      s.destroy();
      reject(e);
    };
    const timer = setTimeout(() => fail(new Error(`shellguard daemon timed out after ${timeoutMs} ms`)), timeoutMs);
    s.on("connect", () => s.write(JSON.stringify({ command }) + "\n"));
    s.on("data", (b) => {
      data += b;
      const nl = data.indexOf("\n");
      if (nl < 0) return;
      clearTimeout(timer);
      s.end();
      try {
        resolve(JSON.parse(data.slice(0, nl)));
      } catch {
        reject(new Error(`shellguard daemon sent bad JSON: ${data.slice(0, 200)}`));
      }
    });
    s.on("end", () => {
      clearTimeout(timer);
      if (!data.includes("\n")) reject(new Error("shellguard daemon closed the connection"));
    });
    s.on("error", (e: NodeJS.ErrnoException) => {
      clearTimeout(timer);
      fail(e.code === "ENOENT" || e.code === "ECONNREFUSED" ? new NotRunning(e.code) : e);
    });
  });
}

function start(cmd: string[], sock: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd[0], [...cmd.slice(1), "--serve", "--socket", sock], { detached: true, stdio: "ignore" });
    p.once("error", (e) => reject(new Error(`cannot start shellguard (${cmd[0]}): ${e.message}`)));
    p.once("spawn", () => {
      p.unref(); // don't keep pi alive; the daemon lives on for other sessions
      resolve();
    });
  });
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function check(command: string, opts: Options = {}): Promise<Check | { error: string }> {
  const sock = opts.socket ?? defaultSocket();
  const cmd = opts.command ?? ["shellguard"];
  const timeoutMs = opts.timeoutMs ?? 1000;
  const deadline = Date.now() + (opts.startTimeoutMs ?? 5000);
  let lastStart = 0;

  for (;;) {
    try {
      return await ask(sock, command, timeoutMs);
    } catch (e) {
      if (!(e instanceof NotRunning)) throw e;
      if (Date.now() > deadline) throw new Error(`shellguard daemon did not start (${e.message})`);
    }
    // (re)spawn at most every 1.5 s: a daemon that said "already running" while an old
    // one shut down exits quickly, and the next attempt takes over
    if (Date.now() - lastStart > 1500) {
      lastStart = Date.now();
      await start(cmd, sock);
    }
    await sleep(50);
  }
}
