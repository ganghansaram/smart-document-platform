# Plan 17: PDF → Markdown 지식 파이프라인

> 작성일: 2026-03-19
> 최종 갱신: 2026-03-19
> 상태: 설계 중
> 선행: Plan 16 완료 (Phase 1~4)

---

## 1. 목적

PDF 문서를 **Markdown으로 추출·번역·저장**하여 개인 지식 자산으로 활용할 수 있는 파이프라인을 구축한다.
이는 Translator 시스템을 **개인 지식 저장소**로 진화시키는 핵심 기반이다.

## 2. 배경

### 2.1 Plan 16에서의 이관 사유

Plan 16 Phase 5는 "텍스트 엔진의 HTML 출력"으로 설계되었으나, 다음 변화에 의해 독립 계획으로 분리:

1. **출력 포맷**: HTML → **Markdown** (편집·외부 호환·RAG 연계에 유리)
2. **추출 엔진**: DocLayout-YOLO 재활용 → **PyMuPDF4LLM** (표 구조 추출, 이미지 일괄 처리)
3. **범위**: 단순 뷰어 → **지식 저장소 기반** (챗봇, 검색, 문서 연결의 토대)
4. **대상 문서**: 논문 → **전체 기술문서** (논문, 지침서, 가이드, 스팩 등)
5. **경영층 방향**: NotebookLM + Obsidian의 폐쇄망 버전

### 2.2 대상 문서 유형

| 유형 | 특성 | 핵심 추출 대상 |
|------|------|--------------|
| 학술 논문 | 2단 레이아웃, 수식, 참조 | 텍스트, 수식, 그림 |
| 기술 지침서 | 장절 구조, 절차 표, 주의사항 블록 | 텍스트, **표**, 주의 블록 |
| 가이드/매뉴얼 | 그림 多, 단계별 설명 | 텍스트, **이미지**, 리스트 |
| 스팩/규격 문서 | 요구사항 표, 물성 데이터, 수식 | **표**, 텍스트, 수식 |
| 회의록/보고서 | 단순 텍스트, 간단한 표 | 텍스트, 표 |

**설계 제약**: NotebookLM과 동일하게 **PDF 전용**. 다른 포맷은 외부에서 PDF로 변환 후 업로드하는 방식.

### 2.3 Markdown을 선택하는 이유

| 관점 | PDF 유지 | HTML 생성 | **Markdown 생성** |
|------|---------|----------|-----------------|
| 검색 | 별도 텍스트 추출 필요 | HTML 파싱 필요 | **즉시 검색 가능** |
| RAG | 별도 청킹 파이프라인 | 태그 제거 후 청킹 | **구조 보존 자연 청킹** |
| 편집 | 불가 | 복잡 (HTML 지식 필요) | **누구나 가능** |
| 외부 호환 | PDF 뷰어 | 브라우저 | **Obsidian, Typora, VS Code 등** |
| 다크모드 | PDF.js 미지원 | CSS 필요 | **렌더러가 자동 처리** |
| 복사/붙여넣기 | 깨짐 빈번 | 가능 | **완벽** |
| 데이터 크기 | 원본 유지 | 원본+HTML | **원본+MD (경량)** |

## 3. 핵심 기술 결정

### 3.1 추출 엔진: PyMuPDF4LLM

| 후보 | 장점 | 단점 | 판정 |
|------|------|------|------|
| **PyMuPDF4LLM** | 이미 PyMuPDF 사용 중, 추가 설치 최소, 표 구조 추출, 이미지 일괄 저장 | 스캔 PDF에서 표 추출 한계 | **✅ 채택** |
| MinerU | 최고 품질, DocLayout-YOLO 내장, 수식 LaTeX 변환 | 별도 대형 모델 필요 (~2GB), 폐쇄망 설치 복잡 | 보류 |
| Marker | 인기, LLM 연동 고품질 | GPU 필수, 별도 모델 다운로드, 표 약함 | 부적합 |
| 텍스트 엔진 재활용 | 기존 코드 활용 | 표 구조 미추출, 이미지 별도 저장 안 됨 | 부적합 |

**선택 근거**:
- `pymupdf4llm`은 `pip install pymupdf4llm`만으로 설치 (PyMuPDF 확장)
- 우리가 이미 PyMuPDF 1.25.2를 사용 중
- `to_markdown()` 한 번의 호출로 텍스트+표+이미지+읽기순서 일괄 처리
- 폐쇄망에서 추가 모델 다운로드 불필요 (AI 레이아웃 분석은 선택적)

