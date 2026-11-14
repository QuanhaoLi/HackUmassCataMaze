<!--
Created at: 2026-11-14 10:39 EST
Created by: Codex
Last Modified at: 2026-11-14 10:39 EST
Last Modified by: Codex
-->

# ADR-0007: ESP32-S3 local policy inference

## Status

Accepted after the four-V100 production run completed at 100,364,306 agent steps.

## Context

The production policy contains 1,010,826 parameters and uses Conv2D, GroupNorm, SiLU, Linear, LayerNorm, and GRU. The target ESP32-S3 has verified 16MB Flash and 8MB PSRAM; the current firmware uses approximately 390KB application Flash and 46KB static RAM. ESP-DL supports ESP32-S3 INT8/INT16 Conv, Gemm, GRU, last-axis LayerNormalization, Swish, and the primitive arithmetic/reduction operators needed to express GroupNorm, but does not list GroupNorm as a direct operator. ESP-DL inference is batch-size 1.

## Decision

1. Deploy with ESP-DL `3.3.15` on ESP32-S3. Arduino remains available as an ESP-IDF component so the existing hardware adapters can be reused.
2. Export a single-agent, single-tick policy step with inputs `spatial[1,13,5,5]`, `scalar[1,46]`, and `hidden[1,1,256]`; outputs are `logits[1,9]`, `value[1]`, and `next_hidden[1,1,256]`.
3. Replace every GroupNorm with an exactly equivalent fixed-group expression using Reshape, ReduceMean, Sub, Mul, Add, Sqrt, and Div before ONNX export.
4. SiLU exports as Swish or Sigmoid+Mul. LayerNorm remains last-axis. GRU remains an ONNX GRU operator.
5. Quantize for target `esp32s3` using ESP-DL symmetric power-of-two `w8a8` first. Escalate only accuracy-sensitive operators to `w8a16`/`w16a16` if required.
6. Run three AI sequentially because ESP-DL supports batch size 1; each entity retains its own 256-element hidden state.
7. The legal-action mask stays in portable C++ and is applied after logits, preserving the single action-legality source.
8. The deterministic heuristic policy remains the mandatory fallback when model loading, schema validation, inference, or latency fails.

## Acceptance

- PyTorch and ONNX FP32 outputs align within `1e-5` for logits, value, and hidden state over reviewed and randomized observations.
- The ONNX graph contains only ESP-DL-supported operators after GroupNorm decomposition.
- Quantized action agreement against FP32 is at least `99%` on 10,000 legal observations; no masked action is selected.
- The complete model plus firmware fit verified Flash/PSRAM budgets.
- Three sequential AI inferences complete within 900ms p95, leaving at least 100ms for game, input, display, and audio work in the one-second tick.
- A 10,000-tick physical run has no watchdog, heap-growth, hidden-state corruption, or model/fallback transition failure.
