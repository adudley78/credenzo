"""scripts/install.sh: verify before install, POSIX sh, never clobber a pip install.

The script once installed a hardcoded v0.1.0 (no such release: `curl` without
``-f`` wrote GitHub's "Not Found" page to ``/usr/local/bin/credenzo``), checked
nothing, replaced any ``/usr/local/bin/mcp-audit`` and stopped at
``set -o pipefail`` under dash. These tests run it with stub ``curl``, ``gh``
and ``uname``: nothing is downloaded and the only program run is a stub.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "install.sh"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX sh script")

_CURL = """#!/bin/sh
echo "$*" >> "$STUB_LOG"
case " $* " in
  *" -w "*) printf '%s' "https://github.com/adudley78/credenzo/releases/tag/v9.9.9" ;;
  *) out=""; prev=""
     for a in "$@"; do [ "$prev" = "-o" ] && out="$a"; prev="$a"; done
     printf '#!/bin/sh\\necho "credenzo 9.9.9"\\n' > "$out" ;;
esac
"""
_GH = """#!/bin/sh
echo "gh $*" >> "$STUB_LOG"
exit "${GH_RESULT:-0}"
"""
_UNAME = """#!/bin/sh
case "$1" in -s) echo Linux ;; -m) echo x86_64 ;; esac
"""


def _tools(tmp_path: Path, *, with_gh: bool) -> Path:
    """A PATH directory with the stubs and the few real programs the script uses."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stubs = {"curl": _CURL, "uname": _UNAME}
    if with_gh:
        stubs["gh"] = _GH
    for name, body in stubs.items():
        path = bin_dir / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    for name in ("sh", "mktemp", "chmod", "mv", "ln", "mkdir", "rm", "cat"):
        real = shutil.which(name, path="/usr/bin:/bin")  # not a PATH shim
        assert real is not None, name
        (bin_dir / name).symlink_to(real)
    return bin_dir


def _run(
    tmp_path: Path, *, with_gh: bool = True, **env: str
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    bin_dir = _tools(tmp_path, with_gh=with_gh)
    dest = tmp_path / "dest"
    log = tmp_path / "calls.log"
    proc = subprocess.run(  # noqa: S603 — the repository's own script, stub tools
        [str(bin_dir / "sh"), str(SCRIPT)],
        env={
            "PATH": str(bin_dir),
            "HOME": str(tmp_path),
            "STUB_LOG": str(log),
            "CREDENZO_INSTALL_DIR": str(dest),
            **env,
        },
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc, dest, log


def test_a_verified_binary_is_installed_with_both_names(tmp_path: Path) -> None:
    proc, dest, log = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "credenzo 9.9.9" in proc.stdout
    assert os.access(dest / "credenzo", os.X_OK)
    assert (dest / "mcp-audit").is_symlink()
    calls = log.read_text(encoding="utf-8")
    assert "releases/download/v9.9.9/mcp-audit-linux-x86_64" in calls
    assert "gh attestation verify" in calls
    assert "--signer-workflow adudley78/credenzo/.github/workflows/release.yml" in calls
    curl_calls = [c for c in calls.splitlines() if not c.startswith("gh ")]
    assert len(curl_calls) == 2
    assert all(c.startswith("-fsSL") for c in curl_calls), curl_calls  # -f: no 404 page


def test_a_binary_that_fails_the_check_is_not_installed(tmp_path: Path) -> None:
    proc, dest, _ = _run(tmp_path, GH_RESULT="1")
    assert proc.returncode == 1
    assert "failed the build-provenance check" in proc.stderr
    assert not (dest / "credenzo").exists()


def test_without_gh_nothing_is_installed(tmp_path: Path) -> None:
    proc, dest, _ = _run(tmp_path, with_gh=False)
    assert proc.returncode == 1
    assert "CREDENZO_SKIP_VERIFY=1" in proc.stderr
    assert not (dest / "credenzo").exists()


def test_skip_verify_installs_and_warns(tmp_path: Path) -> None:
    proc, dest, log = _run(tmp_path, with_gh=False, CREDENZO_SKIP_VERIFY="1")
    assert proc.returncode == 0, proc.stderr
    assert "build provenance is not checked" in proc.stderr
    assert (dest / "credenzo").exists()
    assert "gh " not in log.read_text(encoding="utf-8")


def test_an_existing_mcp_audit_that_is_not_a_link_is_left_alone(
    tmp_path: Path,
) -> None:
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "mcp-audit").write_text("#!/bin/sh\necho pip install\n")
    proc, _, _ = _run(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert not (dest / "mcp-audit").is_symlink()
    assert "pip install" in (dest / "mcp-audit").read_text()


def test_a_pinned_version_is_used_and_checked(tmp_path: Path) -> None:
    proc, _, log = _run(tmp_path, CREDENZO_VERSION="v0.36.1")
    assert proc.returncode == 0, proc.stderr
    calls = log.read_text(encoding="utf-8")
    assert "releases/download/v0.36.1/" in calls
    assert " -w " not in f" {calls} "
    (tmp_path / "x").mkdir()
    bad, _, _ = _run(tmp_path / "x", CREDENZO_VERSION="latest; rm -rf /")
    assert bad.returncode == 1
    assert "not a release tag" in bad.stderr
