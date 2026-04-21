# Plan-37: DOCX 변환기 통합 — 엔진 SSOT + 전처리 어댑터 체인

> **목표**: `tools/converter/` (플랫폼 내장) 과 `tools/docx2html-standalone/` (외부 배포용)
> 두 벌로 분기된 DOCX→HTML 변환기를 **단일 엔진(SSOT) + 런타임 어댑터** 구조로 통합한다.
> 엔진 코드·설정·버전은 한 벌로 관리하고, 환경별 차이(Word COM ↔ LibreOffice)는
> 런타임에 선택되는 전처리 어댑터로 격리한다. 플랫폼(리눅스 Docker · 윈도우 톰캣) 과
> Standalone 고객 배포본 모두 **동등한 품질**의 번호 재현(heading · 캡션)을 보장한다.
>
> **전제**: 이 플랫폼은 **아직 운영 개시 전(pre-launch)** 이다. 보호해야 할 실서비스
> 변환 산출물이 없으므로, 품질 개선 알고리즘을 곧바로 기본값으로 채택한다.
> Standalone 배포본은 외부 업체에 이미 전달된 이력이 있어 **출력 안정성**을 유지한다.
>
> **배경 대화**: 2026-04-21, 외부 업체의 "표/이미지 캡션 번호 불일치" 제보 →
> 변환기 이원화 해소 + Linux Docker 주 서비스의 heading 번호 누락 동시 해결 논의
>
> **배경 참고**:
> - `tools/docx2html-standalone/plan.md` — standalone 초기 계획서
> - `tools/docx2html-standalone/email-draft.md` — 외부 업체 전달 문서
> - `memory/MEMORY.md` — DOCX→HTML 변환기 관련 Key Lessons

---

## 설계 원칙

1. **플랫폼 품질 최우선 · Standalone 무회귀** — 플랫폼은 운영 전이라 무회귀 제약 없음. 더 정확한 알고리즘을 곧바로 기본값으로. Standalone은 외부 업체에 배포된 이력이 있어 **기존 출력 동작을 깨지 않아야** 함.
2. **원문 충실도 최우선** — heading 번호 · 캡션 번호(단순 + 복합)가 원문과 일치해야 한다. 이미지 크기·구동 속도 등 운영 비용은 품질을 해치지 않는 선에서만 고려.
3. **환경 간 동등 품질** — 리눅스 Docker(LibreOffice UNO)와 윈도우 톰캣(Word COM), Standalone(Word COM)의 출력이 **의미 단위로 동일**해야 한다.
4. **폐쇄망 호환 필수** — 외부 네트워크 의존 금지. 모든 의존성은 패키지 매니저로 오프라인 반입 가능해야 한다.
5. **엔진 SSOT** — `converter.py`, `omml_to_mathml.py`, `utils.py`, `config.json` 은 **한 디렉토리에만** 존재한다. standalone은 이를 import한다.
6. **얇은 래퍼** — 배포용 래퍼(`docx2html.py`/`gui.py`/`.spec`)는 엔진을 import만 하고 고유 로직을 두지 않는다.
7. **전처리는 어댑터** — 환경별 Word COM / LibreOffice / Native 구현을 **동등한 peer**로 두고 런타임 감지로 선택한다. 새 어댑터 추가도 동일 저장소·동일 커밋에서.
8. **DRM은 사용자 책임** — 모든 배포에서 "원본 DOCX는 DRM 해제 상태로 업로드"를 전제로 한다. 서버가 DRM을 풀지 않는다. `.docx_1` 트릭은 Windows 환경의 저장-시 DRM 재적용을 우회하는 Windows 전용 수단이다.
9. **출력 프로비넌스 필수** — 생성된 HTML 에는 변환기 버전·어댑터·일시를 meta 태그(또는 fragment 주석)로 반드시 embed한다. 이후 재변환 판단·회귀 추적·고객 제보 분석의 **영구 근거**가 된다.
10. **시맨틱 품질 게이트** — 테스트는 바이트 diff에 그치지 않고 caption id 중복·dead link·이미지 누락·SEQ 미해결을 의미 단위로 검증한다.

---

## 1. 현황 진단 (2026-04-21)

### 1.1 환경 매트릭스

| 환경 | DRM | MS Word | 현재 서버측 전처리 | 번호 보존 현황 |
|------|-----|---------|---------------------|----------------|
| **회사 Linux VM (Docker, 주 서비스)** | 없음 (DRM SW 미설치) | 없음 | ✗ (Word COM 불가) | **heading 번호 누락** + SEQ stale |
| 회사 Windows PC (톰캣) | 있음 | 있음 | ✓ (Word COM + `.docx_1`) | 대부분 OK |
| 개발 PC (Docker Desktop, WSL2) | 없음 | 없음 | ✗ (Word COM 불가) | Linux VM과 동일 |
| **Standalone (고객 PC)** | 있음 (고객사 정책) | 있음 | ✓ (Word COM + `.docx_1`) | 단순 캡션 OK / **복합 캡션 불일치** |

**핵심 공통 전제**: 어느 환경이든 사용자는 업로드 전 **로컬에서 DRM을 해제해야 한다**. Linux Docker 서버에는 DRM SW가 없어 이후 자유롭고, Windows 계열에서는 저장 시 DRM이 재적용되므로 `.docx_1` 우회가 필요하다.

### 1.2 두 코드베이스의 분기 (2026-04-15 기준)

| 파일 | Explorer | Standalone | 상태 |
|------|----------|-----------|------|
| `converter.py` | 59 KB | 63 KB | **분기** |
| `word_preprocessor.py` | 5.5 KB | 7.1 KB | **분기** |
| `config.json` | 65줄 | 81줄 | **분기** |
| `omml_to_mathml.py` / `utils.py` | — | — | 동일 |

**Standalone이 앞선 영역**: 제목 감지 4단계 캐스케이드(outlineLvl→style_id→style.name→font), `by_style_id` 매핑, h4~h6 확장, `_BODY_STYLE_IDS` 오감지 차단, `sys._MEIPASS` 폴백, `image_dir_name`/`image_prefix` kwargs, `.docx_1` 수용, `preprocess_only()` 2단계 모드.

**Explorer만 가진 것**: `word_preprocessor._get_temp_dir()` 의 `config.UPLOAD_TEMP_DIR` 연동 (백엔드 통합용).

