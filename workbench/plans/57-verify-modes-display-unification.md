# Plan-57 — Verify 시스템 뷰 통일 (비교/검증 모드를 유사도 모드 기준으로) — v3.1

> 작성일: 2026-05-02 (v1) / 2026-05-02 갱신 (v2 — 1차 design-review 반영) / 2026-05-02 갱신 (v3 — 2차 design-review 반영) / 2026-05-02 갱신 (v3.1 — 3차 design-review 반영, 미세 패치)
> 대상 시스템: Verify (`compare.html` + `backend/api/compare.py`)
> 변경 범위: 백엔드 추출기 통합 + Block AST 모델 + 프론트 패널 렌더링 교체 + 단위/통합 테스트
> 상태: 계획 단계 (사용자 승인 후 진행)

---

## 진행 현황 요약

| Phase | 내용 | 예상 공수 | 상태 |
|-------|------|---------|------|
| Phase 0 | Baseline 캡처 + fail-then-pass 단위 테스트 7건 골격 작성 | 0.5일 | ⬜ 대기 |
| Phase 1 | 백엔드 통합 — `markdown_to_blocks` + Block AST (`block_types`/`heading_levels`/`table_ids`) + `extract_document` 확장 + `extract_text` shim | 2.5일 | ⬜ 대기 |
| Phase 1b | paste 경로 `extract_document(text=...)` 통합 (입력 방식 일관성) | 0.5일 | ⬜ 대기 |
| Phase 2 | 프론트 패널 렌더링 교체 — `renderParagraphs` 가 `display_html` 우선 사용 | 1.5일 | ⬜ 대기 |
| Phase 3 | 비교 모드 diff 정합 — `[data-paragraph-idx]` 셀렉터 + 표 행 단위 처리 + Excel export 표 행 처리 | 2일 | ⬜ 대기 |
| Phase 4 | 검증 모드 정합 — `_check_caption` `block_types` 가드 + `_analyze_structure` 메타 우선 + AI 분류 표 행 제외 + `rule_engine._split_sentences` 영향 검증 | 1.5일 | ⬜ 대기 |
| Phase 5 | 비교/검증 단위 테스트 신규 작성 + Playwright 시각 (3 시나리오) + 자동 회귀 + 점수 변동 정량 기준 | 1.5일 | ⬜ 대기 |
| Phase 6 | 행동 변화 안내 토스트 + history `schema_version` + 가이드 갱신 + 보고서 + done- 처리 | 0.5일 | ⬜ 대기 |
| **합계** | — | **10.5일** | **0/8** |

> 상태 표기: ⬜ 대기 · 🟡 진행 중 · ✅ 완료 · ❌ 보류/롤백

---

## 변경 이력

### v3.1 (2026-05-02) — 3차 design-review 반영 (미세 패치)
- **`_extract_terms` 동형 결함 해결**: `full_text = "\n".join(paragraphs)` 패턴이 `_check_caption` 외에 `_extract_terms` 에서도 동일하게 사용 (compare_service.py:378). 표 셀 안 단위 ("5kg", "100mm") 가 본문 단위로 잘못 카운트되어 인텔리전스 패널 *units* 통계 왜곡. `_check_caption` 과 동일 가드 추가.
- Phase 4 변경 파일에 `_extract_terms` 추가
- Phase 5 신규 Case K — 표 셀 단위가 *units* 통계에 미포함 검증
- 공수 10.5일 유지 (1줄 패치만)

### v3 (2026-05-02) — 2차 design-review 반영
- **C1' 해결 (탭 컨텍스트 누출)**: 표 행 issue context/snippet 변환 정책 명문화 (§2.4 + Phase 4) — backend issue 생성 시 탭 → ` | ` 변환
- **C2' 해결 (`_check_caption` full_text 오염)**: full_text 합치기 단계도 `block_types` 가드 (Phase 4)
- **C3' 해결 (`_HEADING_PATTERN` 형식 불일치)**: paragraphs[i] heading 형식 통일 = 정규식 매칭 보장 (§2.3 + Phase 4)
- **table_id frontend 활용 정책**: 1차 미사용, backlog 이관 명문화 (§2.6)
- **CSS 우선순위**: `[data-paragraph-idx]` 완전 교체 명시, `cp-paragraph` 공존 X (§4 Phase 2 강화)
- **`validate_paragraphs` 호출자 보장**: API 가 항상 메타 전달 명시 (§4 Phase 4 + §1.3)
- **AI 분류 정확도 trade-off**: 1차 자동 EDITORIAL 결정 + backlog 에 *"표 셀 수치 변경 정확도 개선"* 이관 명시 (§7.3)
- **`mergePdfLineBreaks` 처리 결정**: frontend 유지 (paste 시 backend 호출 전 적용) (§4 Phase 1b)
- 공수 10.5일 유지 (Phase 4 보강만, 신규 Phase 없음)

### v2 (2026-05-02) — 1차 design-review 반영
- **C1 해결 (textContent 매핑)**: `block_types` 1차 도입 + char_offset 정책 명문화 (표 행은 행 전체 클래스만, 일반 paragraph 만 span 삽입)
- **C2 해결 (`_check_caption` DOM 파괴)**: 가드를 `block_types` 기반으로 (휴리스틱 폴백 제거)
- **C3 해결 (`_analyze_structure` 깨짐)**: heading 의 `## ` prefix 제거 + 번호 보존 + `heading_levels` 메타 별도 + `_analyze_structure` 동시 수정
- **W1 해결**: AI 분류에서 표 행 자동 제외 (`block_types` 활용)
- **W2 해결**: Phase 1b 신규 — paste 경로 통합
- **W3 해결**: Phase 5 점수 변동 ±5% 정량 기준 추가
- **W4 해결**: Excel export 표 행 처리 (Phase 3)
- **W5 해결**: history `schema_version` 도입 (Phase 6)
- **신규**: 비교/검증 단위 테스트 신규 작성 (Phase 5)
- 공수 8.5일 → 10.5일

### v1 (2026-05-02) — 초안
- 7 Phase 8.5일

---

## 0. Context

### 0.1 사용자 페인 (현재 상태)
같은 `compare.html` 안에서 모드만 토글하면 동일 문서가 다르게 보인다.

| 항목 | 유사도 모드 | 비교/검증 모드 |
|------|-----------|--------------|
| 표 | `<table class="sim-md-table">` 시각 보존 | **표 자체 누락** (`_extract_docx`가 `doc.paragraphs`만 순회) |
| 헤딩 | `<h1~h6>` 위계 표시 | 평탄 `<div class="cp-paragraph">` |
| 본문↔표 순서 | Plan-53 보존 | 분리 순회로 표가 끝에 모임 |
| `## ` markdown prefix | Plan-56으로 자동 변환 | raw 노출 가능 |
| OCR 폴백 | 자동 | 미지원 (스캔 PDF 빈 단락) |
| 페이지 마커 | `<!-- Page N -->` 시각화 | 미지원 |

### 0.2 결함 메커니즘
- **백엔드 분리**: `backend/services/compare_service.py:_extract_docx` 가 `for p in doc.paragraphs:` 만 사용 → `doc.tables` 미처리. `_extract_pdf` 도 표 추출 X.
- **프론트 분리**: `renderParagraphs(panel, paragraphs, pageMap)` (line 517~545) 이 `<div class="cp-paragraph">{escapeHTML(text)}</div>` 평탄 렌더 → 표/헤딩 시각 정보 0.
- **데이터 모델 분리**: 비교/검증 = `paragraphs: string[]` / 유사도 = `markdown + plain_text + display_html`. 같은 입력의 두 데이터 표현이 코드 경로에서 분리.

