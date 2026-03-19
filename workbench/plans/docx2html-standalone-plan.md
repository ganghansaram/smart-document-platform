# DOCX→HTML 독립 변환기 (docx2html-standalone) 계획서

> **목적**: 외부 개발업체(전자정부프레임워크 기반) 및 문서 작성자에게 제공할 단일 EXE 변환기
> **산출물**: `docx2html.exe` (듀얼 모드: GUI + CLI) + 사용 설명서
> **작업 디렉토리**: `tools/docx2html-standalone/`

---

## 1. 배경

- 사내 웹북 개발업체가 DOCX→HTML 변환 기능을 자체 웹 프로세스에 통합하고자 함
- 우리 플랫폼의 `tools/converter/`는 Python 라이브러리로 백엔드에서 직접 import하는 구조
- 업체는 Python 환경이 없으므로 **단일 EXE**로 제공하여 BAT/프로세스에서 호출하는 방식 필요
- 업체 탑재 여부가 미확정 → **문서 작성자에게 직접 배포**할 가능성도 있음 → GUI 필수
- 우리 플랫폼에서는 이 EXE를 사용하지 않음 → 별도 디렉토리에서 독립 관리

## 2. 소스 분석

### 복제 대상 파일 (tools/converter/ → tools/docx2html-standalone/)

| 파일 | 줄수 | 역할 | 수정 필요 |
|------|------|------|-----------|
| `converter.py` | 1430 | DocxConverter 핵심 로직 | ✅ config 경로 PyInstaller 호환 |
| `omml_to_mathml.py` | — | OMML→MathML 수식 변환 | ❌ 그대로 |
| `utils.py` | — | 로거, 유틸, 예외 클래스 | ⚠️ 경미한 조정 |
| `word_preprocessor.py` | — | COM 장절번호 평문화 | ⚠️ config import 제거 |
| `config.json` | — | 스타일 매핑 설정 | ❌ 그대로 |

### 제외 파일

| 파일 | 사유 |
|------|------|
| `pdf_converter.py` | Word 변환 전용, PDF 불필요 |
| `requirements.txt` | EXE용으로 새로 작성 |

### 현재 이미지 처리 구조

```
converter.py:140  → image_dir = get_image_dir(output_path)     # {문서명}_images/
converter.py:946  → filename = f"image_{hash_name}{ext}"        # image_md5해시12자.png
converter.py:953  → rel_path = os.path.relpath(image_path, ...)  # 상대경로로 HTML에 삽입
```

- **이미지 폴더**: `{HTML파일명}_images/` — HTML과 같은 디렉토리에 생성
- **이미지 파일명**: `image_{md5해시12자}.{ext}` — 내용 기반 해시 (중복 방지)
- **HTML 내 경로**: `<img src="{파일명}_images/image_xxx.png">` — 상대경로

### 업체 요청사항: 경로 커스터마이징

업체가 자체 웹 프로세스에 통합할 때, HTML 내 이미지 경로를 서버 구조에 맞춰야 함.

| 옵션 | 기본값 | 예시 | 설명 |
|------|--------|------|------|
| `--image-dir` | `{파일명}_images` | `assets` | 이미지 저장 폴더명 변경 |
| `--image-prefix` | (상대경로 자동) | `/static/img/` | HTML 내 `<img src>` 경로 접두사 |
| `--html-name` | `{입력파일명}.html` | `content.html` | 출력 HTML 파일명 지정 |

예시:
```bash
# 기본 동작
docx2html.exe 매뉴얼.docx
# → 매뉴얼.html + 매뉴얼_images/image_xxx.png
# → <img src="매뉴얼_images/image_xxx.png">

# 업체 커스텀
docx2html.exe 매뉴얼.docx --html-name content.html --image-dir img --image-prefix /uploads/doc123/img/
# → content.html + img/image_xxx.png
# → <img src="/uploads/doc123/img/image_xxx.png">
```

### 의존성

| 패키지 | 용도 | EXE 번들 |
|--------|------|----------|
| `python-docx` | DOCX 파싱 | ✅ 필수 |
| `pywin32` | COM 전처리 (Word 설치 시) | ⚠️ 선택 |
| `tkinterdnd2` | 드래그앤드롭 (GUI) | ⚠️ 선택 (없으면 찾아보기만) |
| `pyinstaller` | EXE 빌드 도구 | 빌드 시만 |

