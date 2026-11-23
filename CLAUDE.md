# Credenzo (formerly mcp-audit)

An open-source, privacy-first CLI tool that scans MCP (Model Context Protocol)
server configurations for security vulnerabilities. Think "Snyk for MCP servers."

## Names (0.33.0 rename)

The product is **Credenzo** and the command is `credenzo`. Use those in every
text a person reads: help text, reports, messages, documentation, examples.

These keep the old name on purpose. Do not rename them without a migration:

- The `mcp-audit` command (same entry point; `_entry._old_name_notice` prints one
  stderr line in a terminal, never in CI, a pipe, or `run`).
- The distribution that holds the code, `mcp-audit-scanner`. The `credenzo`
  distribution (`packaging/credenzo/`) holds no code: it pins the same version,
  forwards the extras and declares the `credenzo` command
  (`tests/test_credenzo_package.py`). Publish it with
  `publish-credenzo-name.yml` after each release.
- The import package `mcp_audit`, the release binary names
  (`mcp-audit-<os>-<arch>`), the spec files.
- The repository is `adudley78/credenzo` (renamed 2026-11-16; GitHub redirects
  the old name). URLs use the new name. `setup-action` accepts a binary signed
  under either name. Never create a repository named `mcp-audit`: that ends
  the redirects.
- Machine contracts: exact `"mcp-audit"` literals (platformdirs directory, SARIF
  tool name, CycloneDX/OpenVEX/Nucleus tool names, `_producer`), lock
  `generated_by`, `mcp-audit/…` and `mcp-audit:` property keys, the
  code-scanning category, `.mcp-audit-policy.yml`, `mcp-audit-feed.pub`, the
  `mcp-audit.dev` API host, `MCP_AUDIT_*` environment variables.
- A wrapped config entry may launch `mcp-audit run` (written before 0.33.0) or
  `credenzo run`; `runtime/wrapping._WRAPPER_NAME` accepts both.
- Pre-commit hook ids `mcp-audit` and `mcp-audit-lock-verify` stay beside
  `credenzo` and `credenzo-lock-verify`; the setup action puts both command
  names on PATH and keeps the `mcp-audit-version` output.

## What this project does

Developers use MCP servers to give AI agents (Claude, Cursor, VS Code Copilot) access
to tools — file systems, databases, APIs, etc. These servers are configured via JSON
files and can be poisoned, misconfigured, or compromised. Credenzo scans those configs
and flags security issues.

## Business model

The `credenzo` command is fully open source under Apache 2.0 — every command and
every check is free for every user. There is no Community / Pro / Enterprise
split and no license-key gate in the package. All paid-license plumbing (Ed25519
signing, revocation lists, `activate` / `license` commands, the `gate()` shim)
was removed in v0.2.0; anything that still references `licensing.py` or
`_gate.py` is stale.

There is one paid offer, beside the package and not in it: **Credenzo Team**
(`team/`, `docs/team.md`, added 2026-11-20). It is a GitHub Action that runs
`credenzo lock --verify` and sends drift alerts (an issue, a webhook message).
The check itself is the free command and always runs. Alerts are free for
personal accounts and public repositories, and $99 a month (up to 10 seats) for
the private repositories of an organization. Rules that keep it honest:

- `team/` is never imported by `src/mcp_audit` and never ships in the wheel or
  the binary (`tests/test_team_action.py::test_the_team_code_is_not_in_the_package`).
  Do not put a licence check in the package.
- `team/credenzo_team.py` and `scripts/team_licenses.py` use the standard
  library only. The action sends nothing to the project (no usage report);
  `docs/telemetry.md` still holds.
- A subscription is found by GitHub owner name in the public licence list on
  the `team-licenses` branch, which `.github/workflows/team-licenses.yml`
  builds from Stripe twice an hour. The list holds digests and fillers, never a
  name, an email address or a Stripe ID; neither job prints one, or a count.
  The length of the list shows no count, but someone who keeps copies of it
  can count the entries that are new. When
  the list cannot be read, alerts stay on.
- The offer (price, checkout link, the date the experiment started) is
  `team/offer.json`; `scripts/team_go_live.py` writes it and the "Subscribe"
  block of `docs/team.md`. `scripts/paid_path_report.py` prints the weekly
  public numbers and applies the continue/stop rule that was set before the
  experiment (10 customers or $1k MRR to continue; after 90 days, fewer than 3
  customers or less than $300 MRR to stop, which at $99 means that 4 customers
  pass the stop line).

Funding is also requested via GitHub Sponsors (handle configured in
`.github/FUNDING.yml`, with a "Support" section in `README.md`).

## Tech stack

- Python 3.11+, managed with `uv`
- CLI: Typer + Rich
- Data models: Pydantic v2
- Testing: pytest + pytest-asyncio
- Linting: Ruff + Bandit
- Packaging: hatchling via pyproject.toml

## Project layout

One line per module. The detail for each one (finding IDs, pipeline step,
budgets, the tests that pin it) is in `docs/module-map.md`: read its entry,
and the module docstring, before you change a module.

