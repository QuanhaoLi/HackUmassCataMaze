# Created at: 2026-11-14 02:16 EST
# Created by: Codex
# Last Modified at: 2026-11-14 02:16 EST
# Last Modified by: Codex
# Fetches the exact cpp-httplib single header into ignored build storage and verifies its digest.

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
MAX_HEADER_BYTES = 2 * 1024 * 1024

project_dir = Path(env.subst("$PROJECT_DIR"))  # type: ignore[name-defined]
vendor_dir = project_dir / ".pio" / "vendor" / "cpp-httplib" / HTTPLIB_VERSION
header_path = vendor_dir / "httplib.h"


def verified(data: bytes) -> bool:
    return sha256(data).hexdigest() == HTTPLIB_SHA256


if header_path.exists() and not verified(header_path.read_bytes()):
    header_path.unlink()

if not header_path.exists():
    with urlopen(HTTPLIB_URL, timeout=30) as response:
        payload = response.read(MAX_HEADER_BYTES + 1)
    if len(payload) > MAX_HEADER_BYTES:
        raise RuntimeError("cpp-httplib header exceeded the 2 MiB safety limit")
    if not verified(payload):
        raise RuntimeError("cpp-httplib SHA-256 verification failed")
    vendor_dir.mkdir(parents=True, exist_ok=True)
    temporary_path = header_path.with_suffix(".tmp")
    temporary_path.write_bytes(payload)
    temporary_path.replace(header_path)

env.Append(CPPPATH=[str(vendor_dir)])  # type: ignore[name-defined]
