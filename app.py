"""TradeGuard · 外贸防骗情报库 —— Streamlit 入口。"""

from __future__ import annotations

import sys
sys.path.append('.')

import streamlit as st

from tradeguard import auth, config, i18n
from tradeguard.database import Database
from tradeguard.ui import components, theme
from tradeguard.ui.nav import PAGES
from tradeguard.ui.pages import check, dashboard, intel, report, settings

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

# 支持页面内部跳转（例如上报成功后去查询）
if "_goto" in st.session_state:
    st.session_state["nav"] = st.session_state.pop("_goto")

with st.sidebar:
    components.brand_block()
    i18n.language_selector()
    counts = db.quick_counts()
    components.stat_strip(
        [
            (i18n.tr("举报", "Reports"), counts["reports"]),
            (i18n.tr("号码", "Numbers"), counts["phones"]),
            (i18n.tr("待复核", "Pending"), counts["pending"]),
        ]
    )
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    page = st.radio(
        i18n.tr("导航", "Navigation"),
        PAGES,
        key="nav",
        label_visibility="collapsed",
        format_func=i18n.page_label,
    )
    if auth.public_mode():
        # 公开部署强制脱敏，避免访客暴露完整号码
        st.session_state["privacy_mode"] = True
        st.caption(i18n.tr("公开演示：列表默认脱敏", "Public demo: numbers are masked"))
    else:
        st.checkbox(i18n.tr("列表页隐藏完整号码", "Mask numbers in lists"), value=True, key="privacy_mode")
    if auth.public_mode():
        st.markdown("---")
        if db.is_postgres:
            st.caption(i18n.tr("公开演示 · 数据持久保存", "Public demo · data is persisted"))
        else:
            st.caption(i18n.tr("公开演示 · 数据可能随应用重启重置", "Public demo · data may reset on restart"))
    else:
        st.markdown("---")
        if db.is_postgres:
            st.caption(
                i18n.tr(
                    "自建部署 · 数据存于你的 PostgreSQL（不经过第三方）",
                    "Self-hosted · data lives in your own PostgreSQL",
                )
            )
        else:
            st.caption(i18n.tr("本地运行 · 数据不上传云端", "Runs locally · data stays on your machine"))
    if db.is_postgres:
        st.caption(i18n.tr("存储：PostgreSQL · 重启不丢", "Storage: PostgreSQL · survives restarts"))
    else:
        st.caption(i18n.tr("存储：本机 SQLite", "Storage: local SQLite"))
    # 管理员状态：只读时给出去哪里登录的明确指引
    if auth.admin_required():
        if auth.is_admin():
            st.caption(i18n.tr("权限：管理员已登录", "Access: admin signed in"))
        else:
            st.caption(i18n.tr(
                "权限：只读 · 到「设置与合规」顶部登录管理员",
                "Access: read-only · sign in under Settings & compliance",
            ))
    st.caption(i18n.tr("风险提示不是判决；无记录也不等于可信。", "Risk signals are not verdicts; no record does not mean safe."))


RENDERERS = {
    "查询验证": check.render,
    "上报记录": report.render,
    "情报库": intel.render,
    "数据看板": dashboard.render,
    "设置与合规": settings.render,
}

RENDERERS[page](db)

if db.is_postgres:
    footer_note = i18n.tr(
        "TradeGuard · PostgreSQL 持久化 · 记录跨重启保留",
        "TradeGuard · PostgreSQL backed · records survive restarts",
    )
elif config.IS_CLOUD:
    footer_note = i18n.tr(
        "TradeGuard · 云端演示版 · SQLite 数据为临时存储，应用重启后会重置",
        "TradeGuard · Cloud demo · SQLite storage is temporary and resets on restart",
    )
else:
    footer_note = i18n.tr(
        "TradeGuard · 本地优先原型 · 所有记录仅保存在这台电脑上",
        "TradeGuard · Local-first prototype · all records stay on this computer",
    )

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:.75rem;margin-top:2.5rem'>"
    + footer_note
    + "</div>",
    unsafe_allow_html=True,
)
