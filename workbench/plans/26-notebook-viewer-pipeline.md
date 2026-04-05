# Plan-26: Notebook 뷰어 + 추출 파이프라인 개선

> **작성일**: 2026-04-05
> **상태**: 설계 논의 (구현 미착수)
> **목적**: Notebook을 플랫폼 참조 구현으로 완성 (연속 스크롤 뷰어 + MD 추출 품질 강화)
> **상위**: Plan-25 (데이터 아키텍처 로드맵) — Phase 1 착수 전에 본 계획 완료 권장

---

## 1. 배경

### 1.1 왜 Notebook을 먼저 완성하는가

Plan-25에서 플랫폼 전체를 "PDF 입력 + PDF.js 열람 + MD 인덱싱" 구조로 통일하기로 결정했다.
Notebook은 이 구조를 유일하게 구현 중인 서브시스템이므로, 여기서 이상적 형태를 완성하고 Explorer/Verify로 복제하는 전략이 가장 안전하다.

### 1.2 Notebook의 세 가지 성격

| 성격 | 업계 참조 | 해당 기능 |
|------|----------|----------|
| **PDF 뷰어** | Adobe Reader, Chrome PDF | 좌측 패널 (원본 열람) |
| **번역 워크벤치** | Trados, MemoQ, SmartCAT | 우측 패널 (번역 결과, 웹뷰) |
| **문서 분석 도구** | NotebookLM, ChatPDF | AI 요약, Q&A, 마인드맵 |

이 구분이 설계의 출발점: **PDF 뷰어 영역은 업계 표준을 따르고, 번역/분석 영역은 그 위에 연동**한다.

---

## Part A: PDF 뷰어 연속 스크롤 전환

### 2. 설계 원칙

#### 2.1 업계 표준 vs 맞춤형

| 영역 | 판정 | 근거 |
|------|:----:|------|
| 좌측 PDF 연속 스크롤 | **업계 표준** | 모든 PDF 뷰어(Adobe, Chrome, Preview)가 채택 |
| 페이지 번호 표시 + 줌 | **업계 표준** | 기본 뷰어 기능 |
| 좌우 패널 페이지 동기화 | **업계 표준** | Trados/MemoQ의 소스-타겟 동기화와 동일 패턴 |
| 우측 PDF 번역 연속 스크롤 | **맞춤형** | 미번역 페이지 placeholder 처리 필요 |
| 우측 웹뷰 전체 스크롤 | **이미 구현** | `webFullViewMode`로 검증 완료 |

**원칙**: 좌측은 표준 PDF 뷰어로, 우측 연동은 검증된 패턴 기반으로 설계.

#### 2.2 기능 유지/변경/제거 판정

| 기능 | 판정 | 사유 |
|------|:----:|------|
| Prev/Next 버튼 | **제거** | 연속 스크롤로 대체. 키보드 PgUp/PgDn으로 충분 |
| 비율 기반 scrollSync | **제거** | 연속 스크롤에서 의미 없음. 페이지 기반으로 대체 |
| 페이지별 웹뷰 모드 | **보조로 격하** | 전체 연속 스크롤을 기본으로 전환 |
| 페이지 번호 표시 | **유지** | 스크롤 위치 기반 자동 갱신 |
| 페이지 직접 입력 이동 | **유지** | 입력 → goToPage → scrollIntoView |
| 줌 +/- | **유지** | 가시 범위 리렌더 |
| 하이라이트/주석 | **유지** | 가상화 범위 내 다중 페이지 렌더로 확장 |
| 텍스트 선택/복사 | **유지** | PDF.js 텍스트 레이어 |
| 용어집 패널 | **유지** | 변경 없음 (페이지 무관) |
| AI 분석 패널 | **유지** | 변경 없음 (문서 레벨) |

---

### 3. 좌측 PDF 뷰어 설계

#### 3.1 목표 구조