### 3.2 표 처리 전략: 이중 접근

기술문서에서 표는 핵심 데이터다. 검색·복사·RAG에서 활용되려면 구조화된 텍스트여야 한다.

| 단계 | 처리 | 결과 |
|------|------|------|
| **1차: PyMuPDF 구조 추출** | `find_tables()` → 셀 데이터 추출 | Markdown 테이블 (`\| A \| B \|`) |
| **2차: 추출 실패 시** | 해당 영역 pixmap 캡처 → Ollama에 이미지 전달 → "이 표를 Markdown으로 변환해줘" | Markdown 테이블 (LLM 생성) |
| **백업: 어떤 경우든** | 원본 영역 이미지도 함께 저장 | `![Table](assets/table_0.png)` — 원본 대조용 |

```markdown
<!-- 추출 성공 시 결과 예시 -->
| 항목 | 인장강도 (MPa) | 연신율 (%) |
|------|:-------------:|:---------:|
| Ti-6Al-4V | 950 | 14 |
| Inconel 718 | 1380 | 12 |

<details><summary>원본 표 이미지</summary>

![Table](assets/table_0.png)
</details>
```

### 3.3 이미지/수식 처리

| 유형 | 처리 | Markdown 표현 |
|------|------|-------------|
| 그림 (figure) | PyMuPDF4LLM `write_images=True` → PNG 추출 | `![Figure 3.1](assets/fig_0.png)` |
| 수식 (formula) | 영역 캡처 → 이미지 저장 (LaTeX 변환은 향후) | `![Formula](assets/formula_0.png)` |
| 차트/그래프 | 이미지 추출 | `![Chart](assets/chart_0.png)` |

> 수식의 LaTeX 변환은 MinerU의 UniMERNet 모델이 필요하며, 현재 폐쇄망 설치가 복잡하므로 초기에는 이미지로 처리. 향후 모델 도입 시 `$E = mc^2$` 형태로 전환 가능.

### 3.4 번역 전략

Markdown 추출 후 번역은 **블록 단위**로 수행:

```
원문 Markdown 추출 → 블록 분리 (heading, paragraph, table, ...) → 블록별 Ollama 번역 → 번역 Markdown 조합
```

| 블록 유형 | 번역 방식 |
|----------|----------|
| 제목 (`## ...`) | 개별 번역 |
| 본문 단락 | 개별 번역 (긴 단락은 분할) |
| 표 셀 데이터 | 셀 텍스트 일괄 번역 (표 구조 유지) |
| 리스트 항목 | 항목 그룹 일괄 번역 |
| 이미지 캡션 | 개별 번역 |
| 이미지/수식 | 번역 대상 아님 (그대로 유지) |

기존 용어집(`glossary.json`)도 동일하게 프롬프트 주입 방식으로 적용.

### 3.5 브라우저 렌더링: marked.js

| 라이브러리 | 크기 | GFM 표 | 폐쇄망 |
|-----------|------|:------:|:------:|
| **marked.js** | ~40KB | ✅ | ✅ |
| markdown-it | ~100KB | ✅ (플러그인) | ✅ |

**marked.js 채택**: 가볍고, 단일 파일 번들, GFM(GitHub Flavored Markdown) 기본 지원.
`js/lib/marked.min.js`로 배치 (PDF.js와 동일 패턴).

렌더링 흐름:
```
서버: web_view.md 원본 전달 (API)
  → 프론트: marked.js로 MD→HTML 변환
  → 우측 패널 <div>에 innerHTML 삽입
  → tokens.css 변수로 스타일링 (다크모드 자동)
```

## 4. 데이터 관리 설계

### 4.1 저장 구조

