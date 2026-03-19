# DOCX → HTML 변환기

Word 문서(.docx)를 HTML로 변환하는 독립 실행 프로그램입니다.

## 요구사항

- **Windows 10/11** (64-bit)
- Python 설치 **불필요** (EXE에 포함)
- 장절번호 전처리 사용 시: **Microsoft Word** 설치 필요

## 사용법

### GUI 모드 (더블클릭)

`docx2html.exe`를 더블클릭하면 GUI가 실행됩니다.

1. **찾아보기** 또는 파일 드래그앤드롭으로 DOCX 파일 선택
2. 출력 위치 확인 (기본: 입력파일과 같은 위치)
3. 필요 시 **고급 옵션** 설정
4. **변환** 클릭
5. 완료 후 **폴더 열기**로 결과 확인

### CLI 모드 (명령줄)

```cmd
docx2html.exe <입력파일.docx> [옵션]
```

#### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `-o`, `--output` | 출력 디렉토리 | 입력파일 위치 |
| `--html-name` | 출력 HTML 파일명 | 입력파일명.html |
| `--image-dir` | 이미지 폴더명 | {파일명}_images |
| `--image-prefix` | HTML 내 이미지 경로 접두사 | 상대경로 자동 |
| `--no-preprocess` | 장절번호 전처리 건너뛰기 | - |
| `--verbose` | 상세 로그 출력 | - |

#### 종료 코드

| 코드 | 의미 |
|------|------|
| 0 | 성공 |
| 1 | 변환 실패 |
| 2 | 파일 없음 / 잘못된 형식 |

#### 예시

```cmd
REM 기본 변환
docx2html.exe 매뉴얼.docx

REM 출력 디렉토리 지정
docx2html.exe 매뉴얼.docx -o C:\output

REM 이미지 경로 커스텀 (웹 서버용)
docx2html.exe 매뉴얼.docx --html-name content.html --image-dir img --image-prefix /static/images/

REM 장절번호 전처리 없이 변환
docx2html.exe 매뉴얼.docx --no-preprocess

REM 상세 로그
docx2html.exe 매뉴얼.docx --verbose
```

### 웹 프로세스 통합 (BAT 래퍼 예시)

```bat
@echo off
REM convert.bat — 웹 프로세스에서 호출
docx2html.exe "%~1" -o "%~dp1output" --image-prefix "/uploads/images/" --no-preprocess
if %ERRORLEVEL% NEQ 0 (
    echo 변환 실패: 코드 %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
echo 변환 완료
```

## 출력 구조

```
출력 디렉토리/
├── {파일명}.html           ← 변환된 HTML
└── {파일명}_images/        ← 추출된 이미지
    ├── image_abc123.png
    ├── image_def456.jpg
    └── ...
```

- HTML은 `<body>` 내용만 포함 (fragment)하며, 별도 `<html>`/`<head>` 감싸기가 필요할 수 있습니다.
- 이미지 파일명은 내용 해시 기반이므로 동일 이미지는 중복 저장되지 않습니다.

## 기능

- Word 스타일 → HTML 태그 매핑 (제목, 본문, 리스트 등)
- 표 변환 (병합 셀 지원: colspan, rowspan)
- 이미지 추출 (JPEG, PNG, EMF, WMF 등)
- 수식 변환 (OMML → MathML)
- 장절번호 평문화 (Word COM, 선택적)
- 각주/미주 변환

## 빌드 (개발자용)

```cmd
pip install -r requirements.txt
build.bat
```

결과: `dist/docx2html.exe` (~23MB)

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| "장절번호 전처리를 건너뜁니다" | Word 미설치 | `--no-preprocess` 사용 또는 Word 설치 |
| 이미지가 HTML에 포함되지 않음 | Word 도형/그리기 객체 | Word에서 해당 도형 → "그림(PNG)"으로 변환 후 재변환 |
| CLI에서 출력이 안 보임 | `--windowed` 빌드 | `--verbose` 추가 또는 출력을 파일로 리다이렉트 |
