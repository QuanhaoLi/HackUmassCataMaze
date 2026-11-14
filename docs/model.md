<!--
Created at: 2026-11-15 00:52 EST
Created by: Codex
Last Modified at: 2026-11-15 00:52 EST
Last Modified by: Codex
-->

# Released AI model

## Product behavior

CataMaze now runs one resident recurrent policy on the ESP32-S3 for every game. The three enemies share one set of learned parameters and execute sequentially, while each enemy owns a separate 256-element GRU hidden state. Starting or restarting a run clears all three hidden states. Map presets do not change the model because each enemy always receives the same 5×5 observation contract.

The portable C++ action mask remains authoritative. A model output can select only a currently legal action, including Wait Action. Model loading, tensor-schema, finite-output, reference-envelope, action-mask, or latency failure latches the deterministic heuristic policy for subsequent decisions.

## Frozen artifact

| Property | Released value |
|---|---|
| Architecture | Shared Conv/GroupNorm/SiLU encoder, scalar MLP, fusion, GRU-256, actor and value heads |
| Parameters | 1,010,826 |
| Inputs | `spatial[1,13,5,5]`, `scalar[1,46]`, `hidden[1,1,256]` |
| Outputs | `logits[1,9]`, `value[1]`, `next_hidden[1,1,256]` |
| Quantization | W8A16 for ESP32-S3 |
| Artifact size | 1,490,800 bytes |
| SHA-256 | `0cc8bb5025ff22c435b0107fd739560f4c4e13c16e2683a1ad3f0e0ee7044322` |
| Calibration | 512 real recurrent Stage-D samples |
| Evaluation | 10,000 separate legal recurrent observations |
| Masked action agreement | 98.61%; explicitly accepted by the product owner |

## Physical ESP32-S3 evidence

The guarded final release ran on the verified 16MB-Flash/8MB-PSRAM board. The firmware occupies 2,903,175 of 6,553,600 application bytes and 54,860 static RAM bytes.

At startup, the firmware writes a frozen real recurrent observation into the model and runs three complete sequential inferences. The accepted physical result was:

| Measurement | Result | Gate |
|---|---:|---:|
| Three sequential inferences | 126,210µs | ≤900,000µs |
| Maximum logit error | 0.021938 | ≤0.10 |
| Value error | 0.016793 | ≤0.50 |
| Maximum hidden error | 0.032408 | ≤0.18 |
| Internal runtime allocation | 167,508 bytes | Observed fit |
| PSRAM runtime allocation | 1,480,032 bytes | Observed fit |

The ESP-DL 3.3.11 runtime's strict raw test differs from the 3.3.15 exporter by two INT16 units in one hidden value. The decoded physical errors above are the release authority and remain within the separately measured W8A16 error envelope.

## Residency

The `.espdl` artifact is embedded permanently in Flash. At boot, one model instance is built and its parameters are copied into PSRAM for inference speed. It remains resident across Home, Setup, Pause, and every match; it is not loaded once per tick or copied once per enemy.

## Remaining endurance gate

The model is released and active, but the 10,000-tick physical endurance run remains outstanding. That run must confirm no watchdog event, heap growth, hidden-state corruption, or fallback transition failure.