```
data/translator/{username}/{doc_id}/
├── original.pdf                    ← 원본 (기존)
├── meta.json                       ← 문서 메타데이터 (기존)
├── pages/{N}/
│   ├── translated.pdf              ← PDF 엔진 결과 (기존, 유지)
│   ├── text_translated.pdf         ← 텍스트 엔진 결과 (기존, 유지)
│   ├── text_mapping.json           ← 텍스트 엔진 매핑 (기존, 유지)
│   ├── source.md                   ← 신규: 원문 Markdown
│   ├── translated.md               ← 신규: 번역 Markdown
│   └── assets/                     ← 신규: 추출된 이미지/표
│       ├── fig_0.png
│       ├── table_0.png
│       └── formula_0.png
├── full_source.md                  ← 신규: 전체 원문 (전 페이지 병합)
├── full_translated.md              ← 신규: 전체 번역 (번역된 페이지 병합)
└── assets/                         ← 신규: 전체 문서 이미지
    └── (페이지별 assets 통합 또는 심볼릭 참조)
```

### 4.2 Markdown Frontmatter

모든 `.md` 파일에 YAML frontmatter를 포함하여 메타데이터를 구조화:

```yaml
---
title: "Deep-RACO: 자율 회피 통신 운용기"
source: "original.pdf"
page: 3
total_pages: 42
model: "gemma3:27b"
extracted_at: "2026-03-19T15:30:00"
translated_at: "2026-03-19T15:35:00"
extractor: "pymupdf4llm"
tags: []
---

## 3.2 시스템 아키텍처

본 시스템은 강화학습 기반 자율 회피 알고리즘을 ...
```

**frontmatter 활용**:
- 검색 시 메타데이터 필터링 (모델별, 날짜별, 태그별)
- 향후 지식 그래프 노드 속성
- Obsidian에서 열었을 때 속성 패널 자동 표시

### 4.3 전체 문서 병합

페이지별 번역이 누적되면, `full_translated.md`로 자동 병합:

```markdown
---
title: "Deep-RACO 소프트웨어 아키텍처 규격서"
pages_translated: [1, 2, 3, 5, 7]
pages_total: 42
last_merged: "2026-03-19T16:00:00"
---

<!-- Page 1 -->
## 1. 프로젝트 개요
...

<!-- Page 2 -->
## 1.1 범위
...

<!-- Page 3 -->
## 2. 아키텍처 드라이버
...
```

이 파일이 **RAG 인덱싱, 챗봇, 검색의 주 입력**이 된다.

### 4.4 데이터 수명 관리

| 데이터 | 생성 시점 | 갱신 시점 | 삭제 시점 |
|--------|----------|----------|----------|
| `source.md` | 최초 웹 뷰 요청 시 | 재추출 요청 시 | 문서 삭제 시 |
| `translated.md` | 번역 완료 시 | 재번역 시 | 문서 삭제 시 |
| `assets/*.png` | 추출 시 | 재추출 시 | 문서 삭제 시 |
| `full_translated.md` | 페이지 번역 완료마다 | 추가 번역 시 자동 갱신 | 문서 삭제 시 |

## 5. 프론트엔드 설계

### 5.1 엔진 토글 확장

```
현재: PDF | 텍스트  (2종)
변경: PDF | 텍스트 | 웹 뷰  (3종)
```

| 모드 | 좌측 패널 | 우측 패널 | 스크롤 동기화 |
|------|-----------|-----------|:----------:|
| PDF | 원문 PDF (PDF.js) | 번역 PDF (pdf2zh) | O |
| 텍스트 | 원문 PDF | 번역 PDF (재조립) | O |
| **웹 뷰** | 원문 PDF | **번역 Markdown (marked.js)** | **X** |

### 5.2 우측 패널 — 웹 뷰 모드

```
┌─────────────────────────────────┐
│  [PDF ▾]  번역 결과              │
├─────────────────────────────────┤
│                                 │
│  ## 3.2 시스템 아키텍처           │
│                                 │
│  본 시스템은 강화학습 기반 ...     │
│                                 │
│  ┌─────────────────────────┐    │
│  │  [Figure 3.1 이미지]     │    │
│  └─────────────────────────┘    │
│                                 │
│  | 항목 | 인장강도 | 연신율 |     │
│  |------|---------|--------|     │
│  | Ti.. | 950     | 14     |     │
│                                 │
│  ▸ 원본 표 이미지                │
│                                 │
└─────────────────────────────────┘
```

**UX 특성**:
- 연속 스크롤 (PDF 페이지 구분 없음)
- Ctrl+F 네이티브 검색
- 텍스트 선택/복사 완벽 동작
- 다크모드 자동 대응 (tokens.css)
- 폰트 크기 조절 (CSS font-size)

### 5.3 클릭 네비게이션 (원문 ↔ 번역)

