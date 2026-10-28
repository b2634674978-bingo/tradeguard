"""管理员门禁：是否要登录由「有没有配密码」决定，而不是由运行环境决定。"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import tradeguard.auth as auth

APP = Path(__file__).resolve().parent.parent / "app.py"


def _open_settings(app: AppTest) -> AppTest:
    app.run()
    app.radio[0].set_value("设置与合规").run()
    return app


def _all_text(app: AppTest) -> str:
    parts = [item.value for item in app.caption]
    parts += [item.value for item in app.markdown]
    parts += [item.value for item in app.success]
    return " ".join(str(part) for part in parts)


def _button(app: AppTest, label: str):
    for button in app.button:
        if button.label == label:
            return button
    raise AssertionError(f"找不到按钮：{label}（现有：{[b.label for b in app.button]}）")


@pytest.fixture()
def password(monkeypatch):
    monkeypatch.setattr(auth, "_admin_password", lambda: "s3cret-pass")
    return "s3cret-pass"


def test_local_without_password_is_open():
    """未配置密码 + 本地环境：不拦人，但要明说为什么没有登录框。"""
    app = _open_settings(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    assert "管理员密码" not in [item.label for item in app.text_input]
    text = _all_text(app)
    assert "本地开发模式" in text
    # 未登录也应有完整管理区
    assert "数据与备份" in text


def test_password_shows_login_form(password):
    app = _open_settings(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    assert "管理员密码" in [item.label for item in app.text_input]
    text = _all_text(app)
    assert "数据与备份" not in text, "未登录不应看到备份与清理入口"
    assert "管理操作已锁定" in text


def test_wrong_password_rejected(password):
    app = _open_settings(AppTest.from_file(str(APP), default_timeout=60))
    app.text_input(key="tg_admin_password").set_value("wrong").run()
    _button(app, "登录").click().run()
    assert not app.exception
    assert "密码不正确" in " ".join(item.value for item in app.error)


def test_login_unlocks_admin_area(password):
    app = _open_settings(AppTest.from_file(str(APP), default_timeout=60))
    app.text_input(key="tg_admin_password").set_value(password).run()
    _button(app, "登录").click().run()
    assert not app.exception
    text = _all_text(app)
    assert "已登录" in text
    assert "数据与备份" in text
    # 登录后不能再残留只读区块，否则页面上会同时出现两套互斥内容
    assert "公开只读模式" not in text
    assert "管理操作已锁定" not in text


def test_public_demo_without_password_is_read_only(monkeypatch):
    """公开部署若忘配密码，宁可只读到底，也不留后门。"""
    monkeypatch.setattr(auth, "PUBLIC_DEMO", True, raising=False)
    app = _open_settings(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    text = _all_text(app)
    assert "未配置 ADMIN_PASSWORD" in text
    assert "数据与备份" not in text
