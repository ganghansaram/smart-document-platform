# Plan 20: Document Intelligence — 마인드맵 + 실용 기능

> 작성일: 2026-03-29
> 수정일: 2026-03-30
> 상태: Phase 1 완료 / Phase 2 착수 대기
> 브랜치: `plan20-document-intelligence`
> 선행: Plan-19 Phase 1~6 완료 (Notebook 플랫폼 핵심 기능 완성)

---

## 1. 배경

### 1.1 방향 전환 경위

Plan-19 Phase 7은 "마인드맵 패널"로 설계되었으나, 여러 차례 검토를 거쳐 방향을 재정의:

1. **독립 패널 → AI 분석 탭 통합**: NotebookLM의 "Studio" 패턴 참고 — 같은 소스를 여러 형식(요약/Q&A/마인드맵)으로 제공
2. **D3.js force-directed → Markmap**: D3.js 직접 구현은 UX 품질 확보에 과도한 공수 소요. 마인드맵 전용 라이브러리(Markmap)가 NotebookLM과 동일한 계층적 트리를 기본 제공
3. **개념 그래프 → 문서 구조 마인드맵**: 네트워크 그래프보다 "중심에서 가지가 뻗어나가는 트리"가 문서 이해에 직관적 (NotebookLM 검증)

### 1.2 설계 원칙

- **NotebookLM 마인드맵을 타깃** — Google이 다수 인원으로 분석·검토한 결과물
- **전용 라이브러리 사용** — 바퀴 재발명 금지, 검증된 도구 활용
- **각 시스템 독립 동작** — Explorer↔Notebook 공유 계층 없음
- **기존 데이터 직접 활용** — `full_translated.md`가 곧 마인드맵 데이터

### 1.3 Phase 2 D3.js 시도 및 롤백 (2026-03-30)

D3.js force-directed로 Phase 2를 구현했으나 다음 문제 확인 후 롤백:
- 라벨 겹침, 그래프 치우침, 라이트 모드 가독성 등 UX 품질 미달
- NotebookLM의 "점진적 가지 펼침" 형태와 근본적으로 다른 패턴
- force-directed는 탐색적 네트워크 분석에 적합, 문서 구조 시각화에는 부적합
- 전용 마인드맵 라이브러리가 더 적은 코드로 더 높은 품질 제공

**결정**: Phase 1(d7e0fcd) 커밋으로 리셋 후, Markmap 라이브러리로 Phase 2 재구현.

---

## 2. 기술 선정: Markmap

### 2.1 라이브러리 비교 (조사 완료)

| 라이브러리 | 용량 | UMD | Vanilla JS | 접기/펼치기 | 다크모드 | 라이선스 | 판정 |
|-----------|:----:|:---:|:----------:|:----------:|:-------:|:-------:|:----:|
| React Flow | ~140KB+ | X | X | 직접구현 | O | MIT | **탈락** (React 필수) |
| D3.js | ~250KB | O | O | 직접구현 | CSS제어 | ISC | **탈락** (공수 과다, UX 미달) |
| GoJS | ~190KB | O | O | 내장 | O | **상용** | **탈락** (유료) |
| Mermaid | ~150KB | O | O | **X** | 내장 | MIT | **탈락** (인터랙션 없음) |
| jsMind | ~30KB | O | O | 내장 | CSS커스텀 | BSD | 2순위 (JSON 기반) |
| **Markmap** | **~60KB** | **O** | **O** | **내장** | CSS커스텀 | **MIT** | **1순위** |

### 2.2 Markmap 선정 이유

1. **Markdown → 마인드맵 자동 변환** — `full_translated.md`를 그대로 넣으면 헤딩 구조가 마인드맵이 됨
2. **접기/펼치기 내장** — NotebookLM처럼 "점진적으로 가지를 펼쳐가는" UX 기본 제공
3. **IIFE 빌드 존재** — `<script>` 태그로 로드, 번들러 불필요 (폐쇄망 호환)
4. **~60KB** — D3.js(250KB)보다 가벼움 (d3 서브셋 자체 번들)
5. **SVG 기반** — CSS 토큰으로 다크모드 대응 가능

### 2.3 Markmap 사용 방식

```html
<script src="js/lib/markmap/d3.min.js"></script>        <!-- d3 서브셋 -->
<script src="js/lib/markmap/markmap-view.min.js"></script>
<script src="js/lib/markmap/markmap-lib.min.js"></script>
```

```js
const { Transformer } = markmap;
const { Markmap } = markmap;
const transformer = new Transformer();

// full_translated.md의 헤딩 구조를 추출하여 Markdown 생성
const mdForMap = extractHeadingsAsMarkdown(fullMd);

const { root } = transformer.transform(mdForMap);
Markmap.create('#mindmap-svg', {
    color: () => 'var(--active-color)',
    paddingX: 16,
    // ... 옵션
}, root);
```

### 2.4 데이터 흐름

