@echo off
chcp 65001 >nul
REM DOCX→HTML 변환기 — EXE 빌드 스크립트 (Plan-37 Phase 2)
REM 사전 요구: pip install -r requirements.txt
REM 엔진 파일은 ../converter/ 에서 docx2html.spec 이 참조합니다.

echo [1/2] Building docx2html.exe from spec ...
pyinstaller --clean docx2html.spec

echo.
echo [2/2] Done.
echo Output: dist\docx2html.exe
pause