**동일 (분기 없음)**: 캡션 감지 · SEQ 해석 · 참조 링크 · 표 병합 · 이미지 추출 · OMML.

### 1.3 실제 발생 중인 문제 (우선순위 순)

**P1 — 회사 Linux VM에서 heading 번호 누락 (주 서비스 이슈)**
- Word COM이 없어 `_flatten_heading_numbers` 스킵 → `numbering.xml` 자동번호가 텍스트로 구워지지 않음 → HTML에서 "1.2 개요"가 "개요"로만 표시
- 사용자가 우회하려고 **로컬 Word에서 수동 전처리** 후 업로드하는 번거로운 UX 발생 중

**P2 — Standalone에서 복합 캡션 번호 불일치 (외부 업체 제보)**
- Word COM `Fields.Update()`가 SEQ 캐시는 refresh하지만 converter가 다음을 처리하지 못함:
  - **STYLEREF 미지원** — "그림 3-1"에서 `{STYLEREF 1 \s}-{SEQ Figure \s 1}` 합성 구조 못 해석
  - **SEQ 스위치 무시** — `\s`(heading 리셋), `\r`(reset), `\c`(repeat) 모두 미파싱
  - **비표준 구분자** — "Figure 1." / "[Figure 1]" / "<그림 1>" 등 `_detect_caption` 정규식이 놓침
- Word SaveAs2 후 일부 필드 구조가 `separate` 마커 소실로 변형되면 cached result를 못 찾아 자체 counter로 오채번

**P3 — 두 코드베이스 분기로 인한 유지보수 부담**
- Standalone 고객 요청이 계속 추가될 예정 → 분기 폭 확대 위험

---

## 2. 제안 아키텍처

### 2.1 목표 구조

```
tools/converter/                         ← 엔진 SSOT (모든 배포의 유일한 소스)
  ├─ converter.py                        (엔진 — 변환 로직)
  ├─ omml_to_mathml.py                   (수식 변환)
  ├─ utils.py                            (공통 유틸)
  ├─ config.json                         (설정 단일)
  ├─ pdf_converter.py                    (Explorer 전용, 유지)
  ├─ preprocess/                         ← 전처리 어댑터 패키지 (신설)
  │   ├─ __init__.py                     (런타임 디스패처)
  │   ├─ base.py                         (어댑터 ABC, 결과 타입)
  │   ├─ word_com.py                     (기존 word_preprocessor 이관)
  │   ├─ libreoffice.py                  (Phase 3, 신규)
  │   └─ native.py                       (Phase 4, 신규, Python 파서)
  ├─ word_preprocessor.py                (shim: 하위호환 re-export)
  ├─ requirements.txt
  └─ tests/                              (회귀 방어, 신설)
      ├─ fixtures/                       (대표 DOCX 5~7종)
      └─ test_conversion.py

tools/docx2html-standalone/              ← 배포 래퍼만 (엔진 미보유)
  ├─ docx2html.py                        (CLI, 엔진 import)
  ├─ gui.py                              (Tk GUI, 엔진 import)
  ├─ docx2html.spec                      (엔진 파일 datas 번들)
  ├─ build.bat
  ├─ requirements.txt                    (엔진 deps + GUI)
  ├─ README.md
  ├─ email-draft.md
  └─ dist/                               (빌드 산출, gitignore)

(삭제)
  tools/docx2html-standalone/{converter,word_preprocessor,omml_to_mathml,utils}.py
  tools/docx2html-standalone/config.json
```

### 2.2 전처리 어댑터 디스패처

```python
# tools/converter/preprocess/__init__.py
from .base import PreprocessResult, PreprocessAdapter
from . import word_com, libreoffice, native

ADAPTER_ORDER = ['word_com', 'libreoffice', 'native']

def preprocess(input_path, output_path=None, policy='auto'):
    """환경 감지 후 가장 적합한 어댑터로 전처리.

    policy:
      'auto'        — 감지 순서대로 첫 가용 어댑터 사용 (기본)
      'word_com'    — Windows+Word 강제
      'libreoffice' — Linux+LibreOffice 강제
      'native'      — Python 파서 강제 (Phase 4)
      'skip'        — 전처리 없이 원본 반환 (디버그용)
    """
    if policy == 'skip':
        return PreprocessResult(path=input_path, adapter='skip', ok=True)

    candidates = ADAPTER_ORDER if policy == 'auto' else [policy]
    tried = []
    for name in candidates:
        adapter = _load(name)
        if not adapter.is_available():
            tried.append((name, 'unavailable'))
            continue
        result = adapter.preprocess(input_path, output_path)
        if result.ok:
            result.tried = tried
            return result
        tried.append((name, result.error))

    return PreprocessResult(
        path=input_path, adapter='none', ok=False,
        error=f"모든 어댑터 실패: {tried}"
    )
```

### 2.3 각 어댑터 책임

| 어댑터 | 의존성 | 사용 환경 | 저장 확장자 | 처리 범위 |
|--------|--------|-----------|-------------|-----------|
| **word_com** | pywin32 + MS Word | Windows PC / Standalone 고객 PC | `.docx_1` (DRM 재적용 우회) | heading 평문화 + `Fields.Update()` |
| **libreoffice** | `soffice` + 한글 폰트 | Linux Docker (회사 VM, 개발 PC) | `.docx` (DRM 없음) | heading 평문화 + 필드 업데이트 (재저장 또는 UNO 매크로) |
| **native** | Python 표준 + `python-docx` | 모든 환경 (폴백) | 전처리 없음 | converter가 `numbering.xml` / STYLEREF / SEQ를 **직접 해석** — 별도 파일 생성 안 함 |

**native 어댑터의 특수성**: 실제로는 "전처리"가 아니라 converter 엔진 내부에서 자체 해석. 어댑터 인터페이스상 `preprocess()` 호출 시 원본 경로 그대로 반환하고 플래그만 세움. converter가 그 플래그를 보고 native 모드로 동작.

### 2.4 Import 경계

```python
# Explorer 백엔드 (backend/api/upload.py)
from converter.preprocess import preprocess
result = preprocess(input_path, policy='auto')
if result.ok:
    convert_input = result.path

# Standalone CLI (tools/docx2html-standalone/docx2html.py)
sys.path.insert(0, str(Path(__file__).parent.parent / 'converter'))
from preprocess import preprocess
# (이하 동일)
```

