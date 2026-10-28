from datetime import date, timedelta

from tradeguard.risk import assess

TODAY = date(2026, 10, 27)


def _report(**overrides):
    payload = {
        "id": 1,
        "categories": ["fake_inquiry"],
        "incident_date": (TODAY - timedelta(days=30)).isoformat(),
        "created_at": (TODAY - timedelta(days=20)).isoformat(),
        "amount": 0,
        "currency": "USD",
        "chat_sha256": None,
        "credibility": 60,
    }
    payload.update(overrides)
    return payload


def test_no_reports_is_unknown():
    risk = assess([], today=TODAY)
    assert risk.level == "unknown"
    assert risk.score == 0


def test_single_report_cannot_be_high():
    risk = assess(
        [
            _report(
                categories=["no_delivery"],
                amount=8000,
                chat_sha256="abc",
                credibility=90,
            )
        ],
        today=TODAY,
    )
    assert risk.score <= 55
    assert risk.level in {"medium", "low", "watch"}


def test_multiple_reports_reach_high():
    reports = [
        _report(
            id=index,
            categories=["no_delivery"],
            amount=3000,
            chat_sha256="abc" if index == 1 else None,
            credibility=80,
        )
        for index in range(1, 4)
    ]
    risk = assess(reports, today=TODAY)
    assert risk.level == "high"
    assert risk.score >= 70
    assert any("3 条" in reason for reason in risk.reasons)


def test_old_records_score_lower_than_recent():
    old = assess([_report(incident_date=(TODAY - timedelta(days=800)).isoformat())], today=TODAY)
    recent = assess([_report()], today=TODAY)
    assert recent.score > old.score