```
좌측 패널 (.panel-scroll#left-scroll)
  └── .pdf-pages-stack
       ├── .pdf-page-wrapper[data-page=1]
       │    ├── <canvas>
       │    ├── .text-layer
       │    └── .annotation-layer
       ├── .pdf-page-wrapper[data-page=2]  ← placeholder (canvas 없음)
       │    └── (빈 — 높이만 확보)
       ...
       └── .pdf-page-wrapper[data-page=N]

  툴바: [페이지 N / 138] [줌 -] [100%] [줌 +]
```

#### 3.2 가상화 (Virtualization)

전체 페이지를 canvas로 렌더하면 메모리 폭발. 가시 영역 ± 버퍼만 렌더:

```
렌더 범위: [현재 보이는 페이지 - 2] ~ [현재 보이는 페이지 + 2]
나머지: placeholder (높이만 확보, canvas/텍스트/주석 레이어 없음)

스크롤 → IntersectionObserver → 범위 재계산
  → 범위 밖: canvas 해제, 텍스트/주석 DOM 제거 (메모리 반환)
  → 범위 안 진입: canvas 렌더 + 텍스트 레이어 + 주석 렌더
  → wrapper는 항상 유지 (placeholder 높이 보존)
```

placeholder 높이: 문서 최초 로드 시 각 페이지의 viewport를 계산하여 고정.

#### 3.3 currentPage 추적

IntersectionObserver로 가장 많이 보이는 페이지를 currentPage로 자동 갱신:

```javascript
observer = new IntersectionObserver(entries => {
  let best = entries.reduce((a, b) =>
    b.intersectionRatio > a.intersectionRatio ? b : a);
  if (best.isIntersecting) {
    var newPage = parseInt(best.target.dataset.page);
    if (newPage !== currentPage) {
      currentPage = newPage;
      updatePageNav();
      emitPageChanged();  // 우측 패널에 알림 (디바운스 적용)
    }
  }
}, { threshold: [0.1, 0.3, 0.5, 0.7] });
```

이미 웹뷰 전체 모드에서 동일 패턴이 검증됨.

#### 3.4 goToPage() 변경

```
현재: canvas를 지우고 새 페이지를 다시 그림
변경: 해당 페이지 wrapper로 scrollIntoView
```

모든 호출처(메모 클릭, Q&A 배지, 키보드, 페이지 입력)가 자동 호환.

#### 3.5 줌 처리

```
줌 변경 →
  1. 새 scale 계산
  2. 모든 wrapper placeholder 높이 업데이트 (viewport.height × newScale)
  3. 현재 스크롤 위치 보정 (줌 전 currentPage의 wrapper 위치 기준)
  4. 가시 범위 내 canvas만 리렌더
```

---

### 4. 우측 패널 기능별 설계

#### 4.1 PDF 번역 (pdf-translate)

**현재**: 우측에 currentPage의 번역 PDF 1페이지 표시.
**변경**: 우측도 연속 스크롤 + 미번역 페이지는 placeholder.

```
우측 PDF 번역 패널:
  ├── page-wrapper[data-page=1] → 번역 완료 → 번역 PDF canvas
  ├── page-wrapper[data-page=2] → 미번역 → "번역하기" 버튼 placeholder
  ├── page-wrapper[data-page=3] → 번역 중 → 스피너
  ...
```

**동기화**: 좌측 currentPage 변경 → 우측 같은 페이지로 scrollIntoView.
**번역 요청**: placeholder의 "번역하기" 버튼 클릭 → 해당 페이지 번역 → 완료 시 placeholder를 canvas로 교체.
**디바운스**: 좌측 빠른 스크롤 중에는 우측 갱신 안 함 (300ms 안정 후 동기화).

**포기하는 것**: 없음. 현재 1페이지 표시가 연속 스크롤 + placeholder로 자연스럽게 확장.

#### 4.2 웹뷰 번역 (web-translate)

**변경 사항**:
- **전체 모드를 기본으로** — 현재도 전체 연속 스크롤이 구현되어 있으므로, 이를 기본 동작으로 승격
- **페이지 모드는 보조** — 토글 버튼으로 전환 가능하되 기본값 아님

