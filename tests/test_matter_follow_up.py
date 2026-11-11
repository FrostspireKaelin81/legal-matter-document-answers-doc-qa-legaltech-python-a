from datetime import date

from matter_follow_up import decide_follow_up


def test_signed_delivery_schedules_review_three_days_before_deadline() -> None:
    decision = decide_follow_up(
        signed_delivered_on=date(2026, 9, 10),
        deadline=date(2026, 9, 20),
    )

    assert decision.status == "signed_delivered_follow_up_scheduled"
    assert decision.follow_up_on == date(2026, 9, 17)


def test_missing_signed_delivery_stays_actionable() -> None:
    decision = decide_follow_up(signed_delivered_on=None, deadline=date(2026, 9, 20))

    assert decision.status == "awaiting_signed_delivery"
    assert decision.follow_up_on == date(2026, 9, 20)
