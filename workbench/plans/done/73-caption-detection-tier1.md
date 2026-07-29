# Plan-73 — 캡션 감지 Tier 1 (표시 전용) 분리 · 웹북 캡션 간격 정상화

> **상태: ✅ 완료 (2026-07-29 — 코드 완성 + 로컬 검증 + 커밋 `5129957`)**
> 사용자 결정: 괄호 표기 **제외**(JS 동치로만 좁힘) · **B안 채택**(캡션 위/아래 대칭) · **조사 배제 추가**(엔진·JS 동시)
> 검증: 웹북 24/16/16px → **4/4/4px** · Explorer `id`·참조링크 변화 **0건** · 실문서 오탐 제거(MyPaper 23→22)
> 보고서: `workbench/reports/plan-73-feedback-2026-07-29.md`
> 배포·업체 전달은 `workbench/DEPLOY-QUEUE.md` (운영 축 — 완료 조건 아님)
> 작성: 2026-07-29 · 트리거: 업체 웹북(전자정부 기반)에 탑재된 standalone 변환기(`docx2html.exe` v1.5.0) 출력에서 **표 위 캡션이 표와 지나치게 떨어져** 보이는 현상 제보. 조사 결과 Explorer 는 정상인데 웹북만 깨지는 이유가 **엔진 결함을 프론트 JS 가 덮고 있었기 때문**으로 확인.
> 근거: `tools/converter/converter.py:1667` `_detect_caption()` · `js/app.js:659` `optimizeContent()` 2단계 · `tools/docx2html-standalone/webbook-content.css:204-221` · `workbench/plans/done/39-docx-caption-hyphen-loss.md`(엔진 SSOT 확인) · `workbench/plans/done/37-converter-unification.md`(Phase 0 회귀 방어망)

## 🧭 한줄 요약

캡션 감지를 **Tier 1(표시 = `class="caption"`)** 과 **Tier 2(의미 = `id` + 본문 참조 링크)** 로 분리하고, **Tier 1 만 프론트 JS 수준으로 완화**한다. 의미 계층(Tier 2)은 완전 동결하여 기존 규칙·문서 계약·회귀 테스트를 하나도 건드리지 않으면서, JS 가 없는 웹북에서도 캡션이 대상에 붙어 보이게 만든다.

## 📊 진행 현황

| 영역 | 상태 | 비고 |
|------|------|------|
| A. 엔진 Tier 분리 | ✅ 완료 | `converter.py` — 참조 캡션 본체 diff 0줄, `tag=='p'` 가드 추가 |
| B. 표시 CSS 수정 | ✅ 완료 | `:has(> img)` 정밀 타겟팅 + 위/아래 대칭(B안) |
| C. 회귀 방어망 | ✅ 완료 | `test_caption_tiers.py` 신규 — 계층 판정 + JS 동치 고정 |
| D. 재빌드·전달 | ✅ 완료 | v1.6.0 exe + `2026-07-29-webbook-exe-v1.6.0/` |
| E. 문서 갱신 | ✅ 완료 | USER-GUIDE·ARCHITECTURE·DEPLOY-QUEUE |

---

## 왜 지금 프레임 (Context)

### 1. 엔진은 이미 한 벌인데, 캡션 "규칙"은 8곳에 흩어져 있다

Explorer 백엔드(`backend/api/upload.py:150`)와 standalone(`docx2html.spec` → `pathex=../converter/`)은 **동일한 `converter.py`** 를 쓴다. 전처리도 양쪽 다 기본 OFF(`backend/config.py:76 WORD_COM_PREPROCESS=False` / v1.5.0 CLI 기본 OFF). **출력 HTML 은 동일**하다.

벌어진 것은 엔진이 아니라 **감지 규칙**이고, 지금 8곳에 따로 박혀 있다.

