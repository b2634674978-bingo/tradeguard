"""应用配置：本地默认落地 SQLite；配置 DATABASE_URL 后切换到 PostgreSQL 持久化。

存储优先级：
1. `DATABASE_URL`（或 `TRADEGUARD_DATABASE_URL`）—— PostgreSQL，云端重启不丢数据；
2. 未配置时回落到 SQLite：本地写 `data/`，云端写系统临时目录（重启即清空）。

注意：Streamlit Community Cloud / Render 免费版的文件系统是临时的，
不配 DATABASE_URL 时 SQLite 数据会在重启、休眠或重新部署后丢失。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

APP_NAME = "TradeGuard"
APP_TITLE = "TradeGuard · 外贸防骗情报库"
APP_TAGLINE = "先查一查，再谈生意"
VERSION = "0.2.0"

# 项目根目录（app.py 所在目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# Streamlit Community Cloud = /mount/src；Render = RENDER=true；本地 Windows 不会命中。
IS_CLOUD = (
    bool(os.environ.get("TRADEGUARD_CLOUD"))
    or Path("/mount/src").exists()
    or os.environ.get("RENDER", "").lower() == "true"
    or bool(os.environ.get("RENDER_SERVICE_ID"))
)
PUBLIC_DEMO = os.environ.get("TRADEGUARD_PUBLIC_DEMO", "1" if IS_CLOUD else "0") == "1"


def _read_secret(name: str) -> str:
    """读 Streamlit Secrets；不在 Streamlit 运行时（如 pytest）直接返回空。"""
    if "streamlit" not in sys.modules:
        return ""
    try:
        import streamlit as st

        value = st.secrets.get(name, "")
        return str(value or "").strip()
    except Exception:  # noqa: BLE001 - 没有 secrets.toml 时会抛异常
        return ""


# 云端持久化数据库：环境变量优先，其次 Streamlit Secrets
DATABASE_URL = (
    os.environ.get("DATABASE_URL", "")
    or os.environ.get("TRADEGUARD_DATABASE_URL", "")
    or _read_secret("DATABASE_URL")
).strip()
IS_POSTGRES = bool(DATABASE_URL)

if os.environ.get("TRADEGUARD_DATA_DIR"):
    DATA_DIR = Path(os.environ["TRADEGUARD_DATA_DIR"])
elif IS_CLOUD:
    # 云端仓库目录可能只读/会被重建；放到系统临时目录，保证 SQLite 可写。
    DATA_DIR = Path(tempfile.gettempdir()) / "tradeguard"
else:
    DATA_DIR = BASE_DIR / "data"

DB_PATH = Path(os.environ.get("TRADEGUARD_DB_PATH", DATA_DIR / "tradeguard.db"))

# 上传与解析上限
MAX_UPLOAD_BYTES = 8 * 1024 * 1024          # 8 MB（旧聊天文件）
MAX_IMAGE_BYTES = 10 * 1024 * 1024           # 单张截图上限 10 MB
MAX_IMAGES = 8                               # 单条举报最多 8 张截图
MAX_CHAT_CHARS = 2_000_000                   # 解析上限，防超大文件卡死
DEFAULT_LIMIT = 100


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
