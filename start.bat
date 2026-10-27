@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 如果本机已安装 .pylibs（开发机/演示机），直接使用，免去重复装依赖
if exist ".pylibs\streamlit\__init__.py" (
    echo [TradeGuard] 使用已安装的本地运行库...
    set "PYTHONPATH=%~dp0.pylibs"
    python -m streamlit run app.py --global.developmentMode=false --server.port 8501
    goto :eof
)

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not exist ".venv\Scripts\python.exe" (
    echo [TradeGuard] 首次运行，正在创建虚拟环境...
    python -m venv .venv
    if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
)
echo [TradeGuard] 检查依赖...
"%PYTHON%" -m pip install -r requirements.txt
echo [TradeGuard] 启动中，浏览器将打开 http://127.0.0.1:8501 ...
"%PYTHON%" -m streamlit run app.py --server.port 8501
pause
