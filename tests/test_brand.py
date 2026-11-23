"""Tests for where output names the project: version, help, footers, links."""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_audit._brand import MD_FOOTER, REPO_URL
from mcp_audit.cli import app
from mcp_audit.cli import version as version_mod


def test_version_second_line_only_for_a_person(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(version_mod, "_is_tty", lambda stream: True)
    for name in ("CI", "GITHUB_ACTIONS", "CREDENZO_NO_STAR_PROMPT"):
        monkeypatch.delenv(name, raising=False)
    assert version_mod._person_at_terminal()
    monkeypatch.setenv("CI", "true")
    assert not version_mod._person_at_terminal()
    monkeypatch.delenv("CI")
    monkeypatch.setenv("CREDENZO_NO_STAR_PROMPT", "1")
    assert not version_mod._person_at_terminal()


def test_version_first_line_is_unchanged_for_scripts() -> None:
    # setup-action writes `credenzo version` to $GITHUB_OUTPUT: one line only.
    out = CliRunner().invoke(app, ["version"]).output
    assert out.strip().splitlines() == [out.strip().splitlines()[0]]
    assert out.startswith("credenzo ")


def test_help_names_the_repository() -> None:
    out = CliRunner().invoke(app, ["--help"], env={"COLUMNS": "200"}).output
    assert REPO_URL in out


def test_markdown_footer_links_the_repository() -> None:
    assert f"]({REPO_URL})" in MD_FOOTER
    assert MD_FOOTER.startswith("<sub>") and MD_FOOTER.endswith("</sub>")


def test_diff_pr_comment_ends_with_the_footer() -> None:
    from mcp_audit.diff.render import render_pr_comment

    assert render_pr_comment([], "base", "head").rstrip().endswith(MD_FOOTER)


def test_lock_pr_comment_ends_with_the_footer() -> None:
    from mcp_audit.lock.verifier import VerifyResult, render_pr_comment

    out = render_pr_comment(VerifyResult(checked_servers=2))
    assert out.rstrip().endswith(MD_FOOTER)


def test_killchain_report_ends_with_the_footer() -> None:
    from mcp_audit.killchain.render import render_markdown
    from mcp_audit.models import AttackPathSummary

    out = render_markdown([], AttackPathSummary(), timestamp=dt.datetime(2026, 1, 1))
    assert out.rstrip().endswith(MD_FOOTER) and out.endswith("\n")


def test_team_alert_is_signed() -> None:
    import importlib.util

    team_file = Path(__file__).resolve().parent.parent / "team" / "credenzo_team.py"
    spec = importlib.util.spec_from_file_location("credenzo_team_sig", team_file)
    assert spec and spec.loader
    team = importlib.util.module_from_spec(spec)
    sys.modules["credenzo_team_sig"] = team
    spec.loader.exec_module(team)
    text = team.message([], 1, "acme/app", "https://example.invalid/run")
    assert text.splitlines()[-1] == team.SIGNATURE
    assert REPO_URL in team.SIGNATURE


def test_dashboard_links_the_repository() -> None:
    from mcp_audit.output.dashboard import _DASHBOARD_HTML

    assert f'href="{REPO_URL}"' in _DASHBOARD_HTML
