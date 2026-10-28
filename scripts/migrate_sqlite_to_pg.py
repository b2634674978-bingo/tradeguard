"""把本地 SQLite 的存量数据搬到 Postgres。

用法：
    # 1) 先看会搬多少（默认 dry-run，不写库）
    python scripts/migrate_sqlite_to_pg.py

    # 2) 确认无误后真正写入
    python scripts/migrate_sqlite_to_pg.py --apply

环境变量：
    DATABASE_URL           目标 Postgres 连接串（必填）
    TRADEGUARD_SRC_DB      源 SQLite 路径，默认 ./data/tradeguard.db

说明：
- 记录 id 会重新分配，脚本会打印旧 id -> 新 id 的映射；
- 截图（BLOB/BYTEA）二进制原样搬运，不做二次压缩；
- 目标库若已有相同号码的记录不会去重（本脚本只负责搬运，不做合并）；
- 重复执行会产生重复数据，建议只跑一次。迁移前请先备份源库。
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tradeguard import config  # noqa: E402
from tradeguard.database import Database  # noqa: E402
from tradeguard.dbdriver import mask_url  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="SQLite -> Postgres 数据迁移")
    parser.add_argument("--apply", action="store_true", help="真正写入目标库（默认只统计）")
    parser.add_argument("--src", default=os.environ.get("TRADEGUARD_SRC_DB", str(config.DB_PATH)))
    parser.add_argument("--url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args()

    src_path = Path(args.src)
    if not src_path.is_file():
        print(f"FAIL: 源库不存在：{src_path}")
        return 2
    if not args.url:
        print("FAIL: 请设置 DATABASE_URL")
        return 2

    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row

    reports = src.execute("SELECT * FROM reports ORDER BY id").fetchall()
    image_count = src.execute("SELECT COUNT(*) AS n FROM report_images").fetchone()["n"]
    phone_count = src.execute("SELECT COUNT(*) AS n FROM report_phones").fetchone()["n"]
    appeal_count = src.execute("SELECT COUNT(*) AS n FROM appeals").fetchone()["n"]

    print(f"源库：{src_path}")
    print(f"目标：{mask_url(args.url)}")
    print(f"待迁移：{len(reports)} 条举报 · {phone_count} 个号码 · {image_count} 张截图 · {appeal_count} 条申诉")

    if not args.apply:
        print("\n这是 dry-run，未写入任何数据。确认无误后加 --apply 再执行。")
        return 0

    dst = Database(database_url=args.url)
    print(f"目标引擎：{dst.engine} · {dst.location}\n")

    mapping: dict[int, int] = {}
    copied_images = 0
    copied_appeals = 0

    for row in reports:
        phones = [
            item["phone_norm"]
            for item in src.execute(
                "SELECT phone_norm FROM report_phones WHERE report_id = ? ORDER BY id", (row["id"],)
            )
        ]
        new_id = dst.add_report(
            phones=phones,
            contact_name=row["contact_name"] or "",
            company=row["company"] or "",
            country=row["country"] or "",
            categories=_load_categories(row["categories"]),
            amount=row["amount"],
            currency=row["currency"] or "USD",
            incident_date=row["incident_date"],
            narrative=row["narrative"] or "",
            evidence=row["evidence"] or "",
            source=row["source"] or "manual",
            chat_filename=row["chat_filename"],
            chat_sha256=row["chat_sha256"],
            chat_message_count=row["chat_message_count"],
            credibility=row["credibility"] or 60,
            status=row["status"] or "approved",
            publish_screenshots=bool(row["publish_screenshots"]),
            created_at=row["created_at"],
        )
        mapping[int(row["id"])] = new_id

        images = []
        for image in src.execute(
            "SELECT mime, data, is_public FROM report_images WHERE report_id = ? ORDER BY sort_order, id",
            (row["id"],),
        ):
            images.append(
                {
                    "data": bytes(image["data"]),
                    "mime": image["mime"],
                    "is_public": bool(image["is_public"]),
                }
            )
        if images:
            copied_images += dst.add_report_images(new_id, images)

        print(f"  #{row['id']} -> #{new_id} · {len(phones)} 号码 · {len(images)} 截图")

    for appeal in src.execute("SELECT * FROM appeals ORDER BY id"):
        dst.add_appeal(
            appeal["message"],
            report_id=mapping.get(appeal["report_id"]) if appeal["report_id"] else None,
            phone_norm=appeal["phone_norm"],
        )
        copied_appeals += 1

    counts = dst.quick_counts()
    print()
    print(f"完成：{len(mapping)} 条举报 · {copied_images} 张截图 · {copied_appeals} 条申诉")
    print(f"目标库现有：{counts['reports']} 条举报 · {counts['phones']} 个号码 · {counts['pending']} 条待审")
    print("\n建议：打开站点抽查 3 条记录（文字 + 截图），确认无误后再清空本地库。")
    return 0


def _load_categories(raw: str) -> list[str]:
    import json

    try:
        value = json.loads(raw or "[]")
        return [str(item) for item in value] if isinstance(value, list) else ["other"]
    except (TypeError, ValueError):
        return ["other"]


if __name__ == "__main__":
    raise SystemExit(main())
