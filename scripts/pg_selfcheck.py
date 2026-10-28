"""对真实 Postgres 做一次端到端自检（不需要 Streamlit）。

用法：
    set DATABASE_URL=postgresql://...        # Windows
    export DATABASE_URL=postgresql://...     # macOS / Linux
    python scripts/pg_selfcheck.py

可选：
    python scripts/pg_selfcheck.py "postgresql://..."   # 直接传连接串

脚本会：建表 -> 写入一条自检记录（含截图）-> 查询 -> 聚合 -> 导出 -> 清理，
最后打印 PASS/FAIL。自检记录使用固定号码 +19990000000，结束时删除，不污染数据。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradeguard.database import Database  # noqa: E402
from tradeguard.dbdriver import PSYCOPG_AVAILABLE, mask_url  # noqa: E402

SELFCHECK_PHONE = "+19990000000"


def main() -> int:
    url = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        print("FAIL: 没有 DATABASE_URL，也没有在命令行传入连接串。")
        return 2
    if not PSYCOPG_AVAILABLE:
        print("FAIL: 未安装 psycopg，请先执行 pip install -r requirements.txt。")
        return 2

    print(f"连接目标：{mask_url(url)}")
    db = Database(database_url=url)
    print(f"引擎：{db.engine} · {db.location}")

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))
        print(f"  [{'OK' if ok else 'FAIL'}] {name}{(' · ' + detail) if detail else ''}")

    # 1. 建表
    tables = _table_names(db)
    expected = {"reports", "report_phones", "report_images", "appeals", "meta"}
    check("建表完成", expected.issubset(tables), ", ".join(sorted(tables)))

    # 2. 写入（自增主键 RETURNING 是否正常）
    report_id = db.add_report(
        phones=[SELFCHECK_PHONE],
        contact_name="SelfCheck",
        company="TradeGuard SelfCheck",
        country="测试",
        categories=["other"],
        narrative="这是自检记录，用于验证 Postgres 写入与自增主键，稍后自动删除。",
        amount="1",
        status="pending",
    )
    check("写入举报并回填主键", isinstance(report_id, int) and report_id > 0, f"id={report_id}")

    # 3. 二进制截图（BYTEA）
    saved = db.add_report_images(
        report_id,
        [{"data": b"\xff\xd8\xff\xe0selfcheck", "mime": "image/jpeg", "is_public": True}],
    )
    images = db.get_report_images(report_id)
    check(
        "截图写入并读回",
        saved == 1 and len(images) == 1 and images[0]["data"].startswith(b"\xff\xd8"),
        f"{len(images)} 张 / {images[0]['size'] if images else 0} B",
    )

    # 4. 待审核队列（含 upsert / 冲突子句路径）
    pending = db.list_pending_reports(50)
    check("待审核队列可读", any(item["id"] == report_id for item in pending), f"{len(pending)} 条")

    # 5. 审核通过后进入查询与聚合
    db.set_status(report_id, "approved")
    profile_hit = db.search("9990000000")["profiles"]
    check("号码查询命中", bool(profile_hit), f"{len(profile_hit)} 个档案")

    db.add_appeal("自检申诉，稍后清理。", report_id=report_id)
    check("申诉写入", len(db.list_appeals(200)) >= 1)

    stats = db.stats()
    check("看板聚合", stats["total_reports"] >= 1, f"total={stats['total_reports']}")

    csv_text = db.export_csv()
    check("CSV 导出", len(csv_text) > 100, f"{len(csv_text)} 字符")

    # 6. 清理
    db.delete_report(report_id)
    gone = db.get_report(report_id) is None
    check("删除自检记录", gone)

    failed = [name for name, ok, _ in checks if not ok]
    print()
    if failed:
        print(f"FAIL: {len(failed)} 项未通过 -> {', '.join(failed)}")
        return 1
    print(f"PASS: {len(checks)} 项全部通过，Postgres 持久化链路可用。")
    return 0


def _table_names(db: Database) -> set[str]:
    with db._connect() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        ).fetchall()
    names = set()
    for row in rows:
        names.add(row["table_name"] if hasattr(row, "keys") else row[0])
    return names


if __name__ == "__main__":
    raise SystemExit(main())