### 0.3 실사용 데이터 (Plan-57 작성 직전 측정)
- admin/testbot 최근 history 20건: **100% 유사도 모드**
- 비교 세션 디스크: 1건 (2026-03-15, 7주 전)
- 검증 모드 history: 0건

→ 비교/검증 모드는 dormant 상태이나, 시스템 정합성 + 향후 부활 가능성을 위해 통합 정당화. 실사용 0인 만큼 회귀 위험도 사용자 영향 0.

### 0.4 산업 표준 (외부 조사)
- **MS Word Compare**: 단일 추출 엔진 + 통합 Track Changes 뷰 (SSOT)
- **Draftable**: 단일 "Draftable engine" + 렌더링 프로파일
- **Diff Guru / Obsidian Drift / Markdown Utils**: markdown AST 1회 파싱 → 다중 뷰
- **Vale linter**: markdown-aware 단일 파서 → 에디터 인라인 오버레이
- **CCMS / SSOT 원칙**: 한 번 추출, 다중 렌더링

→ 현대 표준은 통합 추출 + 다중 렌더링. 우리 분리 파이프라인은 anti-pattern.

### 0.5 통합 가능성 (전문가 검증)
- 3 모드 모두 동일 ALLOWED_EXTENSIONS (`.doc, .docx, .pdf` 업로드 + 텍스트 paste)
- `extract_document` 모듈 주석에 *"향후 비교/검증 모드에서도 재사용 가능"* 명시 (의도된 미완 통합)
- v2 의 Block AST 모델로 char_offset / heading 메타 / table 메타 모두 정합 보장 (§2.2)

---

## 1. 목표

### 1.1 In Scope
- 비교/검증 모드의 백엔드 추출기를 `extract_document` 로 통합 (Block AST 도입)
- 비교/검증 모드의 프론트 패널을 유사도 모드와 동일한 `sim-md-view` 기반 렌더링으로 교체
- diff/validation/AI 분류 알고리즘을 `block_types` 메타로 정확화 (표 행/heading 차등 처리)
- paste 경로도 통합 (입력 방식 일관성)
- Plan-52~56 의 모든 개선 효과 자동 적용
- 비교/검증 모드 자체 단위 테스트 신규 작성 (회귀 안전망)

### 1.2 Out of Scope
- diff 표 셀 단위 비교 (Plan-52와 동일 ROI 판단으로 미채택)
- 비교/검증 모드 신기능 (UX 부활 캠페인 등) — 별도 plan
- 검증 규칙 추가 (기존 규칙 그대로, 시그니처만 `block_types` optional 매개변수 추가)
- API 시그니처 *제거* (응답 필드 추가만, 기존 필드 보존)
- `compare_service._extract_docx`/`_extract_pdf` 즉시 제거 (다음 PR로 미룸)

### 1.3 비기능 요구
- 회귀 0: 기존 단위 테스트 100% PASS + 비교/검증 신규 테스트 PASS
- 점수 변동: ±5% 이내 (Phase 5 정량 기준)
- API 호환: 기존 frontend 코드 무수정으로도 동작 (legacy `paragraphs` 필드 잔존)
- history 호환: `schema_version` 으로 옛 데이터 식별 가능
- 롤백 가능: thin shim 1회 revert로 즉시 복원

---

## 2. 핵심 설계 — Block AST + SSOT

### 2.1 데이터 모델 (v2 — `block_types` + 메타 추가)
```python
# extract_document(...) 통합 후 반환
{
    "markdown": str,                  # 표시용 (Plan-52~56 적용된 풍부 형식)
    "plain_text": str,                # 유사도 연산용 (현재 그대로)
    "paragraphs": list[str],          # 비교/검증 호환 — block 단위 plain text
    "block_types": list[str],         # 신규 — 'paragraph'|'heading'|'table_row'
    "heading_levels": list[int|None], # 신규 — heading 일 때 1~6, 그 외 None
    "table_ids": list[int|None],      # 신규 — 같은 table 의 행 그룹화 ID, 그 외 None
    "page_map": list[int|None],       # paragraphs[i] ↔ 페이지 번호 1:1
    "display_html": str,              # data-paragraph-idx="i" 부착 풍부 HTML
    "page_count": int|None,
    "is_scanned": bool,
}
```

5개 list 필드 (`paragraphs`, `block_types`, `heading_levels`, `table_ids`, `page_map`) 는 **모두 같은 길이** 보장.

### 2.2 Block AST 모델 (내부)
```python
@dataclass
class Block:
    type: Literal["paragraph", "heading", "table_row"]
    text: str            # paragraphs[i] 가 될 plain text (markup 제거)
    raw_md: str          # 원본 markdown 라인 (display_html 생성용)
    page: int | None
    heading_level: int | None  # heading 일 때 1~6
    table_id: int | None       # 같은 table 의 행 그룹화 (전역 단조 증가)
```

`page_break` 는 Block 으로 만들지 않고 별도 페이지 매핑으로 처리.

### 2.3 paragraphs[i] 산출 규칙 (★ char_offset 정합 핵심)

| 블록 타입 | paragraphs[i] 값 | 예시 |
|---------|-----------------|------|
| paragraph | 본문 텍스트 그대로 | `"본 문서는 검증을 다룬다."` |
| heading | `## ` prefix 제거 + 번호+점+공백 보존 | `"1.2. SCOPE"` (원본: `## 1.2. SCOPE`) 또는 `"1.2 SCOPE"` (원본 형식 유지) |
| table_row | `\t` (탭) 으로 셀 구분 | `"A100\t5\t검증 완료. 출하 가능."` |

**heading 형식 정책** (v3 — `_HEADING_PATTERN` 정합):
- DOCX heading 스타일에서 derive 시 원본 텍스트 그대로 보존 (markdown prefix만 제거)
- `_HEADING_PATTERN` 을 `r"^(\d+(?:\.\d+)*)\.?\s+(.+)"` 로 완화 — 점 유무 모두 매칭 (Phase 4)
- 번호 없는 heading (예: "Abstract") → `_analyze_structure` 폴백 처리 (number="", title=text)

**탭 구분자 채택 이유**:
- 표 셀 안 텍스트에 공백/마침표가 자주 등장 → 공백 join 시 셀 경계 모호
- 탭은 일반 본문에 거의 없는 문자 → 셀 경계 명확
- `_check_*` 규칙이 paragraphs[i] 를 보고 char_offset 계산 시 셀 안 텍스트가 탭으로 둘러싸여 있어 셀 단위 식별 가능
- DOM textContent (`<tr>.textContent`) 와는 별개 — char_offset 시각화는 §2.4 정책 따름

**탭 구분자 부작용 차단** (v3 — 사용자 노출 차단):
- backend 가 issue 생성 시 `context` 필드 안의 탭 → ` | ` 변환 (§2.4 의 헬퍼 `_format_issue_context` 사용)
- substring 매칭 (`para.find(term)`) 은 탭이 자연 경계 역할 → "검증" + "필요" 셀 → "검증\t필요" 에서 "검증필요" 같은 cross-cell 매칭 자동 차단

### 2.4 char_offset 정책 (★ Critical C1/C2 + v3 컨텍스트 누출 해결)

