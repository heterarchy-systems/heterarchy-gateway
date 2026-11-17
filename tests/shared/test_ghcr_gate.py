"""Grouped private GHCR gate tests backed by a local fake gh executable."""

import asyncio
import os
import signal
from dataclasses import dataclass
from pathlib import Path

import pytest

_GATEWAY_ROOT = Path(__file__).resolve().parents[2]
_CHECK_GHCR_SCRIPT = _GATEWAY_ROOT / ".github" / "scripts" / "check_ghcr.sh"
_GHCR_IMAGE = "ghcr.io/heterarchy-systems/heterarchy-gateway"
_VERSION = "0.1.0"
_DUMMY_AUTH = "synthetic-value-that-must-not-appear"

_FAKE_GH_SCRIPT = """#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$FAKE_GH_CALL_LOG"

if [[ "${2:-}" == "--include" ]]; then
    status=${FAKE_GH_HTTP_STATUS:?}
    visibility=${FAKE_GH_VISIBILITY:-}
    printf 'HTTP/2 %s fixture\\r\\nX-Fixture: true\\r\\n\\r\\n%s\\n' "$status" "$visibility"
    if [[ "$status" != "200" ]]; then
        printf 'simulated gh API error\\n' >&2
        exit 1
    fi
    exit 0
fi

if [[ "${2:-}" == "--paginate" ]]; then
    printf '%s\\n' "${FAKE_GH_TAGS:-}"
    exit 0
fi

printf 'unexpected fake gh invocation\\n' >&2
exit 2
"""


@dataclass(frozen=True, slots=True, kw_only=True)
class _GhcrGateCase:
    """Inputs and expected effects for one GHCR gate case."""

    phase: str
    http_status: int
    visibility: str
    tags: tuple[str, ...]
    expected_status: int
    expected_stdout: str
    expected_stderr: str
    expects_pagination: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class _GhcrInvocation:
    """One fake-gh environment and the exact script command to execute."""

    command: tuple[str, ...]
    environment: dict[str, str]
    call_log: Path


class _GhcrGateBuilder:
    """Build isolated check_ghcr.sh invocations with a fake gh executable."""

    def __init__(self, *, fixture_root: Path) -> None:
        self._fixture_root = fixture_root
        self._fake_bin = fixture_root / "bin"
        self._fake_bin.mkdir(parents=True, exist_ok=True)
        self._fake_gh = self._fake_bin / "gh"
        self._fake_gh.write_text(_FAKE_GH_SCRIPT, encoding="utf-8")
        self._fake_gh.chmod(0o755)
        self._call_log = fixture_root / "gh-calls.log"

    def build(self, *, case: _GhcrGateCase) -> _GhcrInvocation:
        self._call_log.write_text("", encoding="utf-8")
        environment = dict(os.environ)
        environment.update(
            {
                "FAKE_GH_CALL_LOG": str(self._call_log),
                "FAKE_GH_HTTP_STATUS": str(case.http_status),
                "FAKE_GH_VISIBILITY": case.visibility,
                "FAKE_GH_TAGS": "\n".join(case.tags),
                "GH_TOKEN": _DUMMY_AUTH,
                "PATH": os.pathsep.join(
                    (str(self._fake_bin), environment.get("PATH", "/usr/bin:/bin"))
                ),
            }
        )
        result = _GhcrInvocation(
            command=("/bin/bash", str(_CHECK_GHCR_SCRIPT), _GHCR_IMAGE, _VERSION, case.phase),
            environment=environment,
            call_log=self._call_log,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class _ProcessResult:
    """Captured result of one owned GHCR check process."""

    return_code: int
    stdout: str
    stderr: str


async def _run_process(
    *,
    command: tuple[str, ...],
    environment: dict[str, str],
) -> _ProcessResult:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=_GATEWAY_ROOT,
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=10)
    except BaseException:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()
        raise

    return_code = process.returncode
    if return_code is None:
        raise RuntimeError("GHCR check process exited without a return code")
    result = _ProcessResult(
        return_code=return_code,
        stdout=stdout_bytes.decode("utf-8"),
        stderr=stderr_bytes.decode("utf-8"),
    )
    return result


