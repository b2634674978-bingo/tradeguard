"""应用配置：本地默认落地；Streamlit Cloud 使用可写临时目录。

重要：Streamlit Community Cloud 的容器文件系统是临时的，应用重启/重新部署后
SQLite 数据会丢失。公开演示版只应放虚构数据；真实数据请用私有部署或外部数据库。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

APP_NAME = "TradeGuard"
APP_TITLE = "TradeGuard · 外贸防骗情报库"
APP_TAGLINE = "先查一查，再谈生意"
VERSION = "0.1.0"

# 项目根目录（app.py 所在目录）
BASE_DIR = Path(__file__).resolve().parent.parent

# Streamlit Community Cloud 的仓库路径固定为 /mount/src；本地 Windows 不会命中。
IS_CLOUD = bool(os.environ.get("TRADEGUARD_CLOUD")) or Path("/mount/src").exists()
PUBLIC_DEMO = os.environ.get("TRADEGUARD_PUBLIC_DEMO") == "1" or IS_CLOUD

if os.environ.get("TRADEGUARD_DATA_DIR"):
    DATA_DIR = Path(os.environ["TRADEGUARD_DATA_DIR"])
elif IS_CLOUD:
    # 云端仓库目录可能只读/会被重建；放到系统临时目录，保证 SQLite 可写。
    DATA_DIR = Path(tempfile.gettempdir()) / "tradeguard"
else:
    DATA_DIR = BASE_DIR / "data"

DB_PATH = Path(os.environ.get("TRADEGUARD_DB_PATH", DATA_DIR / "tradeguard.db"))

# 上传与解析上限
MAX_UPLOAD_BYTES = 8 * 1024 * 1024          # 8 MB
MAX_CHAT_CHARS = 2_000_000                   # 解析上限，防超大文件卡死
DEFAULT_LIMIT = 100


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