스크롤 동기화 대신 **클릭 기반 양방향 탐색**:

- 우측 Markdown 블록 클릭 → 좌측 PDF 해당 영역으로 스크롤 + 박스 하이라이트
- 좌측 PDF 영역 클릭 → 우측 Markdown 해당 블록으로 스크롤 + 배경 플래시

구현: 각 Markdown 블록에 `data-block-id` 속성 → source_rect 좌표와 매핑.

## 6. API 설계

### 6.1 신규 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/translator/web-extract/{doc_id}/page/{page_num}` | Markdown 추출 시작 |
| GET | `/api/translator/web-extract/{doc_id}/page/{page_num}/status` | 추출 상태 조회 |
| POST | `/api/translator/web-translate/{doc_id}/page/{page_num}` | Markdown 번역 시작 |
| GET | `/api/translator/web-translate/{doc_id}/page/{page_num}/status` | 번역 상태 조회 |
| GET | `/api/translator/web-view/{doc_id}/page/{page_num}` | 페이지 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/full` | 전체 병합 Markdown 서빙 |
| GET | `/api/translator/web-view/{doc_id}/assets/{filename}` | 이미지 자산 서빙 |

### 6.2 처리 흐름

```
사용자: "웹 뷰" 모드 선택 → 페이지 이동

1. source.md 존재?
   YES → 3으로
   NO  → 2. PyMuPDF4LLM 추출 (source.md + assets/) → 3으로

3. translated.md 존재?
   YES → 4으로
   NO  → 번역 버튼 표시 → 클릭 시 Ollama 블록 번역 → translated.md 저장 → 4로

4. translated.md를 API로 전달 → 프론트에서 marked.js 렌더링
```

## 7. 실행 계획

### Phase 1: 추출 파이프라인 (PyMuPDF4LLM)

- [ ] `pymupdf4llm` 패키지 설치 및 폐쇄망 whl 준비
- [ ] `services/md_extractor.py` — PDF→Markdown 추출 모듈
  - `extract_page()`: 단일 페이지 → source.md + assets/
  - `extract_full()`: 전체 페이지 → full_source.md
  - 표 추출 전략: `find_tables()` 1차 → 실패 시 이미지 캡처
  - frontmatter 자동 생성
- [ ] 다양한 PDF 유형으로 추출 품질 검증
  - 논문 (2단, 수식)
  - 스팩 (표 다수)
  - 매뉴얼 (이미지 다수)
  - 스캔 PDF (OCR 필요 여부 확인)
- [ ] 예상 공수: 2~3일

### Phase 2: 번역 파이프라인

- [ ] `services/md_translator.py` — Markdown 블록 번역 모듈
  - Markdown 파싱 → 블록 분리 (heading, paragraph, table, list, image)
  - 블록별 Ollama 번역 (이미지/수식은 스킵)
  - 표 셀 번역 (구조 유지)
  - 용어집 적용 (기존 glossary.json 재활용)
  - translated.md 저장 + frontmatter 갱신
- [ ] `full_translated.md` 자동 병합 로직
- [ ] 예상 공수: 2~3일

### Phase 3: API + 프론트엔드

- [ ] `api/translator.py`에 웹 뷰 엔드포인트 추가 (6.1 참조)
- [ ] `marked.js` 번들 (`js/lib/marked.min.js`)
- [ ] 엔진 토글 3종 확장 (`pdf | text | web`)
- [ ] 우측 패널: 웹 뷰 모드 Markdown 렌더링
- [ ] Markdown 스타일시트 (tokens.css 변수 활용, 다크모드)
- [ ] 클릭 네비게이션 (원문 PDF ↔ 번역 Markdown)
- [ ] 예상 공수: 3~4일

### Phase 4: 다운로드 + 데이터 활용 기반

- [ ] Markdown 다운로드 (.md 파일)
- [ ] 전체 병합 Markdown 다운로드
- [ ] 이미지 포함 ZIP 다운로드 (Obsidian vault로 바로 사용 가능)
- [ ] 검색 인덱스에 Markdown 텍스트 포함
- [ ] 예상 공수: 1~2일

## 8. 지식 플랫폼 확장 (Phase 1~4 이후)

Plan 17의 Phase 1~4가 **추출·번역·뷰어·다운로드**를 완성하면,
아래 기능들은 이미 확보된 데이터(임베딩, 용어집, frontmatter, Markdown 텍스트)를 활용하여
**경량으로 구현 가능**하다. Obsidian이 사용자 수동 작업에 의존하는 것과 달리,
우리는 **AI가 자동으로 처리**하여 사용자 노력을 최소화하는 것이 차별점이다.

### 8.1 자동 요약 + 키워드 추출 (난이도: 하)

문서 업로드 또는 번역 완료 시, Ollama가 자동으로 요약과 키워드를 생성하여 frontmatter에 저장한다.
사용자 노력: **없음**. 업로드만 하면 됨.

```yaml
# frontmatter에 자동 추가
---
summary: "본 논문은 Ti-6Al-4V 합금의 적층제조 시 잔류응력 제어 방법을 제안한다..."
keywords: [적층제조, 잔류응력, Ti-6Al-4V, 열처리, 시뮬레이션]
---
```

**구현**:
- 번역 완료 콜백에서 `full_translated.md` 텍스트를 Ollama에 전달
- 프롬프트: "이 문서를 3줄로 요약하고 핵심 키워드 5개를 추출해줘"
- 결과를 frontmatter의 `summary`, `keywords` 필드에 저장
- 카드 목록에서 요약 미리보기 표시

### 8.2 관련 문서 자동 추천 (난이도: 하)

문서 열람 시 하단에 관련 문서를 자동으로 표시한다. 사용자가 링크를 수동으로 거는 Obsidian과 달리,
**시스템이 유사도를 계산하여 자동 연결**한다.

```
📎 관련 문서
├── [0.92] Ti-6Al-4V 적층제조 표준 시험법 (키워드 4개 일치)
├── [0.87] 잔류응력 측정 가이드라인 (임베딩 유사도)
└── [0.81] 열처리 공정 규격서 (용어집 3개 공유)
```

**구현**:
- 유사도 = 임베딩 코사인 유사도(70%) + 키워드 겹침(20%) + 용어집 공유도(10%)
- 문서 수가 수십~수백 개이므로 FAISS 없이 브루트포스 계산 가능
- bge-m3 임베딩은 이미 Explorer RAG에서 사용 중 (인프라 재활용)
- 결과를 JSON으로 캐싱, 새 문서 추가 시 갱신

### 8.3 용어 기반 자동 연결 (난이도: 하)

용어집에 등록된 용어가 문서에 등장하면, 해당 용어를 자동 하이라이트하고
같은 용어가 등장하는 다른 문서 목록을 팝업으로 표시한다.

```
Markdown 렌더링 시:
  "적층제조" 텍스트 발견
  → <span class="term-link" data-term="적층제조">적층제조</span> 로 변환
  → 클릭 시 "이 용어가 등장하는 문서 5건" 팝업
