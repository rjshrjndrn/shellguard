"""CLI: shellguard "<command>"  |  echo "<command>" | shellguard  |  shellguard --serve

Prints one JSON line. Exit code: 0 safe, 1 dangerous, 2 usage error.
"""
import json
import sys
from pathlib import Path

USAGE = 'usage: shellguard "<command>"   or   echo "<command>" | shellguard'


def serve_main(args: list[str]) -> int:
    import argparse

    from shellguard.daemon import default_socket, serve

    ap = argparse.ArgumentParser(prog="shellguard --serve")
    ap.add_argument("--socket", type=Path, default=default_socket())
    ap.add_argument("--idle", type=float, default=1800, help="exit after this many idle seconds")
    a = ap.parse_args(args)
    print(f"shellguard daemon stopped: {serve(a.socket, idle=a.idle)}", file=sys.stderr)
    return 0


def main() -> int:
    if sys.argv[1:2] == ["--serve"]:
        return serve_main(sys.argv[2:])
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
