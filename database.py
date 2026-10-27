"""本地 SQLite 数据层：举报记录、号码索引、查询聚合、统计与导入导出。"""

from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from . import config
from .constants import (
    CATEGORIES,
    CATEGORY_BY_LABEL,
    CATEGORY_LABELS,
    REPORT_STATUS,
    SOURCES,
)
from .normalize import (
    company_key,
    digits_only,
    format_phone,
    mask_phone,
    normalize_phone,
    phone_variants,
    pick_display_name,
)
from .risk import assess
from .seed import demo_reports

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    incident_date TEXT,
    contact_name TEXT NOT NULL DEFAULT '',
    company TEXT NOT NULL DEFAULT '',
    country TEXT NOT NULL DEFAULT '',
    categories TEXT NOT NULL,
    amount REAL,
    currency TEXT NOT NULL DEFAULT 'USD',
    narrative TEXT NOT NULL DEFAULT '',
    evidence TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    chat_filename TEXT,
    chat_sha256 TEXT,
    chat_message_count INTEGER,
    credibility INTEGER NOT NULL DEFAULT 60,
    status TEXT NOT NULL DEFAULT 'approved',
    reporter_hash TEXT
);

CREATE TABLE IF NOT EXISTS report_phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    phone_norm TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'subject',
    UNIQUE (report_id, phone_norm),
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_report_phones_norm ON report_phones(phone_norm);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);

CREATE TABLE IF NOT EXISTS appeals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER,
    phone_norm TEXT,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat(timespec="seconds")