```
full_translated.md (또는 full_extracted.md)
    ↓
헤딩 구조 추출 (## → ###  → #### 계층)
+ AI 키워드 삽입 (ai_summary.json → keywords)
    ↓
Markdown 문자열 조립 (마인드맵용)
    ↓
Markmap.transform() → tree 데이터
    ↓
Markmap.create() → SVG 렌더링
    ↓
노드 클릭 → goToPage() + scrollIntoView()
```

**핵심**: 백엔드 API가 헤딩+키워드를 Markdown 형태로 반환하거나,
프론트에서 기존 `full_translated.md` API 응답을 직접 파싱하여 변환.

---

## 3. 현재 상태 (2026-03-30)

### 3.1 완료 항목

| Phase | 내용 | 커밋 | 상태 |
|:-----:|------|------|:----:|
| 1a | frontmatter keywords 자동 기록 | d7e0fcd | ✅ |
| 1b | 카드 목록 메모 수 배지 | d7e0fcd | ✅ |

### 3.2 현재 파일 상태

- `translator.html`: AI 탭 [요약][Q&A] 2개, 마인드맵 disabled 버튼 존재
- `translator.js`: Phase 2 코드 없음 (깨끗한 상태)
- `translator.css`: Phase 2 CSS 없음
- `js/lib/`: D3.js 없음, Markmap 아직 없음
- 백엔드: concept-map API 없음

---

## 4. 단계별 실행 계획

### Phase 1: 선행 정리 — ✅ 완료

- ✅ 1a: frontmatter keywords 자동 기록
- ✅ 1b: 카드 목록 메모 수 배지

### Phase 2: AI 분석 패널 — 마인드맵 탭 (~2~3일)

> NotebookLM 마인드맵을 타깃. Markmap 라이브러리 사용.
> 기존 [요약][Q&A] 탭 옆에 [마인드맵] 탭 추가.
> 아이콘 레일의 마인드맵 disabled 버튼 삭제.

#### Step 1: Markmap 번들 확보

- Markmap IIFE 파일 다운로드 → `js/lib/markmap/` 배치
  - `markmap-lib.min.js` (~12KB)
  - `markmap-view.min.js` (~15KB)
  - `d3.min.js` (Markmap 전용 d3 서브셋, ~30KB)
- `translator.html`에 `<script>` 로드 추가

#### Step 2: 백엔드 — 마인드맵 데이터 API

- `GET /api/translator/document/{doc_id}/mindmap` — 신규
- `full_translated.md` (또는 `full_extracted.md`)에서:
  1. 헤딩 구조 추출 (`##`, `###`, `####` → 계층적 Markdown)
  2. `ai_summary.json`의 keywords를 최하위 가지로 삽입
  3. 용어 태그(`[용어: A=B]`) 중 빈도 높은 것을 가지로 추가 (선택)
- 응답: `{ "markdown": "# 문서제목\n## 서론\n### 배경\n- 키워드1\n- 키워드2\n## 관련연구\n..." }`
- 불필요한 본문 텍스트는 제외, 헤딩+키워드만 포함

#### Step 3: 프론트엔드 — 탭 구조 + Markmap 렌더링

**HTML 변경:**
- 탭 바: `<button class="ai-tab-btn" data-tab="mindmap">마인드맵</button>` 추가
- 콘텐츠: 빈 상태 UI + SVG 컨테이너
  ```html
  <div class="ai-tab-content" id="ai-tab-mindmap" style="display:none">
      <div id="mm-empty">요약을 먼저 생성하세요</div>
      <div id="mm-container" style="display:none">
          <svg id="mm-svg"></svg>
      </div>
  </div>
  ```
- 마인드맵 disabled 레일 버튼 삭제

**JS 변경:**
- 탭 전환 로직 확장 (`_initAiTabs`에 `mindmap` 케이스 추가)
- `_loadMindmap()` — API fetch → Markmap 렌더링
- `_renderMindmap(markdown)` — Markmap.transform + create
- 캐시: `_mmCache = { docId, instance }` (문서 전환 시 초기화)
- 노드 클릭 → 해당 섹션 헤딩으로 스크롤 (Markmap 이벤트 활용)

**CSS 변경:**
- `#ai-tab-mindmap` flex 레이아웃 (전체 높이 활용)
- `#mm-svg` 100% 너비/높이
- Markmap 기본 스타일 위에 다크모드 오버라이드:
  - 라이트: 노드 텍스트 `var(--text-dark)`, 배경 `var(--white)`
  - 다크: 노드 텍스트 `var(--text-dark)` (다크에서 밝은 색), 라인 색상 조정
- 가지 색상: `var(--active-color)` 기반 또는 Markmap 기본 컬러 팔레트

#### Step 4: UX 품질 검증

- 라이트/다크 모드 양쪽 스크린샷 비교
- 접기/펼치기 동작 확인
- 노드 클릭 → 섹션 스크롤 확인
- 확장 모드(전체 화면)에서의 레이아웃
- 패널 크기 변경(리사이즈) 시 SVG 재조정
- 요약 없는 문서에서의 빈 상태 UI