```
src/mcp_audit/
├── cli/                           # Typer app; one submodule per command group
│   ├── __init__.py                # `app` and sub-apps; re-exports the names tests patch
│   ├── __main__.py                # `python -m mcp_audit.cli` (PyInstaller target)
│   ├── _helpers.py                # `_write_output`
│   ├── scan.py                    # scan, discover, pin, watch (`_apply_*` stages, `_write_*` output)
│   ├── check.py                   # check: one-page verdict
│   ├── fix.py                     # fix: safe remediations
│   ├── wrap.py                    # wrap / unwrap: launch local servers through `credenzo run`
│   ├── run.py                     # `run` in --help; `_entry.py` dispatches it to runtime/
│   ├── guard.py                   # `guard` in --help; `_entry.py` dispatches it to runtime/guard.py
│   ├── diff.py                    # diff: MCP-aware diff for PR review and CI gates
│   ├── baseline.py                # baseline: save / list / compare / delete / export
│   ├── registry.py                # update-registry, verify
│   ├── rules.py                   # rule: validate / test / list
│   ├── policy.py                  # policy: validate / init / check
│   ├── extensions.py              # extensions: discover / scan
│   ├── agent_files.py             # agent-files: discover / scan
│   ├── plugins.py                 # plugins: discover / scan
│   ├── lock.py                    # lock: write, --verify, --accept mcp-lock.json
│   ├── _bundle.py                 # --bundle / --bundle-key for scan and affected
│   ├── sast.py                    # sast
│   ├── sbom.py                    # sbom: CycloneDX 1.5
│   ├── affected.py                # affected: is this advisory in a discovered server?
│   ├── reach.py                   # reach: what can the agents on this machine touch?
│   ├── vet.py                     # vet: pre-install package verdict
│   ├── shadow.py                  # shadow: shadow MCP server sweep
│   ├── killchain.py               # killchain: top blast-radius-cutting changes
│   ├── snapshot.py                # snapshot: signed forensic snapshots
│   ├── dashboard.py               # dashboard
│   ├── fleet.py                   # merge: fleet report from scan JSON files
│   ├── push_nucleus.py            # push-nucleus: scan and upload to Nucleus
│   ├── register.py                # register: opt-in registration
│   ├── advise.py                  # advise and `feed verify`
│   └── version.py                 # version
├── scanner.py                     # Orchestrator: discovery → parsing → `_run_static_pipeline` → score
├── scoring.py                     # Score 0–100 and grade A–F (docs/scoring.md)
├── discovery.py                   # Finds MCP config files across all supported clients
├── config_parser.py               # Parses JSON configs, normalizes across client formats
├── models.py                      # Pydantic models: Finding, ServerConfig, ScanResult, ScanScore, …
├── owasp_mcp.py                   # Single source of truth for OWASP MCP Top 10 codes/names
├── verdict.py                     # Pure verdict builder for `vet`
├── watcher.py                     # `watch` filesystem watcher
├── mcp_client.py                  # Live MCP connection for --connect
├── _paths.py                      # Find bundled data in source, wheel and frozen builds
├── _network.py                    # --offline mutual exclusion for network flags
├── _entry.py                      # Console script; dispatches `run` and `guard` before Typer loads
├── _jcs.py                        # RFC 8785 canonical JSON, stdlib only (used by `run`)
├── runtime/                       # `credenzo run` and `guard`: stdlib only on the launch path (docs/run.md)
│   ├── cli.py                     # argparse for `run`; exit 78 when enforce refuses
│   ├── relay.py                   # Byte-exact stdio relay; enforce mode goes line by line
│   ├── gate.py                    # Launch gate: argv vs the lock entry
│   ├── wrapping.py                # Wrap and unwrap entries; when a wrapper is trusted
│   ├── guard.py                   # `credenzo guard`: Claude Code PreToolUse hook
│   └── tools.py                   # ToolGuard: live tools/list vs the lock's tool digests
├── _redact.py                     # Local-path redaction for output that leaves the host
├── bundle.py                      # Signed air-gapped data bundle
├── gateways.py                    # MCP gateway upstreams (mcptoon, 1MCP, MCPHub)
├── keys/                          # Feed public key (mcp-audit-feed.pub)
├── _gitobjects.py                 # Read-only git object store (never runs git)
├── _gitignore.py                  # gitignore matcher (never runs git)
├── host_platform.py               # windows / wsl / macos / linux
├── harness_versions.py            # Installed agent harness versions, read from files
├── guardrails.py                  # GUARD-001/002: guardrail drift
├── policy_sources.py              # Read-only OS policy readers (plist, registry)
├── affected/                      # `affected` engine: query, match, render
│   ├── transitive.py              # `affected --transitive`
│   ├── fleet.py                   # `affected --fleet`
│   ├── vex.py                     # OpenVEX 0.2.0 writer
│   ├── fixplan.py                 # `affected --fix`
│   └── respond.py                 # Respond block and --policy-out
├── exploit/                       # KEV / EPSS / public-PoC signals
├── analyzers/                     # Detection
│   ├── base.py                    # BaseAnalyzer abstract class
│   ├── poisoning.py               # Tool description poisoning detection
│   ├── credentials.py             # Secret/API key exposure in configs
│   ├── transport.py               # Transport security
│   ├── supply_chain.py            # Package provenance and typosquatting detection
│   ├── hook_runnable.py           # HOOK-004/005: hook commands that cannot start
│   ├── config_hygiene.py          # CFHYG, HARNESS, HOOK-001/002, TRUST-003/008, PERM-001..006
│   ├── rug_pull.py                # Config-entry change detection via hashing
│   ├── toxic_flow.py              # TOXIC-*, INTEG-001: dangerous capability pairs
│   ├── auth.py                    # Remote server authentication checks
│   ├── collision.py               # COLLIDE-001..003: tool name and description copies (--connect)
│   ├── annotations.py             # ANNOT-001: readOnlyHint on a tool that writes
│   ├── delegation.py              # DELEG-001..003: cross-tool delegation (--connect)
│   ├── git_exec.py                # TRUST-006/007: git config that can run code
│   ├── permissions.py             # PERM-001..007: Claude Code permission rules
│   ├── sandbox.py                 # SANDBOX-001..005: sandbox settings a repository loosens
│   ├── rule_secrets.py            # CRED-004: credentials in permission rules
│   ├── rule_secret_history.py     # CRED-005: CRED-004 over git history
│   ├── shipped_settings.py        # CRED-006: settings an image or npm package ships
│   ├── managed_policy.py          # MANAGED-001..007: managed MCP policy vs servers
│   ├── secret_reach.py            # REACH-001..003: credential files readable without a prompt
│   ├── npx_cache.py               # SC-011: known-malicious packages in the npx cache
│   └── attack_paths.py            # Attack paths and the greedy hitting set
├── reach/                         # `reach` engine (pure, no subprocess)
│   ├── engine.py                  # build_machine_reach(): one verdict per agent
│   ├── claude.py                  # Claude Code's answers
│   ├── codex.py                   # Codex answers from config.toml
│   ├── surface.py                 # Allowlists; anything off them is COULDN'T CHECK
│   ├── network.py                 # Does a server reach the network?
│   ├── common.py                  # Shared assessment helpers
│   ├── context.py                 # Paths and capped reads
│   ├── models.py                  # Dataclasses; `sanitize()` is the one choke point
│   └── fleet.py                   # `reach --fleet DIR`
├── agent_files/                   # Instruction, memory and skill files (SKILL-*, MEM-*)
│   ├── models.py                  # AgentFile and surfaces
│   ├── discovery.py               # discover_agent_files()
│   ├── imports.py                 # Claude Code @path imports and "read X" references
│   ├── gitignore.py               # .gitignore matcher read by file
│   ├── heartbeat.py               # MEM-004 detector
│   ├── sleeper.py                 # MEM-005 detector
│   ├── exfil.py                   # MEM-006 detector
│   ├── instruction_shapes.py      # MEM-007/008 detectors
│   ├── drift.py                   # INSTR-001/002: instruction file drift
│   ├── reach.py                   # MEM-003..005 in the default scan and --project
│   ├── framing.py                 # Describes-vs-directs gate for SKILL-001
│   ├── analyzer.py                # analyze_agent_files()
│   ├── skill_package.py           # SKILL-005..008: every file in a skill folder
│   ├── install_steps.py           # Pure text checks for skill install steps
│   └── subagents.py               # AGENT-001..004: subagent definitions
├── plugins/                       # Claude Code plugins (PLUGIN-*, MOD-*)
│   ├── models.py                  # InstalledPlugin dataclass
│   ├── discovery.py               # Installed plugins and their MCP servers
│   ├── analyzer.py                # PLUGIN-001/002
│   ├── checkout.py                # PLUGIN-003/004: pin vs checked-out commit
│   └── mods.py                    # MOD-001..006: Claude Code mods
├── ci_workflows/                  # WORKFLOW-001..003: Actions workflows that run an agent
│   ├── discovery.py               # Find workflow files (bounded)
│   └── analyzer.py                # Analyze them
├── lock/                          # mcp-lock.json (ADR-0005, docs/lock.md)
│   ├── model.py                   # Ownership boundary and top-level checksum
│   ├── writer.py                  # regenerate()/write_lock()
│   ├── verifier.py                # lock --verify: LOCK-001..014
│   ├── section_digests.py         # lock_version 2 section digests
│   ├── guardrail_section.py       # `guardrails` section (LOCK-014)
│   ├── tool_digests.py            # `tools` section: per-tool digests
│   ├── calendar_text.py           # Dates that move with the calendar (stdlib only)
│   ├── tool_text.py               # saved tool text `mcp-lock.tools.json`
│   ├── core.py                    # Stdlib-only primitives shared with `run`
│   └── identity.py, resolve.py, discovery.py, auto_verify.py
├── advisory/                      # OSV 1.6.0 records and the signed feed (see invariants below)
│   ├── schema.py                  # Advisory dataclass → OSV 1.6.0 JSON
│   ├── classify.py                # finding ID → finding_class / observation / CVSS 3.1 vector
│   ├── canonical.py               # RFC 8785 JCS canonicalization
│   ├── freshness.py               # snapshot_version / published_at / expires on index.json only
│   ├── feed.py                    # build_advisory / write_feed
│   ├── sign.py                    # cosign and minisign backends; sign_feed / verify_feed
│   ├── validate.py                # validate_osv() against the vendored schema
│   └── osv_schema/                # Vendored osv-1.6.0.json
├── attestation/                   # --verify-hashes and Sigstore checks
│   ├── hasher.py                  # Layer 1: tarball SHA-256
│   ├── verifier.py                # verify_server_hashes()
│   ├── sigstore_client.py         # Layer 2: Sigstore bundles from npm and PyPI
│   └── sigstore_findings.py       # Layer 2 results → findings
├── baselines/
│   └── manager.py                 # BaselineManager, Baseline, BaselineServer, DriftFinding, DriftType
├── registry/
│   ├── loader.py                  # KnownServerRegistry, RegistryEntry, load_registry()
│   ├── twins.py                   # SC-007 unscoped twins
│   ├── malicious.py               # load_known_malicious(), assess()
│   ├── research.py                # load_research_records(), research_id()
│   └── reachability.py            # Transport tags on known CVEs
├── rules/
│   └── engine.py                  # Policy-as-code rule engine
├── governance/
│   ├── models.py                  # Governance policy models
│   ├── loader.py                  # load_policy() resolution order
│   └── evaluator.py               # evaluate_governance()
├── vulnerability/                 # `scan --check-vulns` (network, opt-in)
│   ├── models.py                  # ResolvedPackage, VulnAdvisory data models
│   ├── resolver.py                # Package and version from a launch line
│   ├── depsdev.py                 # fetch_dependency_graph() → DependencyGraph
│   ├── osv.py                     # OSV.dev queries
│   └── scanner.py                 # check_vulnerabilities()
├── diff/                          # MCP-aware diff engine
│   ├── loader.py                  # Load diff inputs (directory, scan JSON, git SHA)
│   ├── comparator.py              # Compare two ServerConfig lists → flat list of Change objects
│   ├── risk.py                    # Risk classification for diff changes
│   └── render.py                  # Render diff to terminal, JSON, and PR-comment Markdown
├── fixer/                         # `fix` engine: backup, then atomic write
│   ├── fixer.py                   # Orchestrator
│   └── strategies/
│       ├── base.py                # FixStrategy abstract base
│       ├── credentials.py         # CRED-001..003
│       ├── transport.py           # TRANSPORT-001
│       └── pinning.py             # SC-001/002
├── killchain/                     # Decision engine over the attack-path graph
│   ├── recommender.py             # Rank kill switches
│   ├── simulator.py               # What-if simulation
│   ├── patches.py                 # Generate governance-policy denylist / PR-comment patch snippets
│   └── render.py                  # Markdown and JSON output
├── shadow/                        # Shadow MCP server detection
│   ├── allowlist.py               # Operator allowlist of sanctioned servers
│   ├── classifier.py              # Pure sanctioned-vs-shadow classification given server + allowlist
│   ├── risk.py                    # RiskLevel scoring for a single server
│   ├── events.py                  # Structured events for --continuous daemon mode
│   └── state.py                   # first_seen / last_seen state (0o600)
├── snapshot/                      # Forensic snapshot rehydrate/diff
│   ├── rehydrate.py               # Rebuild the attack-path graph of a snapshot
│   └── diff.py                    # "What changed since the snapshot?"
├── output/                        # Formatters (BaseFormatter)
│   ├── base.py                    # BaseFormatter abstract class
│   ├── terminal.py                # Rich-formatted console output
│   ├── sarif.py                   # SARIF for GitHub Security integration
│   ├── nucleus.py                 # Nucleus FlexConnect formatter
│   ├── dashboard.py               # Self-contained HTML dashboard (one template string)
│   ├── check.py                   # `check` verdict
│   ├── advisory.py                # OSV records for `scan --format advisory`
│   ├── cyclonedx.py               # CycloneDX SBOM formatter
│   ├── snapshot.py                # Snapshot formatters: CycloneDX AI/ML-BOM and native JSON
│   ├── pdf.py                     # PDF compliance report
│   ├── reach.py                   # Terminal output for `reach`
│   └── reach_pdf.py               # `reach --report pdf`
├── extensions/
│   ├── models.py                  # Extension models
│   ├── discovery.py               # discover_extensions(), parse_manifest()
│   ├── policy.py                  # EXTPOL-001..003: editor extension allowlists
│   └── analyzer.py                # analyze_extensions()
├── registration/
│   ├── models.py                  # Registration payload models
│   ├── manager.py                 # Load, save, clear (0o600)
│   └── client.py                  # post_registration() / post_ping()
├── sast/
│   ├── runner.py                  # Run semgrep and map its output
│   └── bundler.py                 # Bundled rule path in frozen builds
├── fleet/
│   └── merger.py                  # Fleet merge and HTML
└── data/
    ├── known_npm_packages.yaml    # Legacy npm package list
    ├── exploit-signals.json       # KEV / EPSS / public-PoC snapshot
    ├── research-records.json      # Credited research records with no CVE
    ├── header_dark.png            # Header image for the PDF report
    └── d3.v7.min.js               # Bundled D3 v7
```

