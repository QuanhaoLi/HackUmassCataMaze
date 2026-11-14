## header
Created at: 2026-11-14 02:11 EST
Created by: Codex
Last Modified at: 2026-11-14 02:11 EST
Last Modified by: Codex

## brief intro
- Goal for this folder: hold automated tests grouped by execution target and milestone.
- 架构思路：Native tests prove domain behavior first; future embedded tests reuse portable fixtures without blocking playability.

## folder structure
|-README.md — Introduces the test hierarchy.
|-native/ — Contains GoogleTest suites executed on the development host.

## To-Dos
- Add embedded test folders only when M4/M5 begin.
