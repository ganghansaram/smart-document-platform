# DOCX→HTML 변환기 아키텍처

Smart Document Platform 의 DOCX → HTML 변환기 구조와 운영 규약을 기술합니다.
Plan-37 (2026-04-21~22) 통합 작업 이후의 최종 구조를 기준으로 합니다.

## 목차

**PART 1. 개요**
- [1. 배경](#1-배경)
- [2. 디렉토리 구조](#2-디렉토리-구조)
- [3. 실행 환경 매트릭스](#3-실행-환경-매트릭스)

**PART 2. 처리 파이프라인**
- [4. 변환 흐름](#4-변환-흐름)
- [5. 전처리 어댑터 체인](#5-전처리-어댑터-체인)
- [6. 엔진 핵심 기능](#6-엔진-핵심-기능)

**PART 3. 규약과 한계**
- [7. DRM 우회 규약 (.docx_1)](#7-drm-우회-규약-docx_1)
- [8. Provenance 메타](#8-provenance-메타)
- [9. 지원 범위와 한계](#9-지원-범위와-한계)

**PART 4. 운영·개발**
- [10. 버전 관리와 배포](#10-버전-관리와-배포)
- [11. 테스트 하네스](#11-테스트-하네스)
- [12. 트러블슈팅](#12-트러블슈팅)

---

# PART 1. 개요

## 1. 배경

DOCX → HTML 변환 로직은 원래 **두 벌로 분기**되어 있었습니다.

- `tools/converter/` — 플랫폼 내장 (백엔드 업로드 파이프라인)
- `tools/docx2html-standalone/` — 외부 업체·문서 작성자용 단일 EXE

두 엔진이 개별 진화하면서 품질 차이·유지보수 부담이 누적되어 Plan-37 (2026-04-21~22)
으로 **단일 엔진 + 런타임 어댑터** 구조로 통합했습니다.

### 1-1. 설계 원칙

1. **엔진 SSOT** — 변환 로직은 `tools/converter/` 에만 존재
2. **얇은 래퍼** — Standalone 은 배포 포장지만
3. **전처리는 어댑터** — 환경별 Word COM / LibreOffice / Native 구현을 peer 로 두고 런타임 선택
4. **무회귀 우선** — 품질 개선조차 기본값은 보수적(`prefer_cached`)
5. **DRM 은 사용자 책임** — 서버는 DRM 을 풀지 않음

## 2. 디렉토리 구조

```
tools/converter/                           ← 엔진 SSOT
├── converter.py                           변환 엔진 본체 (~60 KB)
├── config.json                            설정 (style_mapping, numbering 등)
├── numbering_resolver.py                  word/numbering.xml 파서 (Phase 4a)
├── omml_to_mathml.py                      OMML → MathML 수식 변환
├── utils.py                               공통 유틸
├── pdf_converter.py                       PDF 입력 변환 (Explorer 전용)
├── word_preprocessor.py                   하위호환 shim (→ preprocess.word_com)
├── __version__.py                         SemVer 단일 소스 (1.4.0)
├── preprocess/                            전처리 어댑터 패키지
│   ├── __init__.py                        디스패처 (policy 기반 폴백)
│   ├── base.py                            PreprocessResult · PreprocessAdapter
│   ├── word_com.py                        Windows + MS Word COM
│   ├── libreoffice.py                     Linux + LibreOffice Headless
│   └── lo_macro.py                        UNO 매크로 (LibreOffice 번들 Python 에서 실행)
└── tests/
    ├── fixtures/                          대표 DOCX 샘플 (참조 기반)
    ├── golden/                            회귀 비교용 기준 HTML
    ├── semantic_checks.py                 시맨틱 품질 게이트
    ├── test_conversion.py                 pytest 테스트
    └── run_tests.py                       pytest 없이 돌아가는 runner

tools/docx2html-standalone/                ← 얇은 배포 래퍼
├── docx2html.py                           CLI/GUI 진입점 (../converter 참조)
├── gui.py                                 Tk GUI
├── docx2html.spec                         PyInstaller 설정
├── build.bat                              빌드 스크립트
├── requirements.txt
├── README.md                              외부 업체용 사용법
└── email-draft.md                         배포 공지 템플릿
```

## 3. 실행 환경 매트릭스

| 환경 | DRM | MS Word | 전처리 경로 | 비고 |
|------|-----|---------|-------------|------|
| 회사 Linux VM (Docker, 주 서비스) | 없음 | 없음 | **LibreOffice** (UNO 매크로) | 메인 운영 |
| 회사 Windows PC (톰캣) | 있음 | 있음 | **Word COM** (+ `.docx_1` 우회) | 대안 운영 |
| 개발 PC (Docker Desktop) | 없음 | 없음 | LibreOffice | 개발·테스트 |
| Standalone (고객 PC) | 있음/없음 | 있음 | Word COM (+ `.docx_1`) | EXE 배포 |

**공통 전제**: 어느 환경이든 사용자는 업로드 전 **로컬에서 DRM 을 해제**해야 합니다. 서버 쪽에 DRM 해제 기능은 없습니다.

---

# PART 2. 처리 파이프라인

## 4. 변환 흐름

```
DOCX (사용자 DRM 해제 후 업로드)
  │
  ├─→ ① 전처리 어댑터 디스패처
  │     · 환경에 따라 word_com / libreoffice / native / skip 중 선택
  │     · heading 자동번호 평문화 + SEQ 필드 refresh
  │
  ├─→ ② Converter 엔진 (DocxConverter.convert)
  │     · NumberingResolver: numbering.xml 기반 heading 번호 polyfill
  │     · cascade 4단계 heading 감지 (outlineLvl → style_id → style.name → font)
  │     · STYLEREF + SEQ 필드 해석 (\s \r \c \n \* 스위치)
  │     · 캡션 ID 생성 (fig-1, tbl-2-1)
  │     · OMML → MathML 수식 변환
  │     · 이미지 추출 (해시 기반 파일명, 중복 제거)
  │
  ├─→ ③ 캡션 참조 링크화 + provenance meta 삽입
  │
  └─→ HTML (프론트엔드에서 fetch → #main-content 로 주입)
```

## 5. 전처리 어댑터 체인

### 5-1. 디스패처 API

```python
from preprocess import preprocess

result = preprocess(input_path, policy='auto')
# result.path   — 전처리된 파일 경로 (실패 시 원본)
# result.adapter — 사용된 어댑터 이름 ('word_com' | 'libreoffice' | 'skip' | 'none')
# result.ok     — 성공 여부
# result.tried  — 폴백 경로 기록 [(adapter, reason_or_'ok'), ...]
```

### 5-2. Policy 옵션

| Policy | 동작 |
|--------|------|
| `auto` (기본) | word_com → libreoffice → native 순차 시도, 첫 가용 어댑터 사용 |
| `word_com` | Windows+Word 강제 |
| `libreoffice` | LibreOffice 강제 |
| `native` | Python 파서 강제 (Phase 4 에서 엔진 자체가 대부분 수행, 별도 어댑터 없음) |
| `skip` | 전처리 없이 원본 반환 (디버그·사용자가 이미 전처리한 경우) |

### 5-3. 폴백 체인 예시

```
환경: Linux Docker (Word COM 없음, LibreOffice 있음)
정책: 'auto'

tried:
  - word_com: unavailable (pywin32 미설치)
  - libreoffice: ok
adapter=libreoffice
```

## 6. 엔진 핵심 기능

### 6-1. Cascade 4단계 제목 감지

단락의 heading 레벨을 네 단계 우선순위로 판정:

1. **outlineLvl** — OOXML 스펙 정의, 로케일 무관 (가장 권위적)
2. **style_id** — 로케일 무관 매핑 (`Heading1` → h1)
3. **style.name** — 로케일 의존 (`제목 1` → h1)
4. **font size** — 최후 수단

**오감지 방지 (`_is_body_style` guard)**: `Normal` / `BodyText` / `ListParagraph` 등 본문 스타일은 outlineLvl 이나 폰트 크기가 헤딩 범위에 있어도 h 태그로 승격되지 않습니다. 논문 등 일부 문서가 본문 단락에 `outlineLvl val=1` 을 남용하는 사례를 차단.

### 6-2. NumberingResolver (Phase 4a)

`word/numbering.xml` 을 해석하여 heading 자동번호를 **전처리 없이** 생성합니다.

- 지원 포맷: `decimal`, `decimalZero`, `upperRoman`, `lowerRoman`, `upperLetter`, `lowerLetter`
- `<w:lvlText>` 템플릿 (`%1.%2.%3`) 치환
- `<w:lvlRestart>` 기반 하위 level 리셋
- `<w:lvlOverride>` + `<w:startOverride>` 지원

`config.json` 의 `numbering.resolver_mode` 로 동작 제어:
- `prefer_cached` (기본) — 본문 텍스트에 이미 번호 prefix 있으면 스킵
- `always_polyfill` — 무조건 자체 계산
- `off` — NumberingResolver 비활성

### 6-3. STYLEREF + SEQ (Phase 4b, 4c)

`"그림 3-1"` 같은 복합 캡션 = `{STYLEREF "Heading 1" \s}-{SEQ Figure \s 1}` 구조를 정확히 재현:

- `_heading_context` 스택이 문서 순회 중 최신 heading 번호 유지
- `STYLEREF "Heading N"` → 해당 level 번호로 치환
- `SEQ \s N` → heading level N 변경 감지 시 자동 리셋
- `SEQ \r N` → 해당 값으로 설정
- `SEQ \c` → 현재 값 반복 (증가 없음)
- `SEQ \* ARABIC|ROMAN|alphabetic` → 포맷 변환

### 6-4. 캡션·참조 링크

- 캡션 감지 → `<p class="caption" id="fig-N">` 또는 `id="tbl-N-M"`
- 본문의 "Figure 1 참조" 패턴 → `<a data-fig-ref="fig-1">` 자동 링크
- 캡션 스타일(`Caption`/`캡션`) 직접 감지 시 구분자 없이도 인식

---

# PART 3. 규약과 한계

## 7. DRM 우회 규약 (`.docx_1`)

**배경**: 회사 Windows 환경에 적용된 DRM 이 `.docx` 저장 시 자동으로 파일을 재잠금. Word COM 전처리 결과를 다시 converter 가 읽으려 하면 접근 실패.

**해결**: 전처리 결과를 **`.docx_1` 확장자**로 저장. python-docx 는 ZIP 시그니처로 읽으므로 확장자 무관하게 정상 파싱. DRM 은 `.docx` 패턴만 감지해 재잠금하지 않음.

**적용 범위**: Windows + Word COM 경로 **한정**. Linux Docker 의 LibreOffice 경로는 DRM 이 없어 표준 `.docx` 로 저장.

**정리**: `backend/main.py` lifespan 에 24h 경과 `preprocessed_*.docx_1` 고아 파일 자동 청소 훅 등록.

## 8. Provenance 메타

생성된 HTML 에 변환기 버전·어댑터·일시를 **영구 기록**합니다. 재변환 판단·회귀 추적·고객 제보 분석의 근거가 됩니다.

### 8-1. Fragment 모드 (기본)

`config.json` 의 `output.fragment_only: true` — HTML 주석 형태로 삽입:

```html
<!-- converter: smart-doc-platform/docx-converter 1.4.0 | adapter: libreoffice | date: 2026-04-21T14:30:00+00:00 -->
```

### 8-2. 전체 HTML 모드

`fragment_only: false` 시 `<head>` 에 meta 태그:

```html
<meta name="converter" content="smart-doc-platform/docx-converter">
<meta name="converter-version" content="1.4.0">
<meta name="converter-adapter" content="word_com">
<meta name="conversion-date" content="2026-04-21T14:30:00Z">
```

### 8-3. 검색 인덱스 오염 방지

`tools/html_to_text.py` 가 HTML 주석을 **선행 스트립**하므로 provenance 주석이 검색 텍스트에 섞이지 않습니다 (실측 검증 완료).

## 9. 지원 범위와 한계

### 9-1. 지원

- Heading 1~6 (cascade 감지)
- 자동번호 `decimal`, `upperRoman`, `lowerRoman`, `upperLetter`, `lowerLetter`
- SEQ 필드 + 스위치 `\r \s \c \n \*`
- STYLEREF heading 참조
- 캡션 ID + 본문 참조 링크
- 표 병합 (colspan/rowspan) 리치 포매팅
- OMML → MathML (18개 요소)
- 이미지 해시 중복 제거 + image_prefix 경로 커스터마이징

### 9-2. 알려진 한계

| 영역 | 한계 |
|------|------|
| Heading 자동번호 포맷 | `chicago`, `ordinal`, `cardinalText`, `decimalEnclosedCircle` 등 비수치 포맷은 decimal 폴백 |
| `v:shape` 도형 | `pic:pic` 이 아닌 `<w:drawing>` 내부 도형은 이미지 추출 실패 (`shape-placeholder` 출력). `backlog.md` 참조 |
| LO 경로의 TOC | LibreOffice 재저장 시 TOC 복제 단락이 자동 삭제됨 (LO 특성) |
| STYLEREF | `\n` 플래그 등 일부 스위치는 인식만 하고 단순 치환 |
| Unicode 숫자 포맷 | 한글 chosungChosungJa, iroha 등 미지원 |

### 9-3. 알려진 버그 (backlog)

`workbench/plans/backlog.md` 참조:
- LO 전처리 후 heading 매칭 손실 (swa_kor 류 TOC+한글)
- `v:shape` 이미지 추출 실패 (KI-002)

---

# PART 4. 운영·개발

## 10. 버전 관리와 배포

### 10-1. 엔진 버전

`tools/converter/__version__.py` 의 `__version__` 이 단일 소스.
HTML provenance 에 자동 반영됨.

**변경 시기**:
- 번호 생성 로직 변경 (MINOR)
- 어댑터 추가·변경 (MINOR)
- 출력 HTML 구조 breaking 변경 (MAJOR)
- 버그 수정만 (PATCH)

### 10-2. Standalone EXE 빌드

```bash
cd tools/docx2html-standalone
build.bat
# 또는: pyinstaller --clean docx2html.spec
# 산출: dist/docx2html.exe (~24 MB)
```

`.spec` 의 `pathex=[../converter]` + `hiddenimports=[converter, preprocess.*, ...]` 설정으로 엔진 파일이 자동 번들.

### 10-3. Docker 이미지

`Dockerfile` 에 다음 런타임 의존성:
- `libreoffice-writer`, `libreoffice-script-provider-python` — 전처리 어댑터
- `fonts-nanum`, `fonts-noto-cjk` — 한글 폰트

빌드:
```bash
docker compose build backend
# 이미지 약 12 GB (LibreOffice 약 +2 GB)
```

## 11. 테스트 하네스

### 11-1. pytest

```bash
python -m pytest tools/converter/tests/ -v
```

- **test_golden_match** — 현재 converter 출력 vs 골든 HTML fingerprint 비교 (DOM 구조 + 텍스트 hash). Provenance 주석은 제거 후 비교.
- **test_semantic_gates** — 시맨틱 품질 게이트 (캡션 ID 중복·dead link·이미지 무결성·SEQ 미해결)
- **test_golden_semantic_baseline** — 골든 HTML 자체 sanity check

### 11-2. pytest 없는 환경

```bash
python tools/converter/tests/run_tests.py
```

폐쇄망 환경 등 pytest 미설치 상태에서도 동일 검증 가능.

### 11-3. 골든 재생성

엔진 의도적 변경 후:
```bash
python tools/converter/tests/regenerate_golden.py
# --with-word-com 옵션으로 Word COM 전처리 경로 포함도 가능
```

## 12. 트러블슈팅

### Q. Linux Docker 에서 heading 번호가 누락됨

A. Phase 3 이전 증상. Phase 3 이후:
1. LibreOffice 경로 디스패처가 자동 전처리 수행
2. Phase 4 NumberingResolver 가 자체 번호 생성

여전히 누락되면 `LibreOfficeAdapter.is_available()` 확인 (Docker 이미지에 `libreoffice-writer` 포함 여부).

### Q. 캡션 번호가 원문과 어긋남

A. 다음을 순차 확인:
1. 원본 DOCX 의 SEQ 캐시가 stale — Word 에서 F9 로 필드 업데이트 후 저장
2. 복합 캡션("그림 3-1")이면 Phase 4b STYLEREF 해석이 동작해야 함 → heading 단락의 numPr / outlineLvl 존재 여부 확인
3. LO 경로인 경우 TOC 관련 복제 단락 삭제가 영향 (`workbench/plans/backlog.md` 의 `swa_kor` 이슈 참조)

### Q. Provenance 주석이 검색 결과에 뜸

A. `tools/html_to_text.py` 가 주석 스트립을 수행해야 함. 미반영이면 `build-search-index.py` 재실행 + converter 재변환.

### Q. Standalone EXE 가 안티바이러스에서 탐지됨

A. PyInstaller 생성 EXE 의 **알려진 false positive**. 업체측 AV 화이트리스트 등록 권고. 제공 시 `email-draft.md` 의 해당 문구 참조.

### Q. `.docx_1` 파일이 temp 에 누적됨

A. 정상적으로는 backend lifespan 의 `cleanup_stale_temp_files()` 가 24h 경과분 자동 삭제. 비정상 누적 시:
```bash
find /tmp -name 'preprocessed_*.docx_1' -mtime +1 -delete
```

---

## 참고 문서

- `workbench/plans/done-37-converter-unification.md` — 통합 작업 전체 이력
- `workbench/plans/backlog.md` — 알려진 이슈·개선 백로그
- `tools/docx2html-standalone/README.md` — 외부 업체용 EXE 사용법
- `tools/docx2html-standalone/email-draft.md` — 배포 공지 템플릿
- `memory/MEMORY.md` — 운영 중 축적된 교훈