**하위 호환**: `tools/converter/word_preprocessor.py` 는 shim으로 유지
```python
# word_preprocessor.py
from .preprocess.word_com import preprocess as preprocess_docx
from .preprocess.word_com import preprocess_only
```
기존 `from word_preprocessor import preprocess_docx` 호출부 무회귀.

---

## 3. 실행 계획 (단계별)

### Phase 0 — 회귀 방어망 (선행 필수)

**목적**: 이후 모든 단계에서 "HTML 출력이 같다/다르다"를 기계적으로 판정 가능해야 안전.

**작업**:
1. `tools/converter/tests/fixtures/` 에 대표 DOCX 수집 — **`contents/samples/` 에서 활용**
   - 활용 가능 샘플:
     - `contents/samples/MyPaper/MyPaper_20251109_V2.8_Claude.docx` — 논문 (heading + 캡션 + 수식)
     - `contents/samples/SWA_PMS/SWA_PMS.docx`, `SWA_PMS_r1.docx` — 회사 규격서 (heading 자동번호 + 캡션)
     - `contents/samples/SWA_Sample_ENG/SWA_Sample_ENG.docx` — 영문 매뉴얼
     - `contents/samples/SWA_Sample_KOR/SWA_Sample_KOR.docx` — 한글 매뉴얼 (한글 heading 번호 누락 재현용 유력)
     - `contents/samples/sample_20260317.docx` — 보조 샘플
   - 목표 커버리지 (Phase 0에서 각 샘플 내부 검사하여 매핑 확정):
     - (a) 단순 매뉴얼 (제목 3단계, 캡션 5~10)
     - (b) 대형 매뉴얼 (제목 6단계, 캡션 20+, 표 병합, 이미지 다수)
     - (c) 수식 문서 (OMML 포함)
     - (d) STYLEREF 합성 캡션 문서 ("그림 3-1" 형식)
     - (e) SEQ 스위치 사용 문서 (`\s`, `\r`)
     - (f) 한글 heading 자동번호 문서 (Linux Docker에서 번호 누락 재현)
   - 기존 샘플로 커버 안 되는 시나리오는 **최소 DOCX 수동 생성** (Word에서 직접 작성 후 fixtures에 추가)
   - 민감 정보 검사 후 git 포함 여부 판단. 필요 시 `.gitignore` 추가 후 로컬 전용 유지
2. 각 fixture에 대해 **현 Explorer 버전의 Word COM 경로**로 골든 HTML 생성·커밋
3. `test_conversion.py` — 변환 후 골든과 fingerprint 비교 (DOM 구조 + 텍스트 hash)
4. Phase 3/4 도입 어댑터는 **별도 비교 슬롯** (word_com vs libreoffice vs native) — 어댑터 간 차이 추적
5. **Compare 서브시스템 의존 사전 조사** — `backend/services/compare_service.py` 와 `compare.html` 의 converter 출력 의존 매핑. cascade 로 h4~h6 생성·heading ID 변경 시 Compare 결과 영향 확인. Phase 1e 작업 범위 확정 근거.

**시맨틱 품질 게이트** (`tests/semantic_checks.py`, 신설):

바이트 diff가 놓치는 실버그를 잡기 위한 **의미 단위 검증**. 모든 fixture에 대해 실행, 0건 실패를 통과 기준으로.

```python
def check_caption_integrity(html):
    """
    - 같은 id 중복 없음 (fig-1이 두 번 나오면 FAIL)
    - id 패턴 준수: ^(fig|tbl)-\d+(-\d+)?$
    - 모든 <a data-fig-ref href="#..."> 가 실제 존재하는 id를 가리킴 (dead link 0건)
    """

def check_heading_structure(html):
    """
    - heading 개수가 원문 heading 단락 개수와 일치
    - h1~h6 레벨이 건너뛰지 않음 (h2 다음 바로 h4 경고)
    - **heading id 중복 없음** (동일 텍스트 heading 여러 개 발생 시 suffix 부착 확인)
    """

def check_image_integrity(html, output_dir):
    """
    - 모든 <img src> 경로가 실제 파일로 존재
    - 이미지 디렉토리 내 모든 파일이 HTML에서 참조됨 (고아 파일 0건)
    """

def check_seq_resolution(html):
    """
    - 캡션 텍스트에 미해결 플레이스홀더 없음 ("그림 ?-?", 빈 SEQ 결과 등)
    """
```

**Compare 서브시스템 의존 사전 조사** (신설 작업):

`backend/services/compare_service.py` 및 `compare.html` 파이프라인이 converter 출력 HTML 구조에 어떻게 의존하는지 **Phase 0 에서 매핑**. cascade 전환으로 h4~h6 생성·heading ID 변경 시 Compare 결과에 영향 여부 조사.
- 공수 0.2일, Phase 1 착수 전 필수
- 의존 발견 시 Phase 1e 작업 범위 확장 결정 근거

이 검사들은 **Phase 3/4 도입 시 어댑터 전환이 의미 단위로 동등한지** 검증하는 데도 동일하게 사용.

**게이트**: Phase 1 진입 전 (a)(b)(c) fixture 골든 + 시맨틱 검사 모두 통과. (d)(e)(f)는 후속 Phase의 품질 측정용.

---

### Phase 1 — 역이식 (Standalone → Explorer 엔진)

**방침**: 모든 개선은 **옵트인 또는 무해 기본값**. Explorer 기본 동작 불변.

#### 1a. 제목 감지 4단계 캐스케이드 (단일 모드)

- `config.json`에 캐스케이드 알고리즘을 **유일한 모드**로 채택 (pre-launch 플랫폼이라 legacy 게이트 불필요):
  ```json
  "style_mapping": {
    "by_style_id": { "Heading1": "h1", ..., "Heading6": "h6", "Title": "h1" },
    "by_style":    { "제목 1": "h1", ..., "제목 6": "h6", "Heading 1": "h1", ... },
    "by_font_size": { "28": "h1", "24": "h1", "22": "h2", "20": "h2",
                      "18": "h3", "16": "h4", "14": "h5", "default": "p" }
  }
  ```
- `_detect_heading_level()` 는 4단계 캐스케이드 단일 로직:
  1. `outlineLvl` (OOXML 스펙, 로케일 무관)
  2. `style_id` (Heading1~9 정규식 폴백)
  3. `style.name` (제목 N / Heading N)
  4. 폰트 크기 (본문 스타일이면 스킵)
