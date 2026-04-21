# DOCX → HTML 변환기

Word 문서(.docx)를 HTML로 변환하는 독립 실행 프로그램입니다.

## 요구사항

- **Windows 10/11** (64-bit)
- Python 설치 **불필요** (EXE에 포함)
- Microsoft Word 설치: **선택** — 없어도 대부분의 문서는 변환되지만,
  자동번호가 `numbering.xml` 로만 정의된 구조에서 전처리가 있으면 더 정확
- DRM 적용 환경: 업로드 전 **DRM 해제 필수** (서버/EXE 가 DRM 을 풀지 않음)

## 사용법

### GUI 모드 (더블클릭)

`docx2html.exe`를 더블클릭하면 GUI가 실행됩니다.

1. **찾아보기** 또는 파일 드래그앤드롭으로 DOCX 파일 선택
2. 출력 위치 확인 (기본: 입력파일과 같은 위치)
3. 필요 시 **고급 옵션** 설정
4. **변환** 클릭
5. 완료 후 **폴더 열기**로 결과 확인

#### DRM 환경에서 장절번호가 누락될 때

회사 DRM이 적용된 환경에서는 전처리 임시 파일이 암호화되어 장절번호가 빠질 수 있습니다. 이 경우 2단계 워크플로우를 사용하세요:

1. **전처리만** 클릭 → 저장 위치 선택 → 장절번호가 평문화된 `.docx` 생성
2. 생성된 파일을 **DRM 해제** (보안 해제)
3. 해제된 파일을 다시 선택 → **장절번호 전처리** 체크 해제 → **변환** 클릭

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
| `--preprocess-only` | 전처리만 수행 (DRM 환경용, .docx 출력) | - |
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

REM 전처리만 수행 (DRM 환경용 2단계 워크플로우)
docx2html.exe 매뉴얼.docx --preprocess-only
REM → 매뉴얼_preprocessed.docx 생성 → DRM 해제 후 아래 명령으로 변환
docx2html.exe 매뉴얼_preprocessed.docx --no-preprocess

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

## 헤딩 감지 방식

문서의 제목(h1~h6)을 다음 우선순위로 감지합니다:

| 순위 | 방식 | 설명 |
|------|------|------|
| 1 | outlineLvl (OOXML) | Word 내부 개요 수준. 가장 정확하며 로케일 무관 |
| 2 | style_id | "Heading1" 등 내부 스타일 ID. 로케일 무관 |
| 3 | style.name | "제목 1", "Heading 1" 등 표시 이름 |
| 4 | 폰트 크기 | 최후 수단. 본문 스타일(Normal 등)은 제외 |

커스텀 스타일이라도 Word에서 개요 수준을 설정했다면 정상 감지됩니다. `config.json`의 `style_mapping` 섹션에서 매핑을 추가/변경할 수 있습니다.

## 기능

- Word 스타일 → HTML 태그 매핑 (h1~h6, 본문, 리스트 등)
- **자동번호 재현** — `numbering.xml` 기반으로 "1.1.2" 등 다단계 번호 자체 생성 (Word 없는 환경에서도 대부분 동작)
- **복합 캡션** — "그림 3-1" 처럼 STYLEREF + SEQ 합성 필드 정확 재현
- **SEQ 스위치 지원** — `\r` (reset), `\s` (heading 기준 리셋), `\c` (repeat), `\* ARABIC/ROMAN/alphabetic`
- 표 변환 (병합 셀 지원: colspan, rowspan)
- 이미지 추출 (JPEG, PNG, EMF, WMF 등, 내용 해시 중복 제거)
- 수식 변환 (OMML → MathML)
- 장절번호 평문화 (Word COM, 선택적 — 가용 시 자동 사용)
- 각주/미주 변환
- **출력 HTML 에 provenance 주석 embed** — 변환기 버전·일시 영구 기록 (재변환·디버깅 추적용)

## 출력 메타데이터 (provenance)

생성된 HTML 의 첫 줄에 아래와 같은 주석이 자동 삽입됩니다:

```html
<!-- converter: smart-doc-platform/docx-converter 1.4.0 | adapter: word_com | date: 2026-04-21T14:30:00+00:00 -->
```

- `adapter` 값: `word_com` (정상 전처리) / `word_com_failed` / `word_com_error` / `skip` (`--no-preprocess` 사용 시)
- 고객 제보 시 HTML 앞머리만 붙여 보내면 어느 버전·어떤 환경에서 변환됐는지 즉시 확인 가능

## 빌드 (개발자용)

```cmd
pip install -r requirements.txt
build.bat
```

결과: `dist/docx2html.exe` (~24 MB)

**참고**: 엔진 코드는 `../converter/` 에 있으며, `docx2html.spec` 의 `pathex` 설정으로 자동 번들됩니다. 빌드 전 `../converter/` 디렉토리가 존재해야 합니다.

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| "장절번호 전처리를 건너뜁니다" | Word 미설치 | Word 설치 (선택) 또는 `--no-preprocess` 사용 — 대부분의 문서는 자체 번호 생성으로 정상 변환됨 |
| 장절번호가 HTML에 누락 | DRM 이 전처리 파일 암호화 (구 EXE) | 현 버전은 `.docx_1` 확장자로 DRM 우회. 여전히 문제면 "전처리만" → DRM 해제 → 변환 (2단계) |
| 복합 캡션 "그림 3-1" 이 "그림 1" 로 표시 | STYLEREF 가 해당 heading 을 못 찾음 | Word 에서 heading 1 스타일 적용 확인, F9 로 필드 업데이트 후 저장 |
| 헤딩 서식이 뒤죽박죽 | Word에서 스타일 미적용 (폰트 크기만 변경) | Word 에서 "제목 1" 등 스타일 적용 권장 |
| 이미지가 HTML에 포함되지 않음 | Word 도형/그리기 객체 (`v:shape`) | Word 에서 해당 도형 → "그림(PNG)"으로 변환 후 재변환 |
| CLI에서 출력이 안 보임 | `--windowed` 빌드 | `--verbose` 추가 또는 출력을 파일로 리다이렉트 |
| Windows Defender 등이 EXE 를 탐지 | PyInstaller 생성 EXE 의 알려진 false positive | 사내 AV 화이트리스트 등록. EXE 자체는 안전 |
