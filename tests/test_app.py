from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"
PAGES = ["查询验证", "上报记录", "情报库", "数据看板", "帮助与合规"]


def test_app_smoke():
    # 用绝对路径：AppTest 对相对路径是按「调用方文件所在目录」解析的
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    assert not app.exception
    assert app.radio[0].options == PAGES


def test_help_page_renders():
    """前台帮助页：只讲用法与边界，不出现任何运维内容。"""
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    app.radio[0].set_value("帮助与合规").run()
    assert not app.exception

    text = " ".join(item.value for item in app.caption) + " ".join(
        item.value for item in app.markdown
    )
    assert "合规边界" in text
    assert "存储引擎" not in text


def test_query_page_renders():
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    app.radio[0].set_value("查询验证").run()
    assert not app.exception
    app.text_input[0].set_value("+1 555 010 4477").run()
    assert not app.exception