- `_BODY_STYLE_IDS` 상수로 폰트 폴백 오감지 차단
- **기존 `priority` 키 제거** (캐스케이드에 불필요)

**Standalone 출력 영향 확인**: Standalone은 이미 cascade 로 동작 중이므로 이 변경은 **동등 유지** (코드 이관만). fixture 재빌드로 검증.

#### 1b. `config.json` 확장

- `by_style_id` 섹션 추가 — 로케일 무관 매핑
- 제목 4~6 및 Heading 4~6 매핑 (h4~h6 생성 가능)
- `by_font_size` 에 28, 20, 16, 14 추가
- `priority` 키 완전 제거 (상위 호환 shim 없음 — 설정 리더가 경고 로그만 출력)

#### 1c. `word_preprocessor` → `preprocess/word_com.py` 이관

- standalone의 개선 사항 모두 수용:
  - `preprocess_only()` 함수 (DRM 2단계 모드)
  - `.docx_1` 확장자 저장
- Explorer의 `_get_temp_dir()` config 연동 유지 (ImportError 시 None 폴백)
- 파일 위치: `tools/converter/preprocess/word_com.py`
- 구 경로 shim: `tools/converter/word_preprocessor.py` 가 re-export

**무회귀 검증**:
- `backend/api/upload.py:109-112` 가 기존 import 경로(`from word_preprocessor import preprocess_docx`)로 계속 동작
- `.docx_1` 임시파일 cleanup이 `upload.py:151-153` 에서 정상 동작 확인
- `config.UPLOAD_TEMP_DIR` 이 설정된 테스트 환경에서 임시파일이 해당 경로에 생성되는지 확인

**`.docx_1` 고아 파일 정리 훅** (신설):
서버 재기동·크래시 시 temp 디렉토리에 남은 `preprocessed_*.docx_1` 파일 자동 청소.
- FastAPI startup event 에 `_cleanup_stale_preprocessed()` 등록
- 24시간 이상 된 `preprocessed_*.docx_1` 파일 삭제
- 공수 0.1일

#### 1d. `converter.py` 파라미터 확장

- `convert(input, output, options=None, image_dir_name=None, image_prefix=None)` — 기존 호출부는 위치 인자 그대로, 신규 kwargs 기본 None → 무회귀
- `sys._MEIPASS` 폴백 이식 (`__file__.parent` 기본 → 백엔드 실행엔 무해)
- `.docx_1` 입력 허용 (`input_path.suffix.lower() not in ('.docx', '.docx_1')`)

#### 1e. 플랫폼 호환성 확보 — CSS + JS + 검색 인덱스

cascade 채택으로 h4~h6 태그가 새로 생성될 수 있음 → 플랫폼의 CSS·JS·인덱서가 모두 대응해야 함.

**현 상태 (2026-04-21 점검)**:
- `css/content.css` — `.main-content h1~h4` 개별 스타일 있음, **h5/h6 개별 스타일 없음** (스크롤 마진만)
- `css/content.css @media print` — h5/h6 인쇄 스타일 누락
- `css/bookmarks.css:218` — 북마크 아이콘 hover 룰이 **h1~h4만** 지원
- `js/bookmarks.js:278` — `querySelectorAll('h1[id], h2[id], h3[id], h4[id]')` **하드코딩**, h5/h6 북마크 아이콘 미생성
- `js/app.js:630, 668` — 섹션 래핑이 h1/h2 기준 → cascade 시 섹션 구조 재검토 필요 (UX 판단)
- `tools/build-search-index.py:146` — 헤딩 정규식 범위 확인 필요
- `.caption`, `[data-fig-ref]` — 이미 정의되어 있음 (변경 불필요)

**작업**:
1. **CSS 스타일 추가** (`css/content.css`)
   - `.main-content h5`, `.main-content h6` 본문 스타일 (h4와 일관된 축소 스케일)
   - `@media print` 섹션에 h5/h6 룰 존재 여부 확인, 없으면 추가
   - 다크 테마 (`body[data-theme="dark"]`) h5/h6 색상 변형 추가
2. **북마크 CSS** (`css/bookmarks.css:218`)
   - hover 룰에 `h5`, `h6` 추가
3. **북마크 JS** (`js/bookmarks.js:278`)
   - 헤딩 셀렉터를 `'h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]'` 로 확장
4. **검색 인덱스** (`tools/build-search-index.py`)
   - 헤딩 추출 정규식이 h1~h6 전부 커버하는지 확인, 누락 시 확장
5. **섹션 래핑 정책** (`js/app.js:630`)
   - 현행 h1/h2 유지 vs h1~h3 확장 → **Phase 0 Compare 의존 조사 결과에 따라 결정**
   - 기본은 **현행 유지** (성능·디자인 영향 최소)
6. **브라우저 미리보기 검증**
   - 변환된 대표 fixture 결과를 Explorer 에 실제 로드 → h5/h6 렌더링, 북마크 아이콘, 다크/인쇄 모드 수동 확인

**Standalone 측 CSS**:
- Standalone 은 외부 업체가 자체 웹 프로세스에 통합하는 형태 → 우리 CSS·JS 와 별개
- `email-draft.md` 에 **"출력 HTML은 h1~h6 사용, 업체측 CSS에 h5/h6 스타일 정의 권고"** 문구 추가 (Phase 5)

**Phase 1 완료 기준**:
- fixture (a)(b)(c) 변환 결과가 cascade 기반 신규 골든과 일치
- Standalone 재빌드 exe가 기존 exe와 대표 문서 3종에서 바이트 일치 (cascade 는 이미 동일 동작이므로 보장)
- `backend/api/upload.py` 변경 없이 Explorer 업로드 파이프라인 정상
- 플랫폼 CSS 에 h5/h6 스타일 및 북마크 hover 룰 반영
- Explorer 에서 변환 결과 브라우저 로드 시 h5/h6 이 어색하지 않게 렌더링

---

### Phase 2 — Standalone 비우기

**작업**:
1. `tools/docx2html-standalone/` 에서 엔진 파일 5종 삭제
   - `converter.py`, `word_preprocessor.py`, `omml_to_mathml.py`, `utils.py`, `config.json`