```

**구현**:
- `glossary.json`의 source 키워드로 Markdown 텍스트를 스캔
- marked.js 렌더링 후 DOM에서 키워드 매칭 → `<span>` 래핑
- 용어별 문서 인덱스를 서버에서 관리 (`term_index.json`)
- Obsidian의 `[[양방향 링크]]`를 사용자가 수동으로 거는 대신, 용어집이 자동으로 연결

### 8.4 문서 클러스터 시각화 (난이도: 중)

모든 문서의 임베딩 벡터를 2D로 축소하여 D3.js force graph로 시각화한다.
문서 간 거리가 가까울수록 내용이 유사함을 의미한다.

```
  [적층제조 논문들]        [재료 물성 스팩들]
    ●──●                    ●──●
    │  │                    │
    ●──●──●                 ●──●
              [피로 시험 가이드들]
                ●──●──●
```

**구현**:
- 백엔드: 문서별 bge-m3 임베딩 → UMAP으로 2D 축소 (`umap-learn` 패키지)
- 프론트: D3.js force graph (순수 JS, `js/lib/d3.min.js` 번들)
- 노드 = 문서, 엣지 = 유사도 임계값 초과 시 연결
- 노드 색상 = 태그/폴더별, 노드 크기 = 페이지 수 또는 열람 빈도
- 클러스터 라벨: Ollama가 그룹별 대표 키워드 자동 생성
- 노드 클릭 → 해당 문서로 이동
- Translator 좌측 트리 패널 하단에 "지식 맵" 탭으로 접근

### 8.5 문서 타임라인 (난이도: 하)

frontmatter의 날짜 데이터로 시간순 시각화를 제공한다.

```
2026-03 ──●── Ti-6Al-4V 적층제조 논문 [번역 완료]
          ●── 잔류응력 시뮬레이션 가이드 [번역 중]
