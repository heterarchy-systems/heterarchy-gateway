"""Own isolated native Source daemons for the Gateway live acceptance test."""

import asyncio
import os
import signal
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

import httpx

from app.shared.types.json_contract import decode_json

_GATEWAY_ROOT = Path(__file__).resolve().parents[2]
_HERTERARCHY_ROOT = _GATEWAY_ROOT.parent
_FORGE_ROOT = _HERTERARCHY_ROOT / "heterarchy-forge"
_ORCHESTRATION_ROOT = _HERTERARCHY_ROOT / "heterarchy-orchestration"
_RUST_SSD = _HERTERARCHY_ROOT / ".codex" / "rust-ssd"
_RUST_BUILD = Path("/Volumes/256.SSD/RustBuild")
_FORGE_BINARY = _RUST_BUILD / "forge" / "debug" / "forge-backend"
_FIXTURE_MANIFEST = (
    _GATEWAY_ROOT / "tests" / "integration" / "fixtures" / "live_three_daemon" / "Cargo.toml"
)
_FIXTURE_BINARY = _RUST_BUILD / "orchestration" / "debug" / "gateway-live-three-daemon-host"
_CODEX_SHIM_DIRECTORY = _FIXTURE_MANIFEST.parent / "bin"
_CODEX_SHIM = _CODEX_SHIM_DIRECTORY / "codex"
_GATEWAY_PORT = 7979
_READY_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True, slots=True, kw_only=True, repr=False)
class LiveThreeDaemonContext:
    """Private runtime identities and credentials for one isolated live test."""

    fixture_root: Path
    gateway_origin: str
    forge_authorization: str = field(repr=False)
    orchestration_authorization: str = field(repr=False)
    workspace_id: str
    workspace_revision: int
    location_id: str
    location_revision: int
    locator: str
    relative_root: str
    activity_id: str
    session_id: str
    coordinator_agent_id: str
    outbox_migration_id: str
    destination_id: str
    operator_principal_id: str
    workspace_root: Path
    worktree_root: Path


@dataclass(slots=True)
class _OwnedProcess:
    """One process group launched and cleaned by this test builder."""

    name: str
    process: asyncio.subprocess.Process
    log_file: BinaryIO
    log_path: Path

    async def stop(self) -> None:
        """Terminate this owned process group and wait for its leader."""
        if self.process.returncode is not None:
            self.log_file.close()
            return
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(self.process.wait(), timeout=20)
        except TimeoutError:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await asyncio.wait_for(self.process.wait(), timeout=5)
        self.log_file.close()


