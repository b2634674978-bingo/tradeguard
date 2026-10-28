"""管理员门禁：是否要登录，由「有没有配置密码」决定，而不是由运行环境决定。

规则：

- 配置了 ``ADMIN_PASSWORD`` → 任何环境都要求登录（本地也一样）；
- 未配置密码 + 公开演示部署 → 强制只读，谁也不能改数据；
- 未配置密码 + 本地开发 → 开放全部权限（避免本地调试每次都要输密码）。

密码只从 Streamlit Secrets 或服务端环境变量读取，不下发到浏览器。
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

from . import i18n
from .config import PUBLIC_DEMO

ADMIN_FLAG = "tg_admin"
PASSWORD_KEY = "tg_admin_password"
ERROR_FLAG = "tg_admin_error"


def public_mode() -> bool:
    return PUBLIC_DEMO


def _admin_password() -> str | None:
    """管理员密码只从 Secrets 或环境变量读取，禁止硬编码。

    优先级：st.secrets["ADMIN_PASSWORD"] > 环境变量 ADMIN_PASSWORD
            > 环境变量 TRADEGUARD_ADMIN_PASSWORD
    """
    try:
        value = st.secrets.get("ADMIN_PASSWORD")
    except Exception:  # 没有 secrets.toml 或不在 Streamlit 上下文
        value = None
    if value:
        return str(value)
    for name in ("ADMIN_PASSWORD", "TRADEGUARD_ADMIN_PASSWORD"):
        env_value = os.environ.get(name)
        if env_value:
            return env_value
    return None


def admin_configured() -> bool:
    return bool(_admin_password())


def admin_required() -> bool:
    """是否需要登录才能管理数据。

    配了密码就一律要求登录；没配密码时，只有公开部署才强制只读。
    """
    return admin_configured() or PUBLIC_DEMO


def is_admin() -> bool:
    if not admin_required():
        return True
    return bool(st.session_state.get(ADMIN_FLAG))


def public_viewer() -> bool:
    """访客视角：公开部署且未登录。

    只有这种视角才需要脱敏、以及把新举报压进待审核队列。
    本地自用（哪怕配了管理员密码）仍然按完整数据展示、提交即收录，
    否则「配个密码」会意外把本地工作流改掉。
    """
    return PUBLIC_DEMO and not is_admin()


def verify_password(value: str) -> bool:
    expected = _admin_password()
    if not expected:
        return False
    return hmac.compare_digest(str(value or "").encode("utf-8"), expected.encode("utf-8"))


def login_widget() -> None:
    """管理员区块：任何环境都会显示，状态一目了然。"""
    st.markdown(
        "<div class='tg-section-title' style='margin-top:.4rem'>"
        + i18n.tr("管理员", "Admin")
        + "</div>",
        unsafe_allow_html=True,
    )

    if not admin_required():
        st.caption(i18n.tr(
            "本地开发模式：未配置 ADMIN_PASSWORD，当前已具备全部管理权限，无需登录。",
            "Local dev mode: no ADMIN_PASSWORD set, so full admin rights are open without signing in.",
        ))
        st.caption(i18n.tr(
            "在 .streamlit/secrets.toml 或环境变量中配置 ADMIN_PASSWORD 后，将改为需要登录。",
            "Set ADMIN_PASSWORD in .streamlit/secrets.toml or the environment to require a login.",
        ))
        return

    if not admin_configured():
        st.caption(i18n.tr(
            "未配置 ADMIN_PASSWORD：当前为公开只读模式，任何人都无法管理数据。",
            "ADMIN_PASSWORD is not configured: public read-only mode, nobody can manage data.",
        ))
        st.caption(i18n.tr(
            "在平台环境变量或 Secrets 中添加 ADMIN_PASSWORD 后重启应用。",
            "Add ADMIN_PASSWORD to the platform environment or Secrets, then restart the app.",
        ))
        return

    if is_admin():
        st.success(i18n.tr("已登录 · 管理员模式", "Signed in · admin mode"))
        st.button(
            i18n.tr("退出管理员", "Log out"),
            key="tg_admin_logout",
            on_click=_logout,
            use_container_width=True,
        )
        return

    st.caption(i18n.tr(
        "公共访问默认只读；登录后可审核、导入、备份与清理数据。",
        "Public access is read-only; signing in unlocks review, import, backup, and cleanup.",
    ))
    st.text_input(
        i18n.tr("管理员密码", "Admin password"),
        type="password",
        key=PASSWORD_KEY,
        placeholder=i18n.tr("输入密码后点登录", "Enter the password, then sign in"),
    )
    # 用回调而不是脚本内 st.rerun()：否则页面会残留「只读」区块与「管理区」同时出现
    st.button(
        i18n.tr("登录", "Sign in"),
        key="tg_admin_login",
        on_click=_login,
        use_container_width=True,
    )
    if st.session_state.pop(ERROR_FLAG, False):
        st.error(i18n.tr("密码不正确。", "Incorrect password."))


def _login() -> None:
    entered = st.session_state.get(PASSWORD_KEY, "")
    if verify_password(entered):
        st.session_state[ADMIN_FLAG] = True
        st.session_state[ERROR_FLAG] = False
    else:
        st.session_state[ADMIN_FLAG] = False
        st.session_state[ERROR_FLAG] = True


def _logout() -> None:
    st.session_state[ADMIN_FLAG] = False
    st.session_state.pop(PASSWORD_KEY, None)

