# Created at: 2026-11-14 20:04 EST
# Created by: Codex
# Last Modified at: 2026-11-14 20:04 EST
# Last Modified by: Codex
# Reuses frozen Native physics while selecting V2-only persona reward v3.

from __future__ import annotations

from training.env import CataMazeBatchEnv
from training.v2.reward import PersonaRewardCalculator


class PersonaV3BatchEnv(CataMazeBatchEnv):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._reward = PersonaRewardCalculator(self._observation)
