@echo off
chcp 65001 >nul
REM DOCX→HTML 변환기 — EXE 빌드 스크립트
REM 사전 요구: pip install -r requirements.txt

echo [1/2] Building docx2html.exe ...
pyinstaller --onefile --windowed --name "docx2html" ^
    --add-data "config.json;." ^
    --hidden-import win32com ^
    --hidden-import win32com.client ^
    --hidden-import pythoncom ^
    --hidden-import pywintypes ^
    docx2html.py

echo.
echo [2/2] Done.
echo Output: dist\docx2html.exe
pause
