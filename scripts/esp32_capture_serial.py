# Created at: 2026-11-14 04:44 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:44 EST
# Last Modified by: Codex
# Captures bounded ESP32 Serial evidence and optionally requires one line prefix.

import argparse
import sys
import time

import serial


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--require-prefix", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deadline = time.monotonic() + args.seconds
    found = not args.require_prefix
    with serial.Serial(args.port, 115200, timeout=0.2, write_timeout=0.2) as device:
        device.dtr = False
        device.rts = False
        while time.monotonic() < deadline:
            raw = device.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            print(line, flush=True)
            if line.startswith(args.require_prefix):
                found = True
    if not found:
        print(f"missing required Serial prefix: {args.require_prefix}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
