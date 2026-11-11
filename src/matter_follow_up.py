from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FollowUpDecision:
    status: str
    follow_up_on: date | None


def decide_follow_up(signed_delivered_on: date | None, deadline: date) -> FollowUpDecision:
    if signed_delivered_on is None:
        return FollowUpDecision("awaiting_signed_delivery", deadline)
    reminder = deadline.fromordinal(deadline.toordinal() - 3)
    return FollowUpDecision("signed_delivered_follow_up_scheduled", reminder)
