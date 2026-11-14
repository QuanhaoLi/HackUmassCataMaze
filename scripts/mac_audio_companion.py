# Created at: 2026-11-14 04:59 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:59 EST
# Last Modified by: Codex
# Discovers, validates, deduplicates, reconnects, and plays ESP32 audio events on macOS.

import argparse
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import wave

import serial


PREFIX = "CATAMAZE_AUDIO "
SCHEMA = "catamaze.audio.v1"
ALLOWED_EVENTS = {
    "PLAYER_SHOT",
    "PLAYER_DAMAGE",
    "ENEMY_SHOT_HEARD",
    "PLAYER_DEATH",
    "PLAYER_VICTORY",
}
REQUIRED_KEYS = {"schema", "seq", "tick", "event"}
SAMPLE_RATE = 44_100


class SequenceFilter:
    def __init__(self) -> None:
        self.last: int | None = None

    def accept(self, sequence: int) -> bool:
        if not 0 <= sequence <= 0xFFFFFFFF:
            return False
        if self.last is None:
            self.last = sequence
            return True
        delta = (sequence - self.last) & 0xFFFFFFFF
        if delta == 0 or delta >= 0x80000000:
            return False
        self.last = sequence
        return True


def parse_audio_line(line: str) -> dict[str, int | str] | None:
    if len(line.encode("utf-8")) > 128 or not line.startswith(PREFIX):
        return None
    try:
        payload = json.loads(line[len(PREFIX) :])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or set(payload) != REQUIRED_KEYS:
        return None
    if payload.get("schema") != SCHEMA or payload.get("event") not in ALLOWED_EVENTS:
        return None
    sequence = payload.get("seq")
    tick = payload.get("tick")
    if not isinstance(sequence, int) or isinstance(sequence, bool):
        return None
    if not isinstance(tick, int) or isinstance(tick, bool):
        return None
    if not 0 <= sequence <= 0xFFFFFFFF or not 0 <= tick <= 2000:
        return None
    return payload


def event_segments(event: str) -> list[tuple[float, float, float]]:
    return {
        "PLAYER_SHOT": [(880.0, 0.07, 0.26)],
        "PLAYER_DAMAGE": [(520.0, 0.08, 0.30), (0.0, 0.09, 0.0), (420.0, 0.08, 0.30)],
        "ENEMY_SHOT_HEARD": [(360.0, 0.045, 0.18), (0.0, 0.055, 0.0), (360.0, 0.045, 0.18)],
        "PLAYER_DEATH": [(260.0, 0.15, 0.28), (200.0, 0.15, 0.28), (140.0, 0.15, 0.28)],
        "PLAYER_VICTORY": [(660.0, 0.08, 0.22), (0.0, 0.05, 0.0),
                           (880.0, 0.08, 0.22), (0.0, 0.05, 0.0),
                           (1100.0, 0.10, 0.22)],
    }[event]


def generate_wav(event: str, destination: Path) -> None:
    samples: list[int] = []
    phase = 0.0
    for frequency, duration, amplitude in event_segments(event):
        count = int(SAMPLE_RATE * duration)
        for index in range(count):
            if frequency == 0.0:
                sample = 0.0
            else:
                envelope = min(1.0, index / (SAMPLE_RATE * 0.005),
                               (count - index) / (SAMPLE_RATE * 0.005))
                sample = math.sin(phase) * amplitude * max(0.0, envelope)
                phase += 2.0 * math.pi * frequency / SAMPLE_RATE
            samples.append(int(max(-1.0, min(1.0, sample)) * 32767))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))


def ensure_assets(directory: Path) -> dict[str, Path]:
    assets: dict[str, Path] = {}
    for event in sorted(ALLOWED_EVENTS):
        path = directory / f"{event.lower()}.wav"
        if not path.exists():
            generate_wav(event, path)
        assets[event] = path
    return assets


def discover_port(project_dir: Path) -> str:
    command = [str(project_dir / ".venv/bin/pio"), "device", "list", "--json-output"]
    devices = json.loads(subprocess.check_output(command, text=True))
    matches = [device["port"] for device in devices
               if "VID:PID=303A:1001" in device.get("hwid", "")]
    if len(matches) != 1:
        raise RuntimeError(f"expected one Espressif USB device, found {len(matches)}")
    return matches[0]


def play(path: Path, dry_run: bool) -> None:
    if dry_run:
        return
    subprocess.Popen(["/usr/bin/afplay", str(path)], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--assets", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(__file__).resolve().parent.parent
    assets = ensure_assets(args.assets or project_dir / ".artifacts/mac-audio")
    sequence_filter = SequenceFilter()
    deadline = time.monotonic() + args.seconds if args.seconds > 0.0 else None
    backoff = 0.1

    while deadline is None or time.monotonic() < deadline:
        try:
            port = args.port or discover_port(project_dir)
            with serial.Serial(port, 115200, timeout=0.2, write_timeout=0.2) as device:
                device.dtr = False
                device.rts = False
                print(f"MAC_AUDIO_CONNECTED port={port}", flush=True)
                backoff = 0.1
                while deadline is None or time.monotonic() < deadline:
                    raw = device.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    payload = parse_audio_line(line)
                    if payload is None or not sequence_filter.accept(int(payload["seq"])):
                        continue
                    event = str(payload["event"])
                    play(assets[event], args.dry_run)
                    print(f"MAC_AUDIO_EVENT seq={payload['seq']} tick={payload['tick']} event={event}",
                          flush=True)
        except (OSError, RuntimeError, serial.SerialException, json.JSONDecodeError) as error:
            print(f"MAC_AUDIO_DISCONNECTED reason={error}", file=sys.stderr, flush=True)
            if args.port and args.seconds <= 0.0:
                return 1
            time.sleep(backoff)
            backoff = min(2.0, backoff * 2.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
