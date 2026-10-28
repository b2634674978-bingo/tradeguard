import csv
import io

import pytest

from tradeguard.database import Database


@pytest.fixture()
def db(temp_dir):
    return Database(temp_dir / "test.db")


def _seed_report(db, phone="+1 555 010 4477", company="NovaPeak Supplements LLC", **kwargs):
    return db.add_report(
        phones=[phone],
        contact_name=kwargs.pop("contact_name", "Mike R."),
        company=company,
        country="美国",
        categories=kwargs.pop("categories", ["free_samples"]),
        narrative="以采购为名索要免费样品，收到后失联。",
        source="manual",
        **kwargs,
    )


def test_add_and_search_exact(db):
    _seed_report(db)
    result = db.search("+1 555 010 4477")
    assert result["profiles"]
    profile = result["profiles"][0]
    assert profile["phone"] == "15550104477"
    assert profile["risk"]["score"] > 0
    assert profile["report_count"] == 1


def test_search_by_suffix_and_company(db):
    _seed_report(db)
    suffix = db.search("5550104477")
    assert any(profile["match_kind"] == "phone_exact" for profile in suffix["profiles"])

    name = db.search("NovaPeak")
    assert any(profile["match_kind"] == "text" for profile in name["profiles"])


def test_search_no_result(db):
    result = db.search("+44 7700 900999")
    assert result["profiles"] == []


def test_reports_and_stats(db):
    _seed_report(db)
    db.add_report(
        phones=["+44 7700 900123"],
        company="BrightLife Wholesale Ltd",
        categories=["quality"],
        amount=1200,
        currency="GBP",
        narrative="收到的货有近一半包装破损，对方拒绝退款。",
    )
    profiles, total = db.list_contacts()
    assert total == 2
    stats = db.stats()
    assert stats["total_reports"] == 2
    assert stats["total_phones"] == 2


def test_csv_export_and_import(db):
    _seed_report(db)
    exported = db.export_csv()
    assert "NovaPeak" in exported

    imported = db.import_csv(
        "号码,联系人,公司,国家,类型,金额,币种,发生日期,经过\n"
        "+44 7700 900456,James,PureForm,英国,付款凭证存疑,4600,GBP,2026-01-01,假水单要求放货\n"
    )
    assert imported["imported"] == 1
    assert db.quick_counts()["reports"] == 2


def test_delete(db):
    report_id = _seed_report(db)
    db.delete_report(report_id)
    assert db.quick_counts()["reports"] == 0


def test_ensure_seeded_only_once(temp_dir):
    db = Database(temp_dir / "seed.db")
    assert db.ensure_seeded() is True
    assert db.quick_counts()["reports"] == 9
    assert db.ensure_seeded() is False