Standalone rule pack at repo root:
- `semgrep-rules/` — 91 Semgrep rules (47 Python, 44 TypeScript) across 6 categories;
 runnable with `semgrep --config semgrep-rules/ <path>` without Credenzo installed;
 bundled in the pip wheel and PyInstaller binary; see `docs/sast-rules.md`

Data files at project root:
- `registry/known-servers.json` — curated dataset of 56 known-legitimate MCP servers; queried by the supply chain analyzer for typosquatting detection and by the toxic flow analyzer for authoritative capability tags (`RegistryEntry.capabilities`); ships in both the pip wheel and PyInstaller binary
- `registry/known-malicious.json` — mirror of OSV `MAL-*` records for npm/PyPI packages whose name contains `mcp` or that the registry lists (STORY-0097); written only by `scripts/sync_registry_advisories.py --write` (bulk export; a mirror, so withdrawn records are removed); matched offline by exact name for SC-008 and `vet`; ships in the wheel and all four specs; `update-registry` does not refresh it. Kept out of `known-servers.json` so the registry schema is unchanged
- `rules/community/` — 42 bundled community rules total: 41 real detection rules (`COMM-001` through `COMM-039`; `COMM-032` is intentionally reserved/unissued — see `PROVENANCE.md`) plus `STDIO-001`/`STDIO-002a`/`STDIO-002b` (launch-command trust boundary, STORY-0067; `STDIO-001` ships `enabled: false` — see `GAPS.md`) plus `TEMPLATE.yml` itself, which loads as the always-inert `COMM-000` (contribution template — `tests/test_rules.py` guarantees it never fires on a real config); `BOUNTY.md` (bounty program terms) ships alongside but is not a rule file. All ship in both pip wheel and PyInstaller binary and are available to every user with no gating — but "available to" is not "runs for": 40 of the 41 real rules run by default, and `STDIO-001` does not run for anyone (`enabled: false`, no governance-policy toggle exists to turn it on — see `GAPS.md`); see `docs/writing-rules.md` and `docs/contributing-rules.md`

GitHub Action at project root:
- `action.yml` — composite GitHub Action definition; allows any repo to wire Credenzo into CI with a single workflow addition; inputs: `config-paths`, `severity-threshold`, `sarif-output`, `upload-sarif`, `check-vulns`, `verify-signatures`, `run-sast`, `sast-path`, `baseline-name`, `fail-on-findings`, `version`; outputs: `findings-count`, `grade`, `sarif-path`. Uses `github/codeql-action/upload-sarif` (v4, pinned to a commit SHA like every third-party `uses:` ref in `action.yml`, `setup-action/` and `.github/` — `tests/test_action_yaml.py::test_every_third_party_action_ref_is_sha_pinned`) with `continue-on-error: true` so repos without Code Scanning enabled still run cleanly. Marketplace-ready — passes `tests/test_action_yaml.py` structural and safety checks.

Credenzo Team action (`team/`, the one paid offer; docs/team.md):
- `team/action.yml` + `team/credenzo_team.py` — composite action, one step, standard library only. Runs `credenzo lock --verify --if-present --format json` (the command must already be on PATH; stopped after `VERIFY_TIMEOUT_SECONDS`) and returns its exit code: everything after the check runs in `_alerts()` under one `except Exception`, so a fault in an alert never changes the result. On a push, a schedule or a manual run (`ALERT_EVENTS`) on the default branch it keeps one issue for each check ("MCP lock drift"; `Scope` = workflow, job, path, connect, resolve; the marker in the body holds the scope key and a fingerprint of the findings, so the same drift is reported once and a passing check does not close the issue of another check) and POSTs `{"text": ...}` to `alert-webhook`. `GitHub.open_drift_issue` reads an issue as its own only when its author is the token's account (`GET /user`, else `github-actions[bot]`), or a bot account and the issue has the label: a stranger cannot plant an issue with the marker. No redirect is followed (`_NoRedirect`). An alert holds finding IDs, severities, cleaned server/tool names (`clean_name`) and "not verified" names, never a finding's own text or a reason. `decide()` is the whole pricing rule: personal account or public repository = alerts; else the licence list (`read_offer`): not readable or not live = alerts, owner digest in the list = alerts, otherwise the check runs and one notice is printed in a run where an alert was held back. `MEANINGS` must hold every LOCK ID the lock package reports (a test reads the source).
- `team/offer.json` — price, seats, `live_since`, checkout link, payment link ID. Written by `scripts/team_go_live.py`.
- `scripts/team_licenses.py` + `.github/workflows/team-licenses.yml` — Stripe (restricted read key, `team-licenses` environment) to `index.json` on the `team-licenses` branch: `offer` plus `owners`, SHA-256 digests padded with HMAC fillers to a multiple of 64. A failed Stripe request writes nothing. The `publish` job replaces the branch with one parentless commit.
- `scripts/paid_path_report.py` — weekly public numbers (`gh` + pypistats) and `decide()` for the experiment; the paid numbers are arguments, never read or stored.

Pre-commit hook at project root:
- `.pre-commit-hooks.yaml` — pre-commit hook definition; `language: python`, `entry: credenzo` (the old ids `mcp-audit` and `mcp-audit-lock-verify` stay, with `entry: mcp-audit`), `pass_filenames: false` (Credenzo uses its own discovery), `types: [json]` (fires only on staged JSON files), `always_run: false`; default args run `scan --severity-threshold high`; see `docs/pre-commit.md`

CI workflow and example workflows:
- `.github/workflows/mcp-audit-example.yml` — runs Credenzo on this repo on push/PR; also the reference workflow users copy
- `examples/github-actions/basic.yml` — minimal setup (visibility only, never fails build)
- `examples/github-actions/strict.yml` — fail on MEDIUM or higher
- `examples/github-actions/with-baseline.yml` — drift detection against a committed baseline
- `examples/github-actions/team-drift-alerts.yml` — Credenzo Team: lock check on pull requests, pushes and a daily run, with the drift alert
- `examples/pre-commit/basic.yaml` — minimal pre-commit config (blocks on HIGH+)
- `examples/pre-commit/strict.yaml` — strict pre-commit config (blocks on MEDIUM+)

Build and distribution scripts at project root:
- `scripts/install.sh` — curl-based end-user installer for GitHub Releases