2026-02 ──●── 재료 물성 스팩 v2.1 [번역 완료]
          ●── 피로 시험 절차서 [미번역]
2026-01 ──●── 열처리 공정 규격 [번역 완료]
```

**구현**:
- frontmatter의 `extracted_at`, `translated_at` + `tags`로 생성
- 순수 CSS + 약간의 JS로 구현 (외부 라이브러리 불필요)
- 상태 배지: 번역 완료 / 번역 중 / 미번역
- 필터: 태그, 폴더, 기간

### 8.6 Markdown 편집기 (난이도: 중)

번역 결과를 웹에서 직접 수정할 수 있는 WYSIWYG Markdown 편집기를 탑재한다.
Explorer에 Monaco Editor를 번들한 것과 동일한 패턴.

**후보 에디터**:

| 에디터 | 크기 | 방식 | 기반 | 폐쇄망 | 특징 |
|--------|------|------|------|:------:|------|
| **EasyMDE** | ~140KB | 분할 (편집+미리보기) | CodeMirror | ✅ | 가장 심플, 표 삽입 툴바, autosave, GFM 지원, Vanilla JS 즉시 사용 |
| **Milkdown** | ~40KB gzip | WYSIWYG | ProseMirror | ✅ | 플러그인 확장, 헤드리스 디자인, 타이핑 중 실시간 렌더링 |
| Monaco (기존) | 이미 있음 | 코드 에디터 | — | ✅ | Markdown 구문 하이라이트는 되나 미리보기 직접 구현 필요 |

**추천: EasyMDE** — 이유:
- `<script src="js/lib/easymde/easymde.min.js">` 한 줄로 로드 (빌드 불필요)
- 내장 marked.js로 미리보기 렌더링 (Phase 3의 marked.js와 동일)
- 편집+미리보기 분할 모드가 번역 교정 작업에 적합
- 자동 저장(autosave) 내장 → 편집 중 데이터 유실 방지
- 표 삽입 툴바 → 비개발자도 표 편집 가능

**UX 흐름**:
```
웹 뷰 모드에서 "편집" 버튼 클릭
  → 우측 패널이 EasyMDE 에디터로 전환
  → 사용자가 Markdown 직접 수정 (오역 교정, 메모 추가 등)
  → "저장" → translated.md 갱신 → 다시 뷰어 모드로 복귀
```

### 8.7 개인 문서 AI 챗봇 (난이도: 중)

`full_translated.md`를 RAG 입력으로 사용하여, 개인 문서 기반 AI 챗봇을 제공한다.
Explorer의 RAG 파이프라인(FAISS + bge-m3 + 리랭커 + 멀티턴)을 재활용한다.

```
사용자: "이 논문에서 잔류응력 제어 방법이 뭐야?"
챗봇:   "본 논문에서는 3가지 잔류응력 제어 방법을 제시합니다:
         1. 기판 예열 (200~400°C)
         2. 레이저 출력 최적화 (200~350W)
         3. 후열처리 (600°C/2h + 공냉)
         [출처: p.15 §3.4]"