**좌우 동기화**:
```
좌측 스크롤 → currentPage=5 → 우측 전체 모드: _scrollFullViewToPage(5)
우측 스크롤 → Observer → currentPage=7 → 좌측: goToPage(7)
```

기존 `webFullViewMode`의 IntersectionObserver + `_scrollFullViewToPage()` 로직 그대로 활용.

**포기하는 것**: 비율 기반 `syncScroll()` 제거. 페이지 기반 느슨한 동기화로 대체 (업계 표준 — Trados 방식).

#### 4.3 메모 (memo)

**변경 최소**:
- 메모 목록: 변경 없음 (문서 전체, 페이지별 그룹핑)
- 메모 클릭: `goToPage()` → scrollIntoView (자동 호환)
- 좌측 주석 렌더: currentPage 1개 → **가시 범위 내 모든 페이지** (가상화 범위와 연동)

**포기하는 것**: 없음. 오히려 개선 (다중 페이지 주석 동시 표시).

#### 4.4 용어집 (glossary)

**변경 없음**. 문서/페이지 무관한 독립 기능.

#### 4.5 AI 분석 (ai-summary)

**변경 없음**. 요약·Q&A·마인드맵 모두 문서 레벨.
Q&A 페이지 배지 클릭 → `goToPage()` → scrollIntoView (자동 호환).

---

### 5. 좌우 동기화 설계

#### 5.1 기본 원칙: 페이지 기반 느슨한 동기화

```
좌측 스크롤 → IntersectionObserver → currentPage 변경 (디바운스 300ms)
  → 'pageChanged' 이벤트 발행
  → 활성 우측 패널이 구독:
     pdf-translate: 해당 페이지로 스크롤 (우측도 연속 스크롤)
     web-translate: 해당 페이지 섹션으로 스크롤
     memo/glossary/ai: 무시 (문서 레벨)
```

#### 5.2 역방향 동기화

```
우측 웹뷰 전체 모드 스크롤 → Observer → currentPage → 좌측 goToPage
우측 PDF 번역 스크롤 → Observer → currentPage → 좌측 goToPage
메모/Q&A 배지 클릭 → goToPage → 좌측 scrollIntoView
```

#### 5.3 동기화 on/off

현재도 동기화 토글 버튼이 있음. 유지.
OFF 시: 좌우 독립 스크롤 (각자 자유롭게 탐색).

---

### 6. 기존 코드 영향 분석

| 코드 | 변경 범위 |
|------|----------|
| `renderLeftPage()` | 리팩토링 → `renderPageInWrapper(pageNum)` (가상화 범위용) |
| `goToPage()` | canvas 교체 → scrollIntoView |
| `syncScroll()` | 제거 → 페이지 기반 `emitPageChanged()` 이벤트로 대체 |
| Prev/Next 버튼 HTML | 제거 |
| 페이지 표시 UI | 유지 (자동 갱신) |
| `renderAnnotations()` | 단일 페이지 → 가시 범위 다중 페이지 |
| 웹뷰 전체 모드 | 기본값으로 승격 |
| PDF 번역 우측 패널 | 단일 canvas → 연속 스크롤 wrapper 스택 |

---

## Part B: MD 추출 품질 강화

### 7. 현재 구현 현황

`md_extractor.py`에서 다수의 이터레이션을 거쳐 구현 완료된 항목:

| 항목 | 구현 함수 |
|------|----------|
| 심볼 폰트 불릿 → `•` 변환 | `_yolo_extract_text_with_bullets()` |
| 헤딩 이탤릭/볼드 제거 | `_clean_heading_styles()` |
| PyMuPDF4LLM 아티팩트 제거 | `intentionally omitted`, 빈 서식 |
| 캡션 자동 감지 + `<figure>` 래핑 | `_extract_caption_after()` |
| 표 3모드 (extract/image/off) | `_replace_tables_with_images()` |
| DocLayout-YOLO 폴백 | `_needs_yolo_fallback()` → YOLO → dict 3단계 |
| 이미지 영역 캡처 (클리핑 방지) | pixmap clip + BBOX_PADDING |
| 블록 파서 (heading/table/list/paragraph) | `md_translator.py:parse_blocks()` |

