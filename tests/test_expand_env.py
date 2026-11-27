"""``lock --connect --expand-env``: fill ``${VAR}`` as Claude Code does.

Claude Code expands ``${VAR}`` and ``${VAR:-default}`` in a server's
``command``, ``args`` and ``env`` (https://code.claude.com/docs/en/mcp-configuration,
"Environment variable expansion in .mcp.json"). Without ``--expand-env`` a
server gets the literal text, so a server that checks its key at start-up does
not start, and the scheduled Team check alerts every night (finding of
2026-11-27). The end-to-end tests start two small servers of this file's own;
no third-party server runs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from mcp_audit import mcp_client
from mcp_audit.cli import app
from mcp_audit.mcp_client import expand_env_refs
from mcp_audit.models import ServerConfig, TransportType

runner = CliRunner()


@pytest.fixture(autouse=True)
def _off() -> Any:
    mcp_client.set_expand_env(False)
    yield
    mcp_client.set_expand_env(False)


# ── The expansion rules ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "environ", "expected", "missing"),
    [
        ("${K}", {"K": "v"}, "v", []),
        ("Bearer ${K}", {"K": "v"}, "Bearer v", []),
        ("${K}", {"K": ""}, "", []),  # empty counts as set
        ("${K:-d}", {"K": ""}, "", []),  # so the default is not used
        ("${K:-d}", {}, "d", []),
        ("${K:-}", {}, "", []),
        ("${K:-https://a.example/x}", {}, "https://a.example/x", []),
        ("${K}", {}, "${K}", ["K"]),  # unset, no default: kept, reported
        ("${A}-${B}", {"A": "1"}, "1-${B}", ["B"]),
        ("$K and $(K) and ${ K}", {"K": "v"}, "$K and $(K) and ${ K}", []),
        ("${1BAD}", {"1BAD": "v"}, "${1BAD}", []),
        ("plain", {}, "plain", []),
    ],
)
def test_the_rules_of_claude_code(
    text: str, environ: dict[str, str], expected: str, missing: list[str]
) -> None:
    out, _, unset = expand_env_refs(text, environ)
    assert out == expected
    assert unset == missing


def test_a_value_is_not_expanded_again() -> None:
    out, values, _ = expand_env_refs("${A}", {"A": "${B}", "B": "secret"})
    assert out == "${B}"
    assert values == ["${B}"]


def test_the_values_put_in_are_returned_for_redaction() -> None:
    _, values, _ = expand_env_refs("--key=${K} ${U:-x}", {"K": "s3cr3t-value"})
    assert values == ["s3cr3t-value"]


# ── The stdio launch ──────────────────────────────────────────────────────────


class _Capture:
    """A stdio_client stand-in: keeps the launch, writes stderr, then fails."""

    def __init__(self, stderr: bytes = b"") -> None:
        self.params: Any = None
        self._stderr = stderr

    def __call__(self, params: Any, errlog: Any = None) -> _Capture:
        self.params = params
        self._errlog = errlog
        return self

    async def __aenter__(self) -> Any:
        if self._errlog is not None and self._stderr:
            self._errlog.write(self._stderr)
            self._errlog.flush()
        raise RuntimeError("server exited")

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False


def _server(**fields: Any) -> ServerConfig:
    base: dict[str, Any] = {
        "name": "keyed",
        "client": "claude-code",
        "config_path": Path("/tmp/.mcp.json"),  # noqa: S108
        "transport": TransportType.STDIO,
        "command": "node",
        "args": [],
        "env": {},
    }
    base.update(fields)
    return ServerConfig(**base)


async def _launch(server: ServerConfig, stderr: bytes = b"") -> tuple[Any, Any]:
    capture = _Capture(stderr)
    result = await mcp_client._enumerate_stdio(
        server, MagicMock(), capture, lambda **kw: SimpleNamespace(**kw)
    )
    return capture.params, result


@pytest.mark.asyncio
async def test_without_the_flag_the_server_gets_the_literal_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "abc")
    params, _ = await _launch(_server(env={"DEMO_API_KEY": "${DEMO_API_KEY}"}))
    assert params.env["DEMO_API_KEY"] == "${DEMO_API_KEY}"


@pytest.mark.asyncio
async def test_with_the_flag_command_args_and_env_are_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "abc")
    monkeypatch.setenv("TOOL_HOME", "/opt/tool")
    mcp_client.set_expand_env(True)
    params, _ = await _launch(
        _server(
            command="${TOOL_HOME}/bin/server",
            args=["--region", "${REGION:-eu}"],
            env={"DEMO_API_KEY": "${DEMO_API_KEY}", "MODE": "fixed"},
        )
    )
    assert params.command == "/opt/tool/bin/server"
    assert params.args == ["--region", "eu"]
    assert params.env["DEMO_API_KEY"] == "abc"
    assert params.env["MODE"] == "fixed"


@pytest.mark.asyncio
async def test_a_host_variable_that_the_config_does_not_name_stays_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "not-for-the-server")
    monkeypatch.setenv("DEMO_API_KEY", "abc")
    mcp_client.set_expand_env(True)
    params, _ = await _launch(_server(env={"DEMO_API_KEY": "${DEMO_API_KEY}"}))
    assert "AWS_SECRET_ACCESS_KEY" not in params.env
    assert "not-for-the-server" not in params.env.values()


@pytest.mark.asyncio
async def test_a_filled_value_is_redacted_from_what_the_server_says(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "zq-value-0123456789"  # noqa: S105 - a test value
    monkeypatch.setenv("TOKEN", secret)
    mcp_client.set_expand_env(True)
    _, result = await _launch(
        _server(args=["serve", "${TOKEN}"]),
        stderr=f"bad token {secret}\n".encode(),
    )
    assert secret not in (result.error or "")
    assert secret not in (result.server_stderr or "")
    assert "[REDACTED]" in (result.error or "")


@pytest.mark.asyncio
async def test_a_variable_that_is_not_set_is_named_in_the_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEMO_API_KEY", raising=False)
    mcp_client.set_expand_env(True)
    params, result = await _launch(_server(env={"DEMO_API_KEY": "${DEMO_API_KEY}"}))
    assert params.env["DEMO_API_KEY"] == "${DEMO_API_KEY}"
    assert "(--expand-env: not set: DEMO_API_KEY)" in (result.error or "")


@pytest.mark.asyncio
async def test_the_config_itself_is_not_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "abc")
    mcp_client.set_expand_env(True)
    server = _server(env={"DEMO_API_KEY": "${DEMO_API_KEY}"})
    await _launch(server)
    assert server.env == {"DEMO_API_KEY": "${DEMO_API_KEY}"}


# ── The command ───────────────────────────────────────────────────────────────


def test_the_flag_needs_connect(tmp_path: Path) -> None:
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
    result = runner.invoke(app, ["lock", str(tmp_path), "--expand-env"])
    assert result.exit_code == 2
    assert "--expand-env needs --connect" in result.output


def test_each_run_sets_the_flag_again(tmp_path: Path) -> None:
    mcp_client.set_expand_env(True)
    (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
    runner.invoke(app, ["lock", str(tmp_path), "--offline"])
    assert mcp_client._expand_env is False


# ── End to end: two servers of this file's own ───────────────────────────────

_KEYED = '''
import os, sys
from mcp.server.fastmcp import FastMCP

key = os.environ.get("DEMO_API_KEY", "")
if not key or key.startswith("$"):
    print("DEMO_API_KEY is not set", file=sys.stderr)
    sys.exit(1)
if "CREDENZO_TEST_NOT_NAMED" in os.environ:
    print("a variable that the config does not name reached me", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP("keyed")


@mcp.tool()
def lookup(q: str) -> str:
    """Look up a record."""
    return q


mcp.run()
'''

_OPEN = '''
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("open")


@mcp.tool()
def echo(text: str) -> str:
    """Return the text."""
    return text


mcp.run()
'''


@pytest.fixture
def keyed_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pytest.importorskip("mcp.server.fastmcp")
    import importlib

    module = importlib.import_module("mcp_audit.cli.lock")
    monkeypatch.setattr(module, "_sdk_problem", lambda: None)
    monkeypatch.setattr("mcp_audit.discovery._get_client_specs", lambda: [])
    root = tmp_path / "app"
    root.mkdir()
    (root / ".git").mkdir()
    (root / "keyed.py").write_text(_KEYED)
    (root / "open.py").write_text(_OPEN)
    (root / ".mcp.json").write_text(
        json.dumps(
            {
                "mcpServers": {
                    "keyed": {
                        "command": sys.executable,
                        "args": [str(root / "keyed.py")],
                        "env": {"DEMO_API_KEY": "${DEMO_API_KEY}"},
                    },
                    "open": {
                        "command": sys.executable,
                        "args": [str(root / "open.py")],
                    },
                }
            }
        )
    )
    monkeypatch.setenv("CREDENZO_TEST_NOT_NAMED", "1")
    return root


def _verify(root: Path, *extra: str) -> dict:
    result = runner.invoke(
        app, ["lock", str(root), "--verify", "--connect", "--format", "json", *extra]
    )
    # The runner mixes the progress line (stderr) into stdout.
    text = result.stdout
    return json.loads(text[text.index("{") :]) | {"exit": result.exit_code}


def test_a_keyed_server_is_locked_and_verified_with_its_key(
    keyed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "abc-key-for-the-test")
    written = runner.invoke(
        app, ["lock", str(keyed_project), "--connect", "--expand-env"]
    )
    assert written.exit_code == 0, written.output
    lock = json.loads((keyed_project / "mcp-lock.json").read_text())
    assert "abc-key-for-the-test" not in json.dumps(lock)

    passed = _verify(keyed_project, "--expand-env")
    assert passed["exit"] == 0, passed
    assert passed["unverified"] == []

    # Without the flag: the finding of 2026-11-27, kept as the reason for it.
    failed = _verify(keyed_project)
    assert failed["exit"] == 1
    assert [u["name"] for u in failed["unverified"]] == ["claude-code/keyed"]


def test_a_missing_key_is_named(
    keyed_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_API_KEY", "abc-key-for-the-test")
    assert (
        runner.invoke(
            app, ["lock", str(keyed_project), "--connect", "--expand-env"]
        ).exit_code
        == 0
    )
    monkeypatch.delenv("DEMO_API_KEY")
    failed = _verify(keyed_project, "--expand-env")
    assert failed["exit"] == 1
    reasons = " ".join(u["reason"] for u in failed["unverified"])
    assert "not set: DEMO_API_KEY" in reasons
