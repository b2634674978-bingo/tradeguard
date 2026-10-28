"""设置与合规：备份、导入导出、演示数据、申诉与边界说明。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import components, theme
from ... import i18n
from ...auth import admin_configured, is_admin, public_mode
from ...config import APP_TITLE, VERSION

COMPLIANCE_TEXT_EN = """
**Principles**

- Results are **risk signals**, not facts, credit reports, or legal judgments.
- A single uncorroborated report is capped at medium risk.
- Every record can be appealed.
- Data minimization: only numbers, issue types, narratives, amounts, and evidence summaries are stored.
- Cloud demos use temporary storage and reset on restart.

**Boundaries**

- Do not publish these records as a public "scammer list" without verification and legal advice.
- China: PIPL, Civil Code reputation/privacy rules, and personal-information principles.
- Overseas: GDPR, local defamation law, and cross-border data rules.
- This tool is not legal advice.
"""

COMPLIANCE_TEXT = """
**产品原则**

- 结果只是**风险提示**，不是事实认定、征信报告或法律判决；
- 单条未经交叉验证的举报最高只到“中风险”，避免一次指控毁掉一个客户；
- 每条记录都提供申诉入口，申诉保存在本机；
- 数据最小化：只存号码、类型、经过、金额与证据摘要，不保存完整聊天记录；
- 本地完整版的数据只在本机 SQLite；公开演示版运行在云端临时目录，应用重启后会重置。

**使用边界（重要）**