### 8. 잔여 품질 문제 및 개선 방안

#### Step 1 — 후처리 보강 + Marker 벤치마크 (병행 진행)

후처리는 어떤 엔진을 쓰든 필요. 동시에 Marker를 벤치마크하여 엔진 결정.

**(A) 후처리 파이프라인 보강** (코드 추가, 즉시):

| 문제 | 원인 | 해결 |
|------|------|------|
| 헤더/푸터 오염 | 매 페이지 반복 문서 제목·번호 | 페이지 간 첫/마지막 줄 빈도 분석 → 반복 줄 제거 |
| 하이픈 단어 분리 | 줄 끝 하이픈 유지 | `(\w)-\n(\w)` → 합침 |
| 단독 페이지 번호 | "1" 등이 본문에 혼입 | 단독 숫자 줄 제거 |
| 과다 빈 줄 | 3줄 이상 연속 | 2줄로 정리 |

**(B) PyMuPDF4LLM 옵션 활성화** (설정 변경, 즉시):

| 옵션 | 현재 | 개선 |
|------|------|------|
| `margins` | 미사용 | `(0, 50, 0, 50)` 헤더/푸터 크롭 |
| `table_strategy` | `lines_strict` 고정 | 실패 시 `text` 재시도 |

**(C) Marker 벤치마크** (A/B와 병행):

| | PyMuPDF4LLM (현재) | Marker |
|---|---|---|
| 방식 | 규칙 기반 (좌표 추론) | ML 기반 (시각적 레이아웃 이해) |
| 리스트 감지 | 구조 태그 없으면 불가 | 시각적 패턴으로 감지 |
| 헤더/푸터 | 물리적 크롭 (고정값) | 의미적 판별 |
| 속도 | 매우 빠름 | 5~30배 느림 (CPU) |
| 모델 | 없음 (0 MB) | ~2 GB |

**벤치마크**: MIL-STD 실문서 10~20페이지로 비교.
**평가 기준**: 리스트 보존, 표 구조, 헤더/푸터, 읽기 순서, 처리 속도.
**판단**: 품질 유의미 개선 시 Marker 채택, 아니면 PyMuPDF4LLM 유지.
**교체 범위**: `md_extractor.py`의 `extract_page()` 내부 엔진만 교체.
**롤백**: 설정 한 줄로 엔진 전환, 품질 저하 시 즉시 되돌림.

#### Step 2 — LLM 기반 교정 (선택된 엔진에서도 부족한 부분에 적용)

- 추출 후 Ollama에게 "MD 서식 교정" 요청
- 전체 페이지가 아닌 **품질 낮은 블록만 선별** (비용 최소화)
- 기존 Ollama 블록 번역 파이프라인에 교정 호출 삽입 가능

---

## 9. 구현 순서

```
Phase 1: Part B — MD 추출 품질 강화
  ├── (A) 후처리 보강 구현
  ├── (B) PyMuPDF4LLM 옵션 활성화
  └── (C) Marker 벤치마크 → 엔진 결정

Phase 2: Part A — 좌측 PDF 연속 스크롤
  ├── 가상화 컨테이너 + IntersectionObserver
  ├── goToPage → scrollIntoView 변경
  ├── currentPage 자동 추적
  ├── 텍스트/주석 레이어 다중 페이지 관리
  ├── 줌 처리 변경
  └── Prev/Next 버튼 제거, 툴바 정리

Phase 3: Part A — 우측 패널 연동
  ├── PDF 번역: 연속 스크롤 + 미번역 placeholder
  ├── 웹뷰: 전체 모드 기본화
  ├── 좌우 동기화: 페이지 기반 + 디바운스
  ├── 메모: 다중 페이지 주석 렌더
  └── syncScroll 제거

Phase 4: Part B Step 2 — LLM 교정
  └── 품질 부족 블록 선별 → Ollama 교정

Phase 5: 통합 테스트
  └── 실문서 기반 전체 파이프라인 검증
```

