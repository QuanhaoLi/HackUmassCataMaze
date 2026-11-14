<!--
Created at: 2026-11-14 23:59 EST
Created by: Codex
Last Modified at: 2026-11-14 23:59 EST
Last Modified by: Codex
-->

# Embedded deployment projects

## Purpose

This directory owns target-specific deployment probes that must be validated before their runtime is admitted into the production firmware.

## Structure

- `esp32s3_policy_benchmark/` — Loads the frozen CataMaze policy with ESP-DL and measures physical ESP32-S3 inference behavior independently of the product loop.

## Boundary

The benchmark may validate model format, tensor schema, memory, numerical output, and latency. It does not replace the guarded diagnostic and product upload workflow, and it must retain the heuristic policy as the production fallback until every ADR-0007 acceptance gate passes.