### Phase 3: 규격 번호 자동 링크 (~1일)

> 양쪽 시스템(Explorer + Notebook)에서 독립적으로 동작.

- 정규식 패턴: `MIL-STD-\d+[A-Z]?`, `MIL-DTL-\d+`, `AS\d{4,}`, `EN\s?\d{4,}`, `KS\s?[A-Z]\s?\d+` 등
- **Notebook**: 웹뷰 렌더링 후 DOM 후처리 — 매칭 텍스트를 `<a class="spec-link">` 래핑
  - 클릭 시: Explorer 검색 URL로 이동 (`index.html?search=MIL-STD-810`)
- **Explorer**: 본문 렌더링 후 동일 후처리
- 정규식 패턴을 `js/config.js`에 공통 정의 (독립 실행, 공유 데이터 없음)
- precision 우선 (오탐 최소화)

### Phase 4: Notebook 내 관련 문서 추천 (~1~2일)

> Notebook 개인 문서끼리만. Explorer와 무관.

- 문서 열람 시 → 현재 문서의 키워드와 다른 문서의 키워드 비교 (자카드 유사도)
- 뷰어 사이드 또는 카드 목록에 "비슷한 내 문서" 위젯 (최대 3개)
- 백엔드: `GET /api/translator/document/{doc_id}/related` — 키워드 유사도 상위 N개
- 클릭 시 해당 문서 뷰어로 전환

---

## 5. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 상태 |
|:-----:|------|:--------:|:----:|
| 1a | frontmatter keywords 자동 기록 | ~2시간 | ✅ |
| 1b | 카드 목록 메모 수 배지 | ~2시간 | ✅ |
| 2 | **AI 패널 마인드맵 탭** (Markmap) | ~2~3일 | ⬜ |
| 3 | **규격 번호 자동 링크** (Notebook + Explorer 독립) | ~1일 | ⬜ |
| 4 | **Notebook 내 관련 문서 추천** | ~1~2일 | ⬜ |

**전체 합계**: ~5~6일 (Phase 1 완료 제외)

---

## 6. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Markmap IIFE 빌드 확보 | CDN 불가 | 인터넷 환경에서 사전 다운로드, `js/lib/markmap/` 배치 |
| Markmap 다크모드 미지원 | 라이트 전용 스타일 | SVG CSS 오버라이드로 다크 대응 (stroke, fill, text 색상) |
| 헤딩 구조가 빈약한 문서 | 마인드맵이 1~2 노드만 표시 | AI 키워드를 하위 가지로 보충 |
| Markmap 커스터마이징 한계 | 노드 클릭 이벤트 제한 | SVG 이벤트 위임으로 직접 바인딩 |
| 규격 번호 오탐 | 일반 숫자가 링크로 변환 | precision 우선 정규식, 최소 패턴만 적용 |

---

## 7. 성공 지표

| Phase | 지표 |
|:-----:|------|
| 1 | frontmatter에 키워드 자동 기록, 카드에 메모 수 표시 |
| 2 | NotebookLM처럼 가지 접기/펼치기 동작, 라이트/다크 양쪽 가독, 노드 클릭→섹션 이동 |
| 3 | 번역문 내 MIL-STD 등 규격 번호가 클릭 가능한 링크로 표시 |
| 4 | 뷰어에서 "비슷한 내 문서" 최대 3개 추천 |

---

## 8. 참고

### NotebookLM 마인드맵 특징 (2025년 3월~)

- **레이아웃**: 중앙 주제에서 방사형으로 가지 확장 (계층적 트리)
- **점진적 펼침**: 노드 클릭으로 하위 가지 접기/펼치기
- **가지별 색상**: 1차 가지마다 고유 색상
- **노드 클릭**: 해당 개념의 소스 원문 참조
- **깔끔한 스타일**: 둥근 사각형 노드, 유기적 곡선 엣지

### Plan-19 이관 항목

| 원래 위치 | 항목 | 이관 위치 |
|----------|------|----------|
| Plan-19 Phase 7 | 마인드맵 패널 | Phase 2 — AI 탭 마인드맵 (Markmap) |
| Plan-19 섹션 2.2 | frontmatter keywords | Phase 1a ✅ |
| Plan-19 섹션 2.2 | 카드 메모 수 표시 | Phase 1b ✅ |
| Plan-19 섹션 4 | 관련 문서 추천 | Phase 4 |
| Plan-19 섹션 4 | 용어 기반 자동 연결 | Phase 3 (규격 링크) |

### D3.js 시도 기록 (롤백됨)

- 커밋 72c7c34~5f96147 (3건) — force-directed 구현 → UX 미달 → 리셋
- 교훈: 범용 시각화 라이브러리로 마인드맵을 만드는 것은 비효율. 전용 라이브러리 사용이 정답
- D3.js(250KB)는 프로젝트에서 제거됨

### 아카이브

- `done-19-notebook-platform-completion.md` — Phase 1~6 완료, Phase 7 본 계획으로 이관
