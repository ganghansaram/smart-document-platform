# Plan 20: Document Intelligence — 문서 지능 시각화

> 작성일: 2026-03-29
> 상태: 설계 중
> 선행: Plan-19 Phase 1~6 완료 (Notebook 플랫폼 핵심 기능 완성)
> 범위: Plan-19 Phase 7(마인드맵) 방향 재정의 + 지식 시각화 + 향후 확장 기반 마련

---

## 1. 배경과 동기

### 1.1 원래 계획의 한계

Plan-19 Phase 7은 "마인드맵 패널"로 설계되었다. 그러나 본질적으로 **목차(TOC)의 시각적 변환**에 불과하며:
- Explorer의 "On this page" 패널과 기능이 중복
- 문서 간 연결이나 지식 발견에 기여하지 않음
- "지식 저장소" 비전에 미달

### 1.2 플랫폼 비전과의 정렬

Smart Document Platform은 "문서 속 지식을 탐색"하는 도구다. 현재까지 구축된 기능:

| 기능 | 제공 가치 |
|------|----------|
| RAG 검색 (FAISS + BM25) | 질문에 관련 문서 청크 검색 |
| AI 요약 + Q&A | 단일 문서 내 이해 지원 |
| 용어집 | 도메인 용어 한↔영 매핑 |
| 클릭 네비게이션 | 원문↔번역 블록 대응 |

**빠져 있는 것**: 문서의 **구조적 지식**을 시각화하고, 문서 **간** 연결을 발견하는 능력.

### 1.3 업계 동향 (2024~2025)

| 기술 | 핵심 가치 | 대표 사례 |
|------|----------|----------|
| **Knowledge Graph** | 엔터티·관계 구조화 → 지식 탐색 | Boeing DOORS+KG, Airbus 기술문서 KG |
| **Graph-RAG** (MS Research, 2024) | 그래프 기반 커뮤니티 요약 → 추상 질문 대응 | LlamaIndex GraphRAG, LangChain |
| **Concept Map** | LLM 자동 생성 개념 지도 | Notion AI, Obsidian Canvas |
| **Entity Linking** | 문서 간 공유 엔터티로 네트워크 구성 | Semantic Scholar, Google Knowledge Panel |

항공·방산 분야에서는 Knowledge Graph가 가장 활발하지만, 풀 KG 구축은 수주 규모의 프로젝트다.
본 계획은 **현실적으로 실행 가능한 단위**로 분할하여, 점진적으로 KG 기반을 마련한다.

---

## 2. 현재 보유 자산 (활용 가능한 데이터)

새 파이프라인 없이 **이미 존재하는 데이터**:

| 자산 | 위치 | 내용 |
|------|------|------|
| **문서별 AI 키워드** | `ai_summary.json` → `keywords` | 요약 시 자동 추출된 핵심 용어 (~5~10개) |
| **용어집** | `_glossary.json` | 사용자 등록 도메인 용어 (원문↔번역) |
| **MD 헤딩 구조** | `full_translated.md` | `## Section` 계층 → TOC 트리 |
| **번역문 용어 태그** | MD 본문 `[용어: A=B]` | 번역 시 자동 삽입된 용어 매칭 결과 |
| **page_boxes** | `web_page_boxes.json` | 블록별 class (section-header, text, table 등) |
| **Explorer 검색 인덱스** | `search-index.json` | 전체 웹북 문서의 텍스트 + 메타데이터 |
| **FAISS 벡터 인덱스** | `vector-index/` | bge-m3 임베딩, 문서 청크 벡터 |
| **frontmatter** | 각 페이지 MD 상단 | title, page, model, translated_at, summary(빈), keywords(빈) |

---

## 3. 단계별 실행 계획

### Phase 1: 선행 정리 (~반나절)

> Plan-19에서 미완으로 남은 경량 항목 2건 처리.

- **1a**: frontmatter keywords 자동 기록 — AI 요약 완료 시 추출된 키워드를 해당 페이지 frontmatter에 자동 기록 (백엔드 `ai_summary.py` → `translator_service.py` 연동)
- **1b**: 카드 목록 메모 수 배지 — annotation count API 확장 + 카드 UI에 뱃지 표시

### Phase 2: 단일 문서 개념 맵 (~3일) ← 원래 Phase 7 대체

> 마인드맵 대신 **force-directed graph**로 문서 내 개념 관계를 시각화.
> 아이콘 레일 6번(마인드맵) 버튼 활성화 → "개념 맵" 패널로 리네이밍.

