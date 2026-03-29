# Plan 20: Document Intelligence — AI 분석 패널 확장 + 실용 기능

> 작성일: 2026-03-29
> 상태: 설계 확정
> 브랜치: `plan20-document-intelligence`
> 선행: Plan-19 Phase 1~6 완료 (Notebook 플랫폼 핵심 기능 완성)
> 범위: AI 분석 패널 개념 맵 탭 추가 + 규격 번호 자동 링크 + 관련 문서 추천

---

## 1. 배경

### 1.1 방향 전환 경위

Plan-19 Phase 7은 "마인드맵 패널 (아이콘 레일 독립 버튼)"으로 설계되었으나,
검토 결과 다음 문제를 확인:

- 마인드맵 = 목차(TOC)의 시각적 변환에 불과 → 기존 기능과 중복
- 독립 패널로 만들면 내용이 적어 허전함
- NotebookLM 분석 결과, 성공적인 패턴은 "한 곳에서 여러 뷰 제공"

**결정**: 기존 AI 분석 패널(요약·Q&A)에 **개념 맵 탭을 추가**하고,
마인드맵 disabled 버튼은 **삭제**한다.

### 1.2 설계 원칙

- **각 시스템은 독립적으로 잘 동작** — Explorer↔Notebook 공유 계층 없음
- **과도한 설계 금지** — 작게 만들고 실사용을 관찰
- **기존 데이터 최대 활용** — 새 파이프라인 최소화
- **NotebookLM 참고**: 같은 소스를 다른 형식으로 소화하는 패턴 (요약→Q&A→개념맵)

---

## 2. 현재 AI 분석 패널 구조

```html
<!-- translator.html:242~345 -->
<div id="hdr-ai-summary">
    <span class="panel-title">AI 분석</span>
    <div class="ai-tab-bar">
        <button class="ai-tab-btn active" data-tab="summary">요약</button>
        <button class="ai-tab-btn" data-tab="qa">Q&A</button>
        <!-- ← 여기에 개념 맵 탭 추가 -->
    </div>
    ...
</div>
<div id="ai-summary-panel">
    <div id="ai-tab-summary">...</div>    <!-- 요약 탭 -->
    <div id="ai-tab-qa">...</div>          <!-- Q&A 탭 -->
    <!-- ← 여기에 개념 맵 탭 콘텐츠 추가 -->
</div>
```

기존 탭 전환 로직 (`translator.js:3797~3811`)이 `data-tab` 속성으로 동작하므로,
새 탭을 추가하면 **JS 수정 최소화**로 작동한다.

---

## 3. 보유 데이터 자산

| 자산 | 위치 | 개념 맵 활용 |
|------|------|-------------|
| **AI 키워드** | `ai_summary.json` → `keywords[]` | 키워드 노드 |
| **MD 헤딩** | `full_translated.md` `## Section` | 섹션 노드 |
| **용어 태그** | MD 본문 `[용어: A=B]` | 용어 노드 + 섹션↔용어 엣지 |
| **용어집** | `_glossary.json` | 용어 노드 보강 |
| **frontmatter** | 페이지별 `keywords[]` (Phase 1에서 기록) | 페이지별 키워드 |

---

## 4. 단계별 실행 계획

### Phase 1: 선행 정리 (~반나절)

> Plan-19 잔여 2건 + 개념 맵의 전제 조건.

**1a: frontmatter keywords 자동 기록**
- AI 요약 완료 시 추출된 키워드를 해당 페이지 frontmatter `keywords` 필드에 기록
- `ai_summary.py` 결과 → `translator_service.py`에서 MD frontmatter 업데이트
- 개념 맵 API가 이 데이터를 사용

**1b: 카드 목록 메모 수 배지**
- `GET /api/translator/documents` 응답에 `annotation_count` 추가
- 카드 UI에 메모 수 뱃지 표시 (기존 뱃지 패턴 재사용)

### Phase 2: AI 분석 패널 — 개념 맵 탭 (~3일)

> 기존 [요약][Q&A] 탭 옆에 [개념 맵] 탭 추가.
> 마인드맵 disabled 버튼 삭제.

#### Step 1: 백엔드 — concept-map API

- `GET /api/translator/document/{doc_id}/concept-map` — 신규
- 데이터 조립 (실시간, 캐시 불필요 — 문서당 노드 ~50개):
  1. `full_translated.md` 파싱 → `<!-- Page N -->` + `## Heading` 추출 → 섹션 노드
  2. `ai_summary.json` → `keywords[]` → 키워드 노드
  3. MD 본문 `[용어: A=B]` 또는 `[Glossary: A=B]` 정규식 → 용어 노드
  4. 각 키워드/용어가 어느 섹션에 출현하는지 → 엣지 생성
