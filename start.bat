@echo off
chcp 65001 >nul
echo ==================================================
echo   BidTool 投标工具 - 启动脚本
echo ==================================================

REM 检查 Python
where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 检查依赖...
pip install -r requirements.txt -q

REM 启动 Flask 后端
echo [2/3] 启动后端服务（端口 5000）...
start "BidTool Backend" cmd /k "cd /d %~dp0 && python backend/app.py"

REM 等待后端启动
echo [3/3] 等待后端启动...
timeout /t 3 >nul

REM 打开浏览器
echo 正在打开浏览器...
start http://127.0.0.1:5000

echo.
echo ==================================================
echo   启动完成！
echo   浏览器地址：http://127.0.0.1:5000
echo   后端日志窗口请勿关闭
echo ==================================================
pause
