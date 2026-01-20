#!/usr/bin/env python3
import subprocess
import sys


def main() -> int:
    args = ["pytest", *sys.argv[1:]]
    return subprocess.call(args)


if __name__ == "__main__":
    raise SystemExit(main())
