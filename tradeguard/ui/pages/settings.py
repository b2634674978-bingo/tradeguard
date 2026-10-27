"""设置与合规：备份、导入导出、演示数据、申诉与边界说明。"""

from __future__ import annotations

from datetime import date

import streamlit as st

from .. import components, theme
from ...auth import admin_configured, is_admin, public_mode
from ...config import APP_TITLE, VERSION

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
        "设置与合规",
        "你的数据，只属于你" if not public_mode() else "公开演示版 · 管理入口",
        "备份、导入导出、复核申诉，以及这个产品必须守住的边界。"
        if not public_mode()
        else "公开演示版默认只读；管理员登录后可备份、导入和清理数据。",
    )

    if not is_admin():
        _render_read_only(db)
        return

    counts = db.quick_counts()
    if public_mode():
        theme.note(
            "当前是<strong>公开演示部署</strong>。SQLite 位于云端临时目录，应用重启/重新部署会重置；"
            "管理操作仅对已登录管理员开放。",
            "warn",
        )
    left, right = st.columns([1, 1])

    with left:
        with st.container(border=True):
            st.markdown("#### 数据与备份")
            st.markdown(
                f"当前：**{counts['reports']}** 条举报 · **{counts['phones']}** 个号码 · "
                f"**{counts['pending']}** 条待复核"
            )
            st.caption(f"数据库位置：{db.path}")
            st.download_button(
                "下载 SQLite 备份",
                data=db.backup_bytes(),
                file_name=f"tradeguard-backup-{date.today().isoformat()}.db",
                mime="application/octet-stream",
                use_container_width=True,
            )
            st.download_button(
                "导出全部记录 CSV",
                data=db.export_csv(),
                file_name=f"tradeguard-reports-{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with st.container(border=True):
            st.markdown("#### 批量导入")
            st.caption("支持从 Excel 另存为 CSV；表头可用中文或英文。单次最多 500 行。")
            st.download_button(
                "下载 CSV 模板",
                data=db.template_csv(),
                file_name="tradeguard-import-template.csv",
                mime="text/csv",
                use_container_width=True,
            )
            uploaded = st.file_uploader("选择 CSV 文件", type=["csv"], key="csv_import")
            if st.button("导入 CSV", use_container_width=True) and uploaded is not None:
                text = uploaded.getvalue().decode("utf-8-sig", errors="replace")
                result = db.import_csv(text)
                if result["imported"]:
                    st.success(f"成功导入 {result['imported']} 条，跳过 {result['skipped']} 条。")
                else:
                    st.warning(f"没有导入任何记录（跳过 {result['skipped']} 条）。")
                for error in result["errors"]:
                    st.caption(error)

    with right:
        with st.container(border=True):
            st.markdown("#### 演示数据")
            st.caption(
                "首次启动会自动写入 9 条虚构的演示记录（使用各国保留的影视号码），"
                "方便直接体验查询和看板。真实使用前建议清除。"
            )
            if st.button("删除全部演示数据", use_container_width=True):
                removed = db.delete_demo()
                st.success(f"已删除 {removed} 条演示记录。")
                st.rerun()

        with st.container(border=True):
            st.markdown("#### 待审核举报队列")
            pending = db.list_pending_reports(20)
            if not pending:
                st.caption("暂无待审核的举报。")
            else:
                st.caption(f"有 {len(pending)} 条举报等待你审核。")
                for report in pending:
                    with st.expander(f"#{report['id']} · {report.get('contact_name', '')} · {report.get('phones', '')} · {report['created_at'][:10]}"):
                        st.write(f"**公司**：{report.get('company', '未填写')}")
                        st.write(f"**国家**：{report.get('country', '未填写')}")
                        st.write(f"**类别**：{report.get('categories', '')}")
                        if report.get('amount'):
                            st.write(f"**金额**：{report.get('currency', '')} {report.get('amount')}")
                        st.write(f"**经过**：{report.get('narrative', '')}")
                        col1, col2 = st.columns(2)
                        if col1.button("✅ 通过收录", key=f"approve_{report['id']}", use_container_width=True):
                            db.set_status(report['id'], 'approved')
                            st.success("已通过！")
                            st.rerun()
                        if col2.button("❌ 驳回", key=f"reject_{report['id']}", use_container_width=True):
                            db.set_status(report['id'], 'rejected')
                            st.info("已驳回。")
                            st.rerun()

        with st.container(border=True):
            st.markdown("#### 申诉 / 纠错队列")
            appeals = db.list_appeals(20)
            if not appeals:
                st.caption("暂无申诉。")
            else:
                for appeal in appeals:
                    st.markdown(
                        f"- **#{appeal['id']}** · {appeal['created_at']} · 记录 "
                        f"{appeal['report_id'] or '—'}：{appeal['message']}"
                    )

        with st.container(border=True):
            st.markdown("#### 危险操作")
            st.caption("清空前建议先下载备份。此操作不可撤销。")
            confirm = st.text_input("输入「清空」以确认", key="clear_confirm")
            if st.button(
                "清空所有记录",
                type="secondary",
                disabled=confirm.strip() != "清空",
                use_container_width=True,
            ):
                removed = db.clear_all()
                st.success(f"已清空 {removed} 条记录。")
                st.rerun()

    st.markdown("#### 合规边界")
    st.markdown(COMPLIANCE_TEXT)

    theme.divider()
    st.caption(f"{APP_TITLE} · v{VERSION} · 本地优先原型 · 不构成法律意见")


def _render_read_only(db) -> None:
    counts = db.quick_counts()
    st.markdown("#### 公开只读模式")
    if admin_configured():
        theme.note(
            "管理操作已锁定。请在左侧「管理员登录」输入密码后，再备份、导入或清理数据。",
            "warn",
        )
    else:
        theme.note(
            "当前应用没有配置 <strong>ADMIN_PASSWORD</strong>，因此任何人都无法管理数据。"
            "在 Streamlit Cloud 的 App settings → Secrets 添加管理员密码后重启应用即可。",
            "warn",
        )
    st.markdown(
        f"演示库当前有 **{counts['reports']}** 条举报、**{counts['phones']}** 个号码。"
    )
    st.caption(
        "Streamlit Community Cloud 免费版的文件系统是临时的：应用休眠、重启或重新部署后，"
        "新增数据可能丢失。公开演示版请只使用虚构数据；真实数据请使用本地版或私有部署。"
    )
    st.markdown("#### 合规边界")
    st.markdown(COMPLIANCE_TEXT)
    st.caption("本工具不构成法律意见。公开传播他人信息前必须完成核实并咨询律师。")
