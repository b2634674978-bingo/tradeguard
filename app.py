"""TradeGuard · 外贸防骗情报库 —— Streamlit 入口。"""

from __future__ import annotations

import sys
sys.path.append('.')

import streamlit as st

from tradeguard import auth, config
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
    counts = db.quick_counts()
    components.stat_strip(
        [("举报", counts["reports"]), ("号码", counts["phones"]), ("待复核", counts["pending"])]
    )
    st.markdown("<div style='height:.8rem'></div>", unsafe_allow_html=True)
    page = st.radio("导航", PAGES, key="nav", label_visibility="collapsed")
    if auth.public_mode():
        # 公开部署强制脱敏，避免访客暴露完整号码
        st.session_state["privacy_mode"] = True
        st.caption("公开演示：列表默认脱敏")
    else:
        st.checkbox("列表页隐藏完整号码", value=True, key="privacy_mode")
    if auth.public_mode():
        st.markdown("---")
        auth.login_widget()
        st.markdown("---")
        st.caption("公开演示 · 数据可能随应用重启重置")
    else:
        st.markdown("---")
        st.caption("本地运行 · 数据不上传云端")
    st.caption("风险提示不是判决；无记录也不等于可信。")


RENDERERS = {
    "查询验证": check.render,
    "上报记录": report.render,
    "情报库": intel.render,
    "数据看板": dashboard.render,
    "设置与合规": settings.render,
}

RENDERERS[page](db)

if config.IS_CLOUD:
    footer_note = "TradeGuard · 云端演示版 · SQLite 数据为临时存储，应用重启后会重置"
else:
    footer_note = "TradeGuard · 本地优先原型 · 所有记录仅保存在这台电脑上"

st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:.75rem;margin-top:2.5rem'>"
    + footer_note
    + "</div>",
    unsafe_allow_html=True,
)