| 블록 타입 | char_offset 시각화 | 메커니즘 | issue.context 처리 |
|---------|-----------------|---------|------------------|
| paragraph | char_start/char_end span 삽입 (현행) | `<p>` 안에 `<span class="validate-mark">` 부분 색 | 원본 그대로 |
| heading | char_start/char_end span 삽입 (현행) | `<h{n}>` 안에 `<span>` 부분 색 | 원본 그대로 |
| **table_row** | **블록 전체 클래스만 부착, span 삽입 X** | `<tr class="validate-mark severity-warning">` 행 전체 색 | **탭 → ` \| ` 변환** |

**근거**: `<tr>.textContent` 는 cells 무구분자 concat 이라 paragraphs[i] (탭 구분) 와 textContent 가 다름. 표 셀 단위 highlight 를 정확히 그리려면 `<th>/<td>` 안 textContent 안에서 셀별 char_offset 재계산이 필요한데 ROI 부족 → 1차는 행 단위로만.

**v3 추가 — issue context 변환** (탭 누출 방지):
- backend 가 issue 생성 시 `context` 필드의 탭 → ` | ` 변환
- 사용자에게 표시되는 모든 텍스트 (tooltip, drill-down panel, sidebar) 가 탭 미노출
- 공통 헬퍼 `_format_issue_context(text, block_type)` 신규 (`compare_service.py`):
  ```python
  def _format_issue_context(text: str, block_type: str) -> str:
      """issue context 의 탭을 사용자 친화 구분자로 변환."""
      if block_type == 'table_row':
          return text.replace('\t', ' | ')
      return text
  ```
- `_check_forbidden_terms`, `_check_inconsistent_terms`, `_check_sentence_length`, `_check_caption` 모두 `context` 채울 때 호출

**프론트 구현**:
```js
// renderValidationHighlights 의 분기
if (block_types[i] === 'table_row') {
    el.classList.add('validate-mark', 'severity-' + iss.severity);
    el.title = iss.message;  // backend 가 이미 탭 변환된 message 전달
} else {
    // 기존 char_offset span 삽입 로직
}
```

### 2.5 두 뷰 derivation
- **유사도 모드** (변경 없음): `markdown` → `split_sentences` → `_build_tagged_html` (sentence 단위, `data-sent-idx`)
- **비교/검증 모드** (신규): `blocks` → `paragraphs[]` + `block_types[]` + `heading_levels[]` + `table_ids[]` + `display_html` (block 단위, `data-paragraph-idx`)

### 2.6 매핑 보장
- `paragraphs[i]` ↔ `block_types[i]` ↔ `heading_levels[i]` ↔ `table_ids[i]` ↔ `page_map[i]` 1:1
- `display_html` 의 `[data-paragraph-idx="i"]` 셀렉터로 5개 메타 모두 조회 가능
- char_offset 정합은 §2.4 정책 따름 (DOM textContent 와 무관, paragraphs[i] 문자열 기준)

### 2.7 `table_id` frontend 활용 정책 (v3 — 명문화)
- **1차 (Plan-57)**: backend 만 derive, frontend 미사용. diff 결과는 N행 = N modified 단위로 표시.
- **잠재적 활용 (backlog)**: "표 통째로 추가 (N행 added 합집합)" UX 개선, 미니맵 표 단위 마커 압축, 검색 결과의 표 단위 그룹화.
- **이관 위치**: `workbench/plans/backlog.md` 의 *"Verify — 표 단위 diff 합집합 UX"* 항목 신설 (Phase 6 에서 동시 작성).
- **이유**: 1차는 정합성 확보가 목적, 표 단위 UX 는 실사용 데이터 (Step 2 관찰) 기반 결정 권장.

---

## 3. Phase 개요

상단 *"진행 현황 요약"* 표 참조. 상태 갱신은 본 문서 상단 표에서 수행.

---

## 4. Phase 별 상세

### Phase 0 — Baseline 캡처

**목표**: 변경 전 상태를 객관적으로 기록 + 결함을 fail-then-pass 테스트로 명문화.

**산출물**:
- `workbench/screenshots/plan57-before-compare-table.png` — 비교 모드 표 누락
- `workbench/screenshots/plan57-before-verify-table.png` — 검증 모드 표 누락
- `workbench/screenshots/plan57-before-similarity-table.png` — 유사도 모드 정상 (대조군)
- `tests/sim_extract_unification_test.py` 신규 (7 케이스, 모두 fail 상태):
  | Case | 검증 |
  |------|------|
  | A | `extract_document` 가 `paragraphs[]` 반환 |
  | B | `extract_document` 가 `block_types[]` / `heading_levels[]` / `table_ids[]` 반환 |
  | C | `extract_document` 가 `display_html` 반환 (data-paragraph-idx) |
  | **D** ★ | DOCX 표 셀 텍스트가 `paragraphs[]` 에 포함 (현재 결함) |
  | E | 표 행 paragraphs[i] 가 탭 구분 형식 |
  | **F** ★ | heading 의 `## ` prefix 제거 + 번호 보존 + heading_levels[i] 정확 |
  | G | `extract_text` shim 이 `extract_document` 와 동일 결과 |

**완료 기준**: 단위 테스트 7건 작성 (모두 FAIL 상태), before 스크린샷 3건 commit.

---

### Phase 1 — 백엔드 통합 (Block AST 도입)

**목표**: `extract_document` 가 Block AST 기반으로 5개 메타 필드 동시 반환. `extract_text` 는 thin shim 으로 위임.

**변경 파일**:
- `backend/services/document_extractor.py` — `markdown_to_blocks` 신규 + `extract_document` 반환값 확장
- `backend/services/compare_service.py` — `extract_text` 가 `extract_document` 위임 (`_extract_docx`/`_extract_pdf` 는 deprecated)
- `backend/api/compare.py` — `/upload` 응답에 신규 5개 필드 추가 (기존 필드 보존)
- `tests/sim_extract_unification_test.py` — Phase 0 의 7건 PASS

**핵심 함수 신규**:
```python
def markdown_to_blocks(md: str) -> tuple[list[Block], dict[int, int]]:
    """Markdown 을 Block 배열로 파싱 + 페이지 매핑 동시 반환.
    
    Returns:
        blocks: list[Block]
        page_map: list[int|None] — blocks[i] ↔ 페이지 번호
    """
    # <!-- Page N --> 마커 추출 → page tracking
    # ## ... → Block(type='heading', text=h_match.group(2), heading_level=N, table_id=None)
    # | ... | → 연속 표 행을 같은 table_id 로 그룹화, Block(type='table_row', text='\t'.join(cells))
    # 그 외 → Block(type='paragraph', text=원본)
    # 빈 줄 → 블록 생성 안 함

def build_block_tagged_html(blocks: list[Block]) -> str:
    """Block 배열을 data-paragraph-idx 태깅된 HTML 로 변환.
    
    Plan-56 의 _build_tagged_html 를 block 단위로 확장.
    표는 같은 table_id 의 연속 행을 <table class="sim-md-table"> 로 그룹화.
    """
```

**`extract_document` 반환값 확장**:
```python
blocks, page_map = markdown_to_blocks(md)
return {
    "markdown": md,                     # 기존
    "plain_text": plain,                # 기존
    "paragraphs": [b.text for b in blocks],
    "block_types": [b.type for b in blocks],
    "heading_levels": [b.heading_level for b in blocks],
    "table_ids": [b.table_id for b in blocks],
    "page_map": page_map,
    "display_html": build_block_tagged_html(blocks),
    "page_count": ...,                  # 기존
    "is_scanned": ...,                  # 기존
}
```

