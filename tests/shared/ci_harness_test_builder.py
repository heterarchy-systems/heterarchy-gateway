"""Synthetic archive and process builder for the private CI restore boundary."""

import asyncio
import base64
import gzip
import hashlib
import io
import os
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

_RESTORE_SCRIPT = Path(__file__).resolve().parents[2] / ".github/scripts/restore_private_harness.py"

_RUNTIME_PATHS = (
    "HARNESS.toml",
    "HARNESS_MANIFEST.toml",
    "guardrails/__init__.py",
    "guardrails/__main__.py",
    "guardrails/_common.py",
    "guardrails/call_safety_guardrails.py",
    "guardrails/composition_guardrails.py",
    "guardrails/contract_guardrails.py",
    "guardrails/guardrail_runner.py",
    "guardrails/module_boundary_guardrails.py",
    "guardrails/realtime_recovery_guardrails.py",
    "guardrails/source_guardrails.py",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CiHarnessRestoreBuilder:
    """Build non-secret archives and invoke the real standalone restore entrypoint."""

    omitted_path: str | None
    extra_path: str | None
    extra_content: bytes
    symlink: bool
    padding_bytes: int

    def archive(self) -> bytes:
        """Build a complete synthetic guard runtime with an optional invalid entry.

        Args:
            None.
        Return:
            Compressed tar bytes containing synthetic files only.
        """
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            for name in _RUNTIME_PATHS:
                if name == self.omitted_path:
                    continue
                content = b"# Synthetic private-harness restore fixture.\n"
                member = tarfile.TarInfo(f".agents/python_bff_harness/{name}")
                member.size = len(content)
                archive.addfile(tarinfo=member, fileobj=io.BytesIO(content))
            if self.extra_path is not None:
                member = tarfile.TarInfo(self.extra_path)
                member.size = len(self.extra_content)
                if self.symlink:
                    member.type = tarfile.SYMTYPE
                    member.linkname = "../../outside.py"
                    member.size = 0
                archive.addfile(tarinfo=member, fileobj=io.BytesIO(self.extra_content))
        result = buffer.getvalue()
        if self.padding_bytes:
            result = gzip.compress(gzip.decompress(result) + b"\0" * self.padding_bytes)
        return result

    async def execute(
        self,
        *,
        destination: Path,
        digest_matches: bool,
        valid_base64: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Run the same restore command as Actions with a synthetic archive.

        Args:
            destination: Empty checkout owned by the test.
            digest_matches: Whether the supplied SHA matches the archive.
            valid_base64: Whether to encode the archive correctly.
        Return:
            Captured exit status and public command output.
        """
        payload = self.archive()
        encoded = base64.b64encode(payload).decode("ascii") if valid_base64 else "invalid!"
        digest = hashlib.sha256(payload).hexdigest() if digest_matches else "0" * 64
        environment = os.environ.copy()
        environment.update(
            GATEWAY_PRIVATE_HARNESS_TAR_GZ_B64=encoded,
            GATEWAY_PRIVATE_HARNESS_SHA256=digest,
        )
        command = (sys.executable, str(_RESTORE_SCRIPT), "--destination", str(destination))
        process = await asyncio.create_subprocess_exec(
            *command,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        finally:
            if process.returncode is None:
                process.kill()
                await process.wait()
        assert process.returncode is not None
        result = subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode,
            stdout=stdout.decode("utf-8"),
            stderr=stderr.decode("utf-8"),
        )
        assert encoded not in result.stdout + result.stderr
        return result
