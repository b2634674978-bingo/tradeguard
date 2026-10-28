import os
import tempfile
import uuid
from pathlib import Path

import pytest

# 测试使用项目内的临时目录：Windows 沙箱下系统临时目录可能不可写。
BASE = Path(__file__).resolve().parent / ".tmp"
BASE.mkdir(parents=True, exist_ok=True)

_TMP = tempfile.mkdtemp(prefix="app-", dir=BASE)
os.environ.setdefault("TRADEGUARD_DATA_DIR", _TMP)
os.environ.setdefault("TRADEGUARD_DB_PATH", os.path.join(_TMP, "tradeguard.db"))


@pytest.fixture(autouse=True)
def isolate_runtime(monkeypatch):
    """让测试不读本地 .streamlit/secrets.toml。

    否则开发者一旦配了 DATABASE_URL，测试就会连真实线上库写数据；
    配了 ADMIN_PASSWORD，页面又会变成只读，测试结果取决于本机配置。
    这里统一钉死为：本地 SQLite + 未配置管理员密码。
    """
    import tradeguard.auth as auth
    import tradeguard.config as config

    monkeypatch.setattr(config, "DATABASE_URL", "", raising=False)
    monkeypatch.setattr(config, "IS_POSTGRES", False, raising=False)
    monkeypatch.setattr(auth, "PUBLIC_DEMO", False, raising=False)
    monkeypatch.setattr(auth, "_admin_password", lambda: None, raising=False)


@pytest.fixture()
def temp_dir():
    path = BASE / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    yield path
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            child.rmdir()
    path.rmdir()
