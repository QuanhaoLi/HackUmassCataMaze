# Created at: 2026-11-14 04:50 EST
# Created by: Codex
# Last Modified at: 2026-11-14 04:50 EST
# Last Modified by: Codex
# Validates reviewed reward trajectories independently from the training loop.

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from training import _native
from training.reward import COMPONENT_NAMES, REWARD_VERSION, RewardCalculator


STATUS = {
    "running": _native.STATUS_RUNNING,
    "victory": _native.STATUS_VICTORY,
    "death": _native.STATUS_DEATH,
    "timeout": _native.STATUS_TIMEOUT,
}
EVENT = {
    "shot": _native.EVENT_SHOT,
    "damage_applied": _native.EVENT_DAMAGE_APPLIED,
    "damage_credit": _native.EVENT_DAMAGE_CREDIT,
    "entity_died": _native.EVENT_ENTITY_DIED,
}


def _snapshot() -> dict[str, np.ndarray]:
    return {
        "alive": np.ones((1, 3), dtype=np.bool_),
        "positions": np.array([[[1, 1], [2, 2], [3, 3], [4, 4]]], dtype=np.int16),
        "status": np.array([_native.STATUS_RUNNING], dtype=np.uint8),
        "events": np.full((1, 192, 7), -1, dtype=np.int16),
        "event_count": np.zeros((1,), dtype=np.uint16),
        "distance_to_player": np.array([[10, 20, 30]], dtype=np.int16),
        "last_result": np.zeros((1, 4), dtype=np.uint8),
    }


def _apply(snapshot: dict[str, np.ndarray], patch: dict[str, Any]) -> None:
    if "status" in patch:
        snapshot["status"][0] = STATUS[str(patch["status"])]
    if "alive" in patch:
        snapshot["alive"][0] = np.asarray(patch["alive"], dtype=np.bool_)
    if "positions" in patch:
        snapshot["positions"][0] = np.asarray(patch["positions"], dtype=np.int16)
    if "distance_to_player" in patch:
        snapshot["distance_to_player"][0] = np.asarray(
            patch["distance_to_player"], dtype=np.int16
        )
    if "last_result" in patch:
        snapshot["last_result"][0] = np.asarray(patch["last_result"], dtype=np.uint8)
    rows = patch.get("events", [])
    snapshot["event_count"][0] = len(rows)
    for index, (name, actor, target, value) in enumerate(rows):
        snapshot["events"][0, index] = [EVENT[name], actor, target, 0, 0, 0, value]


def validate_reward_fixtures(path: str | Path) -> int:
    fixture_path = Path(path)
    files = sorted(fixture_path.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"no reward fixture YAML files under {fixture_path}")
    validated = 0
    for file in files:
        document = yaml.safe_load(file.read_text(encoding="utf-8"))
        if document.get("version") != REWARD_VERSION:
            raise ValueError(f"{file} reward version does not match {REWARD_VERSION}")
        for case in document.get("cases", []):
            previous = _snapshot()
            current = _snapshot()
            _apply(previous, case.get("previous", {}))
            _apply(current, case.get("current", {}))
            result = RewardCalculator(previous).calculate(previous, current)
            expected = case["expected"]
            for component in COMPONENT_NAMES:
                if component in expected:
                    np.testing.assert_allclose(
                        result.components[component][0],
                        np.asarray(expected[component], dtype=np.float32),
                        atol=1e-6,
                        err_msg=f"{file}:{case['name']}:{component}",
                    )
            np.testing.assert_allclose(
                result.total[0],
                np.asarray(expected["total"], dtype=np.float32),
                atol=1e-6,
                err_msg=f"{file}:{case['name']}:total",
            )
            if "truncated" in expected:
                np.testing.assert_array_equal(result.truncated[0], expected["truncated"])
            validated += 1
    return validated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden-trajectories", default="tests/fixtures/reward")
    arguments = parser.parse_args()
    count = validate_reward_fixtures(arguments.golden_trajectories)
    print(f"REWARD_FIXTURES_OK cases={count} version={REWARD_VERSION}")


if __name__ == "__main__":
    main()
