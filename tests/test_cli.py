"""Step 9: `shellguard "<command>"` prints one JSON line; exit code says the verdict.

exit 0 = safe, 1 = dangerous, 2 = usage error (grep's convention), so hooks can branch on it.
"""
import json
import subprocess
import sys

import pytest


def run(*args, stdin=None):
    return subprocess.run([sys.executable, "-m", "shellguard", *args], input=stdin,
                          capture_output=True, text=True, timeout=60)


@pytest.mark.parametrize("command, label, code", [("rm -rf ~", "dangerous", 1), ("ls -la", "safe", 0)])
def test_argument(command, label, code):
    r = run(command)
    out = json.loads(r.stdout)
    assert out["command"] == command and out["label"] == label
    # "probability" alone reads as confidence in the label; this is P(dangerous)
    assert set(out) == {"command", "label", "danger_probability", "flagged"}
    assert (out["flagged"] == []) == (label == "safe")
    assert 0.0 <= out["danger_probability"] <= 1.0
    assert out["danger_probability"] == round(out["danger_probability"], 3)
    assert r.returncode == code


def test_chain_names_flagged_part():
    out = json.loads(run("cd /tmp && rm -rf build && ls").stdout)
    assert [f["part"] for f in out["flagged"]] == ["rm -rf build"]


def test_several_arguments_are_one_command():
    # shellguard rm -rf ~   (no quotes) means the same as shellguard "rm -rf ~"
    assert json.loads(run("rm", "-rf", "~").stdout)["command"] == "rm -rf ~"


def test_stdin_keeps_newlines():
    r = run(stdin="cd /tmp\nrm -rf ~\n")
    assert json.loads(r.stdout)["command"] == "cd /tmp\nrm -rf ~"  # trailing newline dropped
    assert r.returncode == 1


def test_no_command_is_usage_error():
    r = run(stdin="")
    assert r.returncode == 2
    assert r.stdout == "" and "usage" in r.stderr.lower()


def test_stdout_is_exactly_one_json_line():
    r = run("ls")
    assert r.stdout.count("\n") == 1 and r.stderr == ""


def test_cli_does_not_load_training_libraries():
    # startup time: duckdb is for data prep, torch for model C. (pandas can't be avoided:
    # scikit-learn imports it whenever it is installed, sklearn/utils/fixes.py)
    code = ("import sys, runpy; sys.argv = ['shellguard', 'ls']\n"
            "try: runpy.run_module('shellguard', run_name='__main__')\n"
            "except SystemExit: pass\n"
            "bad = [m for m in ('duckdb', 'torch') if m in sys.modules]\n"
            "assert not bad, bad")
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
