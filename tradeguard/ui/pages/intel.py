"""情报库页：浏览本机已收录的号码档案，支持筛选与导出。"""

from __future__ import annotations

import csv
import io
from datetime import date

import streamlit as st

from .. import components, theme
from ...constants import CATEGORY_KEYS, CATEGORY_LABELS
from ...normalize import format_phone

LEVEL_OPTIONS = {
    "全部风险": "",
    "高风险": "high",
    "中风险": "medium",
    "低风险": "low",
    "关注": "watch",
}


def render(db) -> None:
    theme.page_header(
        "诈骗情报库",
        "所有被上报过的号码，都在这里",
        "按号码聚合记录，展示风险分、涉及类型和最近活跃时间。列表默认脱敏，"
        "可在左下角关闭「隐藏完整号码」。",
    )

    with st.container(border=True):
        columns = st.columns([2.2, 1.5, 1.4, 1.5])
        keyword = columns[0].text_input(
            "搜索", placeholder="号码 / 公司 / 联系人 / 国家", label_visibility="collapsed"
        )
        category_label = columns[1].selectbox(
            "类型",
            ["全部类型"] + [CATEGORY_LABELS[key] for key in CATEGORY_KEYS],
            label_visibility="collapsed",
        )
        level_label = columns[2].selectbox(
            "风险", list(LEVEL_OPTIONS.keys()), label_visibility="collapsed"
        )
        category_key = ""
        if category_label != "全部类型":
            category_key = next(
                key for key in CATEGORY_KEYS if CATEGORY_LABELS[key] == category_label
            )

        profiles, total = db.list_contacts(
            keyword=keyword,
            category=category_key,
            level=LEVEL_OPTIONS[level_label],
            limit=200,
        )

        if profiles:
            columns[3].download_button(
                "导出筛选结果 CSV",
                data=_contacts_csv(profiles),
                file_name=f"tradeguard-contacts-{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    st.caption(f"共 {total} 个号码 / 主体，当前显示 {len(profiles)} 个。列表顺序：风险分从高到低。")
    privacy = st.session_state.get("privacy_mode", True)

    if not profiles:
        components.empty_state(
            "🗂️",
            "没有符合条件的记录",
            ["试试清空搜索词或把风险等级切回「全部风险」。", "库是空的？先去「上报记录」提交第一条。"],
        )
        return

    for profile in profiles:
        key = profile["phone"] or profile["display_name"]
        components.profile_card(
            profile, db, masked=privacy, key_prefix=f"intel_{key}"
        )

    st.caption(
        "隐私提示：这里是你本机的私人情报库。对外转发或公开这些记录前，请先核实事实，"
        "并注意《个人信息保护法》《民法典》名誉权等法律边界。"
    )


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
