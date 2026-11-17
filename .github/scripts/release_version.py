"""Resolve the package version for a supported GitHub release reference."""

import argparse
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

_SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
_VERSION_TAG = re.compile(
    r"refs/tags/v(?P<version>(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*))\Z"
)


def _read_project_version(*, project_file: Path) -> str:
    """Read and validate the plain numeric project version from TOML.

    Args:
        project_file: Project manifest containing [project].version.
    Return:
        Plain numeric SemVer value.
    """
    try:
        with project_file.open("rb") as manifest_stream:
            manifest = tomllib.load(manifest_stream)
    except OSError as error:
        raise ValueError(f"cannot read project file '{project_file}': {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"cannot parse project file '{project_file}': {error}") from error

    project_metadata = manifest.get("project")
    if not isinstance(project_metadata, dict):
        raise ValueError(f"project file '{project_file}' must define a [project] table")

    version = project_metadata.get("version")
    if not isinstance(version, str):
        raise ValueError(f"project file '{project_file}' must define project.version as a string")
    if _SEMVER.fullmatch(version) is None:
        raise ValueError("project.version must be plain numeric SemVer MAJOR.MINOR.PATCH")

    result = version
    return result


def _version_for_reference(*, reference: str, project_version: str) -> str:
    """Validate the requested branch or version tag and choose its version.

    Args:
        reference: GitHub ref, restricted to main or a v-prefixed version tag.
        project_version: Validated project version from pyproject.toml.
    Return:
        Version to publish for the supported reference.
    """
    if reference == "refs/heads/main":
        result = project_version
        return result

    tag_match = _VERSION_TAG.fullmatch(reference)
    if tag_match is None:
        raise ValueError("reference must be refs/heads/main or refs/tags/vMAJOR.MINOR.PATCH")

    tag_version = tag_match.group("version")
    if tag_version != project_version:
        raise ValueError(
            f"tag version {tag_version} does not match project.version {project_version}"
        )

    result = tag_version
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Print one validated version assignment for GitHub Actions output.

    Args:
        argv: Optional command-line arguments, excluding the script name.
    Return:
        Zero after writing exactly one version assignment.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--project", required=True, type=Path)
    arguments = parser.parse_args(argv)

    try:
        project_version = _read_project_version(project_file=arguments.project)
        version = _version_for_reference(
            reference=arguments.reference,
            project_version=project_version,
        )
    except ValueError as error:
        parser.error(str(error))

    sys.stdout.write(f"version={version}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