class LiveThreeDaemonBuilder:
    """Build fixture state and own Forge, Orchestration, and Gateway processes."""

    def __init__(self, fixture_root: Path) -> None:
        """Initialize paths for one pytest-owned scratch tree.

        Args:
            fixture_root: Fresh temporary directory provided by pytest.
        Return:
            None.
        """
        self._fixture_root = fixture_root.resolve()
        self._processes: list[_OwnedProcess] = []
        self.context: LiveThreeDaemonContext | None = None

    async def start(self) -> LiveThreeDaemonContext:
        """Prepare source-backed fixture state and start all HTTP services.

        Args:
            None.
        Return:
            Gateway origin and the source fixture identities.
        """
        await _assert_source_checkout(_FORGE_ROOT, None)
        await _assert_source_checkout(_ORCHESTRATION_ROOT, "56d1d8d")
        _require_loopback_port(_GATEWAY_PORT)
        forge_port = _reserve_loopback_port()
        orchestration_port = _reserve_loopback_port()
        session_authority_port = _reserve_loopback_port()
        assert len({forge_port, orchestration_port, session_authority_port, _GATEWAY_PORT}) == 4

        self._fixture_root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self._fixture_root.chmod(0o700)
        worktree_root = self._fixture_root / "heterarchy-forge-swarm-worktrees"
        worktree_root.mkdir(mode=0o700)
        if not _CODEX_SHIM.is_file() or _CODEX_SHIM.stat().st_mode & 0o022:
            raise RuntimeError("the checked-in Codex fixture is missing or mutable by other users")

        await _build_fixture_host()
        await _run_rust_build(
            _FORGE_ROOT,
            ["build", "--locked", "--offline", "-p", "forge-backend"],
            "forge",
        )
        seed = await self._seed_source_state(
            forge_port,
            session_authority_port,
        )
        operator_authorization = _read_bearer(seed, "operator_bearer_path")
        forge_authorization = _read_bearer(seed, "forge_bearer_path")

        source_environment = _clean_environment()
        source_environment["TMPDIR"] = str(self._fixture_root)
        await self._start_process(
            "forge",
            [_FORGE_BINARY, "serve", Path(_manifest_text(seed, "forge_config_path"))],
            source_environment,
            _FORGE_ROOT,
        )

        orchestration_environment = _clean_environment()
        orchestration_environment.update(
            {
                "TMPDIR": str(self._fixture_root),
                "PATH": f"{_CODEX_SHIM_DIRECTORY}:/usr/bin:/bin",
                "GATEWAY_LIVE_ORCHESTRATION_LISTEN": f"127.0.0.1:{orchestration_port}",
                "GATEWAY_LIVE_SESSION_AUTHORITY_LISTEN": (f"127.0.0.1:{session_authority_port}"),
            }
        )
        await self._start_process(
            "orchestration-fixture-host",
            [_FIXTURE_BINARY, "serve", self._fixture_root],
            orchestration_environment,
            _GATEWAY_ROOT,
        )

        gateway_environment = _clean_environment()
        gateway_environment.update(
            {
                "GATEWAY_FORGE_BASE_URL": f"http://127.0.0.1:{forge_port}/api/v1",
                "GATEWAY_ORCHESTRATION_BASE_URL": f"http://127.0.0.1:{orchestration_port}",
                "GATEWAY_FAILURE_SIMULATION_ENABLED": "false",
                "GATEWAY_HTTP_TIMEOUT_SECONDS": "60.0",
                "GATEWAY_MAX_CONNECTIONS": "100",
                "GATEWAY_MAX_KEEPALIVE_CONNECTIONS": "20",
                "GATEWAY_TRACE_CAPACITY": "100",
                "GATEWAY_HOST": "127.0.0.1",
                "GATEWAY_PORT": str(_GATEWAY_PORT),
                "TMPDIR": str(self._fixture_root),
            }
        )
        gateway_process = await self._start_process(
            "gateway",
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.bootstrap:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(_GATEWAY_PORT),
                "--loop",
                "asyncio",
                "--http",
                "h11",
                "--workers",
                "1",
                "--limit-concurrency",
                "100",
            ],
            gateway_environment,
            _GATEWAY_ROOT,
        )
        self.context = _live_context(
            self._fixture_root,
            seed,
            operator_authorization,
            forge_authorization,
            worktree_root,
        )
        await self._wait_for_gateway_and_backends(gateway_process)
        result = self.context
        return result

    async def stop(self) -> None:
        """Stop only the process groups created by this test.

        Args:
            None.
        Return:
            None.
        """
        errors: list[str] = []
        for owned in reversed(self._processes):
            try:
                await owned.stop()
            except (OSError, TimeoutError) as error:
                errors.append(f"{owned.name} process group did not stop: {error}")
        self._processes.clear()
        if errors:
            raise RuntimeError("; ".join(errors))

    async def stop_after_reader(self, event_task: asyncio.Task[None] | None) -> None:
        """Cancel the SSE reader and stop services even when it failed.

        Args:
            event_task: Optional reader task owned by the integration test.
        Return:
            None after reader completion and process cleanup.
        """
        try:
            if event_task is not None:
                event_task.cancel()
                try:
                    await event_task
                except asyncio.CancelledError:
                    pass
        finally:
            await self.stop()

    async def _wait_for_gateway_and_backends(
        self,
        gateway_process: asyncio.subprocess.Process,
    ) -> None:
        """Poll all readiness through Gateway URLs only.

        Args:
            gateway_process: Owned uvicorn process whose early exit is fatal.
        Return:
            None after liveness, Orchestration, and Forge respond.
        """
        context = self.context
        if context is None:
            raise RuntimeError("live fixture identities were not initialized")
        deadline = asyncio.get_running_loop().time() + _READY_TIMEOUT_SECONDS
        async with httpx.AsyncClient(base_url=context.gateway_origin, timeout=2.0) as client:
            while asyncio.get_running_loop().time() < deadline:
                if gateway_process.returncode is not None:
                    raise RuntimeError("Gateway exited during loopback startup")
                try:
                    liveness = await client.get("/healthz")
                    if liveness.status_code != 200:
                        await asyncio.sleep(0.2)
                        continue
                    profiles = await client.get(
                        "/orchestrations/profiles",
                        headers={"Authorization": context.orchestration_authorization},
                    )
                    locations = await client.post(
                        "/forges/locations/list",
                        headers={"Authorization": context.forge_authorization},
                        json={
                            "forge_api": 1,
                            "request_id": context.activity_id,
                            "op": "location.list",
                            "payload": {},
                        },
                    )
                    if profiles.status_code == 200 and locations.status_code == 200:
                        profile_payload = decode_json(profiles.content)
                        location_payload = decode_json(locations.content)
                        if isinstance(profile_payload, list) and isinstance(location_payload, dict):
                            result = location_payload.get("result")
                            if isinstance(result, dict) and profiles.is_success:
                                return
                except httpx.HTTPError:
                    await asyncio.sleep(0.2)
                    continue
                await asyncio.sleep(0.2)
        raise RuntimeError("Gateway did not complete upstream readiness checks before timeout")

    async def _seed_source_state(
        self, forge_port: int, session_authority_port: int
    ) -> dict[str, str | int]:
        """Run the typed native Source seeder without sending fixture HTTP requests.

        Args:
            forge_port: Reserved loopback port for the native Forge backend.
            session_authority_port: Embedded Orchestration session authority port.
        Return:
            Validated non-secret Source fixture manifest values.
        """
        seed_environment = _clean_environment()
        seed_environment.update(
            {
                "TMPDIR": str(self._fixture_root),
                "GATEWAY_LIVE_FORGE_ADDR": f"127.0.0.1:{forge_port}",
                "GATEWAY_LIVE_SESSION_AUTHORITY_LISTEN": (f"127.0.0.1:{session_authority_port}"),
            }
        )
        output = await _capture_process(
            [_FIXTURE_BINARY, "seed", self._fixture_root],
            working_directory=_GATEWAY_ROOT,
            environment=seed_environment,
            timeout_seconds=60,
        )
        payload = decode_json(output.encode("utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("native fixture seeder returned a non-object payload")
        manifest: dict[str, str | int] = {}
        for key, value in payload.items():
            if isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool)):
                manifest[key] = value
            else:
                raise RuntimeError(f"native fixture manifest field has invalid type: {key}")
        return manifest

    async def _start_process(
        self,
        name: str,
        command: list[str | Path],
        environment: dict[str, str],
        working_directory: Path,
    ) -> asyncio.subprocess.Process:
        """Start one fixture-owned service process in an isolated process group.

        Args:
            name: Local process label used in safe failure messages.
            command: Exact argv vector without shell evaluation.
            environment: Explicit test-only process environment.
            working_directory: Repository root or the fixture root.
        Return:
            Owned process handle.
        """
        log_path = self._fixture_root / "logs" / f"{name}.log"
        log_path.parent.mkdir(mode=0o700, exist_ok=True)
        log_file = log_path.open("xb")
        try:
            process = await asyncio.create_subprocess_exec(
                *(str(argument) for argument in command),
                cwd=str(working_directory),
                env=environment,
                stdout=log_file,
                stderr=asyncio.subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError:
            log_file.close()
            raise
        self._processes.append(
            _OwnedProcess(name=name, process=process, log_file=log_file, log_path=log_path)
        )
        return process


def _live_context(
    fixture_root: Path,
    seed: dict[str, str | int],
    operator_authorization: str,
    forge_authorization: str,
    worktree_root: Path,
) -> LiveThreeDaemonContext:
    """Map the seeder manifest into typed Gateway request context.

    Args:
        fixture_root: Disposable fixture directory.
        seed: Non-secret native Source setup results.
        operator_authorization: Token issued into the scratch catalog.
        forge_authorization: Forge API token written into the scratch tree.
        worktree_root: Worker directory kept outside RustBuild.
    Return:
        Complete context for Gateway-only lifecycle calls.
    """
    workspace_root = Path(_manifest_text(seed, "forge_root")) / "location" / "workspace-0"
    context = LiveThreeDaemonContext(
        fixture_root=fixture_root,
        gateway_origin=f"http://127.0.0.1:{_GATEWAY_PORT}",
        forge_authorization=forge_authorization,
        orchestration_authorization=operator_authorization,
        workspace_id=_manifest_text(seed, "workspace_id"),
        workspace_revision=_manifest_integer(seed, "workspace_revision"),
        location_id=_manifest_text(seed, "location_id"),
        location_revision=_manifest_integer(seed, "location_revision"),
        locator=_manifest_text(seed, "locator"),
        relative_root=_manifest_text(seed, "relative_root"),
        activity_id=_manifest_text(seed, "activity_id"),
        session_id=_manifest_text(seed, "session_id"),
        coordinator_agent_id=_manifest_text(seed, "coordinator_agent_id"),
        outbox_migration_id=_manifest_text(seed, "outbox_migration_id"),
        destination_id=_manifest_text(seed, "destination_id"),
        operator_principal_id=_manifest_text(seed, "operator_principal_id"),
        workspace_root=workspace_root,
        worktree_root=worktree_root,
    )
    return context


def _manifest_text(seed: dict[str, str | int], field: str) -> str:
    value = seed.get(field)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"native fixture manifest is missing text field {field}")
    return value


