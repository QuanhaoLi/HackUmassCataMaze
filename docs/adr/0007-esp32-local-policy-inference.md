<!--
Created at: 2026-11-14 10:39 EST
Created by: Codex
Last Modified at: 2026-11-15 02:30 EST
Last Modified by: Codex
-->

# ADR-0007: ESP32-S3 local policy inference

## Status

Accepted after the four-V100 production run completed at 100,364,306 agent steps.

## Context

The production policy contains 1,010,826 parameters and uses Conv2D, GroupNorm, SiLU, Linear, LayerNorm, and GRU. The target ESP32-S3 has verified 16MB Flash and 8MB PSRAM; the current firmware uses approximately 390KB application Flash and 46KB static RAM. ESP-DL supports ESP32-S3 INT8/INT16 Conv, Gemm, GRU, last-axis LayerNormalization, Swish, and the primitive arithmetic/reduction operators needed to express GroupNorm, but does not list GroupNorm as a direct operator. ESP-DL inference is batch-size 1.

## Decision

1. Export and quantize with ESP-PPQ/ESP-DL `3.3.15`. The production Arduino 3.3.12 package supplies ESP-DL `3.3.11` on ESP-IDF 5.5.5; this runtime is accepted only because the physical startup reference-envelope test passes all logits, value, hidden-state, memory, and latency gates. Its strict raw INT16 test differs by two units in one hidden element and is reported separately rather than hidden.
2. Export a single-agent, single-tick policy step with inputs `spatial[1,13,5,5]`, `scalar[1,46]`, and `hidden[1,1,256]`; outputs are `logits[1,9]`, `value[1]`, and `next_hidden[1,1,256]`.
3. Replace every GroupNorm with an exactly equivalent fixed-group expression using Reshape, ReduceMean, Sub, Mul, Add, Sqrt, and Div before ONNX export.
4. SiLU exports as Swish or Sigmoid+Mul. LayerNorm remains last-axis. GRU remains an ONNX GRU operator.
5. Quantize for target `esp32s3` using ESP-DL symmetric power-of-two `w8a8` first. The released artifact uses W8A16. Its measured masked-action agreement is `98.61%` over 10,000 legal recurrent observations; the product owner explicitly accepted this release threshold on 2026-11-15.
6. Run three AI sequentially because ESP-DL supports batch size 1; each entity retains its own 256-element hidden state.
7. The legal-action mask stays in portable C++ and is applied after logits, preserving the single action-legality source.
8. The deterministic heuristic policy remains the mandatory fallback when model loading, schema validation, inference, or latency fails.

## Acceptance

- PyTorch and ONNX FP32 outputs align within `1e-5` for logits, value, and hidden state over reviewed and randomized observations.
- The ONNX graph contains only ESP-DL-supported operators after GroupNorm decomposition.
- Quantized action agreement against FP32 is at least `98.5%` on 10,000 legal observations; the released W8A16 artifact achieves `98.61%`, and no masked action is selected because the portable C++ mask is authoritative.
- The complete model plus firmware fit verified Flash/PSRAM budgets.
- Three sequential AI inferences complete within 500ms, leaving at least 100ms for game, input, display, audio, and scheduling work in the 600ms tick.
- A 10,000-tick physical run has no watchdog, heap-growth, hidden-state corruption, or model/fallback transition failure.

## Released evidence

The released W8A16 artifact is 1,490,800 bytes with SHA-256 `0cc8bb5025ff22c435b0107fd739560f4c4e13c16e2683a1ad3f0e0ee7044322`. On the final physical N16R8 release, three sequential reference inferences completed in 126,210 microseconds. Maximum decoded errors against the frozen FP32 reference were `0.021938` logits, `0.016793` value, and `0.032408` hidden state. Runtime allocation consumed 167,508 bytes of internal memory and 1,480,032 bytes of PSRAM. The guarded product release reported `policy_ready=true` and `policy_fallback_latched=false`.

The 10,000-tick endurance gate remains post-release validation; any runtime tensor, finite-output, legal-mask, or 500ms latency failure immediately latches the heuristic fallback.
