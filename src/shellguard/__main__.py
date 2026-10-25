"""CLI: shellguard "<command>"  |  echo "<command>" | shellguard

Prints one JSON line. Exit code: 0 safe, 1 dangerous, 2 usage error.
"""
import json
import sys

USAGE = 'usage: shellguard "<command>"   or   echo "<command>" | shellguard'


def main() -> int:
    command = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().rstrip("\n")
    if not command.strip():
        print(USAGE, file=sys.stderr)
        return 2
    from shellguard.check import check  # after arg check: loading the model takes ~1 s

    out = check(command)
    print(json.dumps({"command": command, **out}))
    return 1 if out["label"] == "dangerous" else 0


if __name__ == "__main__":
    sys.exit(main())
