"""Grouped CLI contract checks for the GitHub release version selector."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Self

import pytest

_GATEWAY_ROOT = Path(__file__).resolve().parents[2]
_RELEASE_VERSION_SCRIPT = _GATEWAY_ROOT / ".github" / "scripts" / "release_version.py"
_RELEASE_VERSION_SPEC = spec_from_file_location(
    "gateway_release_version",
    _RELEASE_VERSION_SCRIPT,
)
assert _RELEASE_VERSION_SPEC is not None
assert _RELEASE_VERSION_SPEC.loader is not None
_RELEASE_VERSION_MODULE = module_from_spec(_RELEASE_VERSION_SPEC)
_RELEASE_VERSION_SPEC.loader.exec_module(_RELEASE_VERSION_MODULE)


class ReleaseVersionCommandBuilder:
    """Build invocation arguments and a temporary project manifest for the CLI."""

    def __init__(self, project_root: Path) -> None:
        """Bind one isolated pyproject.toml path.

        Args:
            project_root: Temporary directory owned by the current test case.
        Return:
            None.
        """
        self._project_file = project_root / "pyproject.toml"

    def with_project_manifest(self, *, contents: str) -> Self:
        """Write the manifest content used by one command case.

        Args:
            contents: TOML document under test.
        Return:
            This builder for the current project fixture.
        """
        self._project_file.parent.mkdir(parents=True, exist_ok=True)
        self._project_file.write_text(contents, encoding="utf-8")
        return self

    def build(self, *, reference: str) -> list[str]:
        """Build the CLI arguments with the selected GitHub reference.

        Args:
            reference: GitHub ref passed to the version selector.
        Return:
            Arguments excluding the Python script path.
        """
        result = ["--reference", reference, "--project", str(self._project_file)]
        return result


def test_release_version_outputs_supported_references(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cases: dict[str, tuple[str, str, str]] = {
        "main_branch": (
            '[project]\nname = "sample"\nversion = "0.1.0"\n',
            "refs/heads/main",
            "version=0.1.0\n",
        ),
        "matching_version_tag": (
            '[project]\nname = "sample"\nversion = "0.1.0"\n',
            "refs/tags/v0.1.0",
            "version=0.1.0\n",
        ),
    }
    for case_name, (manifest, reference, expected_output) in cases.items():
        command = ReleaseVersionCommandBuilder(project_root=tmp_path / case_name)
        arguments = command.with_project_manifest(contents=manifest).build(reference=reference)
        exit_code = _RELEASE_VERSION_MODULE.main(argv=arguments)
        captured = capsys.readouterr()

        assert exit_code == 0, case_name
        assert captured.out == expected_output, case_name
        assert captured.err == "", case_name


def test_release_version_rejects_invalid_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    valid_manifest = '[project]\nname = "sample"\nversion = "0.1.0"\n'
    cases: dict[str, tuple[str, str, str]] = {
        "unsupported_branch": (
            valid_manifest,
            "refs/heads/release",
            "reference must be refs/heads/main or refs/tags/vMAJOR.MINOR.PATCH",
        ),
        "tag_version_mismatch": (
            valid_manifest,
            "refs/tags/v0.2.0",
            "tag version 0.2.0 does not match project.version 0.1.0",
        ),
        "leading_zero": (
            '[project]\nname = "sample"\nversion = "00.1.0"\n',
            "refs/heads/main",
            "project.version must be plain numeric SemVer MAJOR.MINOR.PATCH",
        ),
        "prerelease": (
            '[project]\nname = "sample"\nversion = "0.1.0-rc.1"\n',
            "refs/heads/main",
            "project.version must be plain numeric SemVer MAJOR.MINOR.PATCH",
        ),
        "build_metadata": (
            '[project]\nname = "sample"\nversion = "0.1.0+ci.1"\n',
            "refs/heads/main",
            "project.version must be plain numeric SemVer MAJOR.MINOR.PATCH",
        ),
        "missing_version": (
            '[project]\nname = "sample"\n',
            "refs/heads/main",
            "must define project.version as a string",
        ),
        "missing_project_table": (
            '[tool.sample]\nversion = "0.1.0"\n',
            "refs/heads/main",
            "must define a [project] table",
        ),
    }
    for case_name, (manifest, reference, expected_error) in cases.items():
        command = ReleaseVersionCommandBuilder(project_root=tmp_path / case_name)
        arguments = command.with_project_manifest(contents=manifest).build(reference=reference)
        with pytest.raises(SystemExit) as error:
            _RELEASE_VERSION_MODULE.main(argv=arguments)
        captured = capsys.readouterr()

        assert error.value.code == 2, case_name
        assert expected_error in captured.err, case_name
        assert captured.out == "", case_name
