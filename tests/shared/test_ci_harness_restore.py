"""Regression coverage for verified, confined and atomic private CI restoration."""

from dataclasses import replace
from pathlib import Path

import pytest

from tests.shared.ci_harness_test_builder import CiHarnessRestoreBuilder


@pytest.mark.asyncio
async def test_private_harness_restore_accepts_only_complete_confined_runtime(
    tmp_path: Path,
) -> None:
    builder = CiHarnessRestoreBuilder(
        omitted_path=None, extra_path=None, extra_content=b"", symlink=False, padding_bytes=0
    )
    cases = {
        "complete_runtime": (builder, True, True, True),
        "digest_mismatch": (builder, False, True, False),
        "malformed_encoding": (builder, True, False, False),
        "missing_runtime": (
            replace(builder, omitted_path="guardrails/guardrail_runner.py"),
            True,
            True,
            False,
        ),
        "path_traversal": (
            replace(builder, extra_path=".agents/python_bff_harness/../../outside.py"),
            True,
            True,
            False,
        ),
        "symlink": (
            replace(builder, extra_path=".agents/python_bff_harness/link.py", symlink=True),
            True,
            True,
            False,
        ),
        "duplicate_member": (
            replace(builder, extra_path=".agents/python_bff_harness/HARNESS.toml"),
            True,
            True,
            False,
        ),
        "oversized_runtime": (
            replace(
                builder,
                omitted_path="guardrails/_common.py",
                extra_path=".agents/python_bff_harness/guardrails/_common.py",
                extra_content=b"0" * 4_194_304,
            ),
            True,
            True,
            False,
        ),
        "oversized_tar_padding": (replace(builder, padding_bytes=5_242_880), True, True, False),
        "existing_symlink_parent": (builder, True, True, False),
    }
    for name, (case_builder, digest_matches, valid_base64, accepted) in cases.items():
        destination = tmp_path / name
        destination.mkdir()
        if name == "existing_symlink_parent":
            external = tmp_path / "external-harness-parent"
            external.mkdir()
            (destination / ".agents").symlink_to(external, target_is_directory=True)
        completed = await case_builder.execute(
            destination=destination,
            digest_matches=digest_matches,
            valid_base64=valid_base64,
        )
        installed = destination / ".agents/python_bff_harness"
        assert (completed.returncode == 0) is accepted, (name, completed.stderr)
        assert installed.exists() is accepted, name
        assert not (destination / "outside.py").exists(), name
        assert not tuple(destination.glob("gateway-harness-*")), name
        if accepted:
            guard = installed / "guardrails/guardrail_runner.py"
            assert guard.read_bytes() == b"# Synthetic private-harness restore fixture.\n"
            assert guard.stat().st_mode & 0o077 == 0
