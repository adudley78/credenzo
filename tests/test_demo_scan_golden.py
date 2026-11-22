"""End-to-end check: a first scan of ``demo/configs/`` gives the expected findings.

This is the scan step of the ``verify`` skill (``.claude/skills/verify/``).
It runs the real ``scan`` command on the three demo configs and compares one
line per finding (severity, ID, server, tool) with
``tests/golden/demo_scan_findings.json``.  Titles and descriptions are left
out on purpose, so a wording change does not fail it; a new, lost or
re-graded finding does.

The rug-pull state goes to a temporary folder, so each run is a first scan
(the 75 in CLAUDE.md's "Current state"), not a second one.

CFHYG-001 and CFHYG-002 read file and folder permissions.  They are skipped
on Windows and change with the umask of the checkout, so they are left out of
the comparison (``HOST_DEPENDENT_IDS``); their own tests cover them.

When a change is meant to change the demo findings, write the file again and
say why in the CHANGELOG ``[Unreleased]`` section:

    CREDENZO_WRITE_DEMO_GOLDEN=1 uv run pytest tests/test_demo_scan_golden.py

Never write it again to make an unexplained difference go away.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_audit.cli import app

REPO = Path(__file__).resolve().parent.parent
DEMO_CONFIGS = REPO / "demo" / "configs"
GOLDEN = REPO / "tests" / "golden" / "demo_scan_findings.json"
WRITE_ENV = "CREDENZO_WRITE_DEMO_GOLDEN"
HOST_DEPENDENT_IDS = frozenset({"CFHYG-001", "CFHYG-002"})

runner = CliRunner()


def _finding_line(finding: dict) -> str:
    """Return the fields that identify a finding, in one line."""
    tool = finding.get("tool") or "-"
    return f"{finding['severity']} {finding['id']} {finding['server']} {tool}"


def _scan_demo(state_dir: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Run a first scan of the demo configs and return the JSON report."""
    monkeypatch.setattr("mcp_audit.analyzers.rug_pull._STATE_DIR", state_dir)
    monkeypatch.setattr(
        "mcp_audit.analyzers.rug_pull.DEFAULT_STATE_PATH", state_dir / "state.json"
    )
    result = runner.invoke(app, ["scan", str(DEMO_CONFIGS), "-f", "json"])
    assert result.exit_code == 1, (
        f"the demo scan should exit 1 (findings found), got {result.exit_code}:\n"
        f"{result.output[-2000:]}"
    )
    out = result.output
    return json.loads(out[out.index("{") :])


def _summary(doc: dict) -> dict:
    """Reduce a scan report to the part that the golden file pins."""
    findings = [f for f in doc["findings"] if f["id"] not in HOST_DEPENDENT_IDS]
    return {
        "grade": doc["score"]["grade"],
        "count": len(findings),
        "findings": sorted(_finding_line(f) for f in findings),
    }


def test_first_demo_scan_matches_the_golden_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary = _summary(_scan_demo(tmp_path / "state", monkeypatch))

    if os.environ.get(WRITE_ENV) == "1":
        GOLDEN.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        return

    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    added = sorted(set(summary["findings"]) - set(expected["findings"]))
    lost = sorted(set(expected["findings"]) - set(summary["findings"]))
    assert summary == expected, (
        "The demo scan changed.\n"
        f"  new: {added}\n"
        f"  lost: {lost}\n"
        f"  count: {expected['count']} -> {summary['count']}, "
        f"grade: {expected['grade']} -> {summary['grade']}\n"
        "If the change is intended, write the file again "
        f"({WRITE_ENV}=1) and say why in CHANGELOG [Unreleased]."
    )


def test_golden_file_is_not_written_by_default() -> None:
    """The write switch must be off in CI, or the check passes on anything."""
    assert os.environ.get(WRITE_ENV) != "1" or not os.environ.get("CI"), (
        f"{WRITE_ENV}=1 is set in CI"
    )