Measurement scripts (dev tooling, not in the package):
- `scripts/bench_poisoning.py` — POISON-* recall and clean-tool flag rate on MCPTox (fetched by hand at release time, never in CI, never committed; any severity and HIGH-or-above) and precision on the top-100 npm corpus (re-measured 2026-10-29 on 0.23.0, Q-045: 1 of 46 real; labels in `docs/research/poisoning-benchmark/top100-labels.json` with `labelled_patterns_fingerprint`, `precision` prints STALE once the code differs; the 2026-10-22 0.21.x labels kept as `top100-labels-2026-10-22.json`) plus a replay of the corpus's committed evidence fragments; pinned in `docs/research/poisoning-benchmark/results.json`. `tests/test_bench_poisoning.py` fingerprints the whole source of `analyzers/poisoning.py` and `mcp_client.build_runtime_server_config`: any change to either forces a re-measure (`precision --write`, `recall --write`, then update the numbers in `docs/poisoning.md`, `GAPS.md` and `README.md`); see `docs/poisoning.md` (STORY-0088). The `delegation` subcommand (STORY-0100) measures DELEG-001..003 on MCPTox in two session models (poisoned tool on its own server; among the target server's tools), counts flagged clean tools with all 45 servers in one session and each alone, and applies the gate (`gate_decision`); `tests/test_delegation.py` fails if `analyzers/delegation.py` changes without `delegation --write`, or if `SHIPPED_SEVERITY` differs from the recorded decision
- `scripts/bench_competitors.py` — head-to-head benchmark harness (STORY-0146, dev-only, never in CI): `corpus` writes/validates the committed corpus (`docs/research/head-to-head/corpus/`, SHA-256 pinned in `manifest.json`), `run --mcptox PATH [--tools ...] [--write]` runs the installed scanners (SkillSpector static, Cisco mcp-scanner YARA only, Credenzo; Snyk agent-scan is always "not run: needs remote analysis") and pins `docs/research/head-to-head/results.json`, `report` prints the table. It never installs a scanner; a missing one is "not run", never zero. MCPTox is generated into a temp dir outside the repo and only its hashes are committed. Competitor output parsers follow public docs and were run against real output on 2026-11-19 (SkillSpector v2.12.0, Cisco mcp-scanner 4.8.7; 1,686 inputs each, no parse error); results in `results.json`. `tests/test_bench_competitors.py`; see `docs/research/head-to-head/README.md`

## Key conventions

