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
)


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
