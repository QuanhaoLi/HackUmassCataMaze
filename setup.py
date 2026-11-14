# Created at: 2026-11-14 03:41 EST
# Created by: Codex
# Last Modified at: 2026-11-14 03:41 EST
# Last Modified by: Codex
# Builds the in-process C++ Game Core extension used by the Python trainer.

from __future__ import annotations

from pathlib import Path

from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup


ROOT = Path(__file__).parent.resolve()
CORE_SOURCES = sorted(
    path.relative_to(ROOT).as_posix()
    for path in (ROOT / "lib" / "catamaze_core" / "src").glob("*.cpp")
)


setup(
    ext_modules=[
        Pybind11Extension(
            "training._native",
            ["training/native_bindings.cpp", *CORE_SOURCES],
            include_dirs=[str(ROOT / "lib" / "catamaze_core" / "include")],
            cxx_std=17,
            extra_compile_args=["-O3", "-Wall", "-Wextra", "-Wpedantic"],
        )
    ],
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