```

**구현**:
- `full_translated.md` → 청크 분할 (Markdown 구조 기반)
- bge-m3 임베딩 → 문서별 벡터 인덱스 저장
- 챗봇 UI: Explorer의 `ai-chat.js` 패턴 재활용 (슬라이드 패널)
- 멀티턴 대화: Explorer의 `conversation.py` + `query_rewriter.py` 재활용
- 출처 인용: Markdown 블록 ID → 클릭 시 해당 위치로 스크롤

### 8.8 수식 LaTeX 변환 (난이도: 고 — 외부 모델 의존)

현재 수식은 이미지로 캡처하지만, MinerU의 UniMERNet 모델을 도입하면
`$E = mc^2$` 형태의 LaTeX로 변환 가능하다.

- 폐쇄망 설치 복잡도가 높으므로 (모델 ~2GB) 초기에는 보류
- marked.js에 KaTeX 플러그인을 추가하면 LaTeX 렌더링 가능
- 도입 시 수식도 검색/복사/RAG 대상이 됨

### 8.9 우선순위 요약

| 순서 | 기능 | 난이도 | 새 라이브러리 | 이미 가진 데이터 활용 |
|:----:|------|:------:|:----------:|:------------------:|
| 1 | 자동 요약 + 키워드 | 하 | 없음 | Ollama + Markdown |
| 2 | 관련 문서 추천 | 하 | 없음 | bge-m3 임베딩 + 용어집 |
| 3 | 용어 자동 연결 | 하 | 없음 | glossary.json |
| 4 | 문서 타임라인 | 하 | 없음 | frontmatter 날짜 |
| 5 | Markdown 편집기 | 중 | EasyMDE (~140KB) | — |
| 6 | 클러스터 시각화 | 중 | D3.js (~250KB) + UMAP | bge-m3 임베딩 |
| 7 | AI 챗봇 | 중 | 없음 (Explorer 재활용) | full_translated.md |
| 8 | 수식 LaTeX | 고 | UniMERNet (~2GB) + KaTeX | — |

> **1~4번은 새 라이브러리 없이 기존 데이터만으로 구현 가능.**
> 5~7번은 경량 라이브러리 1개씩 추가 또는 기존 코드 재활용.
> 8번만 대형 모델 도입이 필요하여 별도 검토.

## 9. 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| PyMuPDF4LLM 표 추출 정확도 | 복잡한 병합 표에서 깨질 수 있음 | 이미지 백업 + Ollama 2차 변환 |
| 스캔 PDF (이미지 기반) | 텍스트 추출 불가 | OCR 모드 (`use_ocr=True`, Tesseract 필요) 또는 대상 제외 |
| 번역 품질 (블록 단위) | 문맥 단절로 번역 부자연스러움 | 인접 블록 요약을 문맥 힌트로 전달 |
| 기존 엔진과의 혼동 | 3종 엔진 UX 복잡도 | 모드별 명확한 설명 툴팁, 용도 가이드 |
| Markdown 렌더링 보안 | XSS 가능성 | marked.js + DOMPurify 조합 |

## 10. 참고

### 핵심 라이브러리/도구

| 자료 | 용도 | 크기 |
|------|------|------|
| [PyMuPDF4LLM 문서](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | PDF→Markdown 추출 엔진 | PyMuPDF 확장 (pip) |
| [PyMuPDF4LLM API](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/api.html) | `to_markdown()` 파라미터 상세 | — |
| [marked.js](https://marked.js.org/) | Markdown→HTML 브라우저 렌더링 (Phase 3) | ~40KB |
| [EasyMDE](https://github.com/Ionaru/easy-markdown-editor) | WYSIWYG Markdown 편집기 (Phase 8.6) | ~140KB |
| [D3.js](https://d3js.org/) | 클러스터/그래프 시각화 (Phase 8.4) | ~250KB |
| [DOMPurify](https://github.com/cure53/DOMPurify) | Markdown 렌더링 XSS 방어 | ~15KB |

### 벤치마크/비교 자료

| 자료 | 용도 |
|------|------|
| [Marker vs MinerU vs MarkItDown 비교](https://jimmysong.io/blog/pdf-to-markdown-open-source-deep-dive/) | PDF→MD 추출 엔진 벤치마크 |
| [MinerU](https://github.com/opendatalab/MinerU) | 향후 고품질 추출 엔진 후보 (DocLayout-YOLO + UniMERNet) |
| [PyMuPDF RAG/LLM 가이드](https://artifex.com/blog/rag-llm-and-pdf-conversion-to-markdown-text-with-pymupdf) | PyMuPDF4LLM 실전 활용 사례 |

### 프로젝트 내부 문서

| 문서 | 위치 | 관계 |
|------|------|------|
| Plan 16 (완료) | `workbench/plans/done-16-translator-quality-enhancement.md` | 선행 계획 (HiDPI, 용어집, 다운로드) |
| 플랫폼 비전 | `docs/09-PLATFORM-VISION.md` | 지식 플랫폼 로드맵, NotebookLM/Obsidian 기능 분석 |
| Explorer RAG | `backend/services/` | 챗봇 재활용 대상 (faiss, reranker, conversation, query_rewriter) |
| 텍스트 엔진 | `backend/services/text_translator.py` | 기존 DocLayout-YOLO 파이프라인 (병행 유지) |
| 용어집 | `backend/services/translator_service.py` | glossary.json CRUD, 번역·자동연결에서 공유 |
