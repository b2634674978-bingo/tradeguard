"""管理后台：审核、备份、导入、申诉与危险操作。

独立于前台：普通用户不会看到这个页面的入口（需要显式访问 `?admin=1`），
未登录时只剩一个登录框和一句只读说明。
"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import components, theme
from ... import auth, i18n
from ...auth import admin_configured, is_admin, public_mode
from ...config import APP_TITLE, VERSION


def render(db) -> None:
    theme.page_header(
        i18n.tr("管理后台", "Admin"),
        i18n.tr("审核、备份、导入与清场", "Review, backup, import, cleanup"),
        i18n.tr(
            "普通用户看不到这一页。所有改动会立刻对前台生效。",
            "Ordinary visitors never see this page. Changes take effect immediately.",
        ),
    )

    auth.login_widget()

    if not is_admin():
        _render_locked(db)
        return

    st.markdown("---")
    counts = db.quick_counts()
    st.caption(i18n.tr(
        f"当前 {counts['reports']} 条举报 · {counts['phones']} 个号码 · {counts['pending']} 条待复核",
        f"{counts['reports']} reports · {counts['phones']} numbers · {counts['pending']} pending",
    ))
    if public_mode():
        if db.is_postgres:
            theme.note(
                i18n.tr(
                    "公开演示部署 · 数据存放在 PostgreSQL，重启不会丢失。",
                    "Public demo backed by PostgreSQL: data survives restarts.",
                ),
                "info",
            )
        else:
            theme.note(
                i18n.tr(
                    "公开演示部署 · SQLite 位于临时目录，重启/重新部署会重置。",
                    "Public demo: SQLite lives in temporary storage and resets on restart.",
                ),
                "warn",
            )
    else:
        theme.note(
            i18n.tr(
                f"存储引擎：{db.location}",
                f"Storage engine: {db.location}",
            ),
            "info",
        )

    review_tab, data_tab, import_tab, appeal_tab, danger_tab = st.tabs(
        [
            i18n.tr("待审核", "Review"),
            i18n.tr("数据与备份", "Data & backup"),
            i18n.tr("批量导入", "Bulk import"),
            i18n.tr("申诉与纠错", "Appeals"),
            i18n.tr("危险操作", "Danger"),
        ]
    )

    with review_tab:
        _render_review(db)
    with data_tab:
        _render_data(db, counts)
    with import_tab:
        _render_import(db)
    with appeal_tab:
        _render_appeals(db)
    with danger_tab:
        _render_danger(db)

    theme.divider()
    st.caption(f"{APP_TITLE} · v{VERSION} · " + i18n.tr("管理后台", "admin console"))


# ---------------------------------------------------------------- 待审核


def _render_review(db) -> None:
    pending = db.list_pending_reports(30)
    if not pending:
        st.caption(i18n.tr("没有待审核的举报。", "Nothing waiting for review."))
        return

    st.markdown(i18n.tr(f"#### 有 {len(pending)} 条举报待审核", f"#### {len(pending)} report(s) pending"))
    for report in pending:
        with st.container(border=True):
            labels = "、".join(
                i18n.category_label(key) for key in report.get("categories", [])
            ) or i18n.tr("未分类", "Uncategorized")
            st.write(f"**#{report['id']}** · {report['created_at'][:10]} · {labels}")
            st.write(i18n.tr(
                f"联系人：{report['contact_name'] or '未填写'} · 公司：{report['company'] or '未填写'} · 号码：{'、'.join(report.get('phones', [])) or '未填写'}",
                f"Contact: {report['contact_name'] or 'not provided'} · Company: {report['company'] or 'not provided'} · Number: {'、'.join(report.get('phones', [])) or 'not provided'}",
            ))
            st.write(i18n.tr(f"经过：{report['narrative']}", f"Narrative: {report['narrative']}"))
            st.caption(i18n.tr(
                "公开截图：" + ("是，审核通过后访客可见" if report.get("publish_screenshots") else "否，仅管理员可见"),
                "Screenshots public: " + ("yes, visible after approval" if report.get("publish_screenshots") else "no, admin only"),
            ))

            images = report.get("images", [])
            if images:
                for index, image in enumerate(images):
                    st.image(
                        image["data"],
                        caption=i18n.tr(
                            f"截图 {index + 1} · {round(image['size'] / 1024)} KB",
                            f"Screenshot {index + 1} · {round(image['size'] / 1024)} KB",
                        ),
                        use_container_width=True,
                    )
            else:
                st.caption(i18n.tr("📷 没有可显示的截图", "📷 No screenshots available"))

            col1, col2 = st.columns(2)
            if col1.button(i18n.tr("✅ 通过收录", "✅ Approve"), key=f"approve_{report['id']}", use_container_width=True):
                db.set_status(report["id"], "approved")
                st.success(i18n.tr("已通过！", "Approved."))
                st.rerun()
            if col2.button(i18n.tr("❌ 驳回", "❌ Reject"), key=f"reject_{report['id']}", use_container_width=True):
                db.set_status(report["id"], "rejected")
                st.info(i18n.tr("已驳回。", "Rejected."))
                st.rerun()


# ---------------------------------------------------------------- 数据与备份


def _render_data(db, counts) -> None:
    st.markdown(i18n.tr("#### 数据与备份", "#### Data & backup"))
    st.markdown(i18n.tr(
        f"当前：**{counts['reports']}** 条举报 · **{counts['phones']}** 个号码 · **{counts['pending']}** 条待复核",
        f"**{counts['reports']}** reports · **{counts['phones']}** numbers · **{counts['pending']}** pending",
    ))
    st.caption(i18n.tr(f"存储引擎：{db.location}", f"Storage engine: {db.location}"))
    st.download_button(
        i18n.tr("导出全部记录 CSV", "Export all CSV"),
        data=db.export_csv(),
        file_name=f"tradeguard-reports-{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if db.supports_file_backup:
        st.download_button(
            i18n.tr("下载 SQLite 备份", "Download SQLite backup"),
            data=db.backup_bytes(),
            file_name=f"tradeguard-backup-{date.today().isoformat()}.db",
            mime="application/octet-stream",
            use_container_width=True,
        )

        st.divider()
        st.markdown(i18n.tr("**恢复 SQLite 备份**", "**Restore SQLite backup**"))
        st.caption(i18n.tr(
            "上传之前下载的 .db 文件；会覆盖当前数据库和截图。",
            "Upload a previously downloaded .db file. This replaces the current database and screenshots.",
        ))
        backup_file = st.file_uploader(
            i18n.tr("选择 .db 备份", "Choose .db backup"),
            type=["db"],
            key="db_restore",
        )
        confirm_restore = st.checkbox(
            i18n.tr("我确认覆盖当前数据", "I understand this overwrites current data"),
            key="db_restore_confirm",
        )
        if backup_file is not None and st.button(
            i18n.tr("覆盖恢复数据", "Restore backup"),
            disabled=not confirm_restore,
            use_container_width=True,
        ):
            raw_backup = backup_file.getvalue()
            if len(raw_backup) > 200 * 1024 * 1024:
                st.error(i18n.tr("备份文件超过 200 MB。", "Backup exceeds 200 MB."))
            else:
                try:
                    db.restore_from_bytes(raw_backup)
                except Exception as exc:  # noqa: BLE001
                    st.error(i18n.tr(f"恢复失败：{exc}", f"Restore failed: {exc}"))
                else:
                    st.success(i18n.tr(
                        "已恢复备份，请刷新页面后生效。",
                        "Backup restored. Refresh the page to load it.",
                    ))
    else:
        st.divider()
        st.markdown(i18n.tr("**备份（PostgreSQL）**", "**Backup (PostgreSQL)**"))
        st.caption(i18n.tr(
            "当前使用 PostgreSQL，整库备份请在 Supabase / Neon 控制台开启自动备份，"
            "或用 pg_dump 导出；本页仍可导出 CSV 作为人工存档。",
            "This deployment uses PostgreSQL. Use Supabase/Neon automated backups or pg_dump; "
            "CSV export remains available here as a manual archive.",
        ))

    st.divider()
    st.markdown(i18n.tr("#### 演示数据", "#### Demo data"))
    st.caption(i18n.tr(
        "首次启动会自动写入 9 条虚构记录（使用各国保留的影视号码）。真实使用前建议清除。",
        "Nine fictional demo records are seeded on first start. Remove them before real use.",
    ))
    if st.button(i18n.tr("删除全部演示数据", "Delete demo data"), use_container_width=True):
        removed = db.delete_demo()
        st.success(i18n.tr(f"已删除 {removed} 条演示记录。", f"Removed {removed} demo record(s)."))
        st.rerun()


# ---------------------------------------------------------------- 批量导入


def _render_import(db) -> None:
    st.markdown(i18n.tr("#### 批量导入", "#### Bulk import"))
    st.caption(i18n.tr(
        "支持从 Excel 另存为 CSV；表头可用中文或英文。单次最多 500 行。",
        "Export Excel to CSV; Chinese or English headers are supported. Up to 500 rows.",
    ))
    st.download_button(
        i18n.tr("下载 CSV 模板", "Download CSV template"),
        data=db.template_csv(),
        file_name="tradeguard-import-template.csv",
        mime="text/csv",
        use_container_width=True,
    )
    uploaded = st.file_uploader(i18n.tr("选择 CSV 文件", "Choose CSV"), type=["csv"], key="csv_import")
    if st.button(i18n.tr("导入 CSV", "Import CSV"), use_container_width=True) and uploaded is not None:
        text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
        result = db.import_csv(text)
        if result["imported"]:
            st.success(i18n.tr(
                f"成功导入 {result['imported']} 条，跳过 {result['skipped']} 条。",
                f"Imported {result['imported']} row(s), skipped {result['skipped']}.",
            ))
        else:
            st.warning(i18n.tr(
                f"没有导入任何记录（跳过 {result['skipped']} 条）。",
                f"No rows imported ({result['skipped']} skipped).",
            ))
        for error in result["errors"]:
            st.caption(error)


# ---------------------------------------------------------------- 申诉


def _render_appeals(db) -> None:
    appeals = db.list_appeals(50)
    if not appeals:
        st.caption(i18n.tr("暂无人提交申诉。", "No appeals yet."))
        return
    st.markdown(i18n.tr(f"#### {len(appeals)} 条申诉待处理", f"#### {len(appeals)} appeal(s)"))
    st.caption(i18n.tr(
        "核对后如需更正，用「数据与备份」里的 CSV 导出定位记录再处理；原型阶段不提供自动删除。",
        "Verify, then locate the record via CSV export. Automatic deletion is intentionally not provided.",
    ))
    for appeal in appeals:
        with st.container(border=True):
            st.markdown(
                f"**#{appeal['id']}** · {appeal['created_at']} · "
                + i18n.tr(f"记录 {appeal['report_id'] or '—'}", f"report {appeal['report_id'] or '—'}")
            )
            st.write(appeal["message"])


# ---------------------------------------------------------------- 危险操作


def _render_danger(db) -> None:
    if public_mode():
        theme.note(
            i18n.tr(
                "公开部署下清空全部数据不可逆。确认已导出 CSV 备份后再操作。",
                "Clearing all data on a public deployment is irreversible. Export a CSV first.",
            ),
            "warn",
        )
    st.markdown(i18n.tr("#### 清空所有记录", "#### Clear all records"))
    st.caption(i18n.tr("清空前建议先下载备份。此操作不可撤销。", "Download a backup first. This cannot be undone."))
    confirm = st.text_input(i18n.tr("输入「清空」以确认", "Type CLEAR to confirm"), key="clear_confirm")
    if st.button(
        i18n.tr("清空所有记录", "Clear all records"),
        type="secondary",
        disabled=confirm.strip() != i18n.tr("清空", "CLEAR"),
        use_container_width=True,
    ):
        removed = db.clear_all()
        st.success(i18n.tr(f"已清空 {removed} 条记录。", f"Cleared {removed} record(s)."))
        st.rerun()


# ---------------------------------------------------------------- 锁定态


def _render_locked(db) -> None:
    counts = db.quick_counts()
    st.markdown("---")
    if admin_configured():
        theme.note(
            i18n.tr(
                "请在页面顶部的管理员区块输入密码。未登录时这里不提供任何数据操作。",
                "Sign in with the admin block above. Nothing here is actionable until you do.",
            ),
            "warn",
        )
    else:
        theme.note(
            i18n.tr(
                "当前没有配置 <strong>ADMIN_PASSWORD</strong>，因此没有任何人可以管理数据。"
                "在平台环境变量或 Streamlit Secrets 添加管理员密码后重启应用即可。",
                "No <strong>ADMIN_PASSWORD</strong> is configured, so nobody can manage data. "
                "Add it to the platform environment variables or Streamlit Secrets, then restart.",
            ),
            "warn",
        )
    st.caption(i18n.tr(
        f"当前库中有 {counts['reports']} 条举报、{counts['phones']} 个号码、{counts['pending']} 条待复核。",
        f"Currently {counts['reports']} reports, {counts['phones']} numbers, {counts['pending']} pending.",
    ))
    st.caption(i18n.tr("前台用户可以正常查询与上报，这一页只是管理入口。", "Visitors can still search and report normally."))