@pytest.mark.asyncio
async def test_ghcr_gate_validates_visibility_and_numeric_tags(tmp_path: Path) -> None:
    cases: dict[str, _GhcrGateCase] = {
        "inspect_accepts_new_404": _GhcrGateCase(
            phase="inspect",
            http_status=404,
            visibility="",
            tags=(),
            expected_status=0,
            expected_stdout="New GHCR package",
            expected_stderr="",
            expects_pagination=False,
        ),
        "prepare_accepts_new_404": _GhcrGateCase(
            phase="prepare",
            http_status=404,
            visibility="",
            tags=(),
            expected_status=0,
            expected_stdout="New GHCR package",
            expected_stderr="",
            expects_pagination=False,
        ),
        "published_rejects_404": _GhcrGateCase(
            phase="published",
            http_status=404,
            visibility="",
            tags=(),
            expected_status=1,
            expected_stdout="",
            expected_stderr="GHCR package verification failed.",
            expects_pagination=False,
        ),
        "inspect_rejects_403": _GhcrGateCase(
            phase="inspect",
            http_status=403,
            visibility="",
            tags=(),
            expected_status=1,
            expected_stdout="",
            expected_stderr="GHCR package verification failed.",
            expects_pagination=False,
        ),
        "inspect_accepts_private": _GhcrGateCase(
            phase="inspect",
            http_status=200,
            visibility="private",
            tags=(),
            expected_status=0,
            expected_stdout="visibility verified: private",
            expected_stderr="",
            expects_pagination=False,
        ),
        "inspect_rejects_public": _GhcrGateCase(
            phase="inspect",
            http_status=200,
            visibility="public",
            tags=(),
            expected_status=1,
            expected_stdout="",
            expected_stderr="Expected private GHCR visibility; received public.",
            expects_pagination=False,
        ),
        "prepare_rejects_internal": _GhcrGateCase(
            phase="prepare",
            http_status=200,
            visibility="internal",
            tags=(),
            expected_status=1,
            expected_stdout="",
            expected_stderr="Expected private GHCR visibility; received internal.",
            expects_pagination=False,
        ),
        "prepare_rejects_existing_numeric_tag": _GhcrGateCase(
            phase="prepare",
            http_status=200,
            visibility="private",
            tags=("0.1.0", "latest"),
            expected_status=1,
            expected_stdout="GHCR package visibility verified: private.",
            expected_stderr="already exists; choose a new version",
            expects_pagination=True,
        ),
        "prepare_accepts_new_numeric_tag": _GhcrGateCase(
            phase="prepare",
            http_status=200,
            visibility="private",
            tags=("0.0.9", "latest"),
            expected_status=0,
            expected_stdout="GHCR numeric version verified: 0.1.0.",
            expected_stderr="",
            expects_pagination=True,
        ),
        "published_accepts_existing_numeric_tag": _GhcrGateCase(
            phase="published",
            http_status=200,
            visibility="private",
            tags=("0.1.0", "latest"),
            expected_status=0,
            expected_stdout="GHCR numeric version verified: 0.1.0.",
            expected_stderr="",
            expects_pagination=True,
        ),
        "published_rejects_missing_numeric_tag": _GhcrGateCase(
            phase="published",
            http_status=200,
            visibility="private",
            tags=("0.0.9", "latest"),
            expected_status=1,
            expected_stdout="GHCR package visibility verified: private.",
            expected_stderr="Published GHCR version 0.1.0 was not found.",
            expects_pagination=True,
        ),
    }

    for case_name, case in cases.items():
        invocation = _GhcrGateBuilder(fixture_root=tmp_path / case_name).build(case=case)
        result = await _run_process(
            command=invocation.command,
            environment=invocation.environment,
        )
        call_lines = invocation.call_log.read_text(encoding="utf-8").splitlines()

        assert result.return_code == case.expected_status, case_name
        assert case.expected_stdout in result.stdout, case_name
        assert case.expected_stderr in result.stderr, case_name
        assert _DUMMY_AUTH not in result.stdout + result.stderr, case_name
        assert call_lines[0].startswith("api --include "), case_name
        assert len(call_lines) == (2 if case.expects_pagination else 1), case_name
        if case.expects_pagination:
            assert call_lines[1].startswith("api --paginate "), case_name
