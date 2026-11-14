#!/usr/bin/env bash
# Created at: 2026-11-14 02:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:54 EST
# Last Modified by: Codex
# Executes every Native test under AddressSanitizer and UndefinedBehaviorSanitizer.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "${script_dir}/.." && pwd)"
cd "${project_dir}"

# Apple Clang's ASan runtime does not support LeakSanitizer on macOS.
ASAN_OPTIONS="detect_leaks=0:halt_on_error=1:strict_string_checks=1" \
  "${project_dir}/.venv/bin/pio" test -e native_asan
UBSAN_OPTIONS="halt_on_error=1:print_stacktrace=1" \
  "${project_dir}/.venv/bin/pio" test -e native_ubsan
printf 'SANITIZERS_OK\n'