**데이터 소스** (신규 추출 불필요):
- 노드: 헤딩(섹션) + AI 키워드 + 용어집 매칭 용어
- 엣지: 섹션↔키워드 연결 (키워드가 해당 섹션에 출현), 키워드 간 공출현(같은 섹션 공유)

**시각화**:
- D3.js force-directed layout (UMD 빌드, ~250KB, 폐쇄망 호환)
- 노드 크기 = 언급 빈도 / 연결 수
- 노드 색상 = 유형별 (섹션: primary, 키워드: accent, 용어: success)
- 노드 클릭 → 해당 섹션으로 웹뷰 스크롤
- 확장 모드 패널 (기존 패턴 재사용)
- 다크모드 자동 대응

**백엔드** (경량):
- `GET /api/translator/document/{doc_id}/concept-map` — 신규
- 데이터 조립: `ai_summary.json` 키워드 + `full_translated.md` 헤딩 파싱 + 용어 태그 추출
- JSON 응답: `{ nodes: [...], edges: [...] }`

**UX 목표**:
- "이 문서의 핵심 개념이 뭐야?" → 한눈에 파악
- "이 용어가 어느 섹션에서 다뤄져?" → 노드 클릭으로 탐색
- 기존 마인드맵보다 **정보 밀도가 높고 탐색적**

### Phase 3: 문서 간 연결 지도 (~3일)

> 여러 문서를 아우르는 지식 네트워크. Notebook 카드 목록 또는 Explorer에서 접근.

**데이터 소스**:
- 문서별 키워드 벡터 (Phase 2에서 추출된 키워드의 임베딩)
- 용어집 공유도 (같은 용어를 사용하는 문서 쌍)
- 규격 번호 참조 (MIL-STD-xxx, AS/EN-xxx 등 정규식 추출)

**시각화**:
- 각 문서 = 노드, 공유 키워드/용어/규격 = 엣지
- 클러스터 자동 감지 (Louvain 알고리즘 또는 간단한 연결 성분)
- 문서 노드 클릭 → 해당 문서 뷰어로 이동

**백엔드**:
- `GET /api/translator/knowledge-map` — 유저의 전체 문서 네트워크
- 문서 업로드/요약 완료 시 자동으로 연결 정보 갱신

### Phase 4: Graph-RAG 기반 강화 (~5일, 탐색적)

> 지식 그래프를 RAG 파이프라인에 통합하여 AI 답변 품질 향상.

**접근**:
- Phase 2~3에서 구축된 개념 맵 + 문서 연결을 **컨텍스트 소스**로 활용
- 질문 → 관련 키워드 노드 탐색 → 연결된 섹션/문서 청크 수집 → LLM에 주입
- 기존 벡터 검색 결과 + 그래프 탐색 결과를 **하이브리드 RRF**로 병합

**기대 효과**:
- "KF-21의 구조 시험에 적용된 규격과 절차를 정리해줘" → 여러 문서에서 관련 정보 수집
- 현재 단일 청크 기반 RAG로는 불가능한 **문서 횡단 질문** 대응

**리스크**:
- Ollama 소형 모델의 추론 품질 한계
- 그래프 탐색 비용 (문서 수 증가 시)
- 이 Phase는 **탐색적** — ROI 평가 후 범위 조정

---

## 4. 기술 결정 사항

### 시각화 라이브러리

| 후보 | 용량 | 폐쇄망 | 그래프 유형 | 다크모드 |
|------|:----:|:------:|:----------:|:-------:|
| **D3.js** (force-simulation) | ~250KB | UMD ✅ | force-directed ✅ | CSS 제어 ✅ |
| vis.js Network | ~350KB | UMD ✅ | force-directed ✅ | 테마 ✅ |
| Cytoscape.js | ~500KB | UMD ✅ | 다양 | 스타일 API ✅ |
| Sigma.js | ~200KB | UMD ✅ | WebGL 대규모 | 부분 |

**결정**: D3.js force-simulation 권장
- 이미 향후 과제에 D3.js가 언급됨 (클러스터 시각화)
- 가장 가볍고 커스터마이징 자유도 최고
- SVG 기반이라 CSS 토큰(var(--active-color) 등)으로 다크모드 자연 대응
- 단, 노드 수 1000+ 시 성능 저하 → Phase 3에서 페이지네이션 고려

### 데이터 구조