- Every module has a corresponding test file in tests/ (e.g., test_discovery.py)
- Detection patterns are hardcoded in each analyzer (regex constants); supply-chain data is now sourced from `registry/known-servers.json` via `registry/loader.py`
- All findings use the `Finding` Pydantic model from models.py
- Analyzers inherit from `BaseAnalyzer` and implement an `analyze()` method. **Exception:** `rug_pull.py` and `toxic_flow.py` have a no-op `analyze()` — real work is in `analyze_all()` (they need the full server list). `attack_paths.py` is not a `BaseAnalyzer` subclass — it is a standalone module exposing `summarize_attack_paths()`. `collision.py` is also not a `BaseAnalyzer` subclass — it exposes `detect_tool_collisions(pairs)` and is called in `run_scan_async()` after the `--connect` loop, before `_run_static_pipeline()`.
- **`_run_static_pipeline()` in `scanner.py` is the canonical implementation of the analysis pipeline.** Both `run_scan` (sync) and `run_scan_async` (async, after live `--connect` enumeration completes) delegate to it. The helper is intentionally synchronous and runs steps 1–7 in this exact order (after step 0, `analyze_config` per config file, and step 0b, SANDBOX-001..005 `sandbox.analyze_sandbox_files`, which reads ignore files and the user's settings, checks each settings file in its own `try`, and reports read failures and crashes in `result.errors`; only when a `ConfigHygieneAnalyzer` is in the list): (1) per-server analyzers, (2) `RugPullAnalyzer.analyze_all`, (3) `ToxicFlowAnalyzer.analyze_all` with the shared registry, (4) `summarize_attack_paths`, (5) policy-as-code rule engine, (5b) PERM-007 (`permissions.analyze_flagged_server_allows`: `mcp__<server>` allow rules on servers with HIGH+ findings, which needs every finding above; only when a `ConfigHygieneAnalyzer` is in the list), (5c) instruction-file drift INSTR-001/002 (`agent_files/drift.py`, scans with no explicit path, needs every finding above), (5c2) guardrail drift GUARD-001/002 (`guardrails.guardrail_drift_findings`, STORY-0143: Claude Code/Codex/Gemini CLI settings files, scans with no explicit path, same skip rules as 5c), (5d) exploit signals (`apply_exploit_signals`: KEV, EPSS and public-PoC data on CVE findings, STORY-0124), (6) `calculate_score`, (7) attach `registry_stats`. Wire new analyzers or pipeline changes here, not in either entry point. **Exception:** `detect_tool_collisions()` from `collision.py` runs in `run_scan_async()` inside the `if connect:` block, immediately after the per-server enumeration loop and before `_run_static_pipeline()`. It is not part of `_run_static_pipeline()` because it requires live `ServerEnumeration` data that is not available in the static pipeline. `detect_tool_name_squats()` (COLLIDE-002, STORY-0173) and `detect_description_copies()` (COLLIDE-003, STORY-0174) run right after it on the same pairs. `detect_delegation()` from `delegation.py` (DELEG-001..003, STORY-0100) runs after that in the same block, over the same pairs, for the same reason. So does `detect_annotation_contradictions()` from `annotations.py` (ANNOT-001, STORY-0136), after delegation.
- Output formatters inherit from `BaseFormatter` and implement a `format()` method
- The dashboard HTML template is a single large string (`_DASHBOARD_HTML`) embedded in `output/dashboard.py`. All scan data is injected via a `__SCAN_DATA_JSON__` placeholder at render time. D3 v7 is bundled from `data/d3.v7.min.js` and injected via `__D3_JS__`. Do not split the template into separate files.
- **Scoring** runs after all analyzers complete inside `scanner.py` and attaches a `ScanScore` to `ScanResult`. Analyzers never call the scorer directly. See `scoring.py` and `docs/scoring.md`.
- **Registry resolution order** for the supply chain analyzer: explicit `--registry PATH` CLI flag → user-local cache at `<user-config-dir>/mcp-audit/registry/known-servers.json` (written by `update-registry`; path resolved via `platformdirs`) → PyInstaller `sys._MEIPASS/registry/` → `importlib.resources` (pip-installed wheel at `mcp_audit/registry/known-servers.json`) → dev repo-root fallback (`registry/known-servers.json`). Pass `--offline-registry` to skip the user-local cache step. All bundled resource resolution (registry, rules, semgrep-rules, extension vulns) goes through the shared `resolve_bundled_resource()` helper in `_paths.py`.
- **Terminal output** includes a dim one-liner registry stats line after the summary (e.g. "Registry: 60 known servers (v1.0, updated 2026-04-20)") pulled from `ScanResult.registry_stats`; omitted silently if `registry_stats` is `None`.
- **SARIF output** adds a `run.properties` block with `mcp-audit/grade`, `mcp-audit/numericScore`, `mcp-audit/positiveSignals`, and `mcp-audit/deductions` when `ScanResult.score` is not `None`; the block is absent when `--no-score` suppresses scoring.
- `SupplyChainAnalyzer` accepts `registry=KnownServerRegistry` or `registry_path=Path` in `__init__` to allow test injection without touching the filesystem.
- `TransportAnalyzer` accepts an optional `registry=KnownServerRegistry` in `__init__` to tier `TRANSPORT-003` severity by registry membership: verified entries suppress the finding, known-but-unverified entries fire at LOW, unknown packages fire at MEDIUM. `get_default_analyzers()` and `cli/scan.py::_build_custom_analyzers` share the same `SupplyChainAnalyzer.registry` instance so the JSON is read from disk exactly once per scan. Constructing `TransportAnalyzer()` without a registry preserves the historic "always MEDIUM" behaviour for tests that don't need the registry path.
- **Every Finding carries an OWASP MCP Top 10 mapping** in `Finding.owasp_mcp_top_10` (list of `MCP01`–`MCP10` codes; empty list = unmapped). The single source of truth for codes/names is `src/mcp_audit/owasp_mcp.py`. SARIF output exposes the mapping via a `runs[0].taxonomies` block and per-rule `relationships`. The full per-finding-ID mapping is documented in `docs/severity-framework.md`. Terminal output shows codes inline; `credenzo scan --owasp-report` prints a category-level aggregation.
- **Community rules always run.** The policy-as-code rule engine loads `rules/community/` for every scan. Authoring tools (`rule validate`, `rule test`) and custom rule directories (`--rules-dir`, `<user-config-dir>/mcp-audit/rules/`; path resolved via `platformdirs`) are available to everyone — gating has been removed. The engine is invoked via `_run_rules_engine()` in `scanner.py` after all built-in analyzers complete. Rule findings use `analyzer="rules"` and `id=rule.id`.
- **Rule engine resolution order** for community rules: PyInstaller `sys._MEIPASS/rules/community/` → `importlib.resources` (installed wheel at `mcp_audit/rules/community/`) → dev repo-root fallback (`rules/community/`).
- **Supply chain attestation** (`attestation/`) implements Layer 1 hash-based integrity verification. `scan --verify-hashes` downloads package tarballs, computes SHA-256, and compares against pins in `RegistryEntry.known_hashes`. `credenzo verify` is a standalone command for interactive package verification. Attestation findings use `analyzer="attestation"`; CRITICAL for mismatches, INFO for unverifiable cases. See `docs/supply-chain.md`.
- **`scan()` pipeline conventions** (`cli/scan.py`): the `scan` command is a thin orchestrator that delegates each optional phase to a named helper. Helpers are `_apply_*` for pipeline stages that mutate/inject into `ScanResult` (baseline drift, governance, SAST, extensions, agent-files, advisory feed, severity threshold) and `_write_*` for output-layer dispatch (`_write_formatted_output`). Preflight validation lives in `_preflight_checks`. Each helper has a docstring that states when it is called and its contract when the feature is not requested. Future scan-pipeline additions should follow this `_apply_*` / `_write_*` naming and be inserted into `scan()` as a single-line delegation — do not inline new phases in the command body. Test-patched symbols (`verify_server_hashes`, `discover_extensions`, `analyze_extensions`, `run_semgrep`) are imported as their containing module (e.g. `from mcp_audit.sast import runner as _sast_runner`) so `patch("mcp_audit.sast.runner.run_semgrep", ...)` continues to intercept.
- **Capability tags for toxic flow detection** are stored in `RegistryEntry.capabilities` (optional `list[str]` in `registry/known-servers.json`) and consulted by `analyzers/toxic_flow.py::tag_server(server, registry=...)` **before** any keyword or tool-name heuristic fallback. When `registry` is supplied and resolves a known package whose `capabilities` field is not `None`, those tags are returned verbatim — the registry is the single source of truth. The in-module `KNOWN_SERVERS` dict in `toxic_flow.py` is retained as a deterministic fallback for (a) unit tests that inject no registry and (b) cases where the registry is present but the entry has `capabilities=None`. `scanner.py` passes the `SupplyChainAnalyzer.registry` instance to `ToxicFlowAnalyzer(registry=…)` so the JSON file is read from disk exactly once per scan.
  Rules that follow from this (history and measurements: `docs/archive/claude-md-2026-11-16.md`):
  - The registry overrides the heuristics, so an incomplete `capabilities` list on an entry is worse than no list. Declare every capability.
  - `scripts/audit_registry.py` runs four offline checks before its network loop: undeclared capabilities, capability strings that are not `Capability` members, dead capabilities (against `toxic_flow.KNOWN_TAG_ONLY_CAPABILITIES`, where every entry needs a reason), and entries whose whole capability set is tag-only. `tests/test_audit_registry.py` pins all four clean against the shipped registry. Run it with `uv run python3`: the script refuses to measure an `mcp_audit` that is not this repo's.
  - `Capability.CLOUD` is tag-only on purpose. `FILE_WRITE + SHELL_EXEC` is `INTEG-001` in `INTEGRITY_PAIRS`, a separate list from `TOXIC_PAIRS`; consumers use `TOXIC_AND_INTEGRITY_PAIRS`. `FILE_WRITE + NETWORK_OUT` was measured twice and declined (GAPS.md, "FILE_WRITE integrity axis").
  - `Capability.COMMS_OUT` is a wired sink (`TOXIC-008..011`); its keyword rule matches platform names as whole tokens and skips path arguments. Measurements: `docs/severity-framework.md`.
  - The registry-submission issue template has exactly one checkbox per `Capability` member (`tests/test_registry_submission_template.py`).

- **Agent-file scanning** (`agent_files/`) covers the non-MCP-config instruction
  surfaces an agent reads: Claude Code commands/memory, Cursor `.mdc` rules, and
  Copilot instruction/prompt files. It is **not** part of `_run_static_pipeline()`;
  the standalone `agent-files discover|scan` commands call it directly, and `scan
  --include-agent-files` wires it via `_apply_agent_files()` in `cli/scan.py`
  (same `_apply_*` additive convention as `--include-extensions`). Findings use
  `analyzer="agent_files"` (SKILL-001/002/003/004, MEM-001/002) — **except**
  POISON-041/042 (concealment channels, STORY-0068), which this module also
  emits but which always carry `analyzer="poisoning"`, matching the config
  surface, because the shared builder `build_concealment_finding()` lives in
  and is owned by `analyzers/poisoning.py` (see that module's docstring and
  `agent_files/analyzer.py`'s own "documented exception" note). Detection
  patterns are **imported** from `analyzers/poisoning.py` — never forked.
  **MEM-003/MEM-004** (STORY-0098: imports from outside the folder or of a
  `.gitignore`'d file; heartbeat output suppression) also run in a default
  `scan`/`check` (cwd-root instruction files, skipped when cwd is `$HOME`, plus
  `~/.openclaw/workspace/HEARTBEAT.md`) and in `scan --project`, through
  `agent_files/reach.py`; findings are deduplicated across the three paths
  (`reach.finding_key`) and only a symlink leaving the folder (TRUST-002 HIGH)
  is reported on the first two. `tests/conftest.py` stubs the user heartbeat
  lookup.
  **HOOK-001/002** (network-egress and config-write hook commands) deliberately
  live in `analyzers/config_hygiene.py::analyze_config` (pipeline step 0), not in
  `agent_files/`, because they inspect the parsed `hooks` section of a Claude config
  file; they are distinct IDs from CFHYG-005 (which fires on mere presence of a
  `hooks` section) and the conditions do not overlap.
  **Subagent definitions** (`.claude/agents/**/*.md`, STORY-0094) are the exception
  to "not part of the pipeline": their frontmatter is a config surface, so the files
  are `DiscoveredConfig`s (client `claude-code-agent`), `parse_config()` reads their
  inline `mcpServers`, and AGENT-001..004 + HOOK-001/002 run at step 0 in the default
  `scan`/`check` and `scan --project` (`discover_project_agent_configs`, kept out of
  `discover_project_configs` so `lock` never sees them). Only their body text follows
  the skills opt-in (`--include-agent-files`, which passes `include_definitions=False`).

## Critical implementation details

- **VS Code uses `"servers"` as its MCP config root key; all other clients use `"mcpServers"`**
- MCP protocol communication is async — use asyncio and pytest-asyncio
- Core scanning MUST work fully offline — no network calls by default
- OSV.dev lookups **are implemented** via `scan --check-vulns` (deps.dev transitive graph + OSV.dev CVE batch query; shipped v0.6.0). The `--offline` flag enforces mutual exclusion with network-touching opt-in flags (`--verify-hashes`, `--verify-signatures`, `--check-vulns`, `--connect`); a plain scan already makes no network calls, so `--offline` is a no-op for the default configuration
- **Credenzo does not implement semver range resolution anywhere** — no semver library appears in `src/mcp_audit/vulnerability/` or `src/mcp_audit/attestation/`. For an unpinned npm server, `resolve_latest_version()` asks `registry.npmjs.org/<pkg>/latest` (the `latest` dist-tag, npm-pick-manifest's own first-preference rule) rather than computing a highest-satisfying version, so the class of resolver bug an external measurement (issue [#88](https://github.com/adudley78/credenzo/issues/88)) found in a from-scratch range resolver — preferring a higher non-`latest`-tagged version over the dist-tag — cannot reach us; we declined to implement the thing that has the bug. For PyPI, `info.version` from the PyPI JSON API is documented to report the latest **stable** release (pre-releases excluded), matching pip's/`uvx`'s/`pipx`'s own default install behaviour, so it errs the same direction a real install would. `resolver.is_version_range()` (R36) is a syntactic, non-semver detector for a config entry that carries a floating specifier (`^1.2.3`, `~1.2.3`, `>=1.0.0`, `1.2.x`, `*`, `1.0.0 - 2.0.0`, `latest`) rather than an exact pin; `check_vulnerabilities()` and `credenzo sbom` both check it before calling `fetch_transitive_deps()`, because deps.dev requires an exact `(name, version)` key and 404s on a range — without the check, that 404 was caught by `fetch_transitive_deps()`'s own `except URLError/HTTPError` and silently degraded to a top-level-only result carrying the literal range string as its "version," with no warning. Both call sites now resolve a concrete version first (same as the existing "unpinned" path) and surface a visible `VULN-UNPINNED` finding / Rich console warning naming the original range and the resolved version. See "Known limitation: the published graph vs. the installed tree" in `docs/supply-chain.md` for the measured, externally-contributed error-rate bound on the deps.dev-vs-real-install gap this same issue established.
- Rug-pull state is stored in `<user-config-dir>/mcp-audit/state/state.json` (resolved via `platformdirs`; macOS: `~/Library/Application Support/mcp-audit/state/`); a one-time migration copies state files from the legacy `~/.mcp-audit/` location on first access
- **No feature gating in the package.** Credenzo is fully open source (Apache 2.0); every feature ships in every binary. Do not re-introduce conditional feature availability at any layer of `src/mcp_audit`. The one paid offer is the Credenzo Team action in `team/` (see "Business model"): it gates its own alerts, never a command.
- **Watcher callback serialisation.** `_McpConfigEventHandler._fire()` holds `_scan_lock` for the entire duration of the user callback to prevent two `run_scan` calls from racing on `state_<hash>.json`. Events arriving while a scan is in flight are stored in `_pending_rescan` (tuple of latest `(path, event_type)`) and coalesced into a single re-trigger when the active callback returns. Never release the scan lock before the callback finishes.
- Exit codes: 0 = clean, 1 = findings found, 2 = error
- JSON output includes a nested `score` object from `ScanScore`: `{"numeric": int, "grade": str, "positive_signals": [], "deductions": []}` — `numeric` is 0–100, `grade` is "A"–"F", `positive_signals` and `deductions` carry the per-signal strings displayed in the terminal score panel; HTML dashboard displays a colour-coded grade badge in the header
- `scan --no-score` suppresses the grade panel in terminal output only; score is still calculated and present in JSON/HTML
- `scan --registry PATH` overrides the bundled and cached registry for that run
- `scan --offline-registry` uses the bundled registry only, skipping the user-local cache at `<user-config-dir>/mcp-audit/registry/known-servers.json`; typosquatting detection still runs using bundled data
- `scan --baseline NAME` (or `--baseline latest`) loads a saved baseline and appends `DriftFinding`s converted to `Finding` objects (`analyzer="baseline"`) into all output formats after the normal scan
- `scan --output-file PATH` (alias for `--output` / `-o`) writes scan results to a file; parent directories are created automatically; required for the GitHub Action SARIF upload step
- `scan --severity-threshold LEVEL` filters findings to only those at or above the given level and drives exit code; default is `INFO` (all findings); `--severity-threshold high` exits 1 only if HIGH or CRITICAL findings exist
- `scan --rules-dir PATH` loads additional YAML rule files from PATH for this scan; available to all users; community rules always run regardless
- `scan --project <dir>` walks the directory tree of a repository for project-level MCP config files (`.mcp.json`, `.cursor/mcp.json`, `.claude/settings.json`, `.claude/settings.local.json`, `.cursor/settings.json`, `.vscode/mcp.json`, `.amazonq/mcp.json`, `.codex/config.toml`, `.gemini/settings.json`, plus the gateway files `.mcptoon.json`, `.mcptoon.toml` and `.mcphub/servers.json`) and emits `TRUST-001` (HIGH) for every server found; runs the full analyzer pipeline on project-scoped servers too; tree walk caps at depth 8, skips `node_modules`/`.git`; `--project` path is validated to exist (exit 2 on failure); use before opening a freshly cloned repo in an AI editor; additive — default scan is unchanged. CWE-829 / OWASP MCP09. **Symlink handling (TRUST-002/TRUST-004/TRUST-005, added 2026-09-08):** a symlinked directory is still never followed (unchanged loop/blow-up protection) but now emits `TRUST-005` (LOW) naming it instead of vanishing silently; a symlinked config/agent-file *candidate* is included and parsed normally (coverage was never actually at stake — `Path.read_text()` follows a symlink transparently) and reported as `TRUST-002` (HIGH outside the scanned root, MEDIUM inside, INFO if broken) for project/cwd-scoped candidates or `TRUST-004` (always INFO — the GNU Stow/chezmoi/yadm dotfile-manager shape) for user-global/explicit ones. Applies uniformly across `discovery.py` (six sites) and `agent_files/discovery.py` (three sites). A config candidate reached through a symlinked parent directory (`.claude -> /elsewhere`) is treated like a symlinked file (`is_symlink=True`, TRUST-002) in both the `--project` walk and the default scan's cwd check (STORY-0108, `discovery._reached_through_symlink`, the rule STORY-0090 applies to auto-run files); agent-file discovery never descends a symlinked parent (TRUST-005). See `humans/decisions/2026-09-08-trust-002-symlink-sites.md` (marcus repo).
- **CI workflows (STORY-0091).** A scan with no explicit path reads `<cwd>/.github/workflows/` through `ci_workflows.scan_workflows()` in `scanner._discover_and_parse` (findings are scored, like plugin findings; `check` no longer short-circuits to "No MCP config files found" when findings exist); `--project` reads the project and nested repo roots in `_apply_project_scan`, de-duplicated against the cwd copy. `analyzer="ci_workflow"`, `client="github-actions"`, `server`=job id, `tool`=step. No `action.yml` change was needed: the Action's default run is a cwd scan.
- `update-registry` fetches `registry/known-servers.json` from GitHub and saves it to the user-local cache; available to all users
- **Baseline storage** uses 0o700 dir / 0o600 file permissions, same pattern as rug-pull state files; env values are never stored, only key names (security — prevents secrets being persisted to disk)
- `scan --policy PATH` loads a governance policy file; governance findings are appended to `result.findings` after the scan completes (and after baseline drift) so they flow through all output formatters automatically. `--policy`, `policy init`, and `policy check` are all available to every user.
- **Governance policy resolution order** when `--policy` is not given: explicit flag → cwd → git repo root → `<user-config-dir>/mcp-audit/policy.yml` (resolved via `platformdirs`). Returns `None` (no check) if no file found.
- `scan --verify-hashes` downloads package tarballs and verifies SHA-256 against `known_hashes` pins in the registry; requires network; free for all tiers; findings appended to `result.findings` after the scan.

## Advisory feed invariants

The advisory feed is a published, externally-consumed artifact. Breaking any of the
following silently breaks downstream consumers, so treat them as contract:

- **Determinism is the whole product.** The same finding must produce byte-identical
  advisory JSON on every host, forever. Advisory IDs are derived from ecosystem +
  package + rule ID + finding class (+ normalized location when set) — never from a
  filesystem path, hostname, or timestamp. Timestamps come from `--published-at`,
  then `SOURCE_DATE_EPOCH`, and only then wall-clock; never call `datetime.now()`
  inside `build_advisory`.
- **`canonical.py` implements RFC 8785, not "JSON with sorted keys".** Object keys
  sort by UTF-16 code unit (not code point) and numbers use ECMAScript
  `Number::toString`. These differ from `json.dumps(sort_keys=True)` for non-BMP keys
  and for floats. Signatures are over canonical bytes, so any change here invalidates
  every published signature.
- **`src/mcp_audit/owasp_mcp.py` is the only definition of the OWASP MCP Top 10.**
  The advisory package must never hold its own copy of the code list. It publishes the
  bare `MCP01`..`MCP10` form that SARIF output and `docs/owasp-mapping.json` already
  use, so records join to the rest of Credenzo's output without translation, and
  `scripts/validate_owasp_mapping.py` stays the single CI gate. `owasp_codes_for()`
  validates against `owasp_mcp.py` and drops anything unrecognised; `Advisory` raises
  on an unknown code. A finding with no clean mapping gets `owasp_mcp: []` and an
  `owasp_mcp_todo` string — it does not get a guessed code. Two tests enforce this: an
  AST scan for year-suffixed codes in the advisory package's *code* (docstrings are
  exempt — `owasp_codes_for` documents that it accepts that form on input), and a check
  that `mcp_audit.advisory.owasp` stays deleted.
- **The index is the integrity root.** `index.json` records a `canonical_sha256` per
  advisory plus the `signing` block, and is itself signed. `verify_feed` re-canonicalizes
  each advisory, checks its digest against the signed index, verifies its signature, and
  fails on any advisory file present on disk but absent from the index. Do not add a
  verification path that trusts a per-advisory signature alone — that would let an
  attacker swap in a differently-but-validly signed record.
- **Feed freshness lives only on the index.** `snapshot_version`, `published_at`, and
  `expires` are Credenzo fields on `index.json` (`feed_version` 1.1). They are never
  copied onto OSV advisory records. `feed verify` hard-fails on expiry or rollback;
  `scan --advisory-feed` skips matching, emits `feed_status`, and still completes.
  There is no `--allow-expired`. Client `seen.json` is keyed on the signing identity
  (workflow ref + OIDC issuer), not a certificate fingerprint; changing that identity
  resets rollback protection. `.github/workflows/advisory-feed-publish.yml` is the
  only publisher; the minisign project key's private half is the
  `MCP_AUDIT_FEED_SIGNING_KEY` secret (environment `feed-signing`, `main` only) and
  the public half is `keys/mcp-audit-feed.pub`. `publish` must copy
  `index.json.sig` with `index.json`
  (`test_publish_copies_index_json_sig_alongside_index_json`; the first signed
  publish, 2026-09-07, shipped without it). A stateless client accepts any unexpired validly-signed snapshot; TTL is the only
  lever. Stolen key, a publisher omitting advisories at a new version, a client clock
  in the past, and mix-and-match (already bound by `canonical_sha256`) are not covered.
- **Publishing is two-phase.** `write_feed()` emits the unsigned index; `sign_feed()`
  rewrites it with the `signing` block and then signs it. Determinism assertions must
  compare pre-signing output.
- **A feed is signed with a static project key, not Sigstore keyless.** This is the
  documented divergence from `snapshot --sign`, and it is threat-model driven: a
  snapshot is a one-off forensic artifact verified online where the human identity is
  the evidence; a feed is consumed offline, reproducibly, against a stable *project*
  identity. `advise --sign` therefore requires `--key` / `$MCP_AUDIT_SIGNING_KEY` and
  fails fast via `SigningConfig.require_signing_key()` before writing any signature.
  `--keyless` stays reachable for one-off attestations but must never become the
  default. Do not re-point this at `sigstore-python`: it is keyless-only, cannot use a
  static key, and is excluded from the PyInstaller binary.
- **cosign and minisign are optional external tools.** A missing backend degrades
  exactly like a missing semgrep in `sast/runner.py` — an actionable message naming
  the install step and `--no-sign`, never a traceback. Never vendor the crypto into
  the binary to avoid this.
- **Signatures stay detached and over canonical bytes, so rotation never rewrites a
  record.** Nothing signature-shaped is ever stored inside an advisory, and the signed
  payload is the JCS canonicalization rather than the on-disk file. Together these make
  a key rotation invisible to anyone consuming records instead of signatures — IDs,
  digests, and bytes are unchanged, and mirrors see no diff. Inlining a signature or
  certificate into a record would make every rotation churn the whole feed; signing raw
  file bytes would freeze the feed into one byte layout and break re-serialising
  mirrors. `TestRotationLeavesRecordsUntouched` in `tests/test_advisory_sign.py` pins
  this; no other test would catch either regression.
- **An unsigned feed is a supported artifact.** `examples/feed/` ships unsigned
  because signing it reproducibly would mean committing a private key — this stays
  true even now that the *live published* feed on the `feed` branch is signed with
  the real project key; the two are deliberately different artifacts. `verify_feed`
  reports `signed=False` and checks integrity only; tampering is still caught through
  `canonical_sha256`. A feed whose index carries a `signing` block still *fails* when
  a signature is missing, so this can never become a silent downgrade. The signing
  path is proven by ephemeral-keypair tests in `tests/test_advisory_sign.py`.
  **`canonical_sha256` is the only integrity guarantee consumers of the in-repo
  `examples/feed/` get** — no signature covers that fixture, so
  `test_a_mutated_record_still_fails_when_unsigned` is load-bearing rather than
  redundant with the signed-feed tests. Do not weaken it.
- **`x_MCPSA` prefix is deliberate.** OSV restricts `id` prefixes to a registered
  allowlist plus the `x_` experimental namespace, so records validate today. Drop the
  `x_` only once `MCPSA` is registered upstream.
- **Not every finding is an advisory.** `classify.py::is_advisable()` excludes
  informational/stateful IDs (RUGPULL-000/003, ATTEST-010/015, BL-001, COMM-000,
  CFHYG-004). New non-vulnerability finding IDs belong in `NON_ADVISORY_IDS`.
  `observation` distinguishes `package-intrinsic` (the package itself is affected)
  from `deployment` (this installation is misconfigured) — consumers rely on it to
  decide whether the record indicts the upstream package.
- **Advisory prose is published to the world.** `feed.py::redact()` scrubs
  `SECRET_PATTERNS` matches from summary/details before write. Any new field that
  carries analyzer text must go through it.
- **The OSV schema is vendored, not fetched.** `advisory/osv_schema/osv-1.6.0.json`
  is pinned so validation is offline and stable. Bumping it is a deliberate act:
  update `OSV_SCHEMA_VERSION`, re-run the round-trip tests, and re-sign the example
  feed. All four PyInstaller specs and the wheel must keep bundling it.

## Governance vs Rule Engine

The rule engine (`rules/`) pattern-matches inside server configs and produces `Finding` objects with `analyzer="rules"`. The governance engine (`governance/`) enforces *organisational requirements* — approved server lists, minimum scan scores, transport constraints, registry membership, finding tolerances — and produces `Finding` objects with `analyzer="governance"`. They are complementary: run together in every scan when a policy file is present.

Key differences:
- Rule engine: detects security issues in *how servers are configured* (e.g. credential leaks, poisoning patterns)
- Governance engine: enforces *which servers are allowed and what quality bar* the configuration must meet
- Community rules always run; custom rules, `rule validate`, and `rule test` are all available to everyone (no gating)
- Governance `--policy` flag, `policy init`, and `policy check` are all available to every user
- Governance findings appear in a distinct "Policy Violations" panel in terminal output (yellow border)

## Security hardening invariants

The following invariants were established during the pre-launch security hardening
pass (2026-04-17) and **must be maintained** in all future changes:

- **`subprocess.run()` always uses list form with `shell=False` (implicit default).**
  Never construct a shell command as a string and pass it to `subprocess.run()`.
  The `SEMGREP_TIMEOUT_SECONDS = 300` constant in `sast/runner.py` must be used
  for any subprocess timeout; hardcoded timeout integers are forbidden.
- **Baseline and registry cache files are always created at 0o700 dir / 0o600 file.**
 Use `os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)` for sensitive
 writes. Never use `Path.write_text()` for files under the user config directory
 (resolved via `platformdirs.user_config_dir("mcp-audit")`) unless a
 `chmod(0o600)` immediately follows.
- **No bare `except:` clauses.** Use `except Exception:` at minimum, or a more
  specific type. Verify with `grep -rn "except:" src/` — must return zero matches.
- **All user-supplied paths resolved with `Path.resolve()` before use.**
  For baseline paths, confirm the resolved path stays within the storage directory
  via `candidate.relative_to(self._storage_dir)`. For `--registry` and `--policy`
  paths, `resolve()` is sufficient (no boundary check needed).
- **All `--path`, `--registry`, `--sast`, and `--policy` CLI arguments are validated
  to exist before use**, producing a clean exit code 2 and human-readable message on
  failure, never a Python traceback.

## Quality gates

**Dev extras required:** Run `uv sync --extra dev` before running tests for the
first time, or after a fresh clone. A plain `uv sync` omits `pytest-asyncio`
and other dev tools — async tests will silently fail with unknown-mark warnings
if this step is skipped.

- Before each commit, run the `verify` skill (`.claude/skills/verify/SKILL.md`): lint, the tests for the changed code, then the demo scan against `tests/golden/demo_scan_findings.json` and the `run` demo. Its rules: stop after three failed fix rounds; never skip a flaky test or edit a golden file to make a change pass
- Run `uv run pytest` after every change
- Run `uv run ruff check src/ tests/` before committing
- Run `uv run bandit -r src/ -ll -f txt` periodically (we're a security tool — act like it)
- Run `./scripts/update_test_count.py` before tagging a release (or after any PR that changes test count, SAST rule count, community rule count, or analyzer count) to sync all hand-maintained count references in `README.md` and `CLAUDE.md`. The script now covers: test count, SAST rule count (total + Python/TypeScript breakdown), community rule count, concrete analyzer count, and the release pin (`v<pyproject version>`): every `uses: adudley78/credenzo[/setup-action]@` tag or `@main` ref and pinned `version:` input in README.md and the Action docs (`_ACTION_REF_DOCS`, `_VERSION_INPUT_DOCS`), every pre-commit `rev:` for this repo (`_PRE_COMMIT_PIN_FILES`), and `credenzo==` in `docs/enterprise-deployment.md`; prose citing an old release is never rewritten, and `tests/test_update_test_count.py` fails if any example takes a shape the script would miss (STORY-0102), so a release PR fails `--check` until it updates them. CI runs the same script with `--check` on the ubuntu/py3.12 leg and fails on drift.
- Run `python scripts/validate_owasp_mapping.py` after adding any new finding ID to verify it is mapped in `docs/owasp-mapping.json`. CI runs this on the ubuntu/py3.12 leg and fails when any finding ID is missing from the mapping file. **Every PR that adds a new finding ID must also add a mapping entry.**
- Type hints on ALL function signatures
- Docstrings on all public functions and classes

**Bandit** must report no medium or higher issue. A suppression is
`# nosec <rule id>` with a one-line reason, never a bare `# nosec`
(`grep -rn --include=*.py "nosec" src/ | grep -v "nosec B[0-9]"` prints nothing). Bandit does not
flag a TLS context with `verify_mode = CERT_NONE`: review any change to `ssl` use
by hand (`push-nucleus` shipped with checks off until 2026-11-21).

### When to flag for Opus review

If a task involves designing a new module interface, changing how analyzers
interact with each other, restructuring data models, or you find yourself
uncertain between two fundamentally different approaches — stop and say:
"⚡ Architecture decision — consider switching to Opus for this."
Do not attempt to resolve architectural ambiguity by guessing. Flag it.

## Current state

What each feature does is in `README.md`, `docs/README.md` (the index of every document) and `CHANGELOG.md`. Known limits are in `GAPS.md`. The long feature history that used to be here is in `docs/archive/claude-md-2026-11-16.md`.

Counts that `scripts/update_test_count.py` keeps in sync:

- 8 analyzers: poisoning, credentials, transport, supply chain, rug-pull, toxic flow, config hygiene, auth
- 11243 tests passing; `ruff check src/ tests/` clean (zero errors); `ruff format src/ tests/` clean (zero files requiring reformatting) — verify with `uv run pytest --collect-only -q` before each release
- 35 top-level CLI commands: affected, vet, reach, check, fix, run, guard, wrap, unwrap, scan, discover, pin, diff, lock, dashboard, watch, version, update-registry, merge, verify, sast, sbom, push-nucleus, shadow, killchain, snapshot, register, advise, baseline (5 sub-commands: save, list, compare, delete, export), rule (3 sub-commands: validate, test, list), policy (3 sub-commands: validate, init, check), extensions (2 sub-commands: discover, scan), agent-files (2 sub-commands: discover, scan), plugins (2 sub-commands: discover, scan), feed (1 sub-command: verify) — verify with `credenzo --help` before each release
- 56-entry curated dataset of legitimate MCP servers (`registry/known-servers.json`, `docs/registry.md`)
- 42 community rules ship bundled; the breakdown is under "Data files at project root" above
- Demo: 75 findings on a first scan of `demo/configs/` (67 once rug-pull state exists; 76 and 68 up to 0.33.0, before STORY-0171 moved the bare "do not mention" out of POISON-012; POISON-070 still reports that text). Recount before each release: `credenzo scan --path demo/configs/ --format json`. `tests/test_demo_scan_golden.py` pins the first-scan findings without CFHYG-001/002 (67) in `tests/golden/demo_scan_findings.json`

## Provenance

All detection patterns are original implementations based on published security
research. No code was copied from existing scanners. Full source attribution is
documented in PROVENANCE.md — read it before adding new detection patterns.
Every new pattern must cite its research source.
The project now has 8 analyzers with patterns sourced from the research listed in PROVENANCE.md. Update PROVENANCE.md when adding new detection patterns or analyzers.
See GAPS.md for known detection quality limitations, severity calibration issues, and untested areas. Consult before claiming detection completeness or accuracy.

## Commit history audit (2026-04-17)

A full audit of the git history before the public release found no real credentials, internal URLs or key material. Every match was a synthetic test fixture (for example the `ghp_aBcDeF…` and `sk-abcdef…` strings in tests, Semgrep rule fixtures and `demo/configs/`). The full record is in `docs/archive/claude-md-2026-11-16.md`.

## Release engineering

### PyInstaller path resolution — test coverage (2026-04-17)

| Behaviour | Test coverage | Notes |
|---|---|---|
| `_resolve_bundled_path()` returns `_MEIPASS/registry/known-servers.json` when `sys.frozen=True` | `tests/test_registry.py::TestMeipassResolution` | Patches `sys.frozen` + `sys._MEIPASS` via `monkeypatch` |
| `KnownServerRegistry` loads from a simulated `_MEIPASS` layout | `tests/test_registry.py::TestMeipassResolution::test_frozen_registry_loads_via_patched_bundled_path` | Monkeypatches `BUNDLED_REGISTRY_PATH` |
| Corrupt PyInstaller bundle (missing registry file) raises `FileNotFoundError` | `tests/test_registry.py::TestMeipassResolution::test_locate_raises_when_bundled_path_missing` | Both user-cache and bundled path missing |
| Binary entry point and bundled data intact after build | Shared composite + `scripts/smoke_test.py` | `.github/actions/build-binary/` is invoked by CI `binary-smoke` and `release.yml` `build` |

### CI workflow (`.github/workflows/ci.yml`)

Triggers on every pull request and on pushes to `main` (until 2026-11-19 also on every branch push, which ran each pull-request commit twice and left macOS jobs waiting for a runner until their time limit). Runs a 3×2 matrix (6 combinations):
- **OS:** `ubuntu-latest`, `macos-latest`, `windows-latest`
- **Python:** `3.11`, `3.12`
- `fail-fast: false` — a failure on one leg does not cancel the others.

Each test-matrix leg runs: `pip install uv` → `uv pip install -e ".[dev]" --system` → `pytest tests/ -x -q` → `ruff check src/ tests/` → `ruff format --check src/ tests/`. The matrix uses `actions/setup-python` so uv installs into the runner's system Python via `--system`.

`wheel-check` (every push/PR) uses `setup-uv` + CPython 3.12.14, builds the wheel, fetches the publish action's `runtime.txt` at the pinned SHA, and runs that Twine (`uvx twine==… check --strict`) so a Core-Metadata bump fails on the PR, not at the tag. Hatchling stays unpinned; the Twine version is not copied into `ci.yml`.

The workflow status badge is in `README.md`.

### Release workflow (`.github/workflows/release.yml`)

Triggers on `v*.*.*` tags (e.g. `git tag v0.2.0 && git push --tags`), and on `workflow_dispatch`: a dry-run of the `build` job (no GitHub Release, no PyPI) unless dispatched on a `vX.Y.Z` tag with `publish: true`, which is how `release-on-version-bump.yml` starts a release. Builds four binaries in parallel, then creates a GitHub Release with all four attached and auto-generated release notes.

**Merging a version bump to `main` is the release (R73, 2026-10-15).** `.github/workflows/release-on-version-bump.yml` runs on pushes to `main` that touch `pyproject.toml`; `scripts/release_gate.py tag` tags the commit (through the refs API, which refuses an existing tag) only if that commit itself changed `[project].version` (compared with its parent), the version is untagged and above every release tag, and CHANGELOG has a non-empty `## [X.Y.Z]` section (checked with `compose_release_notes.extract_changelog_section`, the same parser the `release` job uses, so empty notes can't fail `release` after `publish-pypi` has used up the version). It then dispatches `release.yml` on the tag with `publish=true`, because a tag pushed with `GITHUB_TOKEN` starts no workflow. Every publishing job in `release.yml` (`release`, `publish-pypi`, `tag-major`) needs the `gate` job (`scripts/release_gate.py publish`): the ref must be a `vX.Y.Z` tag on `main` matching `pyproject.toml`, with a non-empty CHANGELOG section and no higher release tag, and a dispatch must say `publish: true` (a plain dispatch is decided as a dry run before anything is read); every refusal fails the run with its reason. `release.yml` has `concurrency: release-${{ github.ref }}` so a tag never runs twice at once. Recovery when the tag exists but the dispatch failed: `gh workflow run release.yml --ref vX.Y.Z -f publish=true` (re-running the bump workflow only reports "already tagged"). Do not switch the tag push to a personal token (it would start `release.yml` by itself and the dispatch would publish a second run). Pinned by `tests/test_release_gate.py` and `tests/test_ci_binary_smoke.py::test_release_dispatch_is_a_dry_run`.

**Shipped binaries are built by `.github/actions/build-binary/`.** CI `binary-smoke` and this workflow's `build` job both call it (CPython 3.12.14 via `uv python install`, `uv sync --all-extras`, spec, PyInstaller, PYZ inspect, smoke, size). Do not copy those steps into either workflow. History of the three CI/release drifts: `docs/building-binaries.md`.

| Runner | Spec file | Output binary |
|---|---|---|
| `macos-15-intel` | `mcp-audit-darwin-x86_64.spec` | `mcp-audit-darwin-x86_64` |
| `macos-latest` | `mcp-audit-darwin-arm64.spec` | `mcp-audit-darwin-arm64` |
| `ubuntu-latest` | `mcp-audit-linux-x86_64.spec` | `mcp-audit-linux-x86_64` |
| `windows-latest` | `mcp-audit-windows-x86_64.spec` | `mcp-audit-windows-x86_64.exe` |

> `macos-15-intel` builds the x86_64 macOS binary (`macos-13` was retired on 2025-12-08; `macos-latest` is arm64 and would silently produce the wrong architecture). GitHub supports the Intel label through 2027-08.

### PyInstaller spec files

Four spec files live at the repo root: `mcp-audit-darwin-x86_64.spec`, `mcp-audit-darwin-arm64.spec`, `mcp-audit-linux-x86_64.spec`, `mcp-audit-windows-x86_64.spec`. All use a portable SPECPATH-relative root instead of hardcoded absolute paths:

```python
import os
root = os.path.dirname(os.path.abspath(SPECPATH))
```

All four specs include identical `datas` (7 entries: `mcp_audit/data`, the three registry JSONs — `known-servers.json`, `known-extension-vulns.json`, `known-malicious.json` — `rules/community/`, `semgrep-rules/`, and the vendored OSV schema; `tests/test_pyinstaller_specs.py` pins the registry files) and the same full `hiddenimports` list. The only difference between specs is the `name=` field in the `EXE` block.