- 응답 포맷:
  ```json
  {
    "nodes": [
      { "id": "sec-1-1", "type": "section", "label": "I. 서론", "page": 1 },
      { "id": "kw-그래프", "type": "keyword", "label": "그래프" },
      { "id": "gl-분류", "type": "glossary", "label": "분류", "original": "classification" }
    ],
    "edges": [
      { "source": "sec-1-1", "target": "kw-그래프" },
      { "source": "sec-1-1", "target": "gl-분류" }
    ]
  }
  ```

#### Step 2: 프론트엔드 — D3.js 번들 + 탭 추가

- `js/lib/d3.min.js` 번들 (~250KB, UMD 빌드 사전 확보)
- `translator.html` 수정:
  - 탭 바에 `<button class="ai-tab-btn" data-tab="concept-map">개념 맵</button>` 추가
  - 콘텐츠에 `<div class="ai-tab-content" id="ai-tab-concept-map" style="display:none">` 추가
  - 마인드맵 disabled 버튼 (`data-panel="mindmap"`) 삭제
- `translator.js` 탭 전환 로직 확장 (`_initAiTabs`에 `concept-map` 케이스 추가)

#### Step 3: D3.js force-directed 렌더링

- SVG 기반 (CSS 토큰으로 다크모드 자동 대응)
- 노드 시각:
  - 섹션: `var(--active-color)` 원, 크기 = 연결 수
  - 키워드: `var(--color-warning)` 원, 크기 = 출현 빈도
  - 용어: `var(--color-success)` 원, 작은 고정 크기
- 엣지: 얇은 선, 투명도로 weight 표현
- 인터랙션:
  - 노드 호버 → 툴팁 (라벨 + 출현 페이지 + 연결 수)
  - 노드 클릭 → 웹뷰 해당 섹션 스크롤 (기존 goToPage + scrollIntoView 패턴)
  - 드래그로 노드 위치 조정
  - 줌/패닝 (D3 zoom behavior)
- 범례: 좌측 하단에 노드 유형별 색상 범례 (섹션/키워드/용어)

#### Step 4: 상태 관리

- AI 요약이 없으면 → "먼저 요약을 생성하세요" 안내 + 요약 탭 이동 버튼
- 요약은 있지만 키워드가 0개 → "키워드가 없습니다" 안내
- 정상 → D3 그래프 렌더링
- 문서/페이지 전환 시 → 그래프 초기화 후 재로드
- 확장 모드 → SVG viewBox 재계산 (더 넓은 공간 활용)

### Phase 3: 규격 번호 자동 링크 (~1일)

> 양쪽 시스템(Explorer + Notebook)에서 독립적으로 동작. 공유 계층 없음.

- 정규식: `MIL-STD-\d+[A-Z]?`, `MIL-DTL-\d+`, `AS\d{4,}`, `EN\s?\d{4,}`, `KS\s?[A-Z]\s?\d+` 등
- **Notebook**: 웹뷰 렌더링 후 DOM 후처리 — 매칭 텍스트를 `<a class="spec-link">` 로 래핑
  - 클릭 시: Explorer의 해당 규격 검색 URL로 이동 (`index.html?search=MIL-STD-810`)
- **Explorer**: 본문 렌더링 후 동일 후처리
  - 클릭 시: 검색 오버레이 열기
- 양쪽 독립 구현 — 같은 정규식만 공유 (`js/config.js`에 패턴 정의)

### Phase 4: Notebook 내 관련 문서 추천 (~1~2일)

> Notebook 개인 문서끼리만. Explorer와 무관.

- 문서 열람 시 → 현재 문서의 키워드와 다른 문서의 키워드 비교 (자카드 유사도)
- 카드 목록 또는 뷰어 사이드에 "비슷한 내 문서" 위젯 (최대 3개)
- 백엔드: `GET /api/translator/document/{doc_id}/related` — 유저 문서 내 키워드 유사도 상위 N개
- 클릭 시 해당 문서 뷰어로 전환

---

## 5. 기술 결정 사항

### D3.js 선정 이유

| 기준 | D3.js | vis.js | Cytoscape.js |
|------|:-----:|:------:|:------------:|
| 용량 | ~250KB | ~350KB | ~500KB |
| UMD 빌드 | O | O | O |
| SVG 기반 (CSS 토큰 호환) | **O** | Canvas | Canvas/SVG |
| 커스터마이징 자유도 | **최고** | 중 | 중 |
| 학습 곡선 | 높 | 낮 | 중 |