def _manifest_integer(seed: dict[str, str | int], field: str) -> int:
    value = seed.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise RuntimeError(f"native fixture manifest is missing integer field {field}")
    return value


def _read_bearer(seed: dict[str, str | int], field: str) -> str:
    path = Path(_manifest_text(seed, field))
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError(f"native fixture bearer file is missing for {field}")
    bearer = path.read_text(encoding="utf-8").strip()
    if not bearer:
        raise RuntimeError(f"native fixture bearer file is malformed for {field}")
    if not bearer.startswith("Bearer "):
        bearer = f"Bearer {bearer}"
    return bearer


def _clean_environment() -> dict[str, str]:
    """Create an isolated service environment without inherited credentials.

    Args:
        None.
    Return:
        Minimal environment for loopback test services.
    """
    path = os.environ.get("PATH", "/usr/bin:/bin")
    result = {"PATH": path}
    return result


def _reserve_loopback_port() -> int:
    """Reserve then release one ephemeral IPv4 loopback port.

    Args:
        None.
    Return:
        Available nonzero loopback port selected by the kernel.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        result = int(probe.getsockname()[1])
    return result


def _require_loopback_port(port: int) -> None:
    """Fail clearly if the required Gateway port belongs to another process.

    Args:
        port: Fixed Gateway listen port.
    Return:
        None when the port is available.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", port))


