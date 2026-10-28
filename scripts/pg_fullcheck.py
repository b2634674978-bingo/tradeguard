"""在真实 Postgres 上把 Database 的每个公开方法跑一遍。

自检脚本 pg_selfcheck.py 只覆盖 9 个关键路径；页面里还用到 list_contacts、
recent_reports、stats、import_csv、set_status、delete_report 等，这些如果含
SQLite 专有语法，只有真库能暴露。脚本结束后清空本次写入的数据。

用法：
    python scripts/pg_fullcheck.py "postgresql://..."
    DATABASE_URL=... python scripts/pg_fullcheck.py
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradeguard.database import Database  # noqa: E402
from tradeguard.dbdriver import mask_url  # noqa: E402

PREFIX = "PGCHK"


def main() -> int:
    url = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        print("FAIL: 缺少 DATABASE_URL")
        return 2

    print(f"目标：{mask_url(url)}")
    db = Database(database_url=url)
    print(f"引擎：{db.engine} · {db.location}\n")

    results: list[tuple[str, bool, str]] = []

    def run(name: str, fn):
        try:
            value = fn()
            results.append((name, True, ""))
            brief = repr(value)
            print(f"  [OK]   {name} -> {brief[:110]}")
            return value
        except Exception as exc:  # noqa: BLE001
            results.append((name, False, f"{type(exc).__name__}: {exc}"))
            print(f"  [FAIL] {name} -> {type(exc).__name__}: {str(exc)[:160]}")
            return None

    made_ids: list[int] = []

    # ---------------- 写入类 ----------------
    def do_add():
        rid = db.add_report(
            phones=[f"+1 415 555 01{i:02d}" for i in range(3)],
            contact_name=f"{PREFIX} Buyer",
            company=f"{PREFIX} Trading LLC",
            country="US",
            categories=["sample_unpaid", "fake_rfq"],
            narrative=f"{PREFIX} 覆盖测试用的样本描述，包含英文关键字 sample fee。",
            amount="2400",
            currency="USD",
            incident_date="2026-09-30",
            status="pending",
            publish_screenshots=True,
        )
        made_ids.append(rid)
        return rid

    rid1 = run("add_report(pending)", do_add)

    def do_add2():
        rid = db.add_report(
            phones=["+86 138 0000 2222"],
            contact_name=f"{PREFIX} Second",
            company=f"{PREFIX} Import Co",
            categories=["other"],
            narrative=f"{PREFIX} 第二条记录。",
            status="pending",
        )
        made_ids.append(rid)
        return rid

    rid2 = run("add_report(second)", do_add2)

    run("add_report_images", lambda: db.add_report_images(
        rid1, [
            {"data": b"\xff\xd8PGCHK-A", "mime": "image/jpeg", "is_public": True},
            {"data": b"\xff\xd8PGCHK-B", "mime": "image/png", "is_public": False},
        ]
    ))

    run("get_report_images", lambda: len(db.get_report_images(rid1)))
    run("get_report", lambda: (db.get_report(rid1) or {}).get("company"))
    run("list_pending_reports", lambda: len(db.list_pending_reports()))

    # ---------------- 审核动作 ----------------
    run("set_status(approved)", lambda: db.set_status(rid1, "approved"))
    run("set_status(approved)#2", lambda: db.set_status(rid2, "approved"))

    # ---------------- 读类 ----------------
    run("search(phone)", lambda: len(db.search("4155550101")["profiles"]))
    run("search(suffix)", lambda: len(db.search("415555010")["profiles"]))
    run("search(text)", lambda: len(db.search(PREFIX)["text_reports"]))
    run("list_contacts", lambda: (lambda r: (len(r[0]), r[1]))(db.list_contacts(limit=10)))
    run("recent_reports", lambda: len(db.recent_reports(limit=5)))
    run("stats", lambda: db.stats())
    run("quick_counts", lambda: db.quick_counts())
    run("export_rows", lambda: len(db.export_rows()))
    run("export_csv", lambda: len(db.export_csv()))
    run("template_csv", lambda: len(db.template_csv()))
    run("list_appeals", lambda: len(db.list_appeals()))

    # ---------------- 申诉 ----------------
    run("add_appeal", lambda: db.add_appeal(f"{PREFIX} 申诉内容，已付款，请复核。", report_id=rid1))

    # ---------------- CSV 导入（覆盖解析与写入分支） ----------------
    csv_text = (
        "phone,contact_name,company,country,categories,narrative,amount,currency,incident_date\n"
        f"+1 415 555 0199,{PREFIX} Imported,{PREFIX} Imported Co,US,sample_unpaid,"
        f"{PREFIX} 导入测试,100,USD,2026-08-01\n"
    )

    run("import_csv", lambda: db.import_csv(csv_text))

    # ---------------- 删除 ----------------
    def do_delete_one():
        return db.delete_report(rid2)

    run("delete_report", do_delete_one)

    def do_cleanup():
        # 按前缀清理本次脚本写入的所有记录（含 import_csv 生成的）
        candidates: dict[int, str] = {}
        for report in db.recent_reports(limit=500):
            candidates[report["id"]] = f"{report.get('company') or ''} {report.get('contact_name') or ''}"
        for report in db.list_pending_reports():
            candidates[report["id"]] = f"{report.get('company') or ''} {report.get('contact_name') or ''}"
        for profile in db.search(PREFIX)["profiles"]:
            for report in profile["reports"]:
                candidates[report["id"]] = f"{report.get('company') or ''} {report.get('contact_name') or ''}"
        removed = 0
        for report_id, label in candidates.items():
            if PREFIX in label:
                db.delete_report(report_id)
                removed += 1
        return removed

    run("cleanup", do_cleanup)
    run("quick_counts(final)", lambda: db.quick_counts())

    failed = [name for name, ok, _ in results if not ok]
    print()
    if failed:
        print(f"FAIL: {len(failed)} 项未通过 -> {', '.join(failed)}")
        return 1
    print(f"PASS: {len(results)} 项全部通过，Postgres 全方法可用。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
