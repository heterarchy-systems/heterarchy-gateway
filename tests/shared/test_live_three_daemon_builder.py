"""Process ownership regressions for the live three-daemon test builder."""

import asyncio
import os
import signal
import sys
from pathlib import Path

import pytest

from tests.shared.live_three_daemon_builder import (
    LiveThreeDaemonBuilder,
    _capture_process,
    _reserve_loopback_port,
    _rust_launcher_command,
    _rust_runtime_paths,
)

_RUST_CI_LAUNCHER = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "rust_ci.sh"


class _RecordingBuilder(LiveThreeDaemonBuilder):
    """Record process cleanup without starting real Source services."""

    def __init__(self, fixture_root: Path) -> None:
        """Initialize the test builder without launching its daemons.

        Args:
            fixture_root: Isolated scratch directory for the builder.
        Return:
            None.
        """
        super().__init__(fixture_root)
        self.stop_called = False

    async def stop(self) -> None:
        """Record that the reader failure triggered process cleanup.

        Args:
            None.
        Return:
            None.
        """
        self.stop_called = True


@pytest.mark.asyncio
async def test_reader_failure_still_stops_builder(tmp_path: Path) -> None:
    async def fail_reader() -> None:
        raise RuntimeError("reader failed")

    event_task = asyncio.create_task(fail_reader())
    with pytest.raises(RuntimeError, match="reader failed"):
        await event_task

    builder = _RecordingBuilder(tmp_path / "reader-failure")
    with pytest.raises(RuntimeError, match="reader failed"):
        await builder.stop_after_reader(event_task)
    assert builder.stop_called


@pytest.mark.asyncio
async def test_capture_process_reaps_group_when_parent_is_cancelled(tmp_path: Path) -> None:
    child_pids: list[int] = []
    child_ready = asyncio.Event()

    async def record_child_pid(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        child_pid = int((await reader.readline()).decode("ascii").strip())
        child_pids.append(child_pid)
        child_ready.set()
        writer.close()
        await writer.wait_closed()

    port = _reserve_loopback_port()
    server = await asyncio.start_server(record_child_pid, "127.0.0.1", port)
    child_script = tmp_path / "owned_waiting_child.py"
    child_script.write_text(
        "import os\n"
        "import signal\n"
        "import socket\n"
        "import sys\n"
        "with socket.create_connection(('127.0.0.1', int(sys.argv[1]))) as connection:\n"
        "    connection.sendall(f'{os.getpid()}\\n'.encode('ascii'))\n"
        "    signal.pause()\n",
        encoding="utf-8",
    )
    capture_task = asyncio.create_task(
        _capture_process(
            [sys.executable, str(child_script), str(port)],
            working_directory=tmp_path,
            environment={"PATH": os.environ.get("PATH") or "/usr/bin:/bin"},
            timeout_seconds=60,
        )
    )
    try:
        await asyncio.wait_for(child_ready.wait(), timeout=5)
        assert len(child_pids) == 1
        child_pid = child_pids[0]
        capture_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await capture_task
        with pytest.raises(ProcessLookupError):
            os.killpg(child_pid, 0)
    finally:
        if not capture_task.done():
            capture_task.cancel()
            try:
                await asyncio.wait_for(capture_task, timeout=5)
            except asyncio.CancelledError:
                pass
        if child_pids:
            try:
                os.killpg(child_pids[0], signal.SIGKILL)
            except ProcessLookupError:
                pass
        server.close()
        await server.wait_closed()


def test_rust_runtime_paths_preserve_defaults_and_accept_ci_overrides(tmp_path: Path) -> None:
    default_launcher, default_build_root = _rust_runtime_paths(environ={})
    herterarchy_root = Path(__file__).resolve().parents[2].parent
    assert default_launcher == herterarchy_root / ".codex" / "rust-ssd"
    assert default_build_root == Path("/Volumes/256.SSD/RustBuild")
    assert _rust_launcher_command(launcher=default_launcher) == [
        sys.executable,
        str(default_launcher),
    ]

    launcher = tmp_path / "rust-ci.sh"
    build_root = tmp_path / "RustBuild"
    configured_launcher, configured_build_root = _rust_runtime_paths(
        environ={
            "GATEWAY_LIVE_RUST_LAUNCHER": str(launcher),
            "GATEWAY_LIVE_RUST_BUILD_ROOT": str(build_root),
        }
    )
    assert configured_launcher == launcher
    assert configured_build_root == build_root
    assert _rust_launcher_command(launcher=launcher) == [str(launcher)]

    with pytest.raises(RuntimeError, match="GATEWAY_LIVE_RUST_BUILD_ROOT"):
        _rust_runtime_paths(environ={"GATEWAY_LIVE_RUST_BUILD_ROOT": "relative-build"})
    with pytest.raises(RuntimeError, match="GATEWAY_LIVE_RUST_LAUNCHER"):
        _rust_runtime_paths(environ={"GATEWAY_LIVE_RUST_LAUNCHER": "relative-launcher"})


@pytest.mark.parametrize("category", ("forge", "orchestration"))
@pytest.mark.asyncio
async def test_rust_ci_launcher_uses_category_build_root(
    tmp_path: Path,
    category: str,
) -> None:
    build_root = tmp_path / "RustBuild"
    environment = {
        "GATEWAY_LIVE_RUST_BUILD_ROOT": str(build_root),
        "PATH": os.environ.get("PATH") or "/usr/bin:/bin",
    }
    output = await _capture_process(
        [str(_RUST_CI_LAUNCHER), category, "env"],
        working_directory=tmp_path,
        environment=environment,
        timeout_seconds=5,
    )
    configured_environment = dict(
        line.split("=", maxsplit=1) for line in output.splitlines() if "=" in line
    )

    assert configured_environment["CARGO_HOME"] == str(build_root / "cargo-home")
    assert configured_environment["CARGO_TARGET_DIR"] == str(build_root / category)
    assert configured_environment["TMPDIR"] == str(build_root / "tmp")
    assert configured_environment["CARGO_INCREMENTAL"] == "0"
    assert configured_environment["CARGO_PROFILE_DEV_DEBUG"] == "0"
    assert configured_environment["CARGO_PROFILE_TEST_DEBUG"] == "0"
    assert (build_root / "cargo-home").is_dir()
    assert (build_root / category).is_dir()
    assert (build_root / "tmp").is_dir()


@pytest.mark.parametrize(
    "build_root",
    (None, "relative-build"),
    ids=("missing", "relative"),
)
@pytest.mark.asyncio
async def test_rust_ci_launcher_rejects_missing_or_relative_build_root(
    tmp_path: Path,
    build_root: str | None,
) -> None:
    environment = {"PATH": os.environ.get("PATH") or "/usr/bin:/bin"}
    if build_root is not None:
        environment["GATEWAY_LIVE_RUST_BUILD_ROOT"] = build_root

    with pytest.raises(RuntimeError, match="GATEWAY_LIVE_RUST_BUILD_ROOT"):
        await _capture_process(
            [str(_RUST_CI_LAUNCHER), "forge", "env"],
            working_directory=tmp_path,
            environment=environment,
            timeout_seconds=5,
        )
