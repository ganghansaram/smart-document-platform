@echo off
REM 장절번호 평문화 도구 — exe 빌드 스크립트
REM 사전 요구: pip install pyinstaller pywin32

echo [1/2] Building exe...
pyinstaller --onefile --windowed --name "장절번호_평문화" ^
    --icon=NONE ^
    heading_numberer.py

echo [2/2] Done.
echo Output: dist\장절번호_평문화.exe
pause
