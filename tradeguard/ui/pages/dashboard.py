"""数据看板：举报趋势、类型分布、高风险与最近记录。"""

from __future__ import annotations

import streamlit as st

from .. import components, theme
from ... import i18n
from ...auth import public_viewer

try:
    import pandas as pd
except Exception:  # pragma: no cover - pandas 随 streamlit 安装
    pd = None


def render(db) -> None:
    theme.page_header(
        i18n.tr("数据看板", "Dashboard"),
        i18n.tr("骗术在往哪里走？", "Where are the scams moving?"),
        i18n.tr(
            "基于本地库的聚合视图：新增趋势、问题类型、国家分布和高风险号码。",
            "Aggregated view: trends, issue types, countries, and high-risk numbers.",
        ),
    )

    stats = db.stats()
    columns = st.columns(4)
    columns[0].metric(i18n.tr("举报记录", "Reports"), stats["total_reports"])
    columns[1].metric(i18n.tr("涉及号码", "Numbers"), stats["total_phones"])
    columns[2].metric(i18n.tr("高风险号码", "High risk"), stats["high_risk"])
    columns[3].metric(i18n.tr("本月新增", "This month"), stats["this_month"])

    if stats["demo_count"]:
        st.caption(i18n.tr(
            f"当前包含 {stats['demo_count']} 条演示数据（虚构号码），用于展示界面；可在「设置与合规」一键清除。",
            f"{stats['demo_count']} demo records (fictional numbers) are included; remove them in Settings.",
        ))

    if stats["total_reports"] == 0:
        components.empty_state(
            "📊",
            i18n.tr("还没有数据", "No data yet"),
            [i18n.tr("先到「上报记录」提交第一条举报，或到设置中载入演示数据。", "Submit the first report or load demo data in Settings.")],
        )
        return

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown(i18n.tr("#### 近 6 个月新增", "#### New reports, last 6 months"))
        if pd is not None:
            trend = pd.DataFrame(
                {"月份": stats["months"], "新增记录": stats["monthly"]}
            ).set_index("月份")
            st.line_chart(trend, height=280)
        else:
            st.bar_chart(dict(zip(stats["months"], stats["monthly"])), height=280)

    with right:
        st.markdown(i18n.tr("#### 问题类型分布", "#### Issue types"))
        category_rows = [
            {
                i18n.tr("类型", "Issue"): i18n.category_label(key),
                i18n.tr("记录数", "Reports"): count,
            }
            for key, count in stats["categories"].most_common()
        ]
        if category_rows and pd is not None:
            frame = pd.DataFrame(category_rows).set_index("类型")
            st.bar_chart(frame, height=280)
        else:
            st.caption("暂无类型数据")

    left, right = st.columns([1, 1.25])
    with left:
        st.markdown(i18n.tr("#### 国家 / 地区", "#### Countries"))
        if stats["countries"]:
            country_rows = [
                {i18n.tr("国家", "Country"): name, i18n.tr("记录数", "Reports"): count}
                for name, count in stats["countries"]
            ]
            if pd is not None:
                st.bar_chart(
                    pd.DataFrame(country_rows).set_index(i18n.tr("国家", "Country")),
                    height=260,
                )
        else:
            st.caption(i18n.tr("暂无国家数据", "No country data"))

        if stats["currency_totals"]:
            st.markdown(i18n.tr("#### 已记录损失（按币种，未折算）", "#### Reported losses by currency"))
            pills = "".join(
                f'<span class="tg-pill">{currency} <b>{amount:,.0f}</b></span>'
                for currency, amount in sorted(stats["currency_totals"].items(), key=lambda x: -x[1])
            )
            st.markdown(f'<div class="tg-pills">{pills}</div>', unsafe_allow_html=True)

    with right:
        st.markdown(i18n.tr("#### 最近入库", "#### Recent reports"))
        reports = db.recent_reports(4)
        for report in reports:
            components.report_card(report, db, public_view=public_viewer())

    st.caption(i18n.tr(
        f"待复核 {stats['pending']} 条 · 未处理申诉 {stats['appeals']} 条。"
        "统计口径：已收录（approved）记录，同一号码多条举报合并为号码档案。",
        f"{stats['pending']} pending · {stats['appeals']} open appeals. "
        "Only approved reports are counted; multiple reports for a number are merged.",
    ))
