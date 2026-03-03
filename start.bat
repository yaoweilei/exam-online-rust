@echo off
chcp 65001 >nul
echo ========================================
echo   在线试卷系统
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [2/3] 安装依赖包...
    pip install -r requirements.txt
) else (
    echo [2/3] 依赖已安装
)

echo [3/3] 启动服务器...
echo.
echo ========================================
echo   服务器启动成功！
echo   访问地址: http://localhost:8000
echo ========================================
echo.

python server.py

pause