SVG 기반이라 `fill: var(--active-color)` 같은 CSS 변수를 직접 사용할 수 있어,
다크모드 전환 시 별도 로직 없이 자동 대응.

### 개념 맵 데이터 흐름

```
AI 요약 완료
    ↓
ai_summary.json (keywords)
full_translated.md (headings + 용어 태그)
    ↓
GET /concept-map API (실시간 조립)
    ↓
D3.js force-directed SVG
    ↓
노드 클릭 → goToPage() + scrollIntoView()
```

---

## 6. Plan-19 이관 항목

| 원래 위치 | 항목 | 이관 위치 |
|----------|------|----------|
| Plan-19 Phase 7 | 마인드맵 패널 (disabled 버튼) | Phase 2 — AI 탭 개념 맵으로 대체, 버튼 삭제 |
| Plan-19 섹션 2.2 | frontmatter keywords 자동 생성 | Phase 1a |
| Plan-19 섹션 2.2 | 카드 목록 메모 수 표시 | Phase 1b |
| Plan-19 섹션 4 | 관련 문서 자동 추천 | Phase 4 |
| Plan-19 섹션 4 | 용어 기반 자동 연결 | Phase 3 (규격 링크) |

나머지 Plan-19 섹션 4 항목(번역 속도 최적화, 수식 필터링, 알고리즘 스킵, 파일명 리네이밍, 클러스터 시각화, 개인 문서 벡터 검색, 문서 타임라인)은 **별도 백로그**로 관리.

---

## 7. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 상태 |
|:-----:|------|:--------:|:----:|
| 1a | frontmatter keywords 자동 기록 | ~2시간 | ⬜ |
| 1b | 카드 목록 메모 수 배지 | ~2시간 | ⬜ |
| 2 | **AI 패널 개념 맵 탭** (D3.js force-directed) | ~3일 | ⬜ |
| 3 | **규격 번호 자동 링크** (Notebook + Explorer 독립) | ~1일 | ⬜ |
| 4 | **Notebook 내 관련 문서 추천** | ~1~2일 | ⬜ |

**전체 합계**: ~6~7일
**Tier 1 (Phase 1~2)**: ~4일 — AI 분석 완성
**Tier 2 (Phase 3~4)**: ~2~3일 — 실용 기능

---

## 8. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| D3.js 폐쇄망 번들 확보 | CDN 불가 | UMD 빌드 사전 다운로드, `js/lib/d3.min.js` |
| AI 키워드 품질 (소형 모델) | 그래프 노드가 부정확 | 요약 재생성으로 키워드 갱신 가능 |
| 우측 패널 공간 부족 | 그래프가 좁아 가독성 저하 | 확장 모드에서 전체 화면 사용, 줌 지원 |
| 규격 번호 오탐 | 본문 중 숫자가 규격으로 잘못 링크됨 | 정규식 정밀도 우선 (recall보다 precision) |
| 관련 문서 추천 정확도 | 키워드 유사도만으로는 한계 | 문서 수 적을 때는 자카드로 충분, 추후 벡터 확장 |

---

## 9. 성공 지표

| Phase | 지표 |
|:-----:|------|
| 1 | frontmatter에 키워드가 자동 기록됨, 카드에 메모 수 표시 |
| 2 | AI 패널에서 요약→Q&A→개념 맵 탭 전환 자연스러움, 노드 클릭→섹션 이동 |
| 3 | 번역문 내 MIL-STD 등 규격 번호가 클릭 가능한 링크로 표시 |
| 4 | 뷰어에서 "비슷한 내 문서" 최대 3개 추천, 클릭 시 전환 |

---

## 10. 참고

### NotebookLM에서 참고한 패턴

- **"Studio" 패널**: 같은 소스를 여러 형식(요약, FAQ, 마인드맵)으로 제공 → 우리의 [요약][Q&A][개념 맵] 탭 구조
- **원클릭 생성**: 복잡한 설정 없이 버튼 하나로 결과물 생성 → 요약 생성 시 개념 맵도 함께 준비
- **출처 추적**: 노드 클릭 → 원문 해당 위치 → 기존 클릭 네비게이션 패턴 재활용

### 아카이브

- `workbench/plans/done-19-notebook-platform-completion.md` — Phase 1~6 완료, Phase 7 본 계획으로 이관
