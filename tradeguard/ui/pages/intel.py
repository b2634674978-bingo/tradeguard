"""情报库页：浏览本机已收录的号码档案，支持筛选与导出。"""

from __future__ import annotations

import csv
import io
from datetime import date

import streamlit as st

from .. import components, theme
from ... import i18n
from ...constants import CATEGORY_KEYS
from ...normalize import format_phone

LEVEL_OPTIONS = ["", "high", "medium", "low", "watch"]


def render(db) -> None:
    theme.page_header(
        i18n.tr("诈骗情报库", "Scam intelligence"),
        i18n.tr("所有被上报过的号码，都在这里", "Every reported number in one place"),
        i18n.tr(
            "按号码聚合记录，展示风险分、涉及类型和最近活跃时间。列表默认脱敏，"
            "可在左下角关闭「隐藏完整号码」。",
            "Reports are grouped by number with risk score, issue types, and last activity. Numbers are masked by default.",
        ),
    )

    with st.container(border=True):
        columns = st.columns([2.2, 1.5, 1.4, 1.5])
        keyword = columns[0].text_input(
            i18n.tr("搜索", "Search"),
            placeholder=i18n.tr("号码 / 公司 / 联系人 / 国家", "Number / company / contact / country"),
            label_visibility="collapsed",
        )
        category_key = columns[1].selectbox(
            i18n.tr("类型", "Issue"),
            [""] + CATEGORY_KEYS,
            format_func=lambda key: i18n.tr("全部类型", "All issues") if not key else i18n.category_label(key),
            label_visibility="collapsed",
        )
        level_key = columns[2].selectbox(
            i18n.tr("风险", "Risk"),
            LEVEL_OPTIONS,
            format_func=lambda level: i18n.tr("全部风险", "All risk") if not level else i18n.risk_label(level),
            label_visibility="collapsed",
        )

        profiles, total = db.list_contacts(
            keyword=keyword,
            category=category_key,
            level=level_key,
            limit=200,
        )

        if profiles:
            columns[3].download_button(
                i18n.tr("导出筛选结果 CSV", "Export filtered CSV"),
                data=_contacts_csv(profiles),
                file_name=f"tradeguard-contacts-{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.caption(i18n.tr(
        f"共 {total} 个号码 / 主体，当前显示 {len(profiles)} 个。列表顺序：风险分从高到低。",
        f"{total} numbers/entities; showing {len(profiles)}. Sorted by risk score.",
    ))
    privacy = st.session_state.get("privacy_mode", True)

    if not profiles:
        components.empty_state(
            i18n.tr("🗂️", "🗂️"),
            i18n.tr("没有符合条件的记录", "No matching records"),
            [
                i18n.tr("试试清空搜索词或把风险等级切回「全部风险」。", "Clear the search or switch the risk filter back to All."),
                i18n.tr("库是空的？先去「上报记录」提交第一条。", "Empty database? Submit the first report."),
            ],
        )
        return

    for profile in profiles:
        key = profile["phone"] or profile["display_name"]
        components.profile_card(
            profile, db, masked=privacy, key_prefix=f"intel_{key}"
        )

    st.caption(i18n.tr(
        "隐私提示：这里是你本机的私人情报库。对外转发或公开这些记录前，请先核实事实，"
        "并注意《个人信息保护法》《民法典》名誉权等法律边界。",
        "Privacy notice: this is a private intelligence database. Verify facts and consider personal-information and defamation law before sharing.",
    ))


def _contacts_csv(profiles: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["号码", "联系人", "公司", "国家", "风险等级", "风险分", "举报数", "最近记录", "类型"]
    )
    for profile in profiles:
        writer.writerow(
            [
                format_phone(profile["phone"]) if profile["phone"] else "",
                profile["contact_name"],
                profile["company"],
                profile["country"],
                profile["risk"]["label"],
                profile["risk"]["score"],
                profile["report_count"],
                profile["last_seen"],
                "；".join(item["label"] for item in profile["categories"]),
            ]
        )
    return "\ufeff" + buffer.getvalue()