> **주의**: COM 전처리(`word_preprocessor.py`)는 대상 PC에 **Microsoft Word 설치 필수**.
> Word 미설치 환경에서는 전처리 없이 변환 진행.

## 3. 인터페이스 설계

### 듀얼 모드 (하나의 EXE)

```
docx2html.exe                        ← 인자 없이 실행 → GUI
docx2html.exe input.docx -o out/     ← 인자 있으면 → CLI
```

> 전례: `tools/heading-numberer/heading_numberer.py`가 동일 패턴으로 구현됨

### CLI 모드

```
사용법:
  docx2html.exe <입력.docx> [옵션]

필수 인자:
  입력.docx               변환할 Word 파일 경로

옵션:
  -o, --output DIR        출력 디렉토리 (기본: 입력파일 위치)
  --html-name NAME        출력 HTML 파일명 (기본: 입력파일명.html)
  --image-dir NAME        이미지 폴더명 (기본: {파일명}_images)
  --image-prefix PATH     HTML 내 이미지 경로 접두사 (기본: 상대경로 자동)
  --no-preprocess         장절번호 평문화 건너뛰기
  --verbose               상세 로그 출력

종료 코드:
  0  성공
  1  변환 실패
  2  파일 없음/잘못된 형식
```

### GUI 모드 (Tkinter)

```
┌─────────────────────────────────────────┐
│  DOCX → HTML 변환기                     │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────┐            │
│  │  파일을 드래그하거나    │  [찾아보기] │
│  │  여기에 놓으세요        │            │
│  └─────────────────────────┘            │
│                                         │
│  입력: C:\docs\매뉴얼.docx              │
│  출력: C:\docs\                         │
│                                         │
│  ☑ 장절번호 전처리 (Word 필요)          │
│                                         │
│  ▸ 고급 옵션                            │
│    HTML 파일명: [            ] (비우면 원본명) │
│    이미지 폴더: [            ] (비우면 자동) │
│    이미지 경로: [            ] (비우면 상대경로) │
│                                         │
│  [==========>          ] 60%            │
│  이미지 추출 중...                      │
│                                         │
│           [ 변환 ]  [ 폴더 열기 ]       │
└─────────────────────────────────────────┘
```

**GUI 기능:**
- 파일 드래그앤드롭 또는 찾아보기 버튼
- 출력 디렉토리 선택
- 장절번호 전처리 체크박스
- 고급 옵션 접기/펼치기 (HTML 파일명, 이미지 폴더명, 이미지 경로 접두사)
- 진행률 바 + 상태 메시지
- 완료 시 "폴더 열기" 버튼 활성화

## 4. 디렉토리 구조

```
tools/docx2html-standalone/
├── docx2html.py               ← 메인 진입점 (GUI/CLI 분기 + argparse)
├── converter.py                ← 원본 복제 (config 경로 처리 수정)
├── omml_to_mathml.py           ← 원본 복제 (수정 없음)
├── utils.py                    ← 원본 복제 (경미한 조정)
├── word_preprocessor.py        ← 원본 복제 (config import 제거)
├── config.json                 ← 원본 복제 (수정 없음)
├── build.bat                   ← PyInstaller 빌드 스크립트
├── docx2html.spec              ← PyInstaller 설정
├── requirements.txt            ← python-docx, pywin32, pyinstaller
├── README.md                   ← 업체/사용자용 설명서
└── dist/                       ← 빌드 산출물 (.gitignore)
    └── docx2html.exe
```

## 5. 작업 단계

### Phase 1: 파일 복제 및 독립화

- [ ] `tools/docx2html-standalone/` 디렉토리 생성
- [ ] 대상 파일 5개 복제
- [ ] `converter.py` — `_load_config()` 경로를 PyInstaller 호환으로 수정
  ```python
  base_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
  ```
- [ ] `converter.py` — 이미지 경로 커스터마이징 지원
  - `convert()` 메서드에 `image_dir_name`, `image_prefix` 파라미터 추가
  - `_process_images()` → 커스텀 폴더명 사용
  - HTML 삽입 시 `image_prefix` 적용 (지정 시 상대경로 대신 접두사+파일명)
