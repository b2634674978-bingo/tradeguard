#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ -d ".pylibs/streamlit" ]; then
  export PYTHONPATH="$PWD/.pylibs"
  exec python -m streamlit run app.py --global.developmentMode=false --server.port 8501
fi

if [ ! -x .venv/bin/python ]; then
  echo "[TradeGuard] 首次运行，正在创建虚拟环境..."
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
echo "[TradeGuard] 启动中，浏览器将打开 http://127.0.0.1:8501 ..."
.venv/bin/python -m streamlit run app.py --server.port 8501
