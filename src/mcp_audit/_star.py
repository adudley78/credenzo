"""One note, shown once, that asks a person to star the repository.

The note is printed to stderr after the first ``scan`` or ``check`` that ends
with exit code 0 (clean) or 1 (findings), and never again. It is printed only
to a person:

- stdout and stderr are both a terminal (not a pipe, a file or a hook);
- no CI variable is set (``CI``, ``GITHUB_ACTIONS`` and the others below);
- ``CREDENZO_NO_STAR_PROMPT`` is not set;
- the command is not ``--help``.

``run`` and ``guard`` never reach this module: ``_entry.main`` dispatches them
before the Typer app. Nothing is sent anywhere. The only effect on disk is an
empty marker file, ``<user-config-dir>/mcp-audit/star-asked`` (mode 0o600,
directory 0o700), that records that the note was shown. When the marker cannot
be written the note is not printed, so a read-only home never shows it on each
run. Delete the file to see the note again.

Standard library and ``platformdirs`` only. Every fault is swallowed: this
note must never change the output or the exit code of a command.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

REPO_URL = "https://github.com/adudley78/credenzo"
OPT_OUT_ENV = "CREDENZO_NO_STAR_PROMPT"
MARKER_NAME = "star-asked"

#: Commands after which the note can be shown: the two a new user runs first.
COMMANDS = frozenset({"scan", "check"})
#: 0 = clean, 1 = findings. 2 (an error) never shows the note.
EXIT_CODES = frozenset({0, 1})
#: Set by CI systems. Any non-empty value means "not a person at a terminal".
CI_ENV = (
    "CI",
    "GITHUB_ACTIONS",
    "GITLAB_CI",
    "BUILDKITE",
    "CIRCLECI",
    "TF_BUILD",
    "JENKINS_URL",
    "TEAMCITY_VERSION",
    "BITBUCKET_BUILD_NUMBER",
    "CODEBUILD_BUILD_ID",
)
HELP_FLAGS = frozenset({"--help", "-h"})

MESSAGE = (
    f"If Credenzo helped you, please star it on GitHub: {REPO_URL}\n"
    "A star helps other people find the project. This note shows once."
)


def marker_path() -> Path:
    """Return the path of the marker file in the user config directory."""
    from platformdirs import user_config_dir

    return Path(user_config_dir("mcp-audit")) / MARKER_NAME


def _exit_code(code: object) -> int | None:
    """Return the exit code of a ``SystemExit`` code, as ``sys.exit`` reads it."""
    if code is None:
        return 0
    if isinstance(code, bool):
        return int(code)
    return code if isinstance(code, int) else None


def _is_tty(stream: TextIO | None) -> bool:
    try:
        return bool(stream is not None and stream.isatty())
    except (AttributeError, ValueError, OSError):
        return False


def should_ask(
    args: Sequence[str],
    code: object,
    *,
    environ: Mapping[str, str],
    stdout: TextIO | None,
    stderr: TextIO | None,
) -> bool:
    """Return True when the note may be shown after this command.

    This does not read the marker file; :func:`after_command` does.
    """
    if not args or args[0] not in COMMANDS:
        return False
    if HELP_FLAGS & set(args):
        return False
    if _exit_code(code) not in EXIT_CODES:
        return False
    if environ.get(OPT_OUT_ENV):
        return False
    if any(environ.get(name) for name in CI_ENV):
        return False
    return _is_tty(stdout) and _is_tty(stderr)


def _claim_marker(path: Path) -> bool:
    """Create the marker. Return True only for the one call that created it."""
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError:  # FileExistsError included: the note was shown before.
        return False
    os.close(fd)
    return True


def after_command(
    args: Sequence[str],
    code: object,
    *,
    environ: Mapping[str, str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    marker: Path | None = None,
) -> bool:
    """Show the note when this is the first eligible command. Never raise.

    Return True when the note was printed.
    """
    try:
        out = sys.stdout if stdout is None else stdout
        err = sys.stderr if stderr is None else stderr
        env = os.environ if environ is None else environ
        if not should_ask(args, code, environ=env, stdout=out, stderr=err):
            return False
        if not _claim_marker(marker or marker_path()):
            return False
        print(f"\n{MESSAGE}", file=err)
        err.flush()
        return True
    except Exception:  # noqa: BLE001 - a note must never break a command.
        return False