```json
{
  "nodes": [
    { "id": "sec-1", "type": "section", "label": "I. 서론", "page": 1 },
    { "id": "kw-graph", "type": "keyword", "label": "그래프", "count": 12 },
    { "id": "term-분류", "type": "glossary", "label": "분류=classification" }
  ],
  "edges": [
    { "source": "sec-1", "target": "kw-graph", "weight": 5 },
    { "source": "kw-graph", "target": "term-분류", "weight": 3 }
  ]
}
```

### 그래프 저장

- Phase 2: 요청 시 실시간 조립 (문서당 노드 ~50개 이하, 지연 무시)
- Phase 3~4: `concept_graph.json` 파일로 캐시 (문서 업로드/요약 시 재생성)

---

## 5. Plan-19 이관 항목

| 원래 위치 | 항목 | 이관 위치 |
|----------|------|----------|
| Plan-19 Phase 7 | 마인드맵 패널 (disabled 버튼) | Phase 2 — 개념 맵으로 대체 |
| Plan-19 섹션 2.2 | frontmatter keywords 자동 생성 | Phase 1a |
| Plan-19 섹션 2.2 | 카드 목록 메모 수 표시 | Phase 1b |
| Plan-19 섹션 4 | 관련 문서 자동 추천 | Phase 3 하위 항목 |
| Plan-19 섹션 4 | 용어 기반 자동 연결 | Phase 3 엣지 데이터 |
| Plan-19 섹션 4 | 클러스터 시각화 | Phase 3 시각화 |
| Plan-19 섹션 4 | 개인 문서 벡터 검색 확장 | Phase 4 Graph-RAG |

나머지 Plan-19 섹션 4 항목(번역 속도 최적화, 수식 필터링, 알고리즘 스킵, 파일명 리네이밍 등)은 본 계획과 무관하므로 **별도 백로그**로 관리.

---

## 6. 착수 순서 및 예상 공수

| Phase | 내용 | 예상 공수 | 상태 |
|:-----:|------|:--------:|:----:|
| 1a | frontmatter keywords 자동 기록 | ~2시간 | ⬜ |
| 1b | 카드 목록 메모 수 배지 | ~2시간 | ⬜ |
| 2 | **단일 문서 개념 맵** (D3.js force-directed) | ~3일 | ⬜ |
| 3 | **문서 간 연결 지도** (지식 네트워크) | ~3일 | ⬜ |
| 4 | **Graph-RAG 기반 강화** (탐색적) | ~5일 | ⬜ |

**Tier 1 (Phase 1~2)**: ~4일 — 즉시 체감, Plan-19 잔여 해소 + 시각화 기반
**Tier 2 (Phase 3)**: ~3일 — 문서 간 지식 연결
**Tier 3 (Phase 4)**: ~5일 — AI 품질 도약 (탐색적, ROI 평가 후 범위 조정)

---

## 7. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| D3.js 폐쇄망 번들 | CDN 불가 | UMD 빌드 사전 확보, `js/lib/d3.min.js` |
| AI 키워드 품질 (소형 모델) | 개념 맵 노드가 부정확할 수 있음 | 사용자가 키워드 편집 가능하도록 UI 제공 |
| 문서 간 연결 과다 | 그래프가 복잡해져 가독성 저하 | 엣지 weight 임계값 필터링, 클러스터별 색상 |
| Graph-RAG 소형 모델 한계 | 커뮤니티 요약 품질 부족 | Phase 4는 탐색적으로 진행, 모델 업그레이드 대비 |
| 노드 수 증가 시 성능 | D3.js force-simulation 렌더링 지연 | 1000+ 노드 시 WebGL(Sigma.js) 전환 검토 |

---

## 8. 성공 지표

| Phase | 지표 |
|:-----:|------|
| 2 | 문서 열람 시 개념 맵이 3초 이내 렌더링, 노드 클릭으로 해당 섹션 즉시 이동 |
| 3 | 10개 이상 문서 간 연결 네트워크가 의미 있는 클러스터 형성 |
| 4 | 기존 벡터 RAG 대비 문서 횡단 질문의 응답 관련성 체감 향상 |

---

## 9. 참고

### 출처 매핑

| 본 계획 | 원래 출처 |
|---------|----------|
| Phase 1a~1b | Plan-19 섹션 2.2 미해결 항목 |
| Phase 2 | Plan-19 Phase 7 (마인드맵 → 개념 맵 재정의) |
| Phase 3 | Plan-19 섹션 4 (관련 문서 추천, 용어 연결, 클러스터 시각화 통합) |
| Phase 4 | 신규 — 업계 트렌드 기반 |

### 아카이브

- `workbench/plans/done-19-notebook-platform-completion.md` — Phase 1~6 완료, Phase 7 본 계획으로 이관