- [ ] `word_preprocessor.py` — `from config import UPLOAD_TEMP_DIR` 블록 제거
- [ ] `utils.py` — 백엔드 의존 확인 및 제거 (있다면)

### Phase 2: CLI 진입점 구현

- [ ] `docx2html.py` — argparse CLI 구현
  - 입력 파일, `-o`, `--html-name`, `--image-dir`, `--image-prefix`, `--no-preprocess`, `--verbose`
- [ ] 종료 코드: 0=성공, 1=변환 실패, 2=파일 없음
- [ ] stdout에 결과 경로 출력 (업체 프로세스 연동용)
- [ ] CLI 단독 테스트

### Phase 3: GUI 구현

- [ ] Tkinter GUI (듀얼 모드: `sys.argv` 유무로 분기)
- [ ] 파일 선택 (찾아보기 + 드래그앤드롭)
- [ ] 옵션 UI (전처리 체크박스, 고급 옵션 접기/펼치기)
- [ ] 진행률 바 + 상태 메시지 (스레드에서 변환 실행)
- [ ] 완료 시 출력 폴더 열기 버튼
- [ ] 오류 시 메시지 박스

### Phase 4: PyInstaller 빌드 구성

- [ ] `requirements.txt` 작성
- [ ] `build.bat` 작성
  ```bat
  @echo off
  pyinstaller --onefile --windowed --name "docx2html" ^
      --add-data "config.json;." ^
      docx2html.py
  ```
  > `--windowed`: GUI 모드에서 콘솔 창 숨김. CLI 호출 시에도 stdout/stderr 동작함.
- [ ] 빌드 테스트 및 실행 검증 (GUI + CLI 양쪽)
- [ ] `dist/` → `.gitignore`에 추가

### Phase 5: 문서 및 배포 준비

- [ ] `README.md` 작성
  - 설치 요구사항 (없음 / Word 설치 시 추가 기능)
  - GUI 사용법 (스크린샷)
  - CLI 사용법 + 예제
  - 업체용 BAT 통합 예시
  - 오류 대응 가이드
- [ ] 업체용 래퍼 BAT 예시:
  ```bat
  @echo off
  docx2html.exe "%~1" -o "%~dp1output" --image-prefix "/static/images/"
  if %ERRORLEVEL% NEQ 0 echo 변환 실패: %ERRORLEVEL%
  ```

## 6. 고려사항

### pywin32 번들 이슈
- PyInstaller + pywin32 조합은 DLL 누락 문제가 빈번
- `--hidden-import win32com`, `--collect-all win32com` 플래그 필요할 수 있음
- COM 전처리를 선택적으로 분리하면 pywin32 없이도 빌드 가능 (EXE 크기 감소)

### `--windowed` vs `--console`
- `--windowed` 선택: GUI 더블클릭 시 콘솔 창 안 뜸 (일반 사용자 UX)
- CLI에서 호출해도 stdout/stderr는 정상 동작 (파이프, 리다이렉트 가능)
- 단, CLI에서 직접 실행 시 콘솔 출력이 보이지 않을 수 있음 → README에 안내

### EXE 크기 예상
- python-docx만: ~15-20MB
- pywin32 포함: ~25-35MB
- UPX 압축 시 ~60-70% 수준

### 폐쇄망 호환성
- EXE는 Python 미설치 환경에서 실행 가능 (PyInstaller 자체 런타임 포함)
- 인터넷 연결 불필요
- Word COM 전처리만 Microsoft Word 설치 요구

### 향후 피드백 대응
- 업체 요청에 따라 이 디렉토리 내에서만 수정
- 원본 `tools/converter/`에는 영향 없음
- 더 이상 불필요 시 디렉토리째 삭제

## 7. 작업 범위 외

- PDF→HTML 변환 (pdf_converter.py) — 불필요
- 원본 `tools/converter/` 수정 — 건드리지 않음
- 배치 변환 (폴더 내 다수 파일 일괄 변환) — 1차 범위 외, 추후 요청 시 추가
