"""Closed principal identities carried by Orchestration execution contracts."""

from enum import StrEnum


class PrincipalKindEnum(StrEnum):
    """Authenticated principal kinds supported by Orchestration wire identities."""

    TRUSTED_STDIO = "trusted_stdio"
    DIRECT_TOKEN = "direct_token"  # noqa: S105 - source principal kind, not a credential.
    OAUTH_GRANT = "oauth_grant"