**`compare_service.extract_text` shim**:
```python
def extract_text(file_bytes: bytes, ext: str) -> dict:
    """[Deprecated since Plan-57] extract_document 로 위임."""
    from .document_extractor import extract_document
    result = extract_document(file_bytes=file_bytes, ext=ext)
    # 기존 시그니처 보존 + 신규 메타 동봉 (호환)
    return {
        "paragraphs": result["paragraphs"],
        "page_count": result["page_count"],
        "page_map": result["page_map"],
        "block_types": result["block_types"],
        "heading_levels": result["heading_levels"],
        "table_ids": result["table_ids"],
        "display_html": result["display_html"],
    }
```

**완료 기준**: Phase 0 단위 테스트 7건 PASS + 기존 회귀 38건 (Plan-52~56) PASS + `compare_service._extract_docx`/`_extract_pdf` 호출처 0 (grep 확인).

---

### Phase 1b — paste 경로 통합 (W2 해결)

**목표**: 입력 방식 (upload/paste) 에 무관하게 동일 시각 품질 제공.

**변경 파일**:
- `compare.html:818~836` — paste 텍스트를 frontend split → 백엔드 `extract_document(text=...)` 호출로 변경

**`mergePdfLineBreaks` 처리 결정** (v3 — 명시):
- frontend 에 **유지** (compare.html:756~786)
- paste 시 backend 호출 **전** 적용 (PDF 시각적 줄바꿈 → 문장 단위 재결합)
- 이유: backend `extract_document(text=...)` 는 plain text 가 들어오면 문서 구조 알 수 없으므로 PDF-like 정규화 무리. frontend 가 paste 시점의 source 컨텍스트 보유.

**현재 (frontend split)**:
```js
var paragraphs;
if (text.indexOf('\n\n') !== -1) {
    paragraphs = text.split(/\n\n+/);
} else {
    paragraphs = text.split(/\n/);
}
paragraphs = paragraphs.filter(function(p) { return p.trim(); });
onDocumentLoaded(side, '붙여넣기 텍스트', paragraphs);
```

**변경 후 (backend 통합 + mergePdfLineBreaks 보존)**:
```js
// PDF 줄바꿈 병합은 paste 시점 그대로 유지
text = mergePdfLineBreaks(text);

var formData = new FormData();
formData.append('text', text);  // file 대신 text 필드 사용
fetch(API_BASE + '/compare/extract-document', {
    method: 'POST',
    body: formData,
    credentials: 'include'
})
.then(...)
.then(function(data) {
    onDocumentLoaded(side, '붙여넣기 텍스트', {
        paragraphs: data.paragraphs,
        blockTypes: data.block_types,
        headingLevels: data.heading_levels,
        tableIds: data.table_ids,
        pageMap: data.page_map,
        displayHtml: data.display_html
    });
});
```

**완료 기준**: paste 텍스트가 sim-md-view 풍부 렌더로 표시 (Playwright). frontend split 로직만 제거 (mergePdfLineBreaks 보존). PDF 텍스트 paste 시 줄바꿈 정합 회귀 0.

---

### Phase 2 — 프론트 패널 렌더링 교체

**목표**: `renderParagraphs` 가 `display_html` 우선 사용. 메타 데이터 (block_types 등) 를 `docState[side]` 에 보존.

**변경 파일**:
- `compare.html` — `renderParagraphs`, `onDocumentLoaded`, `docState[side]`, `restorePlaceholder`
- `css/compare.css` — `.sim-md-view` 가 비교/검증 모드 패널에서도 활성화 (스타일은 기존 정의 그대로)

**CSS 우선순위 정책** (v3 — 명시):
- 통합 후 **`cp-paragraph` 와 `sim-md-view` 는 동일 패널에 공존하지 않음** (양자택일)
- diff 클래스 (`diff-para-added`, `diff-para-deleted`, `diff-para-modified`, `diff-gap`) 는 **`[data-paragraph-idx]` 블록에 직접 부착** (sim-md-view 안의 `<p>`/`<h{n}>`/`<tr>` 모두)
- 셀렉터 정합:
  ```css
  /* 신규 (Phase 2) — sim-md-view 안의 모든 블록 타입에 diff 클래스 적용 */
  .sim-md-view [data-paragraph-idx].diff-para-added    { background: var(--diff-added); }
  .sim-md-view [data-paragraph-idx].diff-para-deleted  { background: var(--diff-deleted); }
  .sim-md-view [data-paragraph-idx].diff-para-modified { background: var(--diff-modified); }
  
  /* 기존 cp-paragraph 셀렉터 (legacy fallback) — paste 무 backend 시나리오 보존 */
  .cp-paragraph.diff-para-added    { ... }
  ```
- `[data-paragraph-idx]` 셀렉터가 표 행 (`<tr>`) 에도 작동하므로 표 행 diff 클래스 부착 가능

**`renderParagraphs` 확장**:
```js
function renderParagraphs(panel, data) {
    // data: { paragraphs, blockTypes, headingLevels, tableIds, pageMap, displayHtml }
    // (기존 호출 호환: Array.isArray(data) 면 v1 방식)
    
    var displayHtml = data.displayHtml;
    
    // 기존 placeholder/paste/loading/cp-text-content/sim-md-view 제거 로직
    
    if (displayHtml) {
        var div = document.createElement('div');
        div.className = 'sim-md-view';
        div.innerHTML = displayHtml;
        panel.appendChild(div);
    } else {
        // 폴백: 기존 cp-text-content 평탄 렌더 (legacy 경로, paste backend 미가용 시)
    }
}
```

**`docState[side]` 확장**:
```js
docState[side] = {
    file: ...,
    text: ...,
    paragraphs: [],
    blockTypes: [],       // 신규
    headingLevels: [],    // 신규
    tableIds: [],         // 신규
    pageMap: ...,
    displayHtml: ...,     // 신규
    filename: ''
};
```

**완료 기준**: 비교/검증 모드 업로드 → 표/헤딩 시각 보존 (Playwright). paste 도 통합 후 동일 품질.

---

### Phase 3 — 비교 모드 diff 정합 + Excel export

**목표**: `renderDiffHighlights` 가 `[data-paragraph-idx]` 셀렉터로 markdown 블록에 diff 클래스 부착. Excel export 가 표 행 paragraphs 도 가독성 있게 출력.

**변경 파일**:
- `compare.html:3729~3816` — `renderDiffHighlights` 의 HTML 빌드 부분 교체
- `compare.html:5924 부근` — Excel export 표 행 처리

**`renderDiffHighlights` 변경**:
```js
function renderDiffHighlights(changes) {
    var displayHtmlA = docState.a.displayHtml;
    var displayHtmlB = docState.b.displayHtml;
    
    // sim-md-view 컨테이너 재생성
    var divA = recreateSimMdView(panelBodyA, displayHtmlA);
    var divB = recreateSimMdView(panelBodyB, displayHtmlB);
    
    // [data-paragraph-idx] 블록에 diff 클래스 부착
    var changeOrder = buildChangeOrder(changes, docState.a.paragraphs, docState.b.paragraphs);
    
    for (var k = 0; k < changeOrder.length; k++) {
        var entry = changeOrder[k];
        var blockTypeA = docState.a.blockTypes[entry.iA];
        var blockTypeB = docState.b.blockTypes[entry.iB];
        
        if (entry.type === 'modified') {
            // 표 행끼리 비교: 셀 단위 diff 미채택, 행 단위 modified 클래스만
            // paragraph/heading 끼리: 단어 단위 wordDiffs 인라인 span
            if (blockTypeA === 'table_row' || blockTypeB === 'table_row') {
                // 행 전체 modified 클래스만
                addClassToBlock(divA, entry.change.indexA, 'diff-para-modified');
                addClassToBlock(divB, entry.change.indexB, 'diff-para-modified');
            } else {
                // 기존 wordDiffs 인라인 span 로직
            }
        }
        // added, deleted 도 동일 패턴
        // gap 삽입은 [data-paragraph-idx] 블록 직전에
    }
}
```

