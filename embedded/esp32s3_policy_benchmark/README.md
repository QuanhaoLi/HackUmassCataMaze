<!--
Created at: 2026-11-14 23:59 EST
Created by: Codex
Last Modified at: 2026-11-14 23:59 EST
Last Modified by: Codex
-->

# ESP32-S3 policy benchmark

## Goal

Compile and run the frozen CataMaze recurrent policy on the verified N16R8 ESP32-S3 before the model runtime is connected to gameplay.

## Contract

- Runtime: ESP-DL `3.3.15`, target `esp32s3`, batch size one.
- Inputs: `spatial[1,13,5,5]`, `scalar[1,46]`, `hidden[1,1,256]`.
- Outputs: `logits[1,9]`, `value[1]`, `next_hidden[1,1,256]`.
- Model: the accepted W8A16 `.espdl` artifact generated from the 100,364,306-step checkpoint.
- Measurement: one warm-up followed by repeated single-agent and three-agent sequential inference samples.
- Safety: model/schema/output failures are reported and never silently treated as a passing benchmark.

## Structure

- `CMakeLists.txt` — Declares the standalone ESP-IDF project.
- `main/CMakeLists.txt` — Registers the benchmark component and embeds the accepted model artifact.
- `main/idf_component.yml` — Pins the official ESP-DL component.
- `main/main.cpp` — Owns model loading, tensor validation, recurrent calls, and serial evidence.

## Build

From this directory:

```sh
idf.py set-target esp32s3
idf.py build
```

Physical upload is performed only after a fresh repository preflight identifies the verified board. No Flash erase is part of this workflow.
