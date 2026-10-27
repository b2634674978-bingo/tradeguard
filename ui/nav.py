"""页面导航。"""

from __future__ import annotations

import streamlit as st

PAGES = ["查询验证", "上报记录", "情报库", "数据看板", "设置与合规"]


def goto(page: str) -> None:
    if page in PAGES:
        st.session_state["_goto"] = page
    st.rerun()
