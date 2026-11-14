# Created at: 2026-11-14 02:16 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:42 EST
# Last Modified by: Codex
# Fetches exact Native-only single headers into ignored build storage and verifies every digest.

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

Import("env")  # type: ignore[name-defined]  # Provided by PlatformIO/SCons.

HTTPLIB_VERSION = "0.53.1"
HTTPLIB_SHA256 = "bc69d53636a8757cb24a1deb9880bf7e2fdae3a80bbc759e145b8c80913cbfa3"
HTTPLIB_URL = (
    "https://raw.githubusercontent.com/yhirose/cpp-httplib/"
    f"v{HTTPLIB_VERSION}/httplib.h"
)
JSON_VERSION = "3.12.0"
JSON_SHA256 = "aaf127c04cb31c406e5b04a63f1ae89369fccde6d8fa7cdda1ed4f32dfc5de63"
JSON_URL = (
    "https://raw.githubusercontent.com/nlohmann/json/"
    f"v{JSON_VERSION}/single_include/nlohmann/json.hpp"
)
MAX_HEADER_BYTES = 3 * 1024 * 1024

project_dir = Path(env.subst("$PROJECT_DIR"))  # type: ignore[name-defined]
vendor_root = project_dir / ".pio" / "vendor"


def fetch_verified(url: str, expected_digest: str, target: Path) -> None:
    if target.exists() and sha256(target.read_bytes()).hexdigest() != expected_digest:
        target.unlink()
    if target.exists():
        return
    with urlopen(url, timeout=30) as response:
        payload = response.read(MAX_HEADER_BYTES + 1)
    if len(payload) > MAX_HEADER_BYTES:
        raise RuntimeError(f"Native dependency exceeded safety limit: {target.name}")
    if sha256(payload).hexdigest() != expected_digest:
        raise RuntimeError(f"SHA-256 verification failed: {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target.with_suffix(".tmp")
    temporary_path.write_bytes(payload)
    temporary_path.replace(target)


httplib_dir = vendor_root / "cpp-httplib" / HTTPLIB_VERSION
json_dir = vendor_root / "nlohmann-json" / JSON_VERSION
fetch_verified(HTTPLIB_URL, HTTPLIB_SHA256, httplib_dir / "httplib.h")
fetch_verified(JSON_URL, JSON_SHA256, json_dir / "nlohmann" / "json.hpp")
env.Append(CPPPATH=[str(httplib_dir), str(json_dir)])  # type: ignore[name-defined]