**Excel export 표 행 처리** (W4 해결):
```js
// 기존:
docState.a.paragraphs[c.indexA]  // 표 행이면 "col1\tcol2\tcol3"

// 변경 후:
function paragraphForExport(side, idx) {
    var bt = docState[side].blockTypes[idx];
    var text = docState[side].paragraphs[idx];
    if (bt === 'table_row') {
        // 탭 → " | " 변환 (Excel 셀 안에서 가독성)
        return '[표] ' + text.replace(/\t/g, ' | ');
    }
    if (bt === 'heading') {
        var lvl = docState[side].headingLevels[idx];
        return '[H' + lvl + '] ' + text;
    }
    return text;
}
```

**완료 기준**: 표/헤딩 포함 DOCX 2건 비교 → 표 행 변경이 행 단위로 시각화 (Playwright). Excel export 시 표 행이 `[표] col1 | col2 | col3` 형태로 가독성 있게 출력.

---

### Phase 4 — 검증 모드 정합

**목표**: `_check_caption` `block_types` 가드 + `_analyze_structure` 메타 우선 + AI 분류 표 행 제외 + `rule_engine._split_sentences` 영향 검증.

**변경 파일**:
- `backend/services/compare_service.py` — `validate_paragraphs`, `_check_caption`, `_analyze_structure`, `_classify_requirements`, `_extract_terms`, `classify_changes`
- `backend/services/rule_engine.py` — `run_rules` 시그니처 (선택적 `block_types` 매개변수)
- `compare.html` — `renderValidationHighlights` 표 행 분기

**`validate_paragraphs` 시그니처 확장 + 호출자 보장** (v3 — 명시):
```python
def validate_paragraphs(
    paragraphs: list[str],
    preset: str | None = None,
    block_types: list[str] | None = None,    # 신규 — Plan-57 후 항상 전달
    heading_levels: list[int|None] | None = None,  # 신규 — Plan-57 후 항상 전달
) -> dict:
    # block_types 가 None 이면 v1 호환 동작 (헤딩 인식 깨짐 가능)
    # API 가 항상 전달하도록 Phase 4 에서 호출부 동시 수정
    # _check_caption 등에 block_types 전달
    # _analyze_structure 가 heading_levels 우선 사용
```

**API 호출자 (`backend/api/compare.py`) 동시 수정** (v3 — 강제):
```python
# 기존:
result = validate_paragraphs(paragraphs, preset)

# 변경:
result = validate_paragraphs(
    paragraphs,
    preset,
    block_types=body.get("block_types"),
    heading_levels=body.get("heading_levels"),
)
```

**Frontend 호출자 (`compare.html` 검증 실행 핸들러) 동시 수정**:
```js
// /api/compare/validate POST body 에 block_types/heading_levels 동봉
fetch(API_BASE + '/compare/validate', {
    method: 'POST',
    body: JSON.stringify({
        paragraphs: docState.a.paragraphs,
        block_types: docState.a.blockTypes,
        heading_levels: docState.a.headingLevels,
        preset: ...
    }),
    ...
});
```

**`_check_caption` 가드** (Critical C2 + v3 full_text 오염 해결):
```python
def _check_caption(paragraphs, severity, params, label_ko, label_en, block_types=None):
    issues = []
    pattern = re.compile(...)
    
    # v3 — 본문 참조 카운트용 full_text 도 표 행 제외
    # (표 셀 안 "표 N" 텍스트가 본문 참조로 잘못 카운트되는 거짓 음성 방지)
    if block_types:
        full_text = "\n".join(
            p for i, p in enumerate(paragraphs) if block_types[i] != 'table_row'
        )
    else:
        full_text = "\n".join(paragraphs)  # 폴백 (legacy)
    
    # 캡션 수집 — 표 행 제외
    captions = []
    for i, para in enumerate(paragraphs):
        if block_types and block_types[i] == 'table_row':
            continue
        for m in pattern.finditer(para):
            captions.append((i, int(m.group(1)), m.start(), m.end()))
    
    # 번호 연속성 검사 (기존 로직)
    # 본문 참조 확인 — full_text 에 표 행 미포함 (v3)
    for cap in captions:
        ref_count = len(ref_pattern.findall(full_text))
        if ref_count <= 1:
            issues.append({
                # ... context 는 _format_issue_context 호출 (paragraph 이므로 변환 없음)
                "context": _format_issue_context(paragraphs[cap[0]][:40], block_types[cap[0]] if block_types else 'paragraph'),
            })
```

