"""页面导航：公开站与管理员后台分开。

公开站是给普通用户用的，只保留查询、上报、情报库、看板、帮助；
管理后台单独一页，只有带 `?admin=1` 访问时才会出现在导航里。
"""

from __future__ import annotations

import streamlit as st

PUBLIC_PAGES = ["查询验证", "上报记录", "情报库", "数据看板", "帮助与合规"]
ADMIN_PAGE = "管理后台"

# 兼容旧引用：默认只暴露公开页
PAGES = PUBLIC_PAGES


def all_pages(admin_mode: bool = False) -> list[str]:
    return [*PUBLIC_PAGES, ADMIN_PAGE] if admin_mode else list(PUBLIC_PAGES)


def goto(page: str) -> None:
    if page in (*PUBLIC_PAGES, ADMIN_PAGE):
        st.session_state["_goto"] = page
    st.rerun()