def _clean_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip().replace("/", "-")
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date().isoformat()
    except ValueError:
        return None


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else config.DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    # ------------------------------------------------------------ 连接与建表

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(str(self.path), timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def ensure_seeded(self) -> bool:
        """首次运行自动载入演示数据；用户清空后不再自动恢复。"""
        with self._connect() as conn:
            seeded = conn.execute("SELECT value FROM meta WHERE key = 'demo_seeded'").fetchone()
            if seeded:
                return False
            count = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
            inserted = False
            if count == 0:
                for item in demo_reports():
                    payload = dict(item)
                    payload.setdefault("source", "demo")
                    self._insert_report(conn, **payload)
                inserted = True
            conn.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES ('demo_seeded', '1')"
            )
            return inserted

    # ------------------------------------------------------------ 写入

    def add_report(
        self,
        *,
        phones: Iterable[str] | None = None,
        contact_name: str = "",
        company: str = "",
        country: str = "",
        categories: Iterable[str] | None = None,
        amount: float | str | None = None,
        currency: str = "USD",
        incident_date: Any = None,
        narrative: str = "",
        evidence: str = "",
        source: str = "manual",
        chat_filename: str | None = None,
        chat_sha256: str | None = None,
        chat_message_count: int | None = None,
        credibility: int = 60,
        status: str = "approved",
        created_at: str | None = None,
    ) -> int:
        with self._connect() as conn:
            return self._insert_report(
                conn,
                phones=phones,
                contact_name=contact_name,
                company=company,
                country=country,
                categories=categories,
                amount=amount,
                currency=currency,
                incident_date=incident_date,
                narrative=narrative,
                evidence=evidence,
                source=source,
                chat_filename=chat_filename,
                chat_sha256=chat_sha256,
                chat_message_count=chat_message_count,
                credibility=credibility,
                status=status,
                created_at=created_at,
            )

    def _insert_report(self, conn: sqlite3.Connection, **kwargs: Any) -> int:
        phones: list[str] = []
        for raw in kwargs.get("phones") or []:
            norm = normalize_phone(raw)
            if norm and norm not in phones:
                phones.append(norm)

        contact_name = (kwargs.get("contact_name") or "").strip()[:120]
        company = (kwargs.get("company") or "").strip()[:160]
        country = (kwargs.get("country") or "").strip()[:60]

        if not phones and not contact_name and not company:
            raise ValueError("至少填写电话号码、公司名或联系人之一。")

        categories: list[str] = []
        for key in kwargs.get("categories") or []:
            if key in CATEGORIES and key not in categories:
                categories.append(key)
        if not categories:
            categories = ["other"]

        amount = kwargs.get("amount")
        amount_value: float | None = None
        if amount not in (None, "", 0):
            cleaned = re.sub(r"[^0-9.\-]", "", str(amount))
            try:
                amount_value = float(cleaned) if cleaned not in {"", "-", "."} else None
            except ValueError:
                amount_value = None
        if amount_value is not None and amount_value < 0:
            amount_value = None

        status = kwargs.get("status") if kwargs.get("status") in REPORT_STATUS else "approved"
        source = kwargs.get("source") if kwargs.get("source") in SOURCES else "manual"
        credibility = max(0, min(100, int(kwargs.get("credibility") or 60)))
        created_at = kwargs.get("created_at") or _now()

        cursor = conn.execute(
            """
            INSERT INTO reports (
                created_at, incident_date, contact_name, company, country, categories,
                amount, currency, narrative, evidence, source, chat_filename,
                chat_sha256, chat_message_count, credibility, status, reporter_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                _clean_date(kwargs.get("incident_date")),
                contact_name,
                company,
                country,
                json.dumps(categories, ensure_ascii=False),
                amount_value,
                (kwargs.get("currency") or "USD").strip()[:10] or "USD",
                (kwargs.get("narrative") or "").strip()[:5000],
                (kwargs.get("evidence") or "").strip()[:5000],
                source,
                (kwargs.get("chat_filename") or None),
                (kwargs.get("chat_sha256") or None),
                kwargs.get("chat_message_count"),
                credibility,
                status,
                None,
            ),
        )
        report_id = int(cursor.lastrowid)
        for norm in phones:
            conn.execute(
                "INSERT OR IGNORE INTO report_phones (report_id, phone_norm, role) VALUES (?, ?, 'subject')",
                (report_id, norm),
            )
        return report_id

    def set_status(self, report_id: int, status: str) -> None:
        if status not in REPORT_STATUS:
            raise ValueError("未知状态")
        with self._connect() as conn:
            conn.execute("UPDATE reports SET status = ? WHERE id = ?", (status, report_id))

    def delete_report(self, report_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM appeals WHERE report_id = ?", (report_id,))
            conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))

    def delete_demo(self) -> int:
        with self._connect() as conn:
            ids = [row["id"] for row in conn.execute("SELECT id FROM reports WHERE source = 'demo'")]
            if ids:
                qmarks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM appeals WHERE report_id IN ({qmarks})", ids)
                conn.execute(f"DELETE FROM reports WHERE id IN ({qmarks})", ids)
            return len(ids)

    def clear_all(self) -> int:
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
            conn.execute("DELETE FROM report_phones")
            conn.execute("DELETE FROM appeals")
            conn.execute("DELETE FROM reports")
            conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('demo_seeded', '1')")
            return int(count)

    def add_appeal(self, message: str, *, report_id: int | None = None, phone_norm: str | None = None) -> int:
        text = (message or "").strip()
        if len(text) < 5:
            raise ValueError("申诉说明至少写 5 个字。")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO appeals (report_id, phone_norm, message, created_at, status) VALUES (?, ?, ?, ?, 'open')",
                (report_id, phone_norm, text[:2000], _now()),
            )
            return int(cursor.lastrowid)

    # ------------------------------------------------------------ 读取

    def _phones_map(self, conn: sqlite3.Connection, report_ids: list[int]) -> dict[int, list[str]]:
        if not report_ids:
            return {}
        qmarks = ",".join("?" for _ in report_ids)
        rows = conn.execute(
            f"SELECT report_id, phone_norm FROM report_phones WHERE report_id IN ({qmarks}) ORDER BY id",
            report_ids,
        ).fetchall()
        mapping: dict[int, list[str]] = {}
        for row in rows:
            mapping.setdefault(row["report_id"], []).append(row["phone_norm"])
        return mapping

    @staticmethod
    def _row_to_report(row: sqlite3.Row, phones: dict[int, list[str]]) -> dict[str, Any]:
        try:
            categories = json.loads(row["categories"] or "[]")
        except (TypeError, json.JSONDecodeError):
            categories = ["other"]
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "incident_date": row["incident_date"],
            "contact_name": row["contact_name"],
            "company": row["company"],
            "country": row["country"],
            "categories": categories,
            "category_labels": [CATEGORY_LABELS.get(c, c) for c in categories],
            "amount": row["amount"],
            "currency": row["currency"],
            "narrative": row["narrative"],
            "evidence": row["evidence"],
            "source": row["source"],
            "source_label": SOURCES.get(row["source"], row["source"]),
            "chat_filename": row["chat_filename"],
            "chat_sha256": row["chat_sha256"],
            "chat_message_count": row["chat_message_count"],
            "credibility": row["credibility"],
            "status": row["status"],
            "status_label": REPORT_STATUS.get(row["status"], row["status"]),
            "phones": phones.get(row["id"], []),
            "date": row["incident_date"] or row["created_at"][:10],
        }

    def get_report(self, report_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
            if not row:
                return None
            phones = self._phones_map(conn, [report_id])
            return self._row_to_report(row, phones)

    def _reports_for_phone(self, conn: sqlite3.Connection, phone_norm: str) -> list[dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT DISTINCT r.* FROM reports r
            JOIN report_phones rp ON rp.report_id = r.id
            WHERE rp.phone_norm = ? AND r.status = 'approved'
            ORDER BY COALESCE(r.incident_date, r.created_at) DESC
            """,
            (phone_norm,),
        ).fetchall()
        phones = self._phones_map(conn, [row["id"] for row in rows])
        return [self._row_to_report(row, phones) for row in rows]

    def _profile(
        self,
        phone_norm: str,
        reports: list[dict[str, Any]],
        match_reason: str = "",
        *,
        exact: bool = True,
        match_kind: str = "text",
    ) -> dict[str, Any]:
        risk = assess(reports)
        names = Counter(r["contact_name"] for r in reports if r["contact_name"])
        companies = Counter(r["company"] for r in reports if r["company"])
        countries = Counter(r["country"] for r in reports if r["country"])
        categories: Counter[str] = Counter()
        for report in reports:
            for key in report["categories"]:
                categories[key] += 1
        dates = [r["incident_date"] or r["created_at"][:10] for r in reports]
        amount_total = sum(r["amount"] or 0 for r in reports)
        currencies = sorted({r["currency"] for r in reports if r["amount"]})

        has_phone = bool(phone_norm) and not phone_norm.startswith("__")
        name = names.most_common(1)[0][0] if names else ""
        company = companies.most_common(1)[0][0] if companies else ""
        display = pick_display_name(name, company, phone_norm if has_phone else None)

        return {
            "phone": phone_norm if has_phone else "",
            "display_phone": format_phone(phone_norm) if has_phone else "",
            "masked_phone": mask_phone(phone_norm) if has_phone else "",
            "display_name": display,
            "contact_name": name,
            "company": company,
            "country": countries.most_common(1)[0][0] if countries else "",
            "report_count": len(reports),
            "risk": risk.to_dict(),
            "categories": [
                {
                    "key": key,
                    "label": CATEGORY_LABELS.get(key, key),
                    "count": count,
                }
                for key, count in categories.most_common()
            ],
            "first_seen": min(dates) if dates else "",
            "last_seen": max(dates) if dates else "",
            "amount_total": amount_total,
            "currencies": currencies,
            "reports": reports,
            "has_demo": any(r["source"] == "demo" for r in reports),
            "match_reason": match_reason,
            "match_kind": match_kind,
            "exact": exact,
        }

    def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        q = (query or "").strip()
        result: dict[str, Any] = {
            "query": q,
            "profiles": [],
            "text_reports": [],
            "phone_input": None,
            "notes": [],
        }
        if not q:
            return result

        digits = digits_only(q)
        profiles: dict[str, dict[str, Any]] = {}
        exact_norms: set[str] = set()

        if 7 <= len(digits) <= 15:
            result["phone_input"] = digits
            with self._connect() as conn:
                for variant in phone_variants(q):
                    rows = conn.execute(
                        """
                        SELECT DISTINCT rp.phone_norm FROM report_phones rp
                        JOIN reports r ON r.id = rp.report_id
                        WHERE rp.phone_norm = ? AND r.status = 'approved'
                        """,
                        (variant,),
                    ).fetchall()
                    exact_norms.update(row["phone_norm"] for row in rows)

                for norm in sorted(exact_norms):
                    reports = self._reports_for_phone(conn, norm)
                    if reports:
                        profiles[norm] = self._profile(
                            norm, reports, "号码完全匹配", exact=True, match_kind="phone_exact"
                        )

                if not exact_norms:
                    suffix = digits[-8:] if len(digits) >= 8 else digits
                    if len(suffix) >= 7:
                        rows = conn.execute(
                            """
                            SELECT DISTINCT rp.phone_norm FROM report_phones rp
                            JOIN reports r ON r.id = rp.report_id
                            WHERE rp.phone_norm LIKE ? AND r.status = 'approved'
                            LIMIT 30
                            """,
                            (f"%{suffix}",),
                        ).fetchall()
                        for row in rows:
                            norm = row["phone_norm"]
                            if norm in profiles:
                                continue
                            reports = self._reports_for_phone(conn, norm)
                            if reports:
                                profiles[norm] = self._profile(
                                    norm,
                                    reports,
                                    "号码尾号匹配（可能是同一人换号）",
                                    exact=False,
                                    match_kind="phone_suffix",
                                )
                    else:
                        result["notes"].append("至少输入 7 位数字，才能做尾号匹配。")
        elif digits and len(digits) < 7:
            result["notes"].append("号码位数太少，请输入完整号码或至少 7 位数字。")

        with self._connect() as conn:
            like = f"%{q.lower()}%"
            text_rows = conn.execute(
                """
                SELECT * FROM reports
                WHERE status = 'approved'
                  AND (lower(company) LIKE ? OR lower(contact_name) LIKE ? OR lower(narrative) LIKE ?)
                ORDER BY COALESCE(incident_date, created_at) DESC
                LIMIT 50
                """,
                (like, like, like),
            ).fetchall()
            text_reports: list[dict[str, Any]] = []
            if text_rows:
                phones = self._phones_map(conn, [row["id"] for row in text_rows])
                text_reports = [self._row_to_report(row, phones) for row in text_rows]
                text_phones = {
                    report["phones"][0] for report in text_reports if report["phones"]
                }
                for norm in text_phones:
                    if norm in profiles:
                        continue
                    reports = self._reports_for_phone(conn, norm)
                    if reports:
                        profiles[norm] = self._profile(
                            norm,
                            reports,
                            "公司 / 联系人名称匹配",
                            exact=False,
                            match_kind="text",
                        )
                result["text_reports"] = [
                    report for report in text_reports if not report["phones"]
                ][:limit]

        def sort_key(profile: dict[str, Any]):
            return (
                0 if profile["exact"] else 1,
                -profile["risk"]["score"],
                profile["last_seen"] or "",
            )

        result["profiles"] = sorted(profiles.values(), key=sort_key)[:limit]
        return result

    def _all_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reports
                WHERE status = 'approved'
                ORDER BY COALESCE(incident_date, created_at) DESC
                """
            ).fetchall()
            phones = self._phones_map(conn, [row["id"] for row in rows])
            groups: dict[str, list[dict[str, Any]]] = {}
            for row in rows:
                report = self._row_to_report(row, phones)
                key = report["phones"][0] if report["phones"] else f"__report_{report['id']}"
                groups.setdefault(key, []).append(report)
            return [self._profile(key, reports) for key, reports in groups.items()]

    def list_contacts(
        self,
        *,
        keyword: str = "",
        category: str = "",
        level: str = "",
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], int]:
        profiles = self._all_profiles()
        keyword = (keyword or "").strip()
        if len(digits_only(keyword)) >= 7:
            keyword = digits_only(keyword)
        keyword = keyword.lower()

        def matches(profile: dict[str, Any]) -> bool:
            if keyword:
                haystack = " ".join(
                    [
                        profile["phone"],
                        profile["contact_name"],
                        profile["company"],
                        profile["country"],
                        " ".join(c["label"] for c in profile["categories"]),
                    ]
                ).lower()
                if keyword not in haystack:
                    return False
            if category and category not in {c["key"] for c in profile["categories"]}:
                return False
            if level and profile["risk"]["level"] != level:
                return False
            return True

        filtered = [profile for profile in profiles if matches(profile)]
        filtered.sort(key=lambda p: p["last_seen"] or "", reverse=True)
        filtered.sort(key=lambda p: p["risk"]["score"], reverse=True)
        return filtered[:limit], len(filtered)

    def recent_reports(self, limit: int = 8) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reports
                WHERE status = 'approved'
                ORDER BY COALESCE(incident_date, created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            phones = self._phones_map(conn, [row["id"] for row in rows])
            return [self._row_to_report(row, phones) for row in rows]

    def stats(self) -> dict[str, Any]:
        profiles = self._all_profiles()
        today = date.today()
        month_prefix = today.strftime("%Y-%m")
        months = []
        cursor = today.replace(day=1)
        for _ in range(6):
            months.append(cursor.strftime("%Y-%m"))
            cursor = (cursor - timedelta(days=1)).replace(day=1)
        months.reverse()

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reports WHERE status = 'approved' ORDER BY created_at"
            ).fetchall()
            reports = [dict(row) for row in rows]
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM reports WHERE status = 'pending'"
            ).fetchone()["n"]
            appeals = conn.execute("SELECT COUNT(*) AS n FROM appeals").fetchone()["n"]

        category_counter: Counter[str] = Counter()
        country_counter: Counter[str] = Counter()
        monthly_counter: Counter[str] = Counter({month: 0 for month in months})
        currency_totals: Counter[str] = Counter()
        demo_count = 0
        this_month = 0
        for report in reports:
            try:
                categories = json.loads(report["categories"] or "[]")
            except (TypeError, json.JSONDecodeError):
                categories = []
            for key in categories:
                category_counter[key] += 1
            if report["country"]:
                country_counter[report["country"]] += 1
            date_key = (report["incident_date"] or report["created_at"])[:7]
            if date_key in monthly_counter:
                monthly_counter[date_key] += 1
            if report["source"] == "demo":
                demo_count += 1
            if report["created_at"][:7] == month_prefix:
                this_month += 1
            if report["amount"]:
                currency_totals[report["currency"] or "其他"] += float(report["amount"])

        phone_profiles = [p for p in profiles if p["phone"]]
        return {
            "total_reports": len(reports),
            "total_phones": len(phone_profiles),
            "high_risk": sum(1 for p in profiles if p["risk"]["level"] == "high"),
            "medium_risk": sum(1 for p in profiles if p["risk"]["level"] == "medium"),
            "this_month": this_month,
            "pending": pending,
            "appeals": appeals,
            "demo_count": demo_count,
            "categories": category_counter,
            "countries": country_counter.most_common(6),
            "months": months,
            "monthly": [monthly_counter[month] for month in months],
            "currency_totals": dict(currency_totals),
        }

    # ------------------------------------------------------------ 导入 / 导出

    def export_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["记录ID", "号码", "联系人", "公司", "国家", "类型", "金额", "币种",
             "发生日期", "经过", "证据", "来源", "状态", "录入时间"]
        )
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM reports ORDER BY COALESCE(incident_date, created_at) DESC"
            ).fetchall()
            phones = self._phones_map(conn, [row["id"] for row in rows])
            for row in rows:
                report = self._row_to_report(row, phones)
                writer.writerow(
                    [
                        report["id"],
                        "；".join(format_phone(p) for p in report["phones"]),
                        report["contact_name"],
                        report["company"],
                        report["country"],
                        "；".join(report["category_labels"]),
                        report["amount"] or "",
                        report["currency"],
                        report["incident_date"] or "",
                        report["narrative"],
                        report["evidence"],
                        report["source_label"],
                        report["status_label"],
                        report["created_at"],
                    ]
                )
        return "\ufeff" + buffer.getvalue()

    def template_csv(self) -> str:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["号码", "联系人", "公司", "国家", "类型", "金额", "币种", "发生日期", "经过", "证据"]
        )
        writer.writerow(
            [
                "+1 555 010 0000",
                "示例联系人",
                "示例公司（请替换）",
                "美国",
                "样品费未付；无效询盘",
                "0",
                "USD",
                "2026-01-01",
                "填写至少 10 个字的事情经过",
                "聊天里的关键原话（可选）",
            ]
        )
        return "\ufeff" + buffer.getvalue()

    def import_csv(self, text: str) -> dict[str, Any]:
        raw = (text or "").lstrip("\ufeff")
        reader = csv.DictReader(io.StringIO(raw))
        imported = 0
        skipped = 0
        errors: list[str] = []

        aliases = {
            "phone": "phone", "phones": "phone", "号码": "phone", "电话": "phone",
            "contact": "contact_name", "contact_name": "contact_name", "联系人": "contact_name",
            "company": "company", "公司": "company",
            "country": "country", "国家": "country",
            "categories": "categories", "category": "categories", "类型": "categories", "问题类型": "categories", "骗术类型": "categories",
            "amount": "amount", "金额": "amount",
            "currency": "currency", "币种": "currency",
            "incident_date": "incident_date", "date": "incident_date", "发生日期": "incident_date",
            "narrative": "narrative", "notes": "narrative", "经过": "narrative", "描述": "narrative",
            "evidence": "evidence", "证据": "evidence",
        }

        for index, row in enumerate(reader, start=2):
            if imported + skipped >= 500:
                errors.append("单次最多导入 500 行，剩余行已忽略。")
                break
            if not any((value or "").strip() for value in row.values()):
                continue
            data: dict[str, str] = {}
            for key, value in row.items():
                if key is None:
                    continue
                mapped = aliases.get(key.strip().lower())
                if mapped:
                    data[mapped] = (value or "").strip()
            phone_raw = data.get("phone", "")
            phone_parts = [part for part in re.split(r"[;；,，|]", phone_raw) if part.strip()]
            categories: list[str] = []
            raw_categories = data.get("categories", "").strip()
            if raw_categories in CATEGORIES:
                categories = [raw_categories]
            elif raw_categories in CATEGORY_BY_LABEL:
                categories = [CATEGORY_BY_LABEL[raw_categories]]
            else:
                for part in re.split(r"[;；,，/、|]", raw_categories):
                    part = part.strip()
                    if not part:
                        continue
                    if part in CATEGORIES:
                        categories.append(part)
                    elif part in CATEGORY_BY_LABEL:
                        categories.append(CATEGORY_BY_LABEL[part])
            try:
                self.add_report(
                    phones=phone_parts,
                    contact_name=data.get("contact_name", ""),
                    company=data.get("company", ""),
                    country=data.get("country", ""),
                    categories=categories or ["other"],
                    amount=data.get("amount", "") or None,
                    currency=data.get("currency", "USD") or "USD",
                    incident_date=data.get("incident_date") or None,
                    narrative=data.get("narrative", ""),
                    evidence=data.get("evidence", ""),
                    source="csv_import",
                )
                imported += 1
            except Exception as exc:  # noqa: BLE001 - 汇总给用户看
                skipped += 1
                errors.append(f"第 {index} 行：{exc}")

        return {"imported": imported, "skipped": skipped, "errors": errors[:10]}

    def backup_bytes(self) -> bytes:
        return self.path.read_bytes()

    def quick_counts(self) -> dict[str, int]:
        with self._connect() as conn:
            reports = conn.execute("SELECT COUNT(*) AS n FROM reports").fetchone()["n"]
            phones = conn.execute("SELECT COUNT(DISTINCT phone_norm) AS n FROM report_phones").fetchone()["n"]
            pending = conn.execute(
                "SELECT COUNT(*) AS n FROM reports WHERE status = 'pending'"
            ).fetchone()["n"]
        return {"reports": int(reports), "phones": int(phones), "pending": int(pending)}

    def list_appeals(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM appeals ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def list_pending_reports(self, limit: int = 20) -> list[dict[str, Any]]:
        """列出所有待审核的举报"""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT r.*, GROUP_CONCAT(rp.phone_norm, ', ') as phones
                FROM reports r
                LEFT JOIN report_phones rp ON r.id = rp.report_id
                WHERE r.status = 'pending'
                GROUP BY r.id
                ORDER BY r.created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]