| # | 위치 | 패턴 성격 | 용도 |
|---|---|---|---|
| 1 | `converter.py:1688` | 구분자 **필수** (가장 엄격) | 감지 → class + id + link |
| 2 | `converter.py:1718` `_make_caption_id` | 구분자 불필요 | ID 생성 |
| 3 | `converter.py:1784` `_linkify_references` | 구분자 불필요 | 본문 참조 링크 |
| 4 | `js/app.js:660` | 느슨 + 150자 가드 | **Explorer 전용** 화면 폴백 |
| 5 | `js/figure-popup.js:208` | 느슨 (`Fig.` 미포함) | 팝업 캡션 탐색 |
| 6 | `backend/services/similarity_engine.py:454` | `Tbl.` (≠ `Tab.`) | 유사도 점수 제외 |
| 7 | `backend/services/compare_service.py:506` | 앵커 없음 `finditer` | Verify 규칙 검증 |
| 8 | `tools/converter/pdf_converter.py:282` | 별도 구현 | PDF 경로 |

방향이 뒤집혀 있다 — **가장 느슨한 규칙이 프론트엔드(#4)에, 가장 엄격한 규칙이 엔진(#1)에** 있다.

### 2. 그래서 Explorer 는 멀쩡하고 웹북만 깨졌다

```js
// js/app.js:659-667 — 콘텐츠를 #main-content 에 넣기 직전 실행
var captionPattern = /^(Figure|Table|그림|표|Fig\.)\s*\d/i;
doc.querySelectorAll('p').forEach(function(p) {
    if (p.classList.contains('caption')) return;   // 엔진이 붙였으면 비켜감
    var text = p.textContent.trim();
    if (captionPattern.test(text) && text.length < 150) p.classList.add('caption');
});
```

엔진이 놓친 캡션을 브라우저에서 다시 잡아준다. `tools/docx2html-standalone/` 에는 **`.js` 파일이 하나도 없다** — 산출물은 `<style>` + `<div class="docx-content">` 정적 HTML(`docx2html.py:129`). 구제할 주체가 없다.

실측 판정 차이:

| 캡션 표기 | 엔진 | Explorer JS |
|---|:---:|:---:|
| `표 1. 시스템 구성` | ✅ | ✅ |
| **`표 1 시스템 구성`** (공백만) | ❌ | ✅ |
| **`표1 시스템 구성`** (붙여쓰기) | ❌ | ✅ |
| **`Table 1 Overview`** | ❌ | ✅ |
| **`그림 2 흐름도`** | ❌ | ✅ |
| `Tab. 1: x` | ✅ | ❌ |
| `[표 1]` · `<표 1>` · `(표 1)` | ❌ | ❌ |
| `표 A-1 부록` | ❌ | ❌ |

`_detect_caption()` docstring(`converter.py:1674`)은 "구분자 후보: `:` `：` `–` `—` `-` `.` `]` `>` **공백**(개행 포함)"이라 적어놨는데, 실제 문자 클래스 `[:：–—\-.\]\>]` 에 **공백이 없다.** 문서-구현 불일치.

### 3. 감지 실패 시 간격이 6배로 벌어진다

| 상태 | 캡션 `<p>` 하단 | `<table>` 상단 | 실제 간격 |
|---|---|---|---|
| 감지 성공 | 4px (`.caption`) | 4px (`.caption + table`) | **4px** |
| 감지 실패 | 16px (`p`) | 24px (`table`) | **24px** (마진 병합) |

### 4. 이미지로 캡처한 표는 정규식만 고쳐도 안 낫는다 (CSS 2차 결함)

```css
/* webbook-content.css:210 */
.docx-content .caption + p > img { margin-top: 4px; }   /* ← img 에 마진 */
```

간격을 만드는 주체는 `img` 가 아니라 **감싼 `<p>`** 다(`_extract_inline_images` 는 `<p><img></p>` 를 낸다 — `converter.py:1377`). Explorer 는 `css/tokens.css:10` 의 `* { margin: 0 }` 전역 리셋 덕에 우연히 가려졌지만, 그 리셋이 없는 웹북에서는 `<p>` 기본 마진이 살아난다.

> 문서 담당자들이 "표현이 어려운 표를 이미지로 캡처"하는 관행이 실재하므로 **이 경로가 오히려 주 증상**일 수 있다.

### 5. 규칙 영향 전수 조사 결과 — Tier 2 만 안 건드리면 깨지는 규칙이 없다

| 대상 | 근거 | 영향 |
|---|---|---|
| Verify 규칙 검증 (`table_caption`/`figure_caption`) | `compare.py:75 extract_text()` → **평문 단락 배열**로 동작. HTML class 안 봄 | **없음** |
| 유사도 `exclude_caption` (Plan-45 v3 자동 제외) | `similarity_engine.py:605` — **문장 텍스트** 기반 | **없음** |
| 검색 인덱스 (`build-search-index.py`) | 캡션 참조 없음 | **없음** |
| `semantic_checks.py` `caption_id_unique` / `caption_id_pattern` | **ID 를 늘리면** 위반 위험 | Tier 2 동결 시 **없음** |
| `docs/04-USER-GUIDE.md:864` "구분자 필수" 계약 | Tier 2 기준을 서술 → 유효 유지 | 한 줄 **보강만** |
| Explorer 렌더링 | 최종 `.caption` 집합 = **엔진 ∪ JS**. 엔진을 JS 수준으로 넓혀도 합집합 불변 | **없음** |

`js/app.js:662` 의 `if (p.classList.contains('caption')) return;` 덕분에 **JS 는 엔진 결과를 덮어쓰지 않는다.** 충돌은 구조적으로 발생하지 않는다.

### 6. 반대로 Tier 2 를 풀면 즉시 규칙이 깨진다

`_detect_caption()` 은 클래스만 붙이지 않는다 — `id="tbl-1"` 부여 + `_caption_map` 등록 + **본문 "표 1" 자동 하이퍼링크**(`_linkify_references`)까지 동반한다. 여기를 넓히면:

- `semantic_checks.py:44` `caption_id_unique` error 증가 (이미 KI-001 로 "원본 저자가 '표 16' 을 두 번 사용" 사례 존재)
- 엔진 주석이 직접 경고한 본문 오탐 — *"'그림 1 또한 중요하다' 같은 본문 오탐을 피하기 위해 기본은 구분자 필수"*
- `docs/04-USER-GUIDE.md:864` 사용자 계약 위반

**엄격함은 실수가 아니라 의도된 설계였다.** 그래서 푸는 대상을 표시 계층으로만 한정한다.

---

## Scope

### ✅ 하려는 것

1. **엔진 Tier 분리** — `converter.py` 에 표시 전용 판정(Tier 1)을 추가. Tier 2(현행 `_detect_caption`)는 **한 글자도 안 건드림**.
   - Tier 1 통과 → `class="caption"` **만**
   - Tier 2 통과 → 현행 그대로 `class="caption"` + `id` + `_caption_map` + 링크
2. **Tier 1 판정 기준** — 프론트 JS(`app.js:660`)와 **의도적으로 동일 수준**:
   - 구분자 불필요 (`표 1 시스템 구성`)
   - 키워드-숫자 사이 공백 선택 (`표1`)
   - ~~선행 괄호/대괄호/꺾쇠 허용~~ → **제외 확정** (사용자: 사내 문서에 안 쓰임.
     JS 동치로만 좁혀 오탐 표면적 축소)
   - **150자 길이 가드** (JS 와 동일 — 본문 오탐 차단)
   - **조사 배제 추가** (착수 후 사용자 지시) — 번호에 조사가 붙으면 본문
     (`표 1을 보면`, `그림 3과 같이`). JS 도 동시 변경해 동치 유지
3. **웹북 표시 CSS 수정** — `webbook-content.css` 의 `.caption + p > img` → `.caption + p` 로 교정(이미지 캡처 표 대응). `css/content.css` 도 **대칭 정렬**(Explorer 는 전역 리셋으로 가려져 있어 시각 변화 없음, 규칙 일관성 목적).
4. **회귀 방어망** — 캡션 표기 편차 픽스처 추가 + 골든 갱신 + **"Explorer 합집합 불변" 검증**(골든 diff 에 `class="caption"` 추가만 있고 `id=` / `<a data-fig-ref` 변화 0건임을 확인).
5. **v1.6.0 재빌드 + 업체 전달 패키지** — `dist/docx2html.exe` 갱신, `2026-XX-XX-webbook-exe/` 형식으로 README + 메일 초안 동봉 (v1.5.0 전달 선례 답습).
6. **문서 갱신** — `docs/04-USER-GUIDE.md` 캡션 조건 문구에 "표시상 인식은 더 넓다" 보강, `DEPLOY-QUEUE.md` append.

### ⛔ 의도적으로 안 하는 것 (근거 포함)

| 제외 항목 | 근거 |
|---|---|
| **Tier 2(id/link) 완화** | 위 Context §6 — 규칙 3건 즉시 위반 |
| **`표 A-1` 영문자 번호 지원** | `semantic_checks.py:44` `^(fig\|tbl)-\d+(-\d+)*$` 위반(`tbl-a-1`). ID 패턴 규칙까지 동반 수정 필요 → 별건 |
| **`js/app.js:660` 폴백 제거** | `contents/` 의 기존 등록 HTML 은 재변환 전까지 옛 출력. 제거 시 **잘 되던 문서가 깨진다.** 레거시 안전망으로 영구 존치 |
| **`Tab.` / `Tbl.` 축약어 통일** (#1 vs #6) | 유사도 점수에 영향 → Plan-45 체계 재검증 필요. 별건 |
| **표 캡션 위치 규칙 이원화 정합** | `unified-doc-format-spec.md:36` 은 표 캡션을 **표 직후(아래)** 로 정의 — 사내 워드 규칙(표=위)과 반대. 저작 축 vs 변환 축 정책 결정 사안 |
| **목록 문단 캡션** (`_get_list_item_html:950` 이 `_detect_caption` 미호출) | 캡션이 `<li>` 안으로 들어가 표와의 인접성이 구조적으로 깨짐 → 클래스만으로 해결 불가. 구조 변경 필요 |
| **`.figure-wrap` 죽은 셀렉터 제거** | 변환기가 생성하지 않는 클래스(CSS 3파일에만 존재). 순수 정리 항목 → 후속 |
| **`pdf_converter.py` 캡션 경로** | PDF 는 별도 감지 구현. 증상 무관 |

---

## Tasks

### A. 엔진 Tier 분리 (`tools/converter/converter.py`)

- [x] A1. `_is_display_caption(text)` 신설 — Tier 1 판정 (정규식 + 150자 가드). 순수 함수로 분리하여 테스트 가능하게
- [x] A2. `_process_paragraph:722-725` 수정 — `caption_id`(Tier 2) 결과와 `_is_display_caption`(Tier 1) 결과를 OR 로 결합해 `class` 결정. **`id_attr` 은 Tier 2 결과에만 의존(현행 유지)**
- [x] A3. `_detect_caption()` docstring 정정 — "구분자 후보에 공백 포함" 오기 제거 + Tier 1/2 관계 명시
- [x] A4. `__version__.py` → `1.6.0` + 버전 이력 추가

### B. 표시 CSS (웹북 + Explorer 대칭)

- [x] B1. `webbook-content.css` — `.caption + p > img` → **`.caption + p:has(> img)`**
      (계획의 `.caption + p` 는 캡션 뒤 *본문* 문단까지 압축하므로 정밀 타겟팅으로 변경)
- [x] B2. `2026-06-29-webbook-css/docx-content.css` 동일 반영 (CSS-only 배포 A안 패키지 동기화)
- [x] B3. `css/content.css` 대칭 정렬 — Explorer 실화면 확인 후 반영
- [x] B4. 표 / 이미지 캡처 표 브라우저 확인 → **4px** 실측
- [x] **B5 (계획 외·필수)** — `:has()` 규칙을 전부 **독립 규칙으로 분리**.
      셀렉터 그룹은 하나만 못 읽어도 규칙 전체가 폐기되므로, 구형 브라우저
      (`:has()` = Chrome/Edge 105+)에서 **표 규칙까지 같이 죽는 결함**을 자체
      검토로 발견·수정. 동일 패턴의 기존 결함(`css/platform-footer.css:42`)도
      함께 분리. 프로젝트 전체 재스캔 결과 혼재 **0건**

### C. 회귀 방어망 (`tools/converter/tests/`)

- [x] C1. 픽스처 신설 (`fixtures/caption_variants.docx`) — 표기 10종 + 본문 오탐 후보
      8종(조사 5 + 길이초과 1 + 일반 2)
- [x] C2. 계층 경계 단위 테스트 — 표시 캡션에 **`id` 가 없음**을 명시적으로 단언
- [x] C3. 골든 diff 검수 — `id=` / `data-fig-ref` 변화 **0건** 실증
- [x] C4. `semantic_checks.py` 전 골든 통과 (신규 error 0)
- [x] **C5 (계획 외)** — `run_tests.py` 에 캡션 계층 검사 연결.
      fingerprint 가 태그명만 해싱해 class·id 변화를 못 잡는다는 걸 사전 분석에서
      발견 → "테스트 통과"가 안전의 증거가 못 되는 구멍을 메움
- [x] **C6 (계획 외)** — JS 동치 자동 고정(`check_js_parity`). `js/app.js` 의
      정규식·길이가드를 읽어 엔진과 대조 + "선언만 하고 판정에 미사용" 검사

### D. 재빌드 · 업체 전달

- [x] D1. `build.bat` 으로 v1.6.0 exe 빌드 (`pyinstaller --clean docx2html.spec`)
- [x] D2. exe 변환 → 캡션 간격 확인 — **CLI 만 검증**. exit code(0/2)·CLI 인자·
      내장 CSS·provenance 확인. ⚠️ **GUI 모드는 미검증**(대화형 창이라 자동 확인
      불가). 변경은 `converter.py`+CSS 에 한정되고 `gui.py` 시그니처 무변경이라
      위험은 낮으나, 전달 전 GUI 1회 수동 실행 권장
- [x] D3. 전달 패키지 구성 — `2026-XX-XX-webbook-exe-v1.6.0/` (exe + README + 메일 초안). v1.5.0 선례 형식 답습
- [x] D4. 업체가 **교체만 하면 되는지** 확인 — 호출 방식·CLI 인자 변경 없음을 README 에 명시

### E. 문서

- [x] E1. `docs/04-USER-GUIDE.md:864` — Tier 2(ID·링크) 조건은 유지, "표시상 캡션 인식은 더 넓게 동작" 한 줄 보강
- [x] E2. `docs/05-ARCHITECTURE.md` 문서 변환 파이프라인 절에 Tier 1/2 구분 반영
- [x] E3. `workbench/DEPLOY-QUEUE.md` append — v1.6.0 exe 업체 전달 건 (운영 축)

---

## Acceptance

### 필수

1. **웹북 경로**: v1.6.0 exe 출력 HTML 을 리셋 없는 페이지에 삽입했을 때, `표 1 시스템 구성`(구분자 없음) 캡션이 **실제 표·이미지 캡처 표 양쪽 모두** 4px 로 붙는다.
2. **Explorer 무변화**: 골든 diff 에서 `id=` / `data-fig-ref` 변화 **0건**. 로컬 Docker(:80)에서 기존 문서 렌더가 변경 전과 동일.
3. **회귀 테스트**: `tools/converter/tests/run_tests.py` 전 통과 + `semantic_checks` error 0.
4. **본문 오탐 0**: `그림 1 또한 중요하다`, 150자 초과 문단이 `.caption` 을 받지 않는다.
5. **Tier 2 무변경**: `_detect_caption()` 본체·`_make_caption_id()`·`_linkify_references()` diff **0줄**.

### 선호

6. Tier 1 정규식이 `js/app.js:660` 과 **의미적으로 동치**임을 테스트로 고정 (향후 드리프트 감지).
7. 업체 전달 README 에 v1.5.0 → v1.6.0 변경점이 1~2줄로 요약되어 있다.

### 판정 (2026-07-29)

| # | 결과 | 근거 |
|---|------|------|
| 1 | ✅ | 웹북 실측 24/16/16px → **4/4/4px** (v1.5.0 exe 대비) |
| 2 | ✅ / **⚠️ 부분** | 골든 4종 id·링크 변화 **0건**. 다만 **그림 아래 캡션 16px→4px** 는 사용자가 선택한 **B안의 의도된 변경** — 이 항목에 한해 "렌더 동일" 면제 |
| 3 | ✅ | `run_tests.py` 전 통과 · `pytest` 2 passed · 시맨틱 신규 error **0** |
| 4 | ✅ | 픽스처로 고정. **조사 배제 추가**로 실문서 오탐 1건까지 제거(MyPaper 23→22) |
| 5 | ✅ | `_detect_caption` 본체·`_make_caption_id`·`_linkify_references` **diff 0줄** (docstring 만 보강) |
| 6 | ✅ | `check_js_parity()` — 정규식 2종 + 길이가드 + 미사용 검사 |
| 7 | ✅ | README 에 실측 before/after 표 + 브라우저 호환 표 포함 |

---

## 미해결 / 협의 필요 → **전건 해소 (2026-07-29)**

| # | 항목 | 결정 |
|---|---|---|
| 1 | 괄호 표기 실사용 빈도 | ✅ **사내 미사용** → Tier 1 에서 제외, JS 동치로만 좁힘 |
| 2 | `css/content.css` 대칭 수정 | ✅ **승인·반영** (B안). 캡션 위는 무변화, 그림 아래만 16px→4px |
| 3 | 기존 등록 문서 재변환 | ✅ **불필요** — `contents/*.html` 은 JS 폴백이 계속 커버. 웹북 측 기존 콘텐츠는 업체 판단 (DEPLOY-QUEUE 기록) |
| 4 | `.figure-wrap` 죽은 셀렉터 | ➡️ **후속 이월** — 순수 정리 항목, 보고서 잔여 #5 |

### 전달 전 확인 필요 (사용자·업체 몫 — 코드로 알 수 없음)

| 항목 | 내용 |
|------|------|
| **업체 브라우저 버전** | Chrome/Edge **105 미만**이면 이미지 캡처 표 캡션은 미해결로 남음(표 캡션은 정상 동작하도록 규칙 분리 완료) |
| **업체 페이지 charset** | UTF-8 미선언 시 한글 깨짐. **v1.5.0 부터의 기존 문제** — 검증 중 재현됨 |
| **GUI 1회 수동 실행** | D2 참조 — CLI 만 자동 검증됨 |

---

## 산출물

| 파일 | 성격 |
|---|---|
| `tools/converter/converter.py` | Tier 1 판정 신설 (Tier 2 무변경) |
| `tools/converter/__version__.py` | 1.5.0 → 1.6.0 |
| `tools/docx2html-standalone/webbook-content.css` | `.caption + p` 교정 |
| `tools/docx2html-standalone/2026-06-29-webbook-css/docx-content.css` | 동기화 |
| `css/content.css` | 대칭 정렬 (협의 후) |
| `tools/converter/tests/fixtures/caption_variants.docx` | 신규 픽스처 |
| `tools/converter/tests/golden/*` | 골든 갱신 |
| `tools/docx2html-standalone/dist/docx2html.exe` | v1.6.0 |
| `tools/docx2html-standalone/2026-XX-XX-webbook-exe-v1.6.0/` | 업체 전달 패키지 |
| `docs/04-USER-GUIDE.md` · `docs/05-ARCHITECTURE.md` | 문구 보강 |
| `workbench/DEPLOY-QUEUE.md` | 전달 건 append |

---

## Notes (결정 + 트레이드오프)

- **왜 엔진을 SSOT 로 올리고 JS 를 남기나** — 감지 규칙의 정의는 엔진 하나로 모으되, JS 는 "레거시 콘텐츠 안전망"으로 역할을 재정의한다. 규칙 확장은 앞으로 엔진에서만 한다. JS 제거는 기존 등록 문서를 깨뜨리므로 영구 금지.
- **왜 Tier 를 나누나** — 표시(무해)와 의미(ID·링크, 규칙 결합)는 위험도가 다르다. 하나의 정규식으로 둘을 겸하던 구조가 "느슨하게 풀면 규칙이 깨진다"는 교착을 만들었다. 분리하면 표시만 안전하게 넓힐 수 있다.
- **트레이드오프** — Tier 1 완화로 `.caption` 이 늘면 `text-align: center` 를 받는 문단도 는다. 150자 가드가 주 방어선이고, 본문이 "표 N…" 으로 시작하면서 150자 미만인 경우는 실제로 드물다. 이 위험은 Explorer 가 이미 동일 기준으로 **수개월 운영해 왔다**는 사실로 실증된다 — 새 위험이 아니라 **기존에 감수 중이던 위험을 엔진으로 옮기는 것**.
- **완료 정의** = 코드 완성 + 로컬 Docker 검증 + exe 빌드·육안 확인. **업체 전달·웹북 반영은 완료 조건 아님**(`DEPLOY-QUEUE.md` 운영 축).
- **조사 과정에서 발견한 별건 3종**(축약어 `Tab.`/`Tbl.` 불일치, `figure-popup.js` 의 `Fig.` 누락, Verify `_check_caption` 의 앵커 없는 `finditer` 로 본문 참조까지 캡션으로 계수)은 이번 범위 밖. `backlog.md` 승격 후보.

---

## Progress Log

- **2026-07-29** — plan 생성. 선행 조사 완료(캡션 규칙 8개소 전수 추적, Explorer/웹북 차이 원인 규명, 규칙 영향 분석). 협의 대기.
- **2026-07-29** — 사용자 결정 반영(괄호 표기 제외 · B안 채택) 후 `/run-plan` 실행. A~E 전 영역 완료. 사전 분석에서 **fingerprint 가 속성 변화를 못 잡는다**(`run_tests.py:54` 태그명만 해싱)는 점을 발견해 `test_caption_tiers.py` 로 방어망 보강. 웹북 실측 24/16/16px→4px, Explorer id·링크 변화 0건.
- **2026-07-29 (실문서 검증)** — 합성 픽스처로 부족해 `contents/samples/` 실문서 5종을 v1.5.0/v1.6.0 exe 로 대조. **SWA 매뉴얼 3종은 캡션 문단 자체가 없고**(표 앞에 h3 직행), MyPaper 캡션 22개는 전부 구분자 표기라 이미 검출되던 것 → **"구분자 없는 캡션"이 샘플에 0건**. 실문서에서 확인된 유일한 변화가 **오탐 1건**이었음. JS 폴백도 동일 오탐을 내는 것을 실행으로 확인(7/7 일치) → 새 위험이 아니라 기존 Explorer 판정의 이식임이 실증됨.
- **2026-07-29 (조사 배제)** — 위 오탐 대응으로 사용자 지시. 번호에 조사가 붙으면 본문 판정. **`js/app.js` 도 동시 변경**해 동치 유지. 판정 22건 불일치 0 · JS 실행 대조 12/12 · **실문서 MyPaper 23→22**(오탐 제거).
- **2026-07-29 (자체 검토 — `:has()` 결함)** — `:has()` 를 핵심 규칙 그룹에 넣은 것이 결함임을 자체 검토로 발견. CSS 는 셀렉터 그룹에 못 읽는 게 하나라도 있으면 **규칙 전체를 폐기**하므로, 구형 브라우저에서 **표 규칙까지 죽어 v1.5.0 보다 나빠질** 뻔했다(시뮬레이션 24px). `:has()` 규칙 전면 분리 후 4px 확인. 같은 패턴의 기존 결함 `css/platform-footer.css:42` 도 수정, 프로젝트 전체 혼재 0건.
- **2026-07-29 (완료)** — 커밋 `5129957` (20 files, +1011/-17). 미해결 4건 전건 해소, 잔여 11건은 보고서 "잔여·후속"으로 이관. 업체 전달·배포는 `DEPLOY-QUEUE.md` 운영 축으로 분리(완료 조건 아님).
