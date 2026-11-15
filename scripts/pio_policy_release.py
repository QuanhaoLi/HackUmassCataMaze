# Created at: 2026-11-14 18:51 EST
# Created by: Codex
# Last Modified at: 2026-11-14 18:51 EST
# Last Modified by: Codex
# Refuses an ESP32 product build when release manifest, artifact, or generated header drifts.

from pathlib import Path
import subprocess

Import("env")  # type: ignore[name-defined]  # noqa: F821

project_dir = Path(env.subst("$PROJECT_DIR"))  # type: ignore[name-defined]  # noqa: F821
command = [
    env.subst("$PYTHONEXE"),  # type: ignore[name-defined]  # noqa: F821
    str(project_dir / "scripts/generate_policy_release.py"),
    "--check",
]
subprocess.run(command, cwd=project_dir, check=True)
