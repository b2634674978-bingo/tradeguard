"""管理员后台与前台的分界：普通用户看不到任何管理入口。"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import tradeguard.auth as auth

APP = Path(__file__).resolve().parent.parent / "app.py"


def _open(app: AppTest, page: str) -> AppTest:
    app.run()
    app.radio[0].set_value(page).run()
    return app


def _open_admin(app: AppTest) -> AppTest:
    return _open(app, "管理后台")


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
def admin_route(monkeypatch):
    """模拟访问 ?admin=1（AppTest 不支持直接设置 query_params）。"""
    monkeypatch.setattr(auth, "admin_entry_requested", lambda: True, raising=False)


@pytest.fixture()
def password(monkeypatch):
    monkeypatch.setattr(auth, "_admin_password", lambda: "s3cret-pass")
    return "s3cret-pass"


# ---------------------------------------------------------------- 前台纯净


def test_public_pages_have_no_admin_entry():
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    assert app.radio[0].options == ["查询验证", "上报记录", "情报库", "数据看板", "帮助与合规"]

    for page in app.radio[0].options:
        _open(app, page)
        assert not app.exception
        text = _all_text(app)
        assert "管理员密码" not in text, f"{page} 不应出现登录框"
        assert "数据与备份" not in text, f"{page} 不应出现备份入口"
        assert "危险操作" not in text, f"{page} 不应出现清空入口"


def test_help_page_explains_product():
    app = AppTest.from_file(str(APP), default_timeout=60)
    _open(app, "帮助与合规")
    assert not app.exception
    text = _all_text(app)
    assert "合规边界" in text
    assert "我是当事人" in text


# ---------------------------------------------------------------- 管理后台


def test_admin_route_exposes_backend(admin_route):
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    assert "管理后台" in app.radio[0].options


def test_local_without_password_is_open(admin_route):
    app = _open_admin(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    assert "管理员密码" not in [item.label for item in app.text_input]
    text = _all_text(app)
    assert "本地开发模式" in text
    assert "数据与备份" in text


def test_password_shows_login_form(admin_route, password):
    app = _open_admin(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    assert "管理员密码" in [item.label for item in app.text_input]
    text = _all_text(app)
    assert "数据与备份" not in text, "未登录不应看到备份与清理入口"
    assert "请输入密码" in text or "未登录" in text


def test_wrong_password_rejected(admin_route, password):
    app = _open_admin(AppTest.from_file(str(APP), default_timeout=60))
    app.text_input(key="tg_admin_password").set_value("wrong").run()
    _button(app, "登录").click().run()
    assert not app.exception
    assert "密码不正确" in " ".join(item.value for item in app.error)


def test_login_unlocks_admin_area(admin_route, password):
    app = _open_admin(AppTest.from_file(str(APP), default_timeout=60))
    app.text_input(key="tg_admin_password").set_value(password).run()
    _button(app, "登录").click().run()
    assert not app.exception
    text = _all_text(app)
    assert "已登录" in text
    assert "数据与备份" in text


def test_public_demo_without_password_is_read_only(admin_route, monkeypatch):
    """公开部署若忘配密码，宁可只读到底，也不留后门。"""
    monkeypatch.setattr(auth, "PUBLIC_DEMO", True, raising=False)
    app = _open_admin(AppTest.from_file(str(APP), default_timeout=60))
    assert not app.exception
    text = _all_text(app)
    assert "未配置 ADMIN_PASSWORD" in text
    assert "数据与备份" not in text