async def _assert_source_checkout(
    source_root: Path,
    expected_revision: str | None,
) -> None:
    """Require a clean pinned Source checkout before a live contract test.

    Args:
        source_root: Read-only adjacent Source repository.
        expected_revision: Required short Source commit.
    Return:
        None when the Source checkout matches the test contract.
    """
    revision = (
        await _capture_process(
            ["git", "-C", source_root, "rev-parse", "--short", "HEAD"],
            working_directory=source_root,
            environment=os.environ.copy(),
            timeout_seconds=10,
        )
    ).strip()
    status = await _capture_process(
        ["git", "-C", source_root, "status", "--porcelain"],
        working_directory=source_root,
        environment=os.environ.copy(),
        timeout_seconds=10,
    )
    if (expected_revision is not None and revision != expected_revision) or status:
        raise RuntimeError(f"live e2e requires clean Source revision {expected_revision}")


async def _build_fixture_host() -> None:
    """Build the Source-backed fixture host under the canonical Rust SSD target.

    Args:
        None.
    Return:
        None after Cargo verifies the locked fixture graph.
    """
    await _run_rust_build(
        _ORCHESTRATION_ROOT,
        [
            "build",
            "--locked",
            "--offline",
            "--manifest-path",
            str(_FIXTURE_MANIFEST),
            "--bin",
            "gateway-live-three-daemon-host",
        ],
        "orchestration",
    )


async def _run_rust_build(
    source_root: Path,
    arguments: list[str],
    category: str,
) -> None:
    """Run Cargo with the Gateway uv interpreter and the approved Rust SSD target.

    Args:
        source_root: Working Source checkout whose rust-toolchain selects Cargo.
        arguments: Cargo subcommand and explicit package/manifest arguments.
        category: Configured Rust SSD target name.
    Return:
        None after a successful locked build.
    """
    command = [
        sys.executable,
        str(_RUST_SSD),
        category,
        "cargo",
        *arguments,
    ]
    await _capture_process(
        command,
        working_directory=source_root,
        environment=os.environ.copy(),
        timeout_seconds=900,
    )


async def _capture_process(
    command: list[str | Path],
    *,
    working_directory: Path,
    environment: dict[str, str],
    timeout_seconds: float,
) -> str:
    """Run one bounded owned command and return its standard output.

    Args:
        command: Executable and argument vector, without shell evaluation.
        working_directory: Explicit source or project directory.
        environment: Explicit caller or build environment.
        timeout_seconds: Upper bound before the owned process is terminated.
    Return:
        Decoded standard output from a successful process.
    """
    process = await asyncio.create_subprocess_exec(
        *(str(argument) for argument in command),
        cwd=str(working_directory),
        env=environment,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        start_new_session=True,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout_seconds)
    except TimeoutError as error:
        await _terminate_owned_process_group(process)
        raise RuntimeError("Owned build/bootstrap command exceeded its deadline") from error
    except BaseException:
        await _terminate_owned_process_group(process)
        raise
    if process.returncode != 0:
        detail = output.decode("utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"Owned command failed ({process.returncode}): {detail}")
    result = output.decode("utf-8")
    return result


async def _terminate_owned_process_group(process: asyncio.subprocess.Process) -> None:
    """Terminate and reap one interrupted command and its owned process group.

    Args:
        process: Command leader started in its own session.
    Return:
        None after the leader is reaped and its process group is signaled.
    """
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except TimeoutError:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    if process.returncode is None:
        await process.wait()
