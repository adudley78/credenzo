---
name: verify
description: Use before each commit in this repository, and to confirm a fix. Lints, runs the tests for the changed code, then runs the real scan and the `run` demo end to end.
---

# Verify a change

Run the steps in order. Stop at the first failure. All steps are offline.

1. Lint: `uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/`
2. The tests for the changed code: `tests/test_<module>.py` for each changed module, the tests that its `docs/module-map.md` entry names, and each changed test file. Run them with `uv run pytest <files> -q -rs`.
3. End to end: `uv run pytest tests/test_demo_scan_golden.py tests/test_demo_run.py -q -rs`. The first scans `demo/configs/` and compares each finding with `tests/golden/demo_scan_findings.json`. The second runs `demo/run/run.sh` (needs the `mcp` extra).
4. Before a pull request: the "Verify block" in `CONTRIBUTING.md`.

Put the commands and results in the pull request body. Name each skipped test and its reason: a skip is not a pass.

## Rules

- If a check still fails after three fix rounds, stop. Report what fails, what you tried, and your best guess at the cause.
- Do not skip a flaky test, add sleeps, or retry until it passes. Find the root cause. If you cannot, delete the test and record why in the pull request and `GAPS.md`.
- Do not edit a golden file, count, threshold, fingerprint or assertion to make your change pass. If the change is meant to change the result, run `CREDENZO_WRITE_DEMO_GOLDEN=1 uv run pytest tests/test_demo_scan_golden.py` and give the reason in CHANGELOG `[Unreleased]`.
