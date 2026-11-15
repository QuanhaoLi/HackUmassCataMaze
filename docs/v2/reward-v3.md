<!--
Created at: 2026-11-14 20:04 EST
Created by: Codex
Last Modified at: 2026-11-14 20:04 EST
Last Modified by: Codex
-->

# V2-only persona reward v3

## Why a new reward version is required

The architecture-only run preserved V1 reward v2 exactly. It demonstrated that separate heads and persona modulation can create divergence at the recurrent stage, but full training returned to nearly identical high-shooting behavior. V1 reward gives every surviving AI `+10` on timeout, while persona shaping is much smaller; this makes delaying the player a strong shared optimum and suppresses the desired secondary styles.

Reward v3 changes no game rule, observation, action, event, hidden state or terminal status. It only changes V2 training credit.

## Frozen values

Shared terminal reward:

| Outcome | V2 reward v3 |
|---|---:|
| Player death | `+20` |
| Player escape | `-20` |
| Timeout | `-5` |

Persona shaping:

| Event | aggressive | cautious | explorer |
|---|---:|---:|---:|
| Player damage per effective HP | `+4.00` | `+1.00` | `+0.50` |
| Player kill bonus | `+10.00` | `+5.00` | `+3.00` |
| Self damage per HP | `-0.75` | `-3.00` | `-1.00` |
| Self death | `-8.00` | `-25.00` | `-10.00` |
| Actual shot ammo cost | `-0.05` | `-0.08` | `-0.06` |
| First visit | `+0.001` | `+0.002` | `+0.050` |
| Successful revisit | `0.000` | `0.000` | `0.000` |
| Non-terminal tick | `-0.0020` | `-0.0005` | `-0.0020` |
| Distance potential coefficient | `+0.15` | `-0.02` | `0.00` |

Unchanged shared penalties:

- friendly damage `-1.0` per effective HP;
- friendly kill `-3.0`;
- wall/bounds `-0.02`;
- entity/conflict block `-0.005`;
- invalid fallback `-0.10`;
- explorer positive coverage cap `+5.0`.

## Intended causal effects

- aggressive must earn its higher shooting rate through effective damage; the larger per-shot cost prevents indiscriminate spam;
- cautious receives a strong survival gradient and a small potential reward for increasing player distance;
- explorer receives material coverage credit without reintroducing a revisit penalty that previously made required maze backtracking worse than waiting;
- timeout is negative, so none of the styles can satisfy the common objective by stalling.

## Training boundary

The reward-v3 run:

1. starts from recurrent checkpoint SHA `d155f283f73754c9dbb9d7142f8221bde4a6de27dc8b8c1385f63137bf85c597`;
2. resets optimizer and rollout state;
3. trains the full V2 model on curriculum C at learning rate `3e-5`;
4. uses a distinct run directory and checkpoint format metadata;
5. first evaluates at 5M, then may continue to15M only while effectiveness and persona metrics improve;
6. never overwrites the reward-v2 25M failure evidence.

## Acceptance

Reward v3 does not change the final gates. It must still pass the exact aggressive/cautious/explorer thresholds, every opponent's V1 escape-regression bound, no-timeout substitution check, actor-only export, per-persona99% quantization, and checksummed model-only handoff.
