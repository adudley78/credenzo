#!/usr/bin/env python3
"""Weekly numbers for the Credenzo Team experiment, and the decision.

The experiment has one rule, set before it started:

- Continue when there are 10 paying customers or $1,000 of monthly revenue.
- Stop when, 90 days after subscriptions opened, there are fewer than 3
  paying customers or less than $300 of monthly revenue. At $99 a month,
  3 customers are $297, so the stop line needs 4 customers.

This script reads the numbers that are public (GitHub through the ``gh``
command, PyPI through pypistats.org) and applies the rule to the two numbers
that are not: paying
customers and monthly revenue. Give those with ``--customers`` and ``--mrr``
(read them from the Stripe dashboard). They are not read from Stripe here and
are not written anywhere, so a run of this script in a public log shows
nothing private unless you pass them.

Not measured, on purpose: guard blocks, and locks or checks in private
repositories. Credenzo sends no telemetry (docs/telemetry.md), so the only
usage numbers are the public ones below.

Only numbers that show use by people are printed. These are left out:

- PyPI downloads with no operating system. pip, uv and the other installers
  send it; bots, security scanners, mirrors and browsers do not. In November
  2026 they were 75% of all downloads.
- Repository clones and release downloads. The CI of this repository makes
  part of them on each run, and GitHub does not show which part.

The PyPI installs are those of ``mcp-audit-scanner``. An install of
``credenzo`` also installs ``mcp-audit-scanner`` (the code is there), so the
two names are counted once. The installs still include CI runs of users.

Usage::

    python3 scripts/paid_path_report.py --customers 0 --mrr 0
    python3 scripts/paid_path_report.py --json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OFFER_PATH = ROOT / "team" / "offer.json"
REPO = "adudley78/credenzo"

SUCCESS_CUSTOMERS = 10
SUCCESS_MRR_USD = 1000
STOP_CUSTOMERS = 3
STOP_MRR_USD = 300
WINDOW_DAYS = 90

#: Public code searches. Each counts repositories other than this one.
SEARCHES = {
    "public_repos_with_a_credenzo_lock": [
        '"generated_by" "mcp-audit" filename:mcp-lock.json'
    ],
    "public_repos_that_run_the_action": [
        "adudley78/credenzo path:.github/workflows",
        "adudley78/mcp-audit path:.github/workflows",
    ],
    "public_repos_that_run_the_team_action": [
        "adudley78/credenzo/team path:.github/workflows"
    ],
}
SEARCH_PAUSE_SECONDS = 7  # The code search API allows 10 requests a minute.

OWNER = REPO.split("/")[0]
#: The distribution that holds the code, and the name that installs it.
PYPI_CODE_PACKAGE = "mcp-audit-scanner"
PYPI_NAME_PACKAGE = "credenzo"
PYPI_PAUSE_SECONDS = 3  # pypistats.org answers 429 to fast requests.

#: The words printed for each number. A key that is not here is not printed.
LABELS = {
    "stars": "stars",
    "forks": "forks",
    "visitors_14_days": "unique visitors, 14 days (the owner included)",
    "people_who_opened_an_issue_or_pr_30_days": "people other than the owner"
    " who opened an issue or pull request, 30 days",
    "pypi_installs_7_days": "PyPI installs, 7 days",
    "pypi_installs_30_days": "PyPI installs, 30 days",
    "pypi_installs_30_days_with_the_name_credenzo": "of these, with the name credenzo",
    "pypi_downloads_30_days_with_no_installer_percent": "PyPI downloads with no"
    " installer (left out), %",
    "latest_release": "latest release",
    "public_repos_with_a_credenzo_lock": "public repos with a Credenzo lock",
    "public_repos_that_run_the_action": "public repos that run the action",
    "public_repos_that_run_the_team_action": "public repos that run the Team action",
}

Api = Callable[[str, dict[str, str]], Any]
PyPI = Callable[[str], Any]


def decide(
    live_since: str | None, today: date, customers: int | None, mrr: float | None
) -> dict[str, Any]:
    """Apply the rule. Return the state, the day count and one sentence."""
    if not live_since:
        return {
            "state": "NOT LIVE",
            "day": None,
            "text": "Subscriptions are not open. The 90 days have not started.",
        }
    day = (today - date.fromisoformat(live_since)).days
    if customers is None or mrr is None:
        return {
            "state": "UNKNOWN",
            "day": day,
            "text": f"Day {day} of {WINDOW_DAYS}. Give --customers and --mrr.",
        }
    if customers >= SUCCESS_CUSTOMERS or mrr >= SUCCESS_MRR_USD:
        return {
            "state": "CONTINUE",
            "day": day,
            "text": f"Day {day}. The success line is met. Continue Priority 1.",
        }
    if day >= WINDOW_DAYS and (customers < STOP_CUSTOMERS or mrr < STOP_MRR_USD):
        return {
            "state": "STOP",
            "day": day,
            "text": f"Day {day}. Below the stop line after {WINDOW_DAYS} days."
            " Stop work on the lock offer and start Priority 2.",
        }
    if day >= WINDOW_DAYS:
        return {
            "state": "CONTINUE",
            "day": day,
            "text": f"Day {day}. Above the stop line and below the success line.",
        }
    return {
        "state": "RUNNING",
        "day": day,
        "text": f"Day {day} of {WINDOW_DAYS}. No decision before day {WINDOW_DAYS}"
        " unless the success line is met.",
    }


def gh_api(path: str, fields: dict[str, str]) -> Any:
    """GET a GitHub REST path with the ``gh`` command. ``None`` on failure."""
    args = ["gh", "api", "-X", "GET", path]
    for key, value in fields.items():
        args += ["-f", f"{key}={value}"]
    try:
        done = subprocess.run(  # noqa: S603
            args, capture_output=True, text=True, check=False, timeout=60
        )
        return json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def pypistats_system(package: str) -> Any:
    """Return the daily downloads by operating system from pypistats.org.

    Each row is ``{"category": "Linux" | ... | "null", "date": ..., "downloads": n}``.
    ``None`` when the site cannot be read.
    """
    url = f"https://pypistats.org/api/packages/{package}/system"
    try:
        # A constant https URL of pypistats.org.
        opened = urllib.request.urlopen(url, timeout=20)  # noqa: S310  # nosec B310
        with opened as response:
            rows = json.loads(response.read())["data"]
        return rows if isinstance(rows, list) else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def pypi_counts(rows: Any, days: int) -> dict[str, int] | None:
    """Count the downloads of the last ``days`` days of data.

    ``installs`` have an operating system (pip, uv and other installers send
    one). ``no_installer`` have none: bots, scanners, mirrors and browsers.
    pypistats.org is one day late, so the window ends on its last date.
    """
    if not isinstance(rows, list):
        return None
    valid = [
        r
        for r in rows
        if isinstance(r, dict)
        and isinstance(r.get("date"), str)
        and isinstance(r.get("downloads"), int)
    ]
    if not valid:
        return None
    try:
        end = max(date.fromisoformat(r["date"]) for r in valid)
        start = end.toordinal() - days + 1
        window = [
            r for r in valid if date.fromisoformat(r["date"]).toordinal() >= start
        ]
    except ValueError:
        return None
    no_installer = sum(r["downloads"] for r in window if r.get("category") == "null")
    total = sum(r["downloads"] for r in window)
    return {"installs": total - no_installer, "no_installer": no_installer}


def people_who_opened(api: Api, since: date) -> list[str] | None:
    """Return the people other than the owner who opened an issue or PR.

    Bots (Dependabot and others) are not people and are not counted.
    """
    people: set[str] = set()
    for kind in ("issue", "pull-request"):
        query = f"repo:{REPO} is:{kind} created:>={since.isoformat()} -author:{OWNER}"
        found = api("search/issues", {"q": query, "per_page": "100"})
        items = _get(found, "items")
        if not isinstance(items, list):
            return None
        for item in items:
            user = _get(item, "user")
            if _get(user, "type") == "User" and _get(user, "login"):
                login = str(_get(user, "login"))
                if login.lower() != OWNER.lower():
                    people.add(login)
    return sorted(people)


def _get(data: Any, *keys: str) -> Any:
    for key in keys:
        data = data.get(key) if isinstance(data, dict) else None
    return data


def public_numbers(
    api: Api = gh_api,
    pause: Callable[[float], None] = time.sleep,
    pypi: PyPI = pypistats_system,
    today: date | None = None,
) -> dict[str, Any]:
    """Collect the public numbers. A number that cannot be read is ``None``."""
    today = today or date.today()
    repo = api(f"repos/{REPO}", {})
    release = api(f"repos/{REPO}/releases/latest", {})
    code_rows = pypi(PYPI_CODE_PACKAGE)
    pause(PYPI_PAUSE_SECONDS)
    name_rows = pypi(PYPI_NAME_PACKAGE)
    week = pypi_counts(code_rows, 7)
    month = pypi_counts(code_rows, 30)
    name_month = pypi_counts(name_rows, 30)
    seen = month and month["installs"] + month["no_installer"]
    numbers: dict[str, Any] = {
        "stars": _get(repo, "stargazers_count"),
        "forks": _get(repo, "forks_count"),
        "visitors_14_days": _get(api(f"repos/{REPO}/traffic/views", {}), "uniques"),
        "people_who_opened_an_issue_or_pr_30_days": people_who_opened(
            api, date.fromordinal(today.toordinal() - 30)
        ),
        "pypi_installs_7_days": week and week["installs"],
        "pypi_installs_30_days": month and month["installs"],
        "pypi_installs_30_days_with_the_name_credenzo": name_month
        and name_month["installs"],
        "pypi_downloads_30_days_with_no_installer_percent": round(
            100 * month["no_installer"] / seen
        )
        if month and seen
        else None,
        "latest_release": _get(release, "tag_name"),
    }
    for name, queries in SEARCHES.items():
        repos: set[str] | None = set()
        for query in queries:
            pause(SEARCH_PAUSE_SECONDS)
            found = api("search/code", {"q": query, "per_page": "100"})
            items = _get(found, "items")
            if not isinstance(items, list):
                repos = None
                break
            repos |= {
                str(_get(item, "repository", "full_name"))
                for item in items
                if isinstance(item, dict)
            }
        numbers[name] = None if repos is None else sorted(repos - {REPO})
    return numbers


def render(numbers: dict[str, Any], decision: dict[str, Any]) -> str:
    """Return the report as Markdown."""
    lines = [
        f"**{decision['state']}** - {decision['text']}",
        "",
        "| Public number | Value |",
        "|---|---|",
    ]
    for name, value in numbers.items():
        if name not in LABELS:
            continue
        label = LABELS[name]
        if isinstance(value, list):
            shown = f"{len(value)}" + (f" ({', '.join(value)})" if value else "")
        else:
            shown = "not read" if value is None else str(value)
        lines.append(f"| {label} | {shown} |")
    lines += [
        "",
        "Left out because they do not show use by people: PyPI downloads"
        " with no installer (bots, scanners, mirrors), repository clones and"
        " release downloads (this repository's CI makes part of them). PyPI"
        " installs count both names once and include CI runs of users.",
        "",
        "Not measured: guard blocks, and locks or checks in private"
        " repositories. Credenzo sends no telemetry.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Print the report. Return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--customers", type=int, help="paying customers (Stripe)")
    parser.add_argument("--mrr", type=float, help="monthly revenue in USD (Stripe)")
    parser.add_argument("--json", action="store_true", help="print JSON")
    args = parser.parse_args(argv)

    offer = json.loads(OFFER_PATH.read_text(encoding="utf-8"))
    decision = decide(offer.get("live_since"), date.today(), args.customers, args.mrr)
    numbers = public_numbers()
    if args.json:
        print(json.dumps({"decision": decision, "public": numbers}, indent=2))
    else:
        print(render(numbers, decision))
    return 0


if __name__ == "__main__":
    sys.exit(main())
