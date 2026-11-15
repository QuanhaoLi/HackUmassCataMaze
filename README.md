## header
Created at: 2026-11-13 23:42 EST
Created by: Codex
Last Modified at: 2026-11-15 06:30 EST
Last Modified by: Codex

## brief intro
- Goal for this repository: build the product-grade CataMaze game and its trainable, personality-conditioned AI agents.
- 架构思路：先以 `agents/` 固化工程约束，以 `docs/` 固化游戏环境和强化学习合同；后续实现必须先更新对应文档，再按清晰分层落代码与测试。

## folder structure
|-README.md — Introduces the repository and indexes its top-level structure.
|-CONTEXT.md — Defines the canonical product language for Home, Setup, Game Session, pause, queue, and WAIT semantics.
|-.gitignore — Excludes local operating-system metadata from version control.
|-.clang-format — Defines the repository-wide C++17 formatting contract.
|-.github/ — Contains documented Native continuous-integration workflows.
|-platformio.ini — Pins Native build, test, and dependency configuration.
|-pyproject.toml — Pins the Python package, Native extension build, tests, and RL dependencies.
|-setup.py — Builds the in-process pybind11 Game Core extension.
|-plan.md — Defines ordered implementation milestones and their executable acceptance gates.
|-requirements-dev.txt — Pins the project-local PlatformIO Core version.
|-requirements-train-v100.txt — Selects the Volta-compatible CUDA 12.6 PyTorch wheel for the approved V100 host.
|-agents/ — Contains mandatory operating instructions for coding agents; see `agents/README.md`.
|-docs/ — Contains the normative game, engineering, hardware, restriction, and reinforcement-learning specifications; see `docs/README.md`.
|-lib/ — Contains portable C++ domain, application, and rendering libraries; see `lib/README.md`.
|-scripts/ — Contains reproducible acceptance helpers; see `scripts/README.md`.
|-showcase/ — Contains the backend-free Cloudflare Pages browser showcase; see `showcase/README.md`.
|-src/ — Contains thin executable entry points; see `src/README.md`.
|-test/ — Contains target-specific automated tests; see `test/README.md`.
|-tests/ — Contains Python RL contract tests and reviewed fixtures; see `tests/README.md`.
|-training/ — Contains the Native training bridge and recurrent-PPO implementation; see `training/README.md`.
|-web/ — Contains the dependency-free Native browser UI; see `web/README.md`.

## To-Dos
- Deliver milestones in `plan.md`, preserving playable-game-first ordering.
- Implement the deterministic game environment defined in `docs/gamerules.md` and `docs/structure.md`.
- Implement and validate the reinforcement-learning system defined in `docs/reward.md`.
- Add a README before adding any new folder or subfolder.
