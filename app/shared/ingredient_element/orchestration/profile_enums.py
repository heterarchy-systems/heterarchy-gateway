"""Closed Profile vocabularies mirrored from Orchestration source contracts."""

from enum import StrEnum


class CliEngineEnum(StrEnum):
    """Supported local CLI execution engines."""

    CODEX = "codex"
    AGY = "agy"


class ProfileLifecycleStateEnum(StrEnum):
    """Durable Agent Profile lifecycle states."""

    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class ProfileProviderFamilyEnum(StrEnum):
    """Provider metadata values exposed by Agent Profile responses."""

    UNBOUND = "unbound"
    CHATGPT = "chatgpt"


class ProfileCreationOriginEnum(StrEnum):
    """Audit origins exposed by Agent Profile responses."""

    USER_MANUAL = "user_manual"
    AGENT_REQUEST = "agent_request"
    IMPORTED = "imported"
    SYSTEM_BOOTSTRAP = "system_bootstrap"


class ProfileMutationKindEnum(StrEnum):
    """Kinds returned in durable Profile mutation receipts."""

    CREATE = "create"
    UPDATE = "update"
    DISABLE = "disable"
    RETIRE = "retire"
