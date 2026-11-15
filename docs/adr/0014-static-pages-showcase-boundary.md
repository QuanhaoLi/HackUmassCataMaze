<!--
Created at: 2026-11-15 06:30 EST
Created by: Codex
Last Modified at: 2026-11-15 06:30 EST
Last Modified by: Codex

Records why the public Pages simulator is isolated from the authoritative product runtime.
-->

# ADR-0014: Isolate the static Pages showcase from the product runtime

- Status: Accepted
- Date: 2026-11-15

## Context

CataMaze needs a phone-compatible public URL that opens directly into the dual-OLED Companion Idle experience. The selected host is Cloudflare Pages and the user explicitly requires a pure front end with no backend. The existing `web/` client deliberately depends on Native versioned APIs and exact framebuffer payloads, so uploading it unchanged would produce a disconnected shell.

Compiling and certifying the full portable C++ product plus ESP-DL behavior for WebAssembly is a separate product effort. Rewriting the Game Core in JavaScript and presenting it as equivalent would create a false second authority and undermine the deterministic cross-target architecture.

## Decision

Create an isolated `showcase/` static target. It demonstrates the reviewed Companion Idle, Home, Setup, game, HUD, six-button gestures, sound language, and a bounded deterministic local maze. It makes no network request after assets load and uses no Cloudflare Functions.

The page labels itself `BROWSER SIM`. It does not claim authoritative Game Core hashes, C++ equivalence, Resident Policy execution, or physical-hardware evidence. Exact product behavior remains in the Native and ESP32 targets. The existing `web/` directory remains the Native framebuffer client and is not repurposed.

The Cloudflare Pages direct-upload project is named `hackumass-catamaze`. The deployed unit is only `showcase/`.

## Consequences

- Visitors receive a fast, install-free, touch-friendly playable artifact.
- The ESP32 remains offline and no public service becomes a game dependency.
- Showcase changes cannot silently change the authoritative rules or model contract.
- A future WebAssembly port may replace the showcase simulation only after it receives its own deterministic equivalence gates and architecture decision.
