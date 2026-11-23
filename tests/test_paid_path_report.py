"""`scripts/paid_path_report.py`: the continue/stop rule and the public numbers."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "paid_path_report", ROOT / "scripts" / "paid_path_report.py"
)
report = importlib.util.module_from_spec(_spec)
sys.modules["paid_path_report"] = report
_spec.loader.exec_module(report)

LIVE = "2026-12-01"


def _state(day: int, customers: int | None, mrr: float | None) -> str:
    today = date.fromordinal(date.fromisoformat(LIVE).toordinal() + day)
    return report.decide(LIVE, today, customers, mrr)["state"]


def test_nothing_is_decided_before_subscriptions_open() -> None:
    got = report.decide(None, date(2026, 12, 1), 50, 5000.0)
    assert (got["state"], got["day"]) == ("NOT LIVE", None)


def test_the_paid_numbers_are_needed_for_a_decision() -> None:
    assert _state(10, None, None) == "UNKNOWN"
    assert _state(10, 3, None) == "UNKNOWN"


@pytest.mark.parametrize(
    ("day", "customers", "mrr", "state"),
    [
        (5, 0, 0.0, "RUNNING"),
        (89, 0, 0.0, "RUNNING"),
        (5, 10, 990.0, "CONTINUE"),  # 10 customers
        (5, 4, 1000.0, "CONTINUE"),  # $1,000 with fewer customers
        (90, 0, 0.0, "STOP"),
        (90, 2, 500.0, "STOP"),  # fewer than 3 customers
        (90, 3, 297.0, "STOP"),  # 3 customers at $99 are under $300
        (90, 4, 396.0, "CONTINUE"),
        (200, 9, 891.0, "CONTINUE"),
        (200, 10, 990.0, "CONTINUE"),
    ],
)
def test_the_rule(day: int, customers: int, mrr: float, state: str) -> None:
    assert _state(day, customers, mrr) == state


def test_the_thresholds_are_the_ones_that_were_set() -> None:
    assert (report.SUCCESS_CUSTOMERS, report.SUCCESS_MRR_USD) == (10, 1000)
    assert (report.STOP_CUSTOMERS, report.STOP_MRR_USD) == (3, 300)
    assert report.WINDOW_DAYS == 90


def _api(overrides: dict[str, Any] | None = None) -> Any:
    answers: dict[str, Any] = {
        "repos/adudley78/credenzo": {"stargazers_count": 6, "forks_count": 4},
        "repos/adudley78/credenzo/releases/latest": {
            "tag_name": "v0.34.0",
            "assets": [{"download_count": 12}, {"download_count": 8}, "junk"],
        },
        "repos/adudley78/credenzo/traffic/views": {"uniques": 83},
        "search/issues": {
            "items": [
                {"user": {"login": "someone", "type": "User"}},
                {"user": {"login": "dependabot[bot]", "type": "Bot"}},
                {"user": {"login": "Adudley78", "type": "User"}},
                {"user": {"login": "someone", "type": "User"}},
            ]
        },
        "search/code": {
            "items": [
                {"repository": {"full_name": "adudley78/credenzo"}},
                {"repository": {"full_name": "someone/app"}},
                {"repository": {"full_name": "someone/app"}},
            ]
        },
        **(overrides or {}),
    }
    return lambda path, _fields: answers.get(path)


def _rows(days: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    return [
        {"date": day, "category": category, "downloads": n}
        for day, counts in days.items()
        for category, n in counts.items()
    ]


#: mcp-audit-scanner: 40 days of data, the last date 2026-11-22.
_CODE = _rows(
    {
        "2026-10-13": {"Linux": 1000, "null": 1000},  # 41 days back: outside
        "2026-10-24": {"Linux": 10, "null": 90},  # day 30 of 30
        "2026-11-15": {"Darwin": 5, "null": 500},  # day 8: in 30, not in 7
        "2026-11-16": {"Linux": 20, "Windows": 2, "null": 300},  # day 7 of 7
        "2026-11-22": {"Linux": 3, "null": 10},
    }
)
_NAME = _rows({"2026-11-20": {"Linux": 7, "null": 50}})


def _pypi(package: str) -> Any:
    return {"mcp-audit-scanner": _CODE, "credenzo": _NAME}.get(package)


TODAY = date(2026, 11, 23)


def test_public_numbers_count_other_repositories_once() -> None:
    pauses: list[float] = []
    numbers = report.public_numbers(_api(), pauses.append, _pypi, TODAY)
    assert numbers["stars"] == 6 and numbers["forks"] == 4
    assert numbers["visitors_14_days"] == 83
    assert numbers["public_repos_with_a_credenzo_lock"] == ["someone/app"]
    searches = sum(len(q) for q in report.SEARCHES.values())
    assert pauses.count(report.SEARCH_PAUSE_SECONDS) == searches


def test_pypi_counts_installs_only() -> None:
    """A download with no operating system is not an install."""
    numbers = report.public_numbers(_api(), lambda _s: None, _pypi, TODAY)
    assert numbers["pypi_installs_7_days"] == 20 + 2 + 3
    assert numbers["pypi_installs_30_days"] == 10 + 5 + 22 + 3
    # 900 of 940 downloads in the 30 days had no installer.
    assert numbers["pypi_downloads_30_days_with_no_installer_percent"] == 96


def test_the_two_pypi_names_are_counted_once() -> None:
    """An install of credenzo also downloads mcp-audit-scanner."""
    numbers = report.public_numbers(_api(), lambda _s: None, _pypi, TODAY)
    assert numbers["pypi_installs_30_days"] == 40  # not 40 + 7
    assert numbers["pypi_installs_30_days_with_the_name_credenzo"] == 7


def test_raw_downloads_clones_and_release_downloads_are_not_printed() -> None:
    numbers = report.public_numbers(_api(), lambda _s: None, _pypi, TODAY)
    assert not {"cloners_14_days", "latest_release_downloads"} & set(numbers)
    assert not any("downloads_last_month" in k for k in numbers)
    text = report.render(numbers, report.decide(None, TODAY, None, None))
    assert "| PyPI installs, 30 days | 40 |" in text
    assert "Left out because they do not show use by people" in text
    assert set(numbers) == set(report.LABELS)


def test_only_people_other_than_the_owner_are_counted() -> None:
    asked: list[dict[str, str]] = []

    def api(path: str, fields: dict[str, str]) -> Any:
        if path == "search/issues":
            asked.append(fields)
        return _api()(path, fields)

    numbers = report.public_numbers(api, lambda _s: None, _pypi, TODAY)
    assert numbers["people_who_opened_an_issue_or_pr_30_days"] == ["someone"]
    assert [f["q"] for f in asked] == [
        "repo:adudley78/credenzo is:issue created:>=2026-10-24 -author:adudley78",
        "repo:adudley78/credenzo is:pull-request created:>=2026-10-24"
        " -author:adudley78",
    ]


@pytest.mark.parametrize(
    "rows", [None, [], [{"date": "not a date", "category": "Linux", "downloads": 1}]]
)
def test_pypi_data_that_cannot_be_read_is_none(rows: Any) -> None:
    assert report.pypi_counts(rows, 30) is None


def test_a_number_that_cannot_be_read_is_none_and_not_zero() -> None:
    api = _api(
        {
            "search/code": None,
            "search/issues": None,
            "repos/adudley78/credenzo/traffic/views": None,
            "repos/adudley78/credenzo/releases/latest": None,
        }
    )
    numbers = report.public_numbers(api, lambda _s: None, lambda _p: None, TODAY)
    assert numbers["visitors_14_days"] is None
    assert numbers["latest_release"] is None
    assert numbers["public_repos_that_run_the_action"] is None
    assert numbers["people_who_opened_an_issue_or_pr_30_days"] is None
    assert numbers["pypi_installs_30_days"] is None
    assert numbers["pypi_downloads_30_days_with_no_installer_percent"] is None
    text = report.render(numbers, report.decide(None, TODAY, None, None))
    assert "| unique visitors, 14 days (the owner included) | not read |" in text
    assert "| public repos that run the action | not read |" in text
    assert "| PyPI installs, 30 days | not read |" in text


def test_zero_installs_is_zero_and_not_none() -> None:
    rows = _rows({"2026-11-22": {"null": 5}})
    numbers = report.public_numbers(_api(), lambda _s: None, lambda _p: rows, TODAY)
    assert numbers["pypi_installs_30_days"] == 0
    assert numbers["pypi_downloads_30_days_with_no_installer_percent"] == 100


def test_the_report_says_what_is_not_measured() -> None:
    numbers = report.public_numbers(_api(), lambda _s: None, _pypi, TODAY)
    text = report.render(numbers, report.decide(LIVE, date(2027, 3, 1), 0, 0.0))
    assert text.startswith("**STOP** - Day 90.")
    assert "| public repos with a Credenzo lock | 1 (someone/app) |" in text
    assert "Not measured: guard blocks" in text
