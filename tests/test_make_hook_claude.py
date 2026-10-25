"""make hook-claude / unhook-claude: install the Claude Code hook globally.

    hooks/pi/{client,decide}.ts ─┐ copy, same layout    ┌▶ CLAUDE_HOOK/pi/
    hooks/claude/hook.ts ────────┘ (hook.ts imports ../pi) └▶ CLAUDE_HOOK/claude/
    CLAUDE_SETTINGS (.hooks.PreToolUse) += {matcher: Bash, node CLAUDE_HOOK/claude/hook.ts}
        idempotent, other hooks and keys untouched, bad JSON -> fail without writing

`-o install` skips the global `uv tool install`; every path points into tmp_path,
so these tests never touch the real ~/.claude.
"""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARK = "shellguard/claude/hook.ts"

GITNEXUS = {"matcher": "Grep|Glob|Bash",
            "hooks": [{"type": "command", "command": "node gitnexus-hook.cjs", "timeout": 10}]}
EXISTING = {
    "model": "opus",
    "hooks": {
        "PreToolUse": [GITNEXUS],
        "SessionStart": [{"hooks": [{"type": "command", "command": "dolly hook session-start"}]}],
    },
}


def make(target, tmp_path, settings=None):
    hook = tmp_path / "hooks" / "shellguard"
    settings = settings or tmp_path / "settings.json"
    r = subprocess.run(["make", "-s", "-o", "install", target, f"CLAUDE_HOOK={hook}",
                        f"CLAUDE_SETTINGS={settings}", f"SG_SOCK={tmp_path / 'nosock' / 'sock'}"],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    return r, hook, settings


def ours(settings):
    return [e for e in json.loads(settings.read_text()).get("hooks", {}).get("PreToolUse", [])
            if any(MARK in h.get("command", "") for h in e["hooks"])]


def test_copies_hook_and_shared_pi_files_without_tests(tmp_path):
    r, hook, _ = make("hook-claude", tmp_path)
    assert r.returncode == 0, r.stderr
    got = sorted(str(p.relative_to(hook)) for p in hook.rglob("*") if p.is_file())
    assert got == ["claude/hook.ts", "pi/client.ts", "pi/decide.ts"]
    assert (hook / "claude/hook.ts").read_bytes() == (ROOT / "hooks/claude/hook.ts").read_bytes()


def test_installed_hook_runs_from_its_new_home(tmp_path):
    # imports resolve in the installed layout; a non-Bash event needs no daemon
    _, hook, _ = make("hook-claude", tmp_path)
    r = subprocess.run(["node", hook / "claude/hook.ts"], input='{"tool_name":"Read"}',
                       capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""


def test_creates_settings_with_bash_pretooluse_entry(tmp_path):
    r, hook, settings = make("hook-claude", tmp_path)
    assert r.returncode == 0, r.stderr
    [entry] = ours(settings)
    assert entry["matcher"] == "Bash"
    [h] = entry["hooks"]
    assert h["type"] == "command"
    assert h["command"] == f'node "{hook}/claude/hook.ts"'
    assert h["timeout"] == 10


def test_keeps_other_hooks_and_keys(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(EXISTING))
    r, _, _ = make("hook-claude", tmp_path, settings)
    assert r.returncode == 0, r.stderr
    s = json.loads(settings.read_text())
    assert s["model"] == "opus"
    assert s["hooks"]["SessionStart"] == EXISTING["hooks"]["SessionStart"]
    assert s["hooks"]["PreToolUse"][0] == GITNEXUS
    assert len(ours(settings)) == 1


def test_running_twice_adds_one_entry(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(EXISTING))
    make("hook-claude", tmp_path, settings)
    r, _, _ = make("hook-claude", tmp_path, settings)
    assert r.returncode == 0, r.stderr
    assert len(ours(settings)) == 1
    assert len(json.loads(settings.read_text())["hooks"]["PreToolUse"]) == 2


def test_bad_settings_json_fails_and_leaves_file_alone(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{ not json")
    r, _, _ = make("hook-claude", tmp_path, settings)
    assert r.returncode != 0
    assert settings.read_text() == "{ not json"


def test_unhook_removes_only_ours(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps(EXISTING))
    _, hook, _ = make("hook-claude", tmp_path, settings)
    r, _, _ = make("unhook-claude", tmp_path, settings)
    assert r.returncode == 0, r.stderr
    assert json.loads(settings.read_text()) == EXISTING
    assert not hook.exists()


def test_unhook_drops_pretooluse_it_emptied(tmp_path):
    _, _, settings = make("hook-claude", tmp_path)
    make("unhook-claude", tmp_path, settings)
    assert "PreToolUse" not in json.loads(settings.read_text()).get("hooks", {})


def test_unhook_when_nothing_installed_is_fine(tmp_path):
    r, _, settings = make("unhook-claude", tmp_path)
    assert r.returncode == 0, r.stderr
    assert not settings.exists()


def test_help_lists_targets():
    out = subprocess.run(["make", "help"], cwd=ROOT, capture_output=True, text=True).stdout
    assert "hook-claude" in out and "unhook-claude" in out
