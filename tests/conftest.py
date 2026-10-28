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
