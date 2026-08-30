from enum import StrEnum


class SendStatus(StrEnum):
    QUEUED = "queued"
    CLAIMING = "claiming"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    WARMING = "warming"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


def can_start_send(status: SendStatus) -> bool:
    return status is SendStatus.QUEUED


def can_mark_sent(status: SendStatus) -> bool:
    return status in {SendStatus.CLAIMING, SendStatus.SENDING}
