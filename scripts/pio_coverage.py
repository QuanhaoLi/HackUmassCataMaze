# Created at: 2026-11-14 02:55 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:55 EST
# Last Modified by: Codex
# Adds the Clang profile runtime flag to the final PlatformIO Native coverage link.

Import("env")  # type: ignore[name-defined]  # Provided by PlatformIO/SCons.

env.Append(LINKFLAGS=["-fprofile-instr-generate"])  # type: ignore[name-defined]
