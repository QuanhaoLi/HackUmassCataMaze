## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 07:02 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: contain public application commands, snapshots, and port contracts.
- 架构思路：所有 adapters 通过这些稳定 contracts 与 simulation owner 通信。

## folder structure
|-README.md — Documents public application headers.
|-application.hpp — Declares the simulation owner, player commands, 9×5 player snapshot, and 5×5 AI lifecycle.
|-audio_event.hpp — Declares canonical player-observable audio events and deterministic arbitration.
|-system_controller.hpp — Declares Home, Setup, Game, Pause, confirmation, Result, and six-button intents.

## To-Dos
- Add adapter-facing bounded command queues during M2 without changing the simulation API.
