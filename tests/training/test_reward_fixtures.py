# Created at: 2026-11-14 04:50 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:02 EST
# Last Modified by: Codex
# Verifies reviewed reward fixtures through the standalone validation path.

from training.validate_reward import validate_reward_fixtures


def test_reviewed_reward_fixtures_pass() -> None:
    assert validate_reward_fixtures("tests/fixtures/reward") == 12