**`_HEADING_PATTERN` 완화** (v3 — Critical C3' 해결):
```python
# 기존: r"^(\d+(?:\.\d+)*)\.\s+(.+)"  — 마지막 점 필수 → "1.2 SCOPE" 미매칭
# 변경: r"^(\d+(?:\.\d+)*)\.?\s+(.+)" — 점 선택 → 양 형식 모두 매칭
_HEADING_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+)")
```
회귀 방지: Phase 5 Case F 가 "1.2 SCOPE" / "1.2. SCOPE" / "Abstract" 3가지 형식 모두 검증.

**`_analyze_structure` 메타 우선** (Critical C3 해결):
```python
def _analyze_structure(
    paragraphs: list[str],
    block_types: list[str] | None = None,
    heading_levels: list[int|None] | None = None,
) -> dict:
    headings = []
    for i, para in enumerate(paragraphs):
        text = para.strip()
        if not text:
            continue
        
        # Plan-57: block_types 가 'heading' 이면 메타 우선
        if block_types and block_types[i] == 'heading':
            level = heading_levels[i] if heading_levels else 1
            # paragraphs[i] 가 "1.2 SCOPE" 또는 "1.2. SCOPE" (## prefix 제거됨, 점 유무 모두 매칭)
            m = _HEADING_PATTERN.match(text)
            if m:
                num_str = m.group(1)
                title = m.group(2).strip()
            else:
                # 번호 없는 heading (예: "Abstract", "Introduction")
                num_str = ""
                title = text
            headings.append({
                "level": level,
                "number": num_str,
                "text": title,
                "paragraph_index": i,
            })
            continue
        
        # 폴백: legacy paragraph 형태 — 본문 안 "1. Title" 검출 (구버전 호환)
        m = _HEADING_PATTERN.match(text)
        if m:
            # ... 기존 로직 (block_types 미전달 시 작동)
```

**`_classify_requirements`**:
- paragraphs[i] 본문 텍스트만 보는 단순 정규식 매칭. heading/표 행 분리로 paragraphs 길이 변동해도 결과 동일 (개별 paragraph 단위 카운트).
- 단, 표 행이 별도 paragraph 가 되면서 기존에 본문에 섞여 있던 표 셀 "shall/should" 패턴 매칭 빈도 변동 가능 → Phase 5 Case I 가 정량 검증.

**`_extract_terms` 가드 추가** (v3.1 — `_check_caption` 동형 결함 해결):
```python
def _extract_terms(
    paragraphs: list[str],
    block_types: list[str] | None = None,  # 신규
) -> dict:
    # v3.1 — _check_caption 동형 결함:
    # full_text 합치기 시 표 행 제외 (표 셀 안 단위가 본문 통계 오염)
    if block_types:
        full_text = "\n".join(
            p for i, p in enumerate(paragraphs) if block_types[i] != 'table_row'
        )
    else:
        full_text = "\n".join(paragraphs)  # 폴백 (legacy)
    
    # 규격 번호, 약어, 단위 매칭 (기존 로직)
    # _UNIT_PATTERN.finditer(full_text) 가 표 셀 단위 미포함 → 인텔리전스 패널 정확화
```
- `validate_paragraphs` 가 `_extract_terms` 호출 시 `block_types` 전달
- 영향: 인텔리전스 패널의 *units* 카운트가 표 셀 안 "5kg", "100mm" 등을 제외 → 본문 단위 통계만 표시. 사용자가 "본문에 사용된 단위" 를 정확히 파악 가능.

**AI 분류 표 행 제외** (Warning W1 해결):
```python
async def classify_changes(changes: list[dict], block_types_a=None, block_types_b=None) -> list[dict]:
    # 표 행 변경은 분류 제외 (LLM 비용 + 의미 분류 무의미)
    auto_unknown = []
    llm_changes = []
    for c in changes:
        bt_a = block_types_a[c.get('indexA', -1)] if block_types_a and c.get('indexA') is not None else None
        bt_b = block_types_b[c.get('indexB', -1)] if block_types_b and c.get('indexB') is not None else None
        if bt_a == 'table_row' or bt_b == 'table_row':
            auto_unknown.append({
                "index": c["index"],
                "tag": "EDITORIAL",  # 표 셀 변경은 보통 데이터 갱신
                "confidence": 0.5,
                "explanation": "표 셀 데이터 변경 (자동 분류)",
            })
        else:
            llm_changes.append(c)
    
    llm_results = await _llm_classify(llm_changes) if llm_changes else []
    # 인덱스 순 병합 후 반환
```

**`rule_engine._split_sentences` 영향 검증** (제 추가 발견):
- `rule_engine.py:61~80` 의 자체 sentence split 이 표 행 paragraphs 에 적용되면 셀 안 마침표가 sentence 경계로 잘못 해석 가능
- Phase 4 에서 `_split_sentences` 호출 전 `block_types[i] == 'table_row'` 면 분리 스킵 가드 추가
- Plan-55 의 `_sentence_split` 표 가드와 동일 패턴

**프론트 `renderValidationHighlights` 표 행 분기** (Critical C1 해결):
```js
function renderValidationHighlights(issues) {
    if (!issues || issues.length === 0) return;
    var content = panelBodyA.querySelector('.sim-md-view') || panelBodyA.querySelector('.cp-text-content');
    var paragraphEls = content.querySelectorAll('[data-paragraph-idx]');
    var blockTypes = docState.a.blockTypes || [];
    
    // 단락별 이슈 그룹화 (기존 로직)
    
    for (var pi in byParagraph) {
        var pIdx = parseInt(pi, 10);
        var el = paragraphEls[pIdx];
        var bt = blockTypes[pIdx];
        
        if (bt === 'table_row') {
            // Plan-57: 표 행은 행 전체에 클래스만 부착
            var topIssue = byParagraph[pi][0].issue;
            el.classList.add('validate-mark', 'severity-' + topIssue.severity);
            el.title = byParagraph[pi].map(function(x) { return x.issue.message; }).join('\n');
            el.setAttribute('data-issue-index', byParagraph[pi][0].globalIndex);
        } else {
            // 기존 char_offset span 삽입 로직
        }
    }
}
```

**완료 기준**: 표/헤딩 포함 DOCX 검증 → 표 셀 textIssue 가 행 단위로 정확히 표시 (Playwright). `_analyze_structure` 가 heading 정확히 인식 (단위 테스트). AI 분류 호출 수가 표 행 수만큼 감소 (로그 검증).

---

### Phase 5 — 비교/검증 단위 테스트 신규 + Playwright + 정량 회귀

**목표**: 비교/검증 모드 자체 단위 테스트 신규 작성 (현재 0건) + 시각·기능·API 3 계층 검증 + 점수 변동 정량 기준.

**비교/검증 단위 테스트 신규 작성** (제 추가 발견):
- `tests/verify/compare_diff_unit_test.py` 신규 (5 케이스):
  | Case | 검증 |
  |------|------|
  | A | 표 행 변경이 diff 결과에 1행 = 1 modified 로 잡힘 |
  | B | heading 변경이 diff 결과에 별도 modified 로 잡힘 |
  | C | 표 추가 (added) 가 N개 added change 로 잡힘 (N = 행 수) |
  | D | wordDiffs 가 paragraph 블록만 인라인 span, table_row 는 행 단위 |
  | E | Excel export 의 표 행 가독성 형식 |

- `tests/verify/verify_validation_unit_test.py` 신규 (6 케이스):
  | Case | 검증 |
  |------|------|
  | F | `_analyze_structure` 가 heading_levels 메타로 정확히 heading 카운트 (3 형식: "1.2 SCOPE"/"1.2. SCOPE"/"Abstract") |
  | G | `_check_caption` 가 표 행 paragraph 에서 거짓 매칭 안 함 + full_text 가드 (본문 참조 카운트 정확) |
  | H | `_check_forbidden_terms` 가 표 셀 안 금지용어 검출 + issue context 가 탭 변환 ` \| ` 형태 |
  | I | `validate_paragraphs` 점수가 paragraphs 길이 변동에도 ±5% 이내 (초과 시 원인 카테고리 보고) |
  | J | `rule_engine._split_sentences` 가 표 행에서 분리 안 함 |
  | **K** ★ (v3.1) | `_extract_terms` 의 *units* 통계가 표 셀 단위 ("5kg" 등) 미포함 — 본문 단위만 카운트 |

**Playwright 시나리오 (3건)**:
1. **시각 통일**: 표/헤딩/페이지 마커 포함 DOCX 1건 → 3 모드 차례로 업로드 → 좌우 패널 시각 동일
2. **비교 모드 표 diff**: 표가 다른 DOCX 2건 → 비교 모드 → 표 행 변경 시각화 + Excel export 가독성 확인
3. **검증 모드 표 issue**: 표 셀에 금지용어 + heading 포함 DOCX → 검증 모드 → 표 행 단위 highlight + heading 별도 표시 + 인텔리전스 패널 헤딩/표/그림 정확 카운트

**자동 회귀 (49건 목표)**:
- 신규 `sim_extract_unification_test.py` 7건
- 신규 `compare_diff_unit_test.py` 5건
- 신규 `verify_validation_unit_test.py` 6건 (v3.1 — Case K 추가)
- 기존 `sim_table_structural_test.py` 19건 PASS
- 기존 `sim_block_order_test.py` 5건 PASS
- 기존 `sim_score_v3_unit_test.py` 5건 PASS
- 기존 `sim_merge_adjacent_unit_test.py` 8건 PASS
- 기존 `sim_label_consistency.sh` PASS

**점수 변동 정량 기준** (Warning W3 해결):
- 검증 모드: 동일 DOCX 의 통합 전/후 score 차이 ≤ 5% (Phase 0 의 baseline 과 비교)
- 유사도 모드: 동일 DOCX 페어의 통합 전/후 similarity_score 차이 ≤ 1% (사실상 0% 기대 — 유사도 모드 코드 무수정)
- 단위 테스트 I 가 자동 검증

**API E2E**:
- 표 + 헤딩 + 본문 + 페이지 마커 mock DOCX → `/api/compare/upload` 응답에 신규 5개 필드 정상
- 동일 DOCX → `/api/compare/extract-document` → upload 와 동일 결과 (양 endpoint 일관성)
- paste 텍스트 → `/api/compare/extract-document` → block_types 정확

**완료 기준**: Playwright 3 시나리오 + 자동 회귀 48/48 PASS + 점수 변동 ±5% 이내.

---

### Phase 6 — 사용자 안내 + history 호환 + 문서화

**목표**: 행동 변화 안내 + history `schema_version` 도입 + 가이드 갱신.

**행동 변화 안내**:
- 첫 비교 또는 검증 모드 진입 후 (localStorage `plan57-behavior-change-seen`) 1회 토스트:
  > "Plan-57로 표·헤딩이 더 풍부하게 인식됩니다. 이전 결과와 수치가 다를 수 있어요."

**history `schema_version` 도입** (Warning W5 해결):
- `data/verify/{user}/_history.json` 의 각 entry 에 `schema_version: 2` 추가 (Plan-57 후 저장분)
- 기존 entry (`schema_version` 없음 또는 1) 는 옛 인덱스 의미로 해석
- `data/verify` 의 backlog *"결과 재열람"* (`workbench/plans/backlog.md`) 진행 시 schema_version 활용

**문서 갱신**:
- `docs/11-VERIFY-SYSTEM.md` — 통합 추출 파이프라인 + Block AST 명시
- `contents/guide/verify-guide.html` — 모드별 시각 일관성 1문단
- `MEMORY.md` 의 *"3 모드가 같은 화면에서 다르게 보임"* 부채 제거

**보고서 + done- 처리**:
- `workbench/reports/plan-57-feedback.md` — Critical 3건 + Warning 5건 모두 해결 확인
- `workbench/plans/57-...md` → `done-57-...md` 리네임

**완료 기준**: 첫 모드 진입 시 토스트 노출 (Playwright), history 신규 entry 에 `schema_version: 2`, 가이드/문서 갱신 commit, 계획서 done- 처리.

---

## 5. 위험 분석 (v2 — Critical 3건 해결 반영)

### 5.1 기술 위험

| 위험 | 수준 | v2/v3 완화 |
|------|------|---------|
| ~~`paragraphs[i]` ↔ `display_html` textContent 불일치 (v1 C1)~~ | **해결 v2** | §2.4 char_offset 정책 — 표 행은 행 단위, paragraph/heading 만 char span |
| ~~`_check_caption` 표 행 거짓 매칭 (v1 C2)~~ | **해결 v2** | `block_types` 1차 도입 + `_check_caption` 가드 |
| ~~`_analyze_structure` 헤딩 인식 실종 (v1 C3)~~ | **해결 v2** | heading prefix 제거 + `heading_levels` 메타 + `_analyze_structure` 동시 수정 |
| ~~탭 구분자가 issue context 로 사용자 노출 (v2 C1')~~ | **해결 v3** | §2.4 의 `_format_issue_context` 헬퍼 — 탭 → ` \| ` 변환 |
| ~~`_check_caption` full_text 합치기 시 표 셀 오염 (v2 C2')~~ | **해결 v3** | full_text 도 block_types 가드 |
| ~~`_HEADING_PATTERN` 과 paragraphs[i] 형식 불일치 (v2 C3')~~ | **해결 v3** | 정규식 `\.?` 완화 + Phase 5 Case F 양 형식 검증 |
| ~~CSS 우선순위 충돌~~ | **해결 v3** | `[data-paragraph-idx]` 완전 교체, `cp-paragraph` 공존 X 명문화 |
| ~~`validate_paragraphs` 호출자가 메타 미전달~~ | **해결 v3** | API + frontend 호출부 동시 수정 명시 |
| ~~`mergePdfLineBreaks` 처리 위치~~ | **해결 v3** | frontend 유지, paste 시 backend 호출 전 적용 명시 |
| 표 1행 = 1 paragraph 분할 시 페이지 경계가 표를 가르면 page_map 어긋남 | **중간** | Plan-52 의 *"페이지 경계 표 분리"* 패턴 재사용 (`_render_table_block`) |
| `rule_engine._split_sentences` 가 표 행 안 마침표 분리 | **낮음** | Phase 4 가드 (Plan-55 패턴 재사용) |
| `markdown_to_blocks` 가 markdown 미세 normalize → `plain_text` 변동 | **낮음** | read-only parsing 명문화 + Phase 0 단위 테스트로 markdown 무변경 검증 |
| 공유 정규식 의도치 않게 수정 | **낮음** | 코드 리뷰 + Plan-56 단위 테스트로 검출 |
| Excel export 표 행 가독성 손실 | **해결** | Phase 3 의 `paragraphForExport` 헬퍼 |
| AI 분류 토큰 폭증 | **해결** | Phase 4 의 표 행 자동 EDITORIAL (정확도 trade-off §7.3 명시) |
| 표 셀 수치 변경 의미 분류 정확도 손실 | **trade-off 인정** | §7.3 (6) 결정, backlog 이관 |

### 5.2 행동 변화 (긍정적이나 사용자 안내)

| 변화 | 영향 | 안내 |
|------|------|------|
| 검증 모드 점수 변동 ±5% 이내 (표 셀 issue 신규) | 정량 보장 | Phase 6 토스트 |
| 비교 모드 변경 카운트 증가 (표 행 변경 신규) | 카운트 증가 | 동일 |
| `paragraphs[]` 길이 증가 (표 N행 + heading 분리) | 사이드바 인덱스 변동 | 동일 |
| 스캔 PDF 처음 지원 (OCR 폴백) | 신규 동작 | 가이드 |
| 인텔리전스 패널 헤딩/표/그림 카운트 정확화 | 정확 향상 | 가이드 |

### 5.3 격리 보장 (유사도 모드 무영향 재확인)
- 매칭 알고리즘 (`similarity_engine` 본체) 무수정
- 검증 규칙 엔진 (`rule_engine`) 본체 무수정 — Phase 4 는 시그니처 확장만 (선택적 매개변수)
- API 시그니처 무수정 (호환 필드 추가)
- explorer/translator 시스템 무영향
- 인증/권한 무영향
- 유사도 모드 핵심 함수 4종 (`_build_tagged_html`, `split_sentences`, `_sentence_split`, `simApplyHighlights`) 변경 0줄

### 5.4 롤백 시나리오
- 단일 PR 권장 → git revert 1회로 즉시 복원
- 부분 롤백: `extract_document` 신규 필드 nullable, frontend 가 displayHtml 미수신 시 자동 fallback
- 운영 hotfix: `compare_service.extract_text` shim 을 원본 구현으로 1줄 교체

---

## 6. 산출물 목록

| 파일 | 변경 유형 | 설명 |
|------|---------|------|
| `backend/services/document_extractor.py` | 변경 | `markdown_to_blocks`, `build_block_tagged_html` 신규 + `extract_document` 5개 필드 확장 |
| `backend/services/compare_service.py` | 변경 | `extract_text` shim, `validate_paragraphs`/`_check_caption`/`_analyze_structure`/`classify_changes` block_types 매개변수 |
| `backend/services/rule_engine.py` | 변경 | `_split_sentences` 표 행 가드, `run_rules` block_types 전파 |
| `backend/api/compare.py` | 변경 | `/upload` 응답에 신규 5개 필드 추가 (호환) |
| `compare.html` | 변경 | `renderParagraphs`, `onDocumentLoaded`, `docState`, `renderDiffHighlights`, `renderValidationHighlights`, paste 통합, Excel export, 토스트 |
| `css/compare.css` | 변경 | `.sim-md-view` 스타일을 비교/검증 모드에서도 활성화 |
| `tests/sim_extract_unification_test.py` | 신규 | 7 케이스 (Phase 0) |
| `tests/verify/compare_diff_unit_test.py` | 신규 | 5 케이스 (Phase 5) |
| `tests/verify/verify_validation_unit_test.py` | 신규 | 5 케이스 (Phase 5) |
| `workbench/screenshots/plan57-{before,after}-*.png` | 신규 | 시각 증거 |
| `workbench/reports/plan-57-feedback.md` | 신규 | 검증 보고서 (Critical 3건 + Warning 5건 해결 확인) |
| `workbench/plans/done-57-...md` | 신규 (rename) | 본 계획서 완료 처리 |
| `docs/11-VERIFY-SYSTEM.md` | 변경 | 통합 파이프라인 + Block AST 명시 |
| `contents/guide/verify-guide.html` | 변경 | 시각 일관성 1문단 |

---

## 7. 코드/UX 전문가 입장 추가 점검 (v2)

### 7.1 코드 전문가 관점
- **SSOT + Block AST**: 한 markdown 소스 → Block 배열 → 두 derivation. Pandoc/MDX/MDAST 와 동일 패턴.
- **Backwards compatibility**: API 응답 필드 추가만, 기존 필드 보존 → 외부 호출자 무영향.
- **Test pyramid 강화**: 단위 (17건 신규 + 38건 기존) + API E2E + Playwright (3 시나리오) — 비교/검증 모드 단위 테스트 0건 → 10건 신규.
- **회귀 안전망 정량화**: 점수 변동 ±5% 이내 자동 검증 (단위 테스트 I).
- **Rollback 단순**: thin shim 1회 revert.
- **Dead code 제거 시점**: `_extract_docx`/`_extract_pdf` 제거는 다음 PR (호환 보장만).

### 7.2 UX 전문가 관점
- **현재 UX 모순 해소**: 같은 문서가 모드마다 다르게 보이는 인지 부하 제거 — 입력 방식 (upload/paste) 도 동일 시각.
- **Progressive enhancement**: displayHtml 미수신 시 fallback 자동 작동.
- **행동 변화 투명성**: 토스트 1회로 점수/카운트 변동 명시.
- **시각 일관성**: 3 모드 + 2 입력 방식 모두 같은 sim-md-view 스타일.
- **접근성 향상**: heading 이 의미 있는 `<h1~h6>` → 스크린리더 위계 인식.
- **인텔리전스 정확화**: heading/표/그림 카운트 정확 → 사용자 신뢰 향상.
- **데이터 호환**: history `schema_version` → 옛 데이터 의미 보존.

### 7.3 결정 사항 (v3)
1. **표 셀 단위 diff 미채택** — Plan-52 ROI 판단 그대로 (행 단위)
2. **paste 경로 1차 통합** (v1 의 후속 plan → 1차 포함)
3. **`block_types` 메타데이터 1차 도입** (v1 의 휴리스틱 폴백 → 정확한 메타)
4. **`compare_service` deprecated 제거 시점** — 다음 PR (호출 0 확인 후)
5. **사용 모니터링** — Phase 6 후 2주간 history 추이 → dormant 모드 부활 여부
6. **AI 분류 표 행 자동 EDITORIAL** (v3 — trade-off 명시)
   - 1차: 표 행 변경은 LLM 호출 없이 `tag="EDITORIAL"`, `confidence=0.5`, `explanation="표 셀 데이터 변경 (자동 분류)"` 자동 부여
   - 정확도 손실 인지: 표 셀 안 수치 변경 (예: "최대값 100→200") 이 STRICTER/MORE_LENIENT 인 경우 EDITORIAL 로 잘못 라벨됨
   - 비용/정확도 trade-off: 표 1개당 LLM 호출 N회 → 0회로 비용 절감 우선
   - **backlog 이관 (필수)**: `workbench/plans/backlog.md` 에 *"Verify — 표 셀 수치 변경 의미 분류 정확도 개선"* 항목 신설 (Phase 6 작성)
     - 옵션 1: 표 행도 LLM 호출하되 batch 압축 (행들 묶어 1회 호출)
     - 옵션 2: 셀 단위 수치 패턴 (`\d+→\d+`) 휴리스틱 사전 분류 후 분기
     - 옵션 3: 표 행 전용 신규 태그 `TABLE_DATA` 도입
7. **table_id frontend 활용** (v3 — backlog) — 1차 미사용, *"표 단위 diff 합집합 UX"* 항목 backlog 신설
8. **점수 변동 ±5% 임계 초과 시 판단 기준** (v3 — 명시)
   - Phase 5 의 ±5% 정량 검사 실패 시 자동으로 회귀가 아닌 *행동 변화*: 단위 테스트 I 가 *원인 카테고리* 보고 (예: "표 셀에서 sentence_length 9건 신규 발견")
   - 행동 변화 정당화 가능 (표 셀 issue 합리적 검출) → Phase 6 토스트 강화로 안내
   - 행동 변화 부당 (예: heading 인식 실패로 점수 하락) → Phase 1/4 재작업 필요

---

## 8. 외부 의존성 / 영향 받는 시스템 재확인

| 시스템 | 영향 | 비고 |
|--------|------|------|
| Explorer | 없음 | `tools/converter/converter.py` 자체 무수정 |
| Translator | 없음 | `md_extractor.py` 무수정 |
| 유사도 모드 (Verify 내) | 없음 | 핵심 함수 4종 무수정, API endpoint 무수정 |
| 비교 모드 (Verify 내) | 변경 | 데이터 모델 + 렌더링 통일 |
| 검증 모드 (Verify 내) | 변경 | 데이터 모델 + 렌더링 + 인텔리전스 정확화 |
| Dashboard / Analytics | 없음 | event payload 무변경 |
| Auth / RBAC | 없음 | 무관 |
| 공통 컴포넌트 (`components.css`, `tokens.css` 등) | 없음 | `.sim-md-view` 만 적용 범위 확장 |

---

## 9. 한 줄 결론 (v3.1)

**Plan-57 v3.1 = "Verify 시스템의 분리된 두 추출/렌더링 파이프라인을 Block AST + SSOT 로 통합한다."** v1 대비 Critical 7건 (v1 3건 + v2 3건 + v3.1 1건) + Warning 5건 + 추가 정합성 4건 (CSS 우선순위, 호출자 보장, mergePdfLineBreaks 처리, table_id 정책) 모두 해결. `block_types` 메타 1차 도입으로 산업 표준 (Pandoc/MDAST) 정합. 비교/검증 단위 테스트 11건 신규 (Case K 포함) + 회귀 안전망 정량화 (±5% 임계). AI 분류 정확도 trade-off 명시 + backlog 이관. 약 10.5일. **3차 design-review 통과, 출시 가능 수준.**