2. `docx2html.py`, `gui.py` 에 `sys.path` 삽입 전환 (개발 모드)
3. `docx2html.spec` 에 `pathex=['../converter']`, `datas=[('../converter/config.json', '.')]`, `hiddenimports=[...]` 반영
4. `build.bat` 동작 확인 → `dist/docx2html.exe` 재빌드
5. 재빌드 exe를 **통합 전 exe와 동일 문서에서 바이트 단위 비교** — 차이 없어야 함
6. `__pycache__` 정리

**Phase 2 완료 기준**:
- standalone 디렉토리에 엔진 파일 0개
- 재빌드 exe 변환 결과 = 기존 exe 결과 (바이트 일치, 대표 문서 3종)
- PyInstaller 번들에 `config.json` 포함 확인 (7z 풀어서 확인)

---

### Phase 3 — LibreOffice 어댑터 추가 + 디스패처 도입 (주 서비스 긴급 개선)

**동기**: 회사 Linux VM에서 heading 번호가 누락되는 P1 문제를 **서버측 자체 전처리로 해소**. 사용자의 로컬 Word 전처리 부담 제거.

#### 3a. `preprocess/libreoffice.py` 구현

```python
class LibreOfficeAdapter(PreprocessAdapter):
    SAFE_FLAGS = [
        '--headless',            # GUI 없이
        '--norestore',           # 충돌 복구 다이얼로그 차단
        '--nologo', '--nofirststartwizard',
        '--safe-mode',           # 매크로·외부 참조·확장 전면 차단
    ]

    def is_available(self):
        return shutil.which('soffice') is not None

    def preprocess(self, input_path, output_path):
        # 방법 A — 단순 재저장 (soffice --convert-to docx)
        #   장점: 구현 간단, Fields.Update 자동 수행
        #   단점: heading 번호 평문화는 별도 필요
        # 방법 B — UNO 매크로로 ListFormat.ListString 평문화
        #   장점: Word COM과 동등한 결과
        #   단점: python3-uno 또는 매크로 스크립트 필요
        ...
```

**보안 방어선**: `--safe-mode` 플래그로 매크로·외부 URL 참조·extension 로딩 전면 차단. 폐쇄망이라 외부 통신 불가하지만 **DOCX에 포함된 악성 매크로로 인한 로컬 권한 상승 시도**를 0-비용으로 차단. 2026년 오피스 문서 처리 파이프라인의 표준 가드.

**구현 선택**: 방법 B 권장 (Word COM과 동등 결과 보장). `soffice --headless --safe-mode --convert-to docx:"MS Word 2007 XML"` 로 재저장하면 `Fields.Update()` 는 자동이지만 heading `ListFormat` 평문화는 UNO 매크로가 필요. `/usr/bin/soffice --headless --safe-mode "macro:///...."` 또는 임시 Basic 스크립트 주입 방식.

#### 3b. Dockerfile 갱신

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-core \
    libreoffice-script-provider-python \
    fonts-nanum fonts-nanum-coding fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
