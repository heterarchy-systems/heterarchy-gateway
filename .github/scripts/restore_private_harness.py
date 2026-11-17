"""Restore the canonical private guard runtime from encrypted Actions secrets."""

import argparse
import base64
import gzip
import hashlib
import hmac
import io
import os
import re
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

_ARCHIVE_ROOT = PurePosixPath(".agents/python_bff_harness")
_MAX_ARCHIVE_BYTES = 36_864
_MAX_UNPACKED_BYTES = 4_194_304
_MAX_TAR_BYTES = 5_242_880
_MAX_FILES = 256
_REQUIRED_FILES = (
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


def restore_private_harness(
    *, destination: Path, encoded_archive: str, expected_digest: str
) -> None:
    """Verify the complete runtime before installing it under the checkout."""
    if not encoded_archive or len(encoded_archive) > _MAX_ARCHIVE_BYTES * 4 // 3:
        raise ValueError("Private harness archive is missing or exceeds its size limit")
    if re.fullmatch(r"[0-9a-fA-F]{64}", expected_digest) is None:
        raise ValueError("Private harness SHA-256 must contain exactly 64 hexadecimal characters")
    payload = base64.b64decode(encoded_archive, validate=True)
    if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), expected_digest.lower()):
        raise ValueError("Private harness SHA-256 verification failed")
    with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as compressed:
        tar_payload = compressed.read(_MAX_TAR_BYTES + 1)
    if len(tar_payload) > _MAX_TAR_BYTES:
        raise ValueError("Private harness TAR exceeds its decompressed size limit")

    destination = destination.resolve()
    target = destination.joinpath(*_ARCHIVE_ROOT.parts)
    if target.exists() or target.is_symlink():
        raise ValueError("Private harness destination already exists")
    if not target.parent.resolve().is_relative_to(destination):
        raise ValueError("Private harness destination escapes the checkout")

    allowed_names = {_ARCHIVE_ROOT / required for required in _REQUIRED_FILES}
    with tarfile.open(fileobj=io.BytesIO(tar_payload), mode="r:") as archive:
        members: list[tarfile.TarInfo] = []
        names: set[PurePosixPath] = set()
        unpacked_bytes = 0
        for member in archive:
            name = PurePosixPath(member.name)
            if (
                not member.isfile()
                or member.size < 0
                or "\\" in member.name
                or ".." in name.parts
                or not name.is_relative_to(_ARCHIVE_ROOT)
                or name not in allowed_names
                or name in names
            ):
                raise ValueError("Private harness archive contains an invalid runtime entry")
            unpacked_bytes += member.size
            if unpacked_bytes > _MAX_UNPACKED_BYTES or len(members) >= _MAX_FILES:
                raise ValueError("Private harness archive exceeds its extraction limits")
            names.add(name)
            members.append(member)

        if any(_ARCHIVE_ROOT / required not in names for required in _REQUIRED_FILES):
            raise ValueError("Private harness archive is missing required runtime files")

        with tempfile.TemporaryDirectory(prefix="gateway-harness-", dir=destination) as temporary:
            staging = Path(temporary)
            archive.extractall(path=staging, members=members, filter="data")
            for member in members:
                staging.joinpath(*PurePosixPath(member.name).parts).chmod(0o600)
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            staging.joinpath(*_ARCHIVE_ROOT.parts).replace(target)


def main() -> None:
    """Restore into the explicitly selected checkout without logging private data."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    restore_private_harness(
        destination=arguments.destination,
        encoded_archive=os.environ.get("GATEWAY_PRIVATE_HARNESS_TAR_GZ_B64", ""),
        expected_digest=os.environ.get("GATEWAY_PRIVATE_HARNESS_SHA256", ""),
    )
    print("Private harness runtime restored and SHA-256 verified.")


if __name__ == "__main__":
    main()