- 不要把这个库里的内容公开发布、群发或做成“骗子名单”网站，除非已完成核实并咨询律师；
- 中国场景注意《个人信息保护法》的最小必要、告知同意、删除权，以及《民法典》名誉权 / 商誉；
- 海外场景注意 GDPR、当地诽谤法与数据跨境规则；
- 本工具不构成法律意见。
"""


def render(db) -> None:
    theme.page_header(
        i18n.tr("设置与合规", "Settings & compliance"),
        i18n.tr("你的数据，只属于你", "Your data stays yours")
        if not public_mode()
        else i18n.tr("公开演示版 · 管理入口", "Public demo · admin"),
        i18n.tr(
            "备份、导入导出、复核申诉，以及这个产品必须守住的边界。",
            "Backup, import/export, appeals, and the boundaries this product must respect.",
        )
        if not public_mode()
        else i18n.tr(
            "公开演示版默认只读；管理员登录后可备份、导入和清理数据。",
            "The public demo is read-only; admins can back up, import, and clean data after signing in.",
        ),
    )

    if not is_admin():
        _render_read_only(db)
        return

    counts = db.quick_counts()
    if public_mode():
        theme.note(
            i18n.tr(
                "当前是<strong>公开演示部署</strong>。SQLite 位于云端临时目录，应用重启/重新部署会重置；"
                "管理操作仅对已登录管理员开放。",
                "This is a <strong>public demo deployment</strong>. SQLite lives in temporary storage and resets on restart; admin actions are locked.",
            ),
            "warn",
        )

    # 待审核队列：图片以 BLOB 存储，用 st.image 完整显示
    pending = db.list_pending_reports(30)
    if pending:
        st.markdown(i18n.tr(f"### 🔔 有 {len(pending)} 条举报待审核", f"### 🔔 {len(pending)} report(s) pending review"))
        for report in pending:
            with st.container(border=True):
                labels = "、".join(
                    i18n.category_label(key) for key in report.get("categories", [])
                ) or i18n.tr("未分类", "Uncategorized")
                st.write(
                    f"**#{report['id']}** · {report['created_at'][:10]} · {labels}"
                )
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
        st.divider()

    left, right = st.columns([1, 1])

    with left:
        with st.container(border=True):
            st.markdown(i18n.tr("#### 数据与备份", "#### Data & backup"))
            st.markdown(i18n.tr(
                f"当前：**{counts['reports']}** 条举报 · **{counts['phones']}** 个号码 · **{counts['pending']}** 条待复核",
                f"**{counts['reports']}** reports · **{counts['phones']}** numbers · **{counts['pending']}** pending",
            ))
            st.caption(i18n.tr(f"数据库位置：{db.path}", f"Database: {db.path}"))
            st.download_button(
                i18n.tr("下载 SQLite 备份", "Download SQLite backup"),
                data=db.backup_bytes(),
                file_name=f"tradeguard-backup-{date.today().isoformat()}.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
            st.download_button(
                i18n.tr("导出全部记录 CSV", "Export all CSV"),
                data=db.export_csv(),
                file_name=f"tradeguard-reports-{date.today().isoformat()}.csv",
                mime="text/csv",
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
                elif not raw_backup.startswith(b"SQLite format 3\x00"):
                    st.error(i18n.tr("这不是有效的 SQLite 备份文件。", "This is not a valid SQLite backup."))
                else:
                    try:
                        db.path.write_bytes(raw_backup)
                        db.init()
                    except Exception as exc:  # noqa: BLE001
                        st.error(i18n.tr(f"恢复失败：{exc}", f"Restore failed: {exc}"))
                    else:
                        st.success(i18n.tr(
                            "已恢复备份，请刷新页面后生效。",
                            "Backup restored. Refresh the page to load it.",
                        ))

        with st.container(border=True):
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

    with right:
        with st.container(border=True):
            st.markdown(i18n.tr("#### 演示数据", "#### Demo data"))
            st.caption(i18n.tr(
                "首次启动会自动写入 9 条虚构的演示记录（使用各国保留的影视号码），方便直接体验查询和看板。真实使用前建议清除。",
                "Nine fictional demo records are seeded on first start. Remove them before real use.",
            ))
            if st.button(i18n.tr("删除全部演示数据", "Delete demo data"), use_container_width=True):
                removed = db.delete_demo()
                st.success(f"已删除 {removed} 条演示记录。")
                st.rerun()

        with st.container(border=True):
            st.markdown(i18n.tr("#### 申诉 / 纠错队列", "#### Appeals"))
            appeals = db.list_appeals(20)
            if not appeals:
                st.caption(i18n.tr("暂无申诉。", "No appeals."))
            else:
                for appeal in appeals:
                    st.markdown(
                        f"- **#{appeal['id']}** · {appeal['created_at']} · 记录 "
                        f"{appeal['report_id'] or '—'}：{appeal['message']}"
                    )

        with st.container(border=True):
            st.markdown(i18n.tr("#### 危险操作", "#### Danger zone"))
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

    st.markdown(i18n.tr("#### 合规边界", "#### Compliance boundaries"))
    st.markdown(COMPLIANCE_TEXT_EN if i18n.lang() == "en" else COMPLIANCE_TEXT)

    theme.divider()
    st.caption(
        f"{APP_TITLE} · v{VERSION} · "
        + i18n.tr("本地优先原型 · 不构成法律意见", "local-first prototype · not legal advice")
    )


def _render_read_only(db) -> None:
    counts = db.quick_counts()
    st.markdown(i18n.tr("#### 公开只读模式", "#### Public read-only mode"))
    if admin_configured():
        theme.note(
            i18n.tr(
                "管理操作已锁定。请在左侧「管理员登录」输入密码后，再备份、导入或清理数据。",
                "Admin actions are locked. Sign in from the sidebar to back up, import, or clean data.",
            ),
            "warn",
        )
    else:
        theme.note(
            i18n.tr(
                "当前应用没有配置 <strong>ADMIN_PASSWORD</strong>，因此任何人都无法管理数据。"
                "在平台环境变量或 Streamlit Secrets 添加管理员密码后重启应用即可。",
                "No <strong>ADMIN_PASSWORD</strong> is configured, so nobody can manage data. "
                "Add it to the platform environment variables or Streamlit Secrets, then restart.",
            ),
            "warn",
        )
    st.markdown(i18n.tr(
        f"演示库当前有 **{counts['reports']}** 条举报、**{counts['phones']}** 个号码。",
        f"The demo has **{counts['reports']}** reports and **{counts['phones']}** numbers.",
    ))
    st.caption(i18n.tr(
        "免费版文件系统是临时的：应用休眠、重启或重新部署后，新增数据可能丢失。"
        "公开演示版请只使用虚构数据；真实数据请使用本地版或私有部署。",
        "Free-tier storage is temporary: data may reset when the app sleeps, restarts, or redeploys. "
        "Use fictional data in public demos; use a local or private deployment for real reports.",
    ))
    st.markdown(i18n.tr("#### 合规边界", "#### Compliance boundaries"))
    st.markdown(COMPLIANCE_TEXT_EN if i18n.lang() == "en" else COMPLIANCE_TEXT)
    st.caption(i18n.tr(
        "本工具不构成法律意见。公开传播他人信息前必须完成核实并咨询律师。",
        "This tool is not legal advice. Verify facts and consult a lawyer before publishing personal information.",
    ))
