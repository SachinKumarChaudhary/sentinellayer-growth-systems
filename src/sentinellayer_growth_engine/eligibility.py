from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LeadEligibility:
    suppressed: bool
    replied: bool
    campaign_active: bool
    mailbox_active: bool
    mailbox_health_ok: bool
    due: bool
    within_daily_limit: bool

    @property
    def allowed(self) -> bool:
        return (
            not self.suppressed
            and not self.replied
            and self.campaign_active
            and self.mailbox_active
            and self.mailbox_health_ok
            and self.due
            and self.within_daily_limit
        )


def is_due(scheduled_at: datetime, now: datetime) -> bool:
    return scheduled_at <= now