**Part B → Part A 순서 이유**: 연속 스크롤 뷰어 구현 시 추출된 MD로 테스트하게 되므로, MD 품질이 좋아야 뷰어 검증도 정확함.

---

## 10. 진행 현황

> 최종 갱신: 2026-04-05

| Phase | 내용 | 상태 | 비고 |
|:-----:|------|:----:|------|
| **1** | **Part B — MD 추출 품질 강화** | ✅ 완료 | |
|  1-A  | 후처리 보강 (머리글/꼬리글, 하이픈, 빈줄) | ✅ | pos 기반 hf 제거 + 하이픈 합침 + 빈줄 정리. 실문서 전후 비교 검증 완료 |
|  1-B  | PyMuPDF4LLM 옵션 활성화 (`margins` 등) | ⏭️ | 1-A pos 기반 제거로 충분, margins 불필요 판정 |
|  1-C  | Marker 벤치마크 → 엔진 결정 | ✅ | PyMuPDF4LLM 유지 (Marker: OCR 아티팩트·표 후퇴·12x 느림) |
| **2** | **Part A — 좌측 PDF 연속 스크롤** | ⬜ 미착수 | |
|  2-A  | 가상화 컨테이너 + IntersectionObserver | ⬜ | |
|  2-B  | goToPage → scrollIntoView 변경 | ⬜ | |
|  2-C  | currentPage 자동 추적 | ⬜ | |
|  2-D  | 텍스트/주석 레이어 다중 페이지 관리 | ⬜ | |
|  2-E  | 줌 처리 변경 | ⬜ | |
|  2-F  | Prev/Next 버튼 제거, 툴바 정리 | ⬜ | |
| **3** | **Part A — 우측 패널 연동** | ⬜ 미착수 | |
|  3-A  | PDF 번역: 연속 스크롤 + 미번역 placeholder | ⬜ | |
|  3-B  | 웹뷰: 전체 모드 기본화 | ⬜ | |
|  3-C  | 좌우 동기화: 페이지 기반 + 디바운스 | ⬜ | |
|  3-D  | 메모: 다중 페이지 주석 렌더 | ⬜ | |
|  3-E  | syncScroll 제거 | ⬜ | |
| **4** | **Part B Step 2 — LLM 교정** | ⬜ 미착수 | |
|  4-A  | 품질 부족 블록 선별 → Ollama 교정 | ⬜ | |
| **5** | **통합 테스트** | ⬜ 미착수 | |
|  5-A  | 실문서 기반 전체 파이프라인 검증 | ⬜ | |

**범례**: ⬜ 미착수 · 🔄 진행 중 · ✅ 완료 · ⏭️ 건너뜀

---

## 11. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 대형 PDF 메모리 과다 | canvas 메모리 점유 | 가상화 ±2 제한 + canvas 명시적 해제 |
| 스크롤 중 우측 과부하 | 잦은 currentPage 변경 | 300ms 디바운스 |
| Marker 품질 기대 이하 | 도입 비용 낭비 | 설정 전환 즉시 롤백 |
| Marker 속도 과다 | 사용자 대기 | 비동기 추출 (현재도 백그라운드) — 체감 영향 제한적 |
| 텍스트 레이어 DOM 복잡도 | 다중 페이지 성능 | 가시 범위만 렌더 + 범위 밖 제거 |
| 우측 PDF 연속 스크롤 복잡도 | 미번역 placeholder 관리 | 단순 구조 (버튼 1개 + 상태 텍스트) |

---

## 참고

- **상위 계획**: [Plan-25](25-data-architecture.md) (데이터 아키텍처 로드맵)
- **목업**: `workbench/mockups/explorer-pdf-comparison.html` — 뷰어 3안 비교
- **현재 코드**: `js/translator.js` (4948줄), `backend/services/md_extractor.py` (871줄)
- **검증된 패턴**: 웹뷰 전체 문서 모드 (`webFullViewMode` + IntersectionObserver)
- **업계 참조**: Adobe Reader (연속 스크롤), Trados (소스-타겟 동기화), NotebookLM (문서 분석)
