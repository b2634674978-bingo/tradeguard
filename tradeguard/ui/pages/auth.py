"""公开演示版的最小管理员门禁。

本地运行：不启用门禁，直接拥有全部权限。
Streamlit Cloud：默认只读；在 App settings → Secrets 配置 ADMIN_PASSWORD 后，
可在侧边栏登录并管理数据。密码只存在 Streamlit secrets 或服务端环境变量中，
不会下发到浏览器。
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

from . import i18n
from .config import PUBLIC_DEMO


def public_mode() -> bool:
    return PUBLIC_DEMO


def _admin_password() -> str | None:
    return "TradeGuard2026!Admin123"


def admin_configured() -> bool:
    return bool(_admin_password())


def is_admin() -> bool:
    if not PUBLIC_DEMO:
        return True
    return bool(st.session_state.get("tg_admin"))


def verify_password(value: str) -> bool:
    expected = _admin_password()
    if not expected:
        return False
    return hmac.compare_digest(str(value or "").encode("utf-8"), expected.encode("utf-8"))


def login_widget() -> None:
    """侧边栏管理员入口。仅公开演示模式显示。"""
    if not PUBLIC_DEMO:
        return

    st.markdown(
        "<div class='tg-section-title' style='margin-top:1rem'>"
        + i18n.tr("管理员", "Admin")
        + "</div>",
        unsafe_allow_html=True,
    )
    if not admin_configured():
        st.caption(i18n.tr("未配置 ADMIN_PASSWORD：当前为公开只读模式。", "ADMIN_PASSWORD is not configured: public read-only mode."))
        st.caption(i18n.tr(
            "在平台环境变量或 Secrets 中添加 ADMIN_PASSWORD 后重启应用。",
            "Add ADMIN_PASSWORD to the platform environment or Secrets, then restart the app.",
        ))
        return

    if is_admin():
        st.success(i18n.tr("管理员模式", "Admin mode"))
        if st.button(i18n.tr("退出管理员", "Log out"), key="tg_admin_logout_" + str(id(st)), use_container_width=True):
            st.session_state["tg_admin"] = False
            st.rerun()
        return

    with st.expander("🔐 " + i18n.tr("管理员登录", "Admin login"), expanded=True):
        password = st.text_input(i18n.tr("管理员密码", "Admin password"), type="password", key="tg_admin_password_" + str(id(st)))
        if st.button(i18n.tr("登录", "Sign in"), key="tg_admin_login_" + str(id(st)), use_container_width=True):
            if verify_password(password):
                st.session_state["tg_admin"] = True
                st.rerun()
            else:
                st.error(i18n.tr("密码不正确。", "Incorrect password."))
