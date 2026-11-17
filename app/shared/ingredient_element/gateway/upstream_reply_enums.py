"""Gateway-owned distinctions between typed upstream response contracts."""

from enum import StrEnum


class UpstreamReplyKind(StrEnum):
    RESULT = "result"
    ERROR = "error"
