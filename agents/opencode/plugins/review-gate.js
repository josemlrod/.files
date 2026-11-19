// Local pre-PR review (see ~/.agents/review/README.md).
// Blocks `git push` / `gh pr create` until a pre-pr round passed, and runs the
// repo's formatter on edited files. All logic is in ~/.agents/review/bin/review.
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const CLI = path.join(os.homedir(), ".agents/review/bin/review");
const SHELL_TOOLS = new Set(["bash", "shell"]);
const EDIT_TOOLS = new Set(["edit", "write", "multiedit"]);
const DEBUG = process.env.REVIEW_PLUGIN_DEBUG;
const dbg = (...a) => DEBUG && fs.appendFileSync(DEBUG, JSON.stringify(a) + "\n");

// Cheap test before calling the CLI. Drops backslash-newline, quotes, and
// backslashes first, as the shell would, so `pu''sh` still counts as push.
const mayPush = (command) => /push|\bpr\b/.test((command ?? "").replace(/\\\n/g, "").replace(/["'\\]/g, ""));

// Returns the block message, or undefined to allow.
function gate(command, cwd) {
  if (!mayPush(command)) return;
  const r = spawnSync(CLI, ["--cwd", cwd, "gate", "--command", command], {
    encoding: "utf8",
    timeout: 30000,
  });
  return r.status === 2 ? r.stderr.trim() : undefined;
}

function format(file, cwd) {
  if (file) spawnSync(CLI, ["--cwd", cwd, "format", file], { encoding: "utf8", timeout: 60000 });
}

// OpenCode 2.x: default export with setup(ctx); tool hooks via ctx.tool.hook.
// The background service is shared across projects, so take cwd from the session.
async function sessionDir(ctx, e, sub) {
  let dir;
  try {
    dir = (await ctx.session.get({ sessionID: e.sessionID }))?.location?.directory;
  } catch {}
  dir = dir || process.cwd();
  return sub ? path.resolve(dir, sub) : dir;
}

export default {
  id: "local.review-gate",
  setup(ctx) {
    ctx.tool.hook("execute.before", async (e) => {
      dbg("before", e.tool, e.input);
      if (!SHELL_TOOLS.has(e.tool)) return;
      const command = e.input?.command;
      if (!mayPush(command)) return;
      const msg = gate(command, await sessionDir(ctx, e, e.input?.workdir));
      if (msg) throw new Error(msg);
    });
    ctx.tool.hook("execute.after", async (e) => {
      if (!EDIT_TOOLS.has(e.tool)) return;
      format(e.input?.path ?? e.input?.filePath, await sessionDir(ctx, e));
    });
  },
};

// OpenCode 1.x: named server plugin with tool.execute.before/after.
export const ReviewGatePlugin = async ({ directory }) => ({
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return;
    const msg = gate(output.args?.command, output.args?.workdir || directory);
    if (msg) throw new Error(msg);
  },
  "tool.execute.after": async (input) => {
    if (EDIT_TOOLS.has(input.tool)) format(input.args?.filePath, directory);
  },
});