```

**이미지 크기 증가 예상**: ~500~700MB (LibreOffice + 한글 폰트). 회사 Linux VM 리소스 충분하다고 확인됨.

#### 3c. 디스패처 활성화

- `backend/api/upload.py` 의 `preprocess_docx(str(input_path))` 호출을
  `preprocess(input_path, policy='auto').path` 로 변경
- Word COM 없는 Linux Docker → 자동으로 LibreOffice 경로 선택
- Windows PC 톰캣 / Standalone → Word COM 경로 유지 (무회귀)

#### 3d. UNO 매크로 내용 설계

LibreOffice 매크로가 수행할 작업:
1. 모든 단락 순회하며 `ParaStyleName` 이 `Heading 1~9` / `제목 1~9` 이면
2. `NumberingIsNumber == true` 인 경우 `ListLabelString` 을 획득
3. 단락 시작부에 `ListLabelString + " "` 를 텍스트로 삽입
4. `NumberingIsNumber = false` 로 번호 제거
5. 전체 문서 `Fields` refresh 후 `storeToURL` 로 저장

**역순 처리 필요** (Word COM과 동일한 이유) — Python 스크립트로 UNO 호출하는 쪽이 유지보수 용이.

#### 3e. 무회귀 검증

- fixture (g) 한글 heading 자동번호 문서:
  - 통합 전: Linux Docker에서 번호 누락
  - Phase 3 적용 후: 번호 보존 (Word COM 경로 결과와 일치)
- fixture (a)(b)(c): LibreOffice 경로 결과 vs Word COM 경로 결과 diff 측정
  - 100% 바이트 일치 기대 안 함. 허용 범위 (ex. whitespace 정규화) 이내인지 확인
  - 차이가 커지는 요소 발견 시 3a 방법 A→B 전환 또는 추가 후처리

#### 3f. HTML 출력 Provenance 메타 태그

변환된 HTML의 `<head>` 에 변환 주체·버전·어댑터 정보를 embed. 재변환 판단·회귀 추적·고객 제보 분석의 영구적 근거가 됨. 업계 전면 채택 (Pandoc·Confluence·Notion 모두 수행).

```html
<meta name="converter" content="smart-doc-platform/docx-converter">
<meta name="converter-version" content="1.4.0">
<meta name="converter-adapter" content="libreoffice">
<meta name="converter-fallback-chain" content="word_com:unavailable,libreoffice:ok">
<meta name="conversion-date" content="2026-04-21T14:30:00Z">
<meta name="conversion-warnings" content="0">
```

**구현**:
- `converter.py` 의 HTML 생성부에서 `_build_provenance_meta()` 호출 → `<head>` 에 삽입
- 버전 번호는 `tools/converter/__version__.py` 에 단일 소스로 관리 (SemVer)
- Phase 4 native 파서가 개입했다면 `converter-numbering-polyfill="native"` 도 추가

**효과**:
- "이 웹북이 어느 버전으로 만들어졌는지" 영원히 추적 가능 — **지금 안 넣으면 기존 웹북들엔 영구적으로 누락**
- 검색 인덱스 재생성 판단 (`converter-version < 1.4.0` 인 웹북만 재변환)
- 고객 제보 HTML 받았을 때 어댑터·어떤 어댑터 폴백 경로가 사용됐는지 즉시 파악

**fragment 모드 호환**: 현재 `config.json` 의 `output.fragment_only: true` 에서는 `<head>` 가 없음. 이 경우 **주석으로 삽입**:
```html
<!-- converter: smart-doc-platform/docx-converter 1.4.0 | adapter: libreoffice | date: 2026-04-21T14:30:00Z -->
```

**다운스트림 오염 방지** — `tools/html_to_text.py` 가 HTML 주석을 검색 텍스트에 포함시키지 않도록 전처리 필요:
```python
# html_to_text.py 맨 앞에 추가
html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
```
이 작업 누락 시 검색 결과에 `converter: ...` 문자열이 히트되는 오염 발생.
- 공수 0.1일, Phase 3f 에 포함

#### 3g. 기존 사용자 흐름 병존 보장

사용자가 이미 **로컬 Word로 전처리한 DOCX**를 업로드하는 기존 워크플로우도 깨지면 안 됨:
- 이미 heading 번호가 본문 텍스트로 박힌 DOCX → LibreOffice 재저장 시 `NumberingIsNumber == false` 이므로 중복 평문화 안 됨
- SEQ 필드는 Fields.Update만 추가로 수행 → 동등 또는 개선
- 결론: 기존 흐름은 그대로 작동하며 오히려 `Fields.Update`가 보강됨

**Phase 3 완료 기준**:
- Docker 이미지 빌드 성공, LibreOffice + 한글 폰트 + safe-mode 플래그 포함
- fixture (f)에서 heading 번호 보존 확인
- fixture (a)(b)(c) Word COM vs LibreOffice 결과 차이가 "허용 가능" 수준 (세부 기준은 검증 후 확정)
- 시맨틱 품질 게이트 통과 (caption id 중복 0·dead link 0·이미지 누락 0·SEQ 미해결 0)
- 생성된 HTML 에 provenance meta 태그(또는 fragment 주석) 포함 확인
- 사용자 로컬 전처리 후 업로드 흐름 정상 동작

---

### Phase 4 — Converter 엔진 자립화 (품질 상한 향상)

**동기**: Standalone의 **복합 캡션 번호 불일치** (P2) 등 Word COM·LibreOffice 모두로 해결 안 되는 converter 자체의 한계를 제거. 전처리 의존도 감소.

#### 4a. `numbering.xml` 파서로 heading 번호 polyfill

- `converter.py` 에 `NumberingResolver` 추가
- 현재 단락의 `numId` + `ilvl` → `abstractNum` 조회 → `lvlText` 포맷 + 카운터 해석
- `lvlOverride` / `startOverride` / `lvlRestart` 지원
- 변환 시 heading 단락에 `ListString` 이 없으면 (native 모드 또는 전처리 실패 시) NumberingResolver 호출 → 번호 prefix 생성

**효과**: 전처리 어댑터 실패해도 heading 번호 표시. LibreOffice 적용 전·후 비교로 검증.

#### 4b. STYLEREF 해석

- heading 단락 순회 시 `heading_context` 스택 유지 (level별 최신 번호)
- 캡션 단락의 XML에서 `STYLEREF` 필드 감지
- result zone이 비어있거나 cached가 의심스러우면 heading_context에서 조회해 렌더
- "그림 {STYLEREF 1}-{SEQ}" 구조를 정확히 합성

#### 4c. SEQ 스위치 완전 지원

- `\s N` — Heading N 진입 시 해당 카테고리 카운터 리셋
- `\r N` — 특정 값으로 리셋
- `\c` — 마지막 값 반복
- `\n` — 증가 (기본)
- `\* ARABIC|ROMAN|alphabetic` — 숫자 형식 (기본 ARABIC 외 1~2개)

#### 4d. `_detect_caption` 정규식 확장

- 구분자 후보 확대: `:` `–` `—` `-` `.` `(공백)` `[` `<`
- 캡션 스타일 ID 직접 감지 (`styleId == 'Caption' || '캡션'`) — 텍스트 매칭 실패 시 보조 단서
- 오감지 방지 규칙 강화

#### 4e. 설정 플래그

```json
"numbering": {
  "resolver_mode": "prefer_cached",  // "prefer_cached" | "always_polyfill" | "off"
  "styleref_enabled": true,
  "seq_switches_enabled": true
}
```

기본값은 보수적: cached 값이 있으면 존중, 없을 때만 polyfill → 무회귀.

**Phase 4 완료 기준**:
- fixture (d) STYLEREF 합성 캡션 문서: Word COM / LibreOffice / native 세 경로 모두 원문 동일 번호 출력
- fixture (e) SEQ 스위치 문서: chapter 리셋 정상 반영
- Phase 1~3 fixture 전체 무회귀 (기본 설정)

---

### Phase 5 — 문서 통합 및 릴리스

1. **`docs/14-CONVERTER-ARCHITECTURE.md`** 신설
   - 엔진·어댑터·래퍼 구조 다이어그램
   - 런타임 어댑터 선택 흐름
   - 환경별 동작 표 (Linux Docker / Windows PC / Standalone / 개발 PC)
   - DRM 전제 조건 명시
   - `.docx_1` 규약과 적용 범위
   - 제목 감지 cascade 설계
   - numbering/STYLEREF/SEQ 처리 한계
2. **`tools/docx2html-standalone/README.md`** 슬림화 — 고객·업체용 관점
3. **`tools/docx2html-standalone/email-draft.md`** 버전 변경 공지 템플릿 갱신
   - 출력 HTML 이 **h1~h6 태그를 사용**함 명시
   - 업체측 자체 CSS 에 h5/h6 스타일 정의 필요 권고
   - Phase 4 SEQ/STYLEREF 개선으로 복합 캡션 번호 정확도 향상 공지
   - DRM 해제 후 업로드 전제 재강조
   - PyInstaller 안티바이러스 false positive 가능성 사전 고지 (오탐)
4. **`memory/MEMORY.md`** — DOCX 변환기 섹션 업데이트
5. **`MEMORY.md`** — 완료 계획 항목에 Plan-37 추가
6. **`workbench/plans/backlog.md`** — Phase 4d 등 후속 개선 여지 기록

---

## 4. 리스크 평가

| # | 리스크 | 확률 | 영향 | 완화책 |
|---|--------|------|------|--------|
| R1 | `.docx_1` 임시파일이 Explorer 다운스트림 로깅·검색 인덱스에 노출 | 낮 | 낮 | Phase 1c에서 upload.py 전 경로 감사, cleanup 동작 확인 |
| R2 | LibreOffice 결과가 Word COM과 미묘하게 다름 | 중 | 중 | Phase 3e에서 어댑터 간 diff 측정, 허용 범위 사전 정의, 초과 시 UNO 매크로 보강 |
| R3 | UNO 매크로 에러 시 조용한 실패 → 번호 누락 재발 | 중 | 중 | 어댑터가 실패를 `PreprocessResult.ok=False` 로 명시 → 디스패처가 다음 어댑터(native)로 폴백 |
| R4 | PyInstaller 빌드 시 `pathex` + `hiddenimports` 누락 | 중 | 중 | Phase 2 에서 dist 재빌드 후 실제 변환 검증, 대표 문서 바이트 비교 |
| R5 | Standalone 고객 배포본과 통합 후 재빌드본의 출력 차이 | 중 | 중 | Phase 2 에서 기존 exe와 바이트 비교, 차이 발견 시 email-draft 템플릿으로 사전 공지 |
| R6 | Phase 4 NumberingResolver의 엣지 케이스 (lvlOverride 등) | 중 | 중 | `resolver_mode: prefer_cached` 기본 — cached 있으면 polyfill 안 함. 실데이터 축적 후 기본 변경 |
| R7 | 이미 평문화된 DOCX를 LibreOffice가 재처리하며 번호 중복 삽입 | 낮 | 중 | UNO 매크로에서 `NumberingIsNumber == false` 단락은 스킵하는 가드 필수 |
| R8 | 기존 사용자 흐름(로컬 전처리)과 신규 흐름(서버 전처리) 혼재로 인한 혼란 | 중 | 낮 | Phase 5 문서화, 업로드 UI에 상태 배지 ("서버 전처리 완료") 표시 검토 |
| R9 | LibreOffice 폐쇄망 반입 — apt 미러 또는 deb 패키지 사전 확보 필요 | 중 | 중 | Dockerfile 에서 필요 `.deb` 목록 명시, 사용자가 오프라인 repo로 반입. 대안: multi-stage build로 빌드타임 온라인 레이어 분리 |
| R10 | 악성 매크로 포함 DOCX 반입 시 LibreOffice 실행 중 권한 상승 | 낮 | 중 | `--safe-mode` 필수 (Phase 3a), 임시 디렉토리 격리, 변환 프로세스 timeout. 폐쇄망이라 외부 통신은 이미 차단 |
| R11 | cascade 로 h5/h6 생성 시 플랫폼 CSS 미정의로 렌더링 어색 | 중 | 낮 | Phase 1e 필수 작업. 브라우저 미리보기 검증 |
| R12 | cascade 로 STYLEREF 오감지로 본문 단락이 h4~h6으로 잘못 승격 | 낮 | 중 | 시맨틱 게이트에서 heading 개수 before/after 비교. 초과 검출 시 `_BODY_STYLE_IDS` 확장 |
| R13 | Standalone 재빌드본이 기존 exe와 출력 차이 (고객 영향) | 중 | 중 | Phase 2 에서 기존 exe와 바이트 비교. cascade 이미 적용 중이라 차이 없을 것으로 기대. 발견 시 email-draft 사전 공지 |

---

## 5. 수용 기준 (Acceptance Criteria)

### Phase 0 (회귀 방어망)
- [ ] fixture (a)(b)(c) 최소 골든 HTML 확정·커밋
- [ ] `test_conversion.py` 바이트 diff 테스트 통과
- [ ] `semantic_checks.py` — caption id 중복·dead link·이미지 누락·SEQ 미해결 전부 0건

### Phase 1~2 (엔진 통합)
- [ ] `tools/converter/` 가 유일한 엔진 디렉토리 (standalone 디렉토리에 엔진 파일 없음)
- [ ] Explorer 업로드 경로 변경 없이 동작 (기존 import도 shim으로 유지)
- [ ] fixture (a)(b)(c) cascade 변환 결과가 Phase 0 골든과 일치
- [ ] 시맨틱 품질 게이트 통과
- [ ] **플랫폼 CSS 에 h5/h6 스타일 및 북마크 hover 룰 추가 완료** (Phase 1e)
- [ ] Explorer 브라우저 미리보기에서 h5/h6 렌더링 어색하지 않음
- [ ] standalone exe 재빌드 결과 = 기존 exe (대표 문서 3종, 바이트 일치)
- [ ] `pytest tools/converter/tests/` 전체 통과

### Phase 3 (LibreOffice 어댑터)
- [ ] Docker 이미지 빌드 성공, LibreOffice + 한글 폰트 + `--safe-mode` 플래그 포함
- [ ] fixture (f): Linux Docker에서 heading 번호 보존 확인
- [ ] fixture (a)(b)(c): Word COM vs LibreOffice 차이 허용 범위 이내
- [ ] **시맨틱 품질 게이트 통과** (LibreOffice 경로 결과 기준)
- [ ] **Provenance meta 태그** 포함 (`converter-version`, `converter-adapter` 등) — fragment 모드는 주석 형태
- [ ] 사용자가 로컬 전처리한 DOCX 업로드 흐름 정상
- [ ] `backend/api/upload.py` 가 디스패처 호출로 전환, 어댑터 장애 시 폴백 동작
- [ ] 회사 Linux VM 실서버에서 대표 문서 5종 수동 검증

### Phase 4 (엔진 자립화, 선택)
- [ ] fixture (d) STYLEREF 캡션 문서: 세 어댑터 모두 원문 동일 번호
- [ ] fixture (e) SEQ 스위치 문서: 리셋 정상
- [ ] Phase 1~3 fixture 무회귀 (기본 설정)
- [ ] Standalone 재배포본으로 외부 업체 제보 샘플 재검증 → 번호 일치

### Phase 5 (문서)
- [ ] `docs/14-CONVERTER-ARCHITECTURE.md` 작성
- [ ] standalone README/email-draft 갱신
- [ ] MEMORY.md 관련 섹션 업데이트

---

## 6. 범위 외 (Out of Scope)

- 서버측 DRM 해제 — 정책·라이선스상 수행하지 않음 (사용자가 로컬에서 해제 후 업로드 전제)
- `pdf_converter.py` 분리/통합 — Explorer 전용으로 유지
- Python 패키지화 (`setup.py`, 설치형 배포) — 통합 후 검토
- Word 외 오피스 (Hancom Office 등) 전처리 지원
- Standalone의 자동 업데이트 시스템
- 번호 렌더링의 ROMAN/alphabetic 등 비표준 형식 완전 지원 (Phase 4에서 일부만)
- **북마크 localStorage 마이그레이션 정책** — 플랫폼 pre-launch 로 저장된 북마크 0건이므로 현 시점 불필요. 운영 개시 후 heading ID 체계 변경 시 재검토 → `backlog.md` 에 "북마크 마이그레이션 도구" 항목 기록
- 섹션 래핑을 h1~h3 으로 확장하는 UX 변경 — Compare 의존 조사 결과에 따라 별도 플랜으로 판단

---

## 7. 타임라인 (러프)

| 단계 | 예상 공수 | 선행 조건 |
|------|-----------|-----------|
| Phase 0 (회귀 방어망 + 시맨틱 게이트 + Compare 의존 조사) | 1.0~1.5일 | fixture 수집 필요 |
| Phase 1 (역이식 + 호환성 확보 CSS/JS/인덱서 + 고아 파일 훅) | 1.4~1.9일 | Phase 0 |
| Phase 2 (standalone 비우기) | 0.5일 | Phase 1 |
| Phase 3 (LibreOffice 어댑터 + safe-mode + provenance + 주석 스트립) | 1.4~2.4일 | Phase 2 |
| Phase 4 (엔진 자립화) | 2~3일 | Phase 3 완료 권장 |
| Phase 5 (문서) | 0.5일 | Phase 3 완료 후 |
| **합계 (Phase 0~5 전체)** | **6.8~9.8일** | |

### §8 의사결정 확정 내역 반영 (pre-launch 플랫폼)

- legacy 게이트 제거로 Phase 1a 공수 소폭 감소
- Phase 1e (CSS + JS bookmarks + 인덱서 + 인쇄/다크 테마) 신설 — +0.4일
- Phase 1c (고아 `.docx_1` 정리 훅) — +0.1일
- Phase 3f 확장 (주석 스트립) — +0.1일
- Phase 0 확장 (Compare 의존 조사 + heading id 중복 게이트) — +0.25일
- 총 추가 0.75일 반영됨
- 모든 phase 를 이번 통합에 포함 (조건부 실행 없음)

---

## 8. 의사결정 확정 사항 (2026-04-21)

사용자와의 대화로 전 항목 확정 완료. Phase 0 착수 준비 완료 상태.

### 8.1 핵심 설계 선택

| # | 항목 | 확정값 | 근거 |
|---|------|--------|------|
| 1 | 제목 감지 알고리즘 | **cascade (단일 모드)** | 플랫폼 운영 전 → 보호할 실서비스 콘텐츠 없음. legacy 게이트 불필요 |
| 2 | ~~기존 변환물 재변환 정책~~ | **해당 없음** | 재변환 대상 콘텐츠 자체가 존재하지 않음 |
| 3 | LibreOffice 어댑터 구현 | **B (UNO 매크로)** | 리눅스 Docker·윈도우 톰캣 양쪽이 동일 품질 내야 하므로 Word COM 동등 결과 필수 |
| 4 | 디스패처 `auto` 순서 | **Word COM → LibreOffice → native** | 각 환경에서 가용한 첫 어댑터 선택 |
| 5 | Phase 4 진행 여부 | **이번 통합에 포함** | Standalone P2 이슈 해결 + 플랫폼 품질 상한 동시 향상 |
| 6 | Standalone 재배포 타이밍 | **Phase 4 완료 후** | 고객이 체감할 품질 개선 포함된 시점에 전달 |

### 8.2 운영·리소스 확정

| 항목 | 결정 | 근거 |
|------|------|------|
| Docker 이미지 크기 제약 | **없음** | 사용자 확인 — 품질 최우선, 반입만 가능하면 OK |
| 폐쇄망 호환 | **필수** | 외부 네트워크 의존 금지 |
| Phase 0 fixture 소스 | **`contents/samples/` 활용** | MyPaper, SWA_PMS, SWA_Sample_{ENG,KOR} 등 이미 확보 |
| 플랫폼 운영 상태 | **pre-launch** | 실서비스 콘텐츠 0건, 보호 의무 없음 |
| Standalone 배포 이력 | **외부 업체에 전달됨** | 출력 안정성(바이트 일치 목표) 유지 필요 |

### 8.3 Pre-launch 덕분에 단순해진 것들

- legacy 모드 gate 불필요 → 엔진 코드 단순화
- `priority` 키 호환 shim 불필요 → 깨끗하게 제거
- 검색 인덱스 재생성 부담 없음 (인덱스 자체가 아직 없음)
- 기존 URL 앵커 · 북마크 호환성 고민 불필요

### 8.4 Standalone 때문에 남은 무회귀 제약

- 재빌드 exe 의 출력이 기존 exe 와 바이트 일치 (대표 문서 3종)
- cascade 는 이미 standalone 에 적용 중이라 차이 없을 것으로 기대, Phase 2 에서 실측 검증

---

## 9. 남은 확인 포인트

### 9.1 구현 진행 중 판단

1. **업로드된 DOCX가 "이미 로컬에서 전처리된 것"인지 서버가 판별 필요한지** — heading 단락에 `w:numPr` 존재 여부로 추정 가능. 판별 로직 추가 시 LibreOffice 재전처리 스킵으로 성능·리스크 감소. 단순성과의 트레이드오프. → Phase 3에서 구현 시 판단.

2. **Standalone 배포 대상자에게 "DRM 해제 후 업로드" 전제 재공지 필요 여부** — email-draft 업데이트 시점에 함께 강조.

---

## 10. 참고 자료

- `tools/docx2html-standalone/plan.md` — standalone 초기 설계
- `tools/docx2html-standalone/email-draft.md` — 외부 업체 전달 문서
- `backend/api/upload.py:85-160` — 현 Explorer converter 호출 지점
- `tools/converter/word_preprocessor.py` · `tools/docx2html-standalone/word_preprocessor.py` — 분기 대상
- `docs/13-DOCKER-OPERATIONS.md` — Docker 운영 가이드 (Dockerfile 수정 영향 지점)
- `memory/MEMORY.md` — DOCX→HTML 변환기 Key Lessons (테이블 병합, 텍스트 색상, OMML, COM 전처리)
- `CLAUDE.md` — 배포 3종 제약, 스타일 규칙
