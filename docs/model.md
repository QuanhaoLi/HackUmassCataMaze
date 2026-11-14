<!--
Created at: 2026-11-15 00:52 EST
Created by: Codex
Last Modified at: 2026-11-14 18:46 EST
Last Modified by: Codex
-->

# Released AI model

## Product behavior

CataMaze now runs one resident recurrent policy on the ESP32-S3 for every game. The three enemies share one set of learned parameters and execute sequentially, while each enemy owns a separate 256-element GRU hidden state. Starting or restarting a run clears all three hidden states. Map presets do not change the model because each enemy always receives the same 5×5 observation contract.

The portable C++ action mask remains authoritative. A model output can select only a currently legal action, including Wait Action. Model loading, tensor-schema, finite-output, reference-envelope, action-mask, or latency failure latches the deterministic heuristic policy for subsequent decisions.

There is no manual model switch. One released Resident Policy is automatic when healthy; Heuristic Fallback is automatic and remains latched until reboot. Starting a new Game Session clears valid recurrent hidden state but does not retry a model that already failed health gates.

## System integration

- Companion Idle, Home, Setup, Pause, Inactivity Prompt, and Result never run inference or advance recurrent hidden state.
- Each Game Session tick builds legal observations for all living AI and submits one atomic Policy Tick.
- The three model actions and three next hidden states commit only if every required inference, finite-output check, legal mask, and complete-tick latency gate passes.
- Any failure discards every provisional next hidden state and makes all AI use Heuristic Fallback for that world transition and every later transition until reboot.
- Policy Health is visible through bounded System/Serial diagnostics without entering Game Core state, observations, rewards, or model inputs.
- Model identity and every release gate come from one versioned release manifest consumed by build, boot diagnostics, and upload acceptance.
- Native parity is an offline acceptance adapter; ONNX/Torch never becomes a browser, Game Core, or standalone gameplay dependency.

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

The `.espdl` artifact is embedded permanently in Flash. At boot, one model instance is built and its parameters are copied into PSRAM for inference speed. It remains resident across Companion Idle, Home, Setup, Pause, and every Game Session; it is not loaded once per tick or copied once per enemy. Residency does not imply inference outside a Game Session.

## Remaining endurance gate

The model is released and active, but the 10,000-tick physical endurance run remains outstanding. That run must confirm no watchdog event, heap growth, hidden-state corruption, or fallback transition failure.
