"""`mcp_audit._star`: the one-time note that asks for a GitHub star."""

from __future__ import annotations

import io
import os
import stat
import sys
from pathlib import Path
from typing import Any

import pytest

from mcp_audit import _entry, _star


class _Tty(io.StringIO):
    """A text stream that says it is a terminal."""

    def isatty(self) -> bool:
        return True


def _ask(
    tmp_path: Path,
    args: list[str] | None = None,
    code: object = 0,
    environ: dict[str, str] | None = None,
    stdout: Any = None,
    stderr: Any = None,
) -> tuple[bool, str]:
    err = _Tty() if stderr is None else stderr
    shown = _star.after_command(
        ["scan"] if args is None else args,
        code,
        environ={} if environ is None else environ,
        stdout=_Tty() if stdout is None else stdout,
        stderr=err,
        marker=tmp_path / "cfg" / "star-asked",
    )
    return shown, err.getvalue()


def test_the_note_is_shown_once(tmp_path: Path) -> None:
    shown, text = _ask(tmp_path)
    assert shown
    assert _star.REPO_URL in text and "star" in text
    assert _ask(tmp_path) == (False, "")
    assert _ask(tmp_path, ["check"]) == (False, "")


def test_check_and_a_scan_with_findings_show_it(tmp_path: Path) -> None:
    assert _ask(tmp_path / "a", ["check"])[0]
    assert _ask(tmp_path / "b", ["scan", "--path", "x"], code=1)[0]


@pytest.mark.parametrize(
    ("args", "code"),
    [
        (["scan"], 2),  # an error
        (["scan"], "usage error"),  # sys.exit("text") is exit code 1 to the shell
        (["scan", "--help"], 0),
        (["check", "-h"], 0),
        (["version"], 0),
        (["lock", "--verify"], 0),
        (["run"], 0),
        (["guard"], 0),
        ([], 0),
    ],
)
def test_other_commands_and_results_do_not_show_it(
    tmp_path: Path, args: list[str], code: object
) -> None:
    assert _ask(tmp_path, args, code) == (False, "")
    assert not (tmp_path / "cfg" / "star-asked").exists()


@pytest.mark.parametrize("name", [*_star.CI_ENV, _star.OPT_OUT_ENV])
def test_ci_and_the_opt_out_do_not_show_it(tmp_path: Path, name: str) -> None:
    assert _ask(tmp_path, environ={name: "1"}) == (False, "")
    assert not (tmp_path / "cfg" / "star-asked").exists()


def test_an_empty_variable_is_not_set(tmp_path: Path) -> None:
    assert _ask(tmp_path, environ={"CI": "", _star.OPT_OUT_ENV: ""})[0]


@pytest.mark.parametrize("piped", ["stdout", "stderr"])
def test_a_pipe_does_not_show_it(tmp_path: Path, piped: str) -> None:
    streams = {piped: io.StringIO()}
    shown, _text = _ask(tmp_path, **streams)
    assert not shown
    assert not (tmp_path / "cfg" / "star-asked").exists()


def test_a_marker_that_cannot_be_written_never_shows_it(tmp_path: Path) -> None:
    """A read-only config directory must not show the note on every run."""
    (tmp_path / "cfg").write_text("a file where the directory should be")
    assert _ask(tmp_path) == (False, "")
    assert _ask(tmp_path) == (False, "")


def test_a_broken_stream_never_raises(tmp_path: Path) -> None:
    class Broken(_Tty):
        def write(self, _text: str) -> int:
            raise OSError("closed")

    shown, _text = _ask(tmp_path, stderr=Broken())
    assert not shown


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_the_marker_is_private(tmp_path: Path) -> None:
    assert _ask(tmp_path)[0]
    marker = tmp_path / "cfg" / "star-asked"
    assert stat.S_IMODE(marker.stat().st_mode) == 0o600
    assert stat.S_IMODE(marker.parent.stat().st_mode) == 0o700
    assert marker.read_bytes() == b""


def test_the_marker_is_in_the_mcp_audit_config_directory() -> None:
    path = _star.marker_path()
    assert path.name == "star-asked"
    assert path.parent.name == "mcp-audit"


def test_the_note_names_the_repository_and_no_reward() -> None:
    """Ask, never pay: GitHub forbids stars in exchange for anything."""
    assert "https://github.com/adudley78/credenzo" in _star.MESSAGE
    for word in ("free", "reward", "unlock", "discount"):
        assert word not in _star.MESSAGE.lower()


def test_the_module_sends_nothing() -> None:
    source = Path(_star.__file__).read_text(encoding="utf-8")
    for name in ("urllib", "socket", "http.client", "requests", "subprocess"):
        assert f"import {name}" not in source and f"from {name}" not in source


def test_the_entry_point_passes_the_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[list[str], object]] = []
    monkeypatch.setattr(_star, "after_command", lambda a, c: calls.append((a, c)))

    def fake_cli() -> None:
        raise SystemExit(1)

    monkeypatch.setattr("mcp_audit.cli.main", fake_cli)
    monkeypatch.setattr(sys, "argv", ["credenzo", "scan"])
    with pytest.raises(SystemExit) as stop:
        _entry.main()
    assert stop.value.code == 1
    assert calls == [(["scan"], 1)]


def test_a_fault_in_the_note_keeps_the_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_a: object) -> bool:
        raise ImportError("not bundled")

    monkeypatch.setattr(_star, "after_command", broken)

    def fake_cli() -> None:
        raise SystemExit(2)

    monkeypatch.setattr("mcp_audit.cli.main", fake_cli)
    monkeypatch.setattr(sys, "argv", ["credenzo", "scan"])
    with pytest.raises(SystemExit) as stop:
        _entry.main()
    assert stop.value.code == 2


@pytest.mark.parametrize("command", ["run", "guard"])
def test_run_and_guard_never_reach_the_note(
    monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(_star, "after_command", lambda *a: calls.append(a))
    monkeypatch.setattr(_entry, "_exit_now", lambda code: sys.exit(code))
    monkeypatch.setattr(sys, "argv", ["credenzo", command, "--help"])
    with pytest.raises(SystemExit):
        _entry.main()
    assert calls == []
