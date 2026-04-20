@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  Upload Standalone Test Server (Plan-35)
echo ============================================
echo  Port    : 8080
echo  Host    : 0.0.0.0
echo  Local   : http://localhost:8080/
echo  Logs    : server.log
echo ============================================
echo.
python server.py
echo.
echo [server stopped]
pause
