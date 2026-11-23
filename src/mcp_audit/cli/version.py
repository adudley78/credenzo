"""The ``version`` command."""

from __future__ import annotations

import os
import sys

from mcp_audit import __version__
from mcp_audit._brand import REPO_URL
from mcp_audit._star import CI_ENV, OPT_OUT_ENV, _is_tty
from mcp_audit.cli import app, console


def _person_at_terminal() -> bool:
    """True for a person at a terminal: no CI variable, no opt-out, a TTY."""
    if os.environ.get(OPT_OUT_ENV) or any(os.environ.get(v) for v in CI_ENV):
        return False
    return _is_tty(sys.stdout)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"credenzo {__version__}")
    # Scripts read the first line (setup-action writes it to $GITHUB_OUTPUT),
    # so the second line goes to a person at a terminal only.
    if _person_at_terminal():
        console.print(
            f"Source, docs and issues: {REPO_URL}  (a star helps others find it)",
            style="dim",
            markup=False,
            highlight=False,
            soft_wrap=True,
        )
