"""TradeGuard · 外贸防骗情报库 —— Streamlit 入口。

前台（查询、上报、情报库、看板、帮助）面向普通用户，不出现任何管理入口；
管理后台独立成一个页面，只有访问 `?admin=1` 时才会出现在导航里。
"""

from __future__ import annotations

import sys
sys.path.append('.')

import streamlit as st

from tradeguard import auth, config, i18n
from tradeguard.database import Database
from tradeguard.ui import components, theme
from tradeguard.ui import nav
from tradeguard.ui.pages import admin, check, dashboard, help, intel, report

st.set_page_config(
    page_title=config.APP_TITLE,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

theme.inject()


@st.cache_resource
def get_db() -> Database:
    database = Database()
    database.ensure_seeded()
    return database


db = get_db()

# 管理后台需要显式访问 ?admin=1，避免普通用户误入
admin_mode = auth.admin_entry_requested()
pages = nav.all_pages(admin_mode)

# 支持页面内部跳转（例如上报成功后去查询）
if "_goto" in st.session_state:
    target = st.session_state.pop("_goto")
    if target in pages:
        st.session_state["nav"] = target

if st.session_state.get("nav") not in pages:
    st.session_state["nav"] = nav.ADMIN_PAGE if admin_mode else pages[0]

with st.sidebar:
    components.brand_block()
    i18n.language_selector()
    counts = db.quick_counts()
    stats = [
        (i18n.tr("举报", "Reports"), counts["reports"]),
        (i18n.tr("号码", "Numbers"), counts["phones"]),
    ]
    if admin_mode:
        stats.append((i18n.tr("待复核", "Pending"), counts["pending"]))
    components.stat_strip(stats)

    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    page = st.radio(
        i18n.tr("导航", "Navigation"),
        pages,
        key="nav",
        label_visibility="collapsed",
        format_func=i18n.page_label,
    )

    if auth.public_mode():
        # 公开部署强制脱敏，避免访客暴露完整号码
        st.session_state["privacy_mode"] = True
        st.caption(i18n.tr("公开演示：号码默认脱敏", "Public demo: numbers are masked"))
    else:
        st.checkbox(i18n.tr("列表页隐藏完整号码", "Mask numbers in lists"), value=True, key="privacy_mode")

    if admin_mode:
        st.markdown("---")
        if db.is_postgres:
            st.caption(i18n.tr("存储：PostgreSQL · 重启不丢", "Storage: PostgreSQL · survives restarts"))
        else:
            st.caption(i18n.tr("存储：本机 SQLite", "Storage: local SQLite"))
        if auth.is_admin():
            st.caption(i18n.tr("权限：管理员已登录", "Access: admin signed in"))
        elif auth.admin_required():
            st.caption(i18n.tr("权限：未登录 · 请先登录", "Access: signed out · please sign in"))

    st.caption(i18n.tr(
        "风险提示不是判决；无记录也不等于可信。",
        "Risk signals are not verdicts; no record does not mean safe.",
    ))


RENDERERS = {
    "查询验证": check.render,
    "上报记录": report.render,
    "情报库": intel.render,
    "数据看板": dashboard.render,
    "帮助与合规": help.render,
    "管理后台": admin.render,
}

RENDERERS[page](db)

if admin_mode:
    if db.is_postgres:
        footer_note = i18n.tr(
            "TradeGuard 管理后台 · PostgreSQL 持久化 · 记录跨重启保留",
            "TradeGuard admin · PostgreSQL backed · records survive restarts",
        )
    else:
        footer_note = i18n.tr(
            "TradeGuard 管理后台 · 本机 SQLite",
            "TradeGuard admin · local SQLite",
        )
else:
    footer_note = i18n.tr(
        "TradeGuard · " + config.APP_TAGLINE,
        "TradeGuard · check before you trade",
    )

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:.75rem;margin-top:2.5rem'>"
    + footer_note
    + "</div>",
    unsafe_allow_html=True,
)
