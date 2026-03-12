내가사# 문서 비교(Document Comparison) 시스템 조사 보고서

> 조사일: 2026-03-12

---

## 1. UI/UX 패턴

### 1.1 비교 뷰 모드

#### Side-by-Side (좌우 분할)
- **설명**: 원본과 수정본을 좌우 패널에 나란히 배치
- **장점**: 두 문서를 동시에 볼 수 있어 직관적, 대규모 변경 파악에 유리
- **단점**: 화면 너비를 많이 차지, 모바일/좁은 화면에서 불리
- **사용 사례**: GitHub PR 리뷰 (split view), Beyond Compare, Araxis Merge, VS Code diff editor
- **구현 참고**: Apryse WebViewer는 PDF/Office/이미지를 side-by-side로 비교 지원

#### Inline / Unified (단일 문서 내 변경점)
- **설명**: 하나의 문서 흐름 안에서 추가/삭제를 `<ins>`/`<del>` 태그로 표시
- **장점**: 화면 공간 효율적, 문맥 흐름을 유지하며 변경점 확인 가능
- **단점**: 대규모 변경 시 가독성 저하, 삭제+추가가 혼재하면 혼란
- **사용 사례**: GitHub unified diff, Google Docs 변경 추적, Word 변경 내용 추적
- **구현 참고**: diff2html이 unified view 렌더링 지원

#### Overlay (겹치기)
- **설명**: 두 문서를 반투명으로 겹쳐 시각적 차이를 표시
- **장점**: 레이아웃/디자인 변경을 직관적으로 파악 (픽셀 단위 비교)
- **단점**: 텍스트 내용 비교에는 부적합, 구조적 변경 파악 어려움
- **사용 사례**: PDF 비교 (Nutrient SDK), 이미지 비교, 웹페이지 레이아웃 비교 (diffsite)
- **변형**: Swipe 모드 (수직 핸들로 좌우 드래그하며 비교)

### 1.2 동기 스크롤 (Synchronized Scrolling)

#### 구현 방식
1. **비례(Proportional) 동기화**: 스크롤 위치를 비율로 계산 (`scrollTop / scrollHeight`)하여 동기화. 문서 길이가 다를 때 적합
2. **픽셀(Pixel) 동기화**: 동일한 픽셀 양만큼 스크롤. 구조가 동일한 문서에 적합
3. **앵커(Anchor) 기반 동기화**: 대응하는 섹션/단락을 앵커로 매핑, 해당 앵커 위치로 스크롤. 구조적 diff에서 가장 정확

#### 라이브러리
- **syncscroll** (946 bytes, Vanilla JS): `syncscroll` 클래스 + 동일 `name` 속성으로 비례 동기화. 폐쇄망 환경에 적합
- **구현 핵심**: `scroll` 이벤트 리스닝 + 상대편 `scrollTop` 업데이트. 무한 루프 방지를 위해 플래그 사용 필수

### 1.3 변경점 네비게이션

#### 표준 패턴
- **Prev/Next 버튼**: 이전/다음 변경점으로 점프 (가장 보편적)
- **키보드 단축키**:
  - VS Code: `F7` / `Shift+F7` (다음/이전 변경점), `Alt+Down` / `Alt+Up`
  - Beyond Compare: `Ctrl+N` (다음), macOS는 `Cmd+Up/Down`
- **변경점 목록 패널**: 사이드바에 모든 변경점을 리스트로 표시, 클릭 시 해당 위치로 이동
- **미니맵**: 전체 문서 축소 뷰에 변경점 위치를 색상 마커로 표시 (VS Code 스타일)

### 1.4 변경점 하이라이트 컬러 컨벤션

| 변경 유형 | 표준 색상 | 대안 (색맹 배려) |
|-----------|-----------|-----------------|
| 추가 (Added) | 초록 (`#e6ffec`, `#2cbe4e`) | 파랑 계열 |
| 삭제 (Deleted) | 빨강 (`#ffeef0`, `#cb2431`) | 주황 계열 |
| 수정 (Modified) | 노랑/주황 (`#fff3cd`) | 보라 계열 |
| 이동 (Moved) | 청록/자홍 | - |

- **접근성 고려**: 남성의 5%, 여성의 0.5%가 적록색맹. 주황-파랑 조합이 대안으로 권장
- **강조 방식**: 배경색 + 좌측 세로 바(gutter bar)가 가장 보편적

### 1.5 필터링 및 요약

- **변경 유형 필터**: 추가만 / 삭제만 / 수정만 보기 토글
- **중요도 필터**: 공백 변경 무시, 대소문자 변경 무시 옵션
- **변경 요약 패널**: 변경 통계 (추가 N건, 삭제 N건, 수정 N건), 카테고리별 분류

---

## 2. Diff 알고리즘

### 2.1 핵심 알고리즘 비교

#### Myers Diff Algorithm
- **원리**: 1986년 Eugene Myers 발표. Edit graph에서 최단 경로를 분할 정복으로 탐색
- **복잡도**: O(ND) — N은 입력 길이, D는 편집 거리
- **특징**: Git의 기본 diff 알고리즘. 최소 편집 거리를 보장
- **장점**: 최적 해 보장, 잘 검증된 알고리즘
- **단점**: 코드 이동이 있을 때 직관적이지 않은 결과 생성 가능

#### Patience Diff
- **원리**: Bram Cohen(BitTorrent 창시자) 개발. 양쪽 파일에서 고유한(1회만 등장) 라인을 "앵커"로 매칭 후 나머지를 재귀적으로 처리
- **특징**: 앵커가 없는 구간은 Myers로 폴백
- **장점**: 함수 경계, 빈 줄 등 구조적 앵커를 잘 인식하여 더 직관적인 diff 생성
- **단점**: 고유 라인이 없는 반복적 텍스트에서 성능 저하

#### Histogram Diff
- **원리**: Patience를 확장. 고유 라인뿐 아니라 "최소 빈도" 라인도 앵커로 활용
- **특징**: Linus Torvalds 선호. JGit(Eclipse)에서 처음 구현
- **장점**: Patience보다 빠르고, 반복 라인이 많은 경우에도 좋은 결과
- **단점**: Myers 대비 최적성 보장 없음

#### 알고리즘 선택 가이드

| 상황 | 권장 알고리즘 |
|------|-------------|
| 일반적 텍스트 비교 | Myers (기본값) |
| 구조적 코드/문서 비교 | Patience 또는 Histogram |
| 성능 우선 | Histogram |
| 패치 적용 신뢰성 | Histogram |
| 최적 편집 거리 필요 | Myers |

### 2.2 비교 단위 (Granularity)

#### 라인 단위 (Line-level)
- 가장 빠르고 일반적, 코드 비교에 표준
- 한 글자만 바뀌어도 라인 전체가 변경으로 표시

#### 단어 단위 (Word-level)
- 산문/기술문서 비교에 가장 적합. 가독성과 세밀도의 균형
- 텍스트를 공백/구두점 기준으로 토큰화 후 diff 수행

#### 문자 단위 (Character-level)
- 오타, 구두점 변경 등 미세한 차이 감지
- 긴 문서에서는 노이즈가 많아 가독성 저하

#### 문장 단위 (Sentence-level)
- 기술문서, 규격서 비교에 유용
- 문장 분리(sentence tokenization) 전처리 필요

### 2.3 구조적 Diff (HTML/XML)

- **일반 텍스트 diff의 한계**: HTML 태그 변경, 속성 순서 변경 등을 의미 없는 변경으로 처리
- **트리 기반 diff**: DOM 트리를 순회하며 노드 단위로 비교
  - 노드 유형, 속성, 내용을 고려한 정밀 비교
  - 노드 이동(relocation)을 삭제+삽입이 아닌 이동으로 인식
- **주요 라이브러리**: diffDOM (JS), htmltreediff (Python), xmldiff (Python)

### 2.4 의미적 Diff (Semantic Diff) — LLM 활용

#### 접근 방식
1. **임베딩 기반 비교**: 문서를 벡터로 변환 후 코사인 유사도 계산. 의미적 유사성은 파악하나 구체적 변경점 식별은 어려움
2. **정보 추출 기반**: LLM으로 핵심 정보(주제, 요구사항, 수치)를 추출 후 구조화된 비교
3. **에이전트 기반**: LLM이 두 문서를 읽고 변경점을 자연어로 설명. 단락/문장/단어 수준 조절 가능

#### 장점
- 동의어/유사 표현 변경 감지 ("온도 허용치" -> "열 한계값")
- 의미가 동일한 문장 재구성을 무시
- 맥락을 이해한 변경 중요도 평가

#### 한계
- 할루시네이션 위험, 결정적(deterministic) 결과 보장 불가
- 비용과 지연 시간
- 폐쇄망 환경에서는 로컬 LLM 필요

#### 실용적 하이브리드 접근
- **1단계**: 전통적 diff로 변경 구간 식별 (빠르고 정확)
- **2단계**: 변경 구간만 LLM에 전달하여 의미적 분석 (비용 절감)
- **적용 예**: 규격서의 수치 변경, 용어 변경, 요구사항 추가/삭제를 카테고리별로 분류

---

## 3. 오픈소스 라이브러리

### 3.1 JavaScript 라이브러리

#### diff-match-patch (Google)
- **GitHub**: [google/diff-match-patch](https://github.com/google/diff-match-patch)
- **특징**: Google Docs 원조 엔진 (2006~). Diff + Match + Patch 3-in-1
- **알고리즘**: Myers diff + Bitap 매칭
- **의존성**: 없음 (Vanilla JS, 단일 파일)
- **브라우저**: IE 5.5 이상 모든 브라우저
- **다국어**: JavaScript, Python, Java, C++, Dart 등 지원
- **평가**: 폐쇄망 환경에 최적. 의존성 제로, 단일 JS 파일로 동작. 문자 단위 diff가 기본이지만 후처리로 단어/라인 단위 변환 가능
- **npm 주간 다운로드**: ~3.2M

#### jsdiff (diff)
- **GitHub**: [kpdecker/jsdiff](https://github.com/kpdecker/jsdiff) — 약 8,880 stars
- **특징**: 문자/단어/라인/문장/CSS/JSON 단위 diff 지원
- **API**: `diffChars()`, `diffWords()`, `diffLines()`, `diffSentences()`, `createPatch()` 등
- **의존성**: 없음
- **평가**: 다양한 granularity 지원이 장점. 대용량 텍스트에서 성능 이슈 보고됨
- **npm 주간 다운로드**: ~59.6M (가장 많음)

#### diff2html
- **GitHub**: [rtfpessoa/diff2html](https://github.com/rtfpessoa/diff2html) — 약 3,218 stars
- **특징**: unified diff 출력을 HTML로 변환하여 시각화. Side-by-side + Line-by-line 뷰 지원
- **용도**: diff 결과의 렌더링/시각화에 특화 (diff 계산 자체는 별도)
- **의존성**: highlight.js (선택적)
- **평가**: diff 계산 라이브러리와 조합하여 사용. 예쁜 HTML diff 뷰 생성에 최적
- **npm 주간 다운로드**: ~255K

#### diffDOM
- **GitHub**: [fiduswriter/diffDOM](https://github.com/fiduswriter/diffDOM)
- **특징**: DOM 요소 간 구조적 diff 수행. 노드 이동을 삭제+삽입이 아닌 재배치로 처리
- **용도**: HTML 구조 비교, DOM 패치
- **평가**: HTML 문서 비교에 적합하지만, 텍스트 내용 비교보다는 DOM 구조 비교에 특화

#### 라이브러리 선택 매트릭스 (JS)

| 요구사항 | 권장 라이브러리 |
|---------|--------------|
| 폐쇄망, 의존성 제로 | diff-match-patch |
| 다양한 granularity (단어/문장) | jsdiff |
| 예쁜 HTML diff 뷰 렌더링 | diff2html |
| HTML DOM 구조 비교 | diffDOM |
| 텍스트 diff + 시각화 조합 | jsdiff + diff2html |

### 3.2 Python 라이브러리

#### difflib (표준 라이브러리)
- **위치**: Python 표준 라이브러리 (별도 설치 불요)
- **알고리즘**: Ratcliff/Obershelp (SequenceMatcher)
- **주요 API**:
  - `SequenceMatcher`: 두 시퀀스의 유사도 비율 계산
  - `HtmlDiff`: 줄 단위 비교 결과를 HTML 테이블로 생성 (인라인 변경점 하이라이트)
  - `unified_diff`, `context_diff`: 표준 diff 형식 출력
- **평가**: 추가 설치 없이 사용 가능. 기본적 텍스트 비교에 충분. HTML 출력 스타일이 다소 구식

#### xmldiff
- **GitHub/PyPI**: [xmldiff](https://pypi.org/project/xmldiff/)
- **알고리즘**: "Change Detection in Hierarchically Structured Information" 논문 기반 + Google diff_match_patch
- **주요 API**: `diff_files()`, `diff_texts()`, `diff_trees()`
- **출력**: XML diff 액션 리스트 또는 사람이 읽을 수 있는 HTML (`<ins>`, `<del>`)
- **의존성**: lxml
- **평가**: HTML/XML 구조 인식 diff. 웹북(HTML) 비교에 직접 활용 가능

#### deepdiff
- **GitHub**: [seperman/deepdiff](https://github.com/seperman/deepdiff)
- **특징**: 모든 Python 객체의 딥 비교. Dict, List, Set, 커스텀 객체 지원
- **주요 기능**: `DeepDiff` (차이 계산), `DeepSearch` (검색), `DeepHash` (해시), `Delta` (패치)
- **옵션**: `ignore_order`, 타입 무시, 경로 제외, float 허용오차 등
- **평가**: 구조화된 데이터(JSON, dict) 비교에 최적. 문서 메타데이터 비교에 유용. 텍스트 비교에는 difflib이 더 적합

#### html-diff / htmltreediff (Python)
- **htmltreediff**: XML 트리 구조를 고려한 diff. `<ins>`, `<del>` 태그로 결과 출력
- **html-diff**: HTML 스니펫 비교. 트리 구조 인식
- **평가**: HTML 문서 비교 시 xmldiff의 대안

#### 라이브러리 선택 매트릭스 (Python)

| 요구사항 | 권장 라이브러리 |
|---------|--------------|
| 설치 불요, 기본 텍스트 비교 | difflib |
| HTML/XML 구조 인식 비교 | xmldiff |
| JSON/구조화 데이터 비교 | deepdiff |
| 가벼운 HTML diff 출력 | htmltreediff |

---

## 4. 방위산업/제조업 기술문서 특화 니즈

### 4.1 규격서(Spec) 버전 간 비교의 핵심 요구사항

#### 변경 추적성 (Traceability)
- 모든 변경에 대해 "누가, 언제, 왜" 기록 필수
- 양방향 추적성: 요구사항 -> 설계 -> 시험 -> 검증 전 과정에서 변경 영향 추적
- 불일치 사항 식별 및 관리 흐름도 유지 (방위사업청 체계공학 기술관리 지침)

#### 수치/규격값 변경 감지
- 허용 오차, 온도 범위, 치수 등 수치 변경은 최우선 하이라이트
- 단위 변경 감지 (mm -> inch, kg -> lb)
- 수치 변경의 영향도 자동 평가 (10% 이상 변경 시 경고 등)

#### 번호 체계 변경 추적
- 절/항/호 번호 재배열 감지 (예: 3.2.1 -> 3.3.1)
- 번호 변경과 내용 변경을 분리하여 표시
- 참조 번호의 연쇄 변경 추적 (3.2.1을 참조하는 모든 곳)

### 4.2 기술문서 특유의 비교 요구사항

#### 용어 통일 검토
- 동일 개념에 대한 용어 불일치 감지 ("파괴 시험" vs "파괴 검사")
- 용어집(glossary) 기반 일관성 검사
- 약어 사용 일관성 (첫 등장 시 풀네임+약어, 이후 약어만)

#### 표(Table) 변경 추적
- 행/열 추가/삭제/이동
- 셀 내용 변경 (특히 수치 변경)
- 표 구조 변경 (병합/분할)
- 일반 텍스트 diff로는 표 구조 변경을 인식하기 어려움 -> 구조적 diff 필요

#### 그림/도면 변경 추적
- 그림 번호/캡션 변경
- 이미지 자체의 변경은 픽셀 비교 또는 해시 비교로 감지
- 도면 참조 번호 변경의 연쇄 영향

#### 적용 규격/참조 문서 변경
- 적용 규격 목록(referenced documents) 변경 감지
- 규격 버전 변경 (KS B 1234:2020 -> KS B 1234:2023)
- 신규 규격 추가/기존 규격 삭제

### 4.3 규정 준수 검토 (Compliance Check)

#### 일반적 접근 방식
1. **요구사항 매핑**: 상위 규격의 각 요구사항이 하위 문서에서 어떻게 충족되는지 매핑
2. **적합성 매트릭스(Compliance Matrix)**: 요구사항별 충족 상태 (적합/부분적합/미적합/해당없음) 관리
3. **자동화 검사**: 필수 섹션 존재 여부, 필수 용어/문구 포함 여부, 금지 표현 사용 여부

#### 방위사업 특수 요구사항
- **형상관리(Configuration Management)**: CSCI(형상항목) 단위 문서 작성, 형상 기준선 대비 변경 추적
- **ITAR 규정**: 민감 정보 포함 여부 자동 검사, 수출 통제 대상 기술 데이터 식별
- **AS9100/ISO 9001**: 품질 관리 문서의 필수 요소 존재 확인
- **체계공학관리계획(SEMP)**: 요구사항 정의 -> 규격서 -> 검증 문서 간 추적성 유지

#### AI/LLM 활용 가능성
- 규격 조항과 구현 문서 간 의미적 매핑 (전통적 키워드 매칭의 한계 극복)
- 변경 영향도 자동 분석 ("이 수치 변경이 영향을 미치는 다른 섹션은?")
- 규격 위반 가능성 자동 탐지

### 4.4 시스템 설계 시 고려사항

#### 본 프로젝트(Smart Document Platform) 적용 방안
- **대상 문서**: HTML 웹북 (DOCX -> HTML 변환 완료 상태)
- **프론트엔드**: diff-match-patch (의존성 제로, Vanilla JS) + 자체 HTML 렌더러
- **백엔드**: difflib (표준) + xmldiff (HTML 구조 인식)
- **UI**: Side-by-side (Translator와 동일한 듀얼 패널 패턴 재사용) + Inline 모드 토글
- **동기 스크롤**: 섹션 앵커 기반 동기화 (웹북의 절/항 ID 활용)
- **단위**: 문장 단위 diff 기본, 단어 단위 하이라이트 보조
- **LLM 연동**: 변경 요약 및 영향도 분석 (RAG 파이프라인 재사용 가능)

---

## 5. 비교/검증 모드 UX 레이아웃

### 5.1 비교 모드 — 상용 서비스 레이아웃 분석

#### Draftable (가장 직관적인 레퍼런스)
```
┌─ 툴바 ──────────────────────────────────────────────────┐
│  [문서A 이름]          [문서B 이름]      [Change List ▸]  │
├──────────────────┬──────────────────┬────────────────────┤
│                  │                  │  Change List       │
│  문서 A (원본)    │  문서 B (수정본)  │  ─────────────     │
│                  │                  │  ☐ 1. 삭제 (1.1)   │
│  삭제=빨간취소선   │  추가=녹색배경    │  ☐ 2. 추가 (1.2)   │
│                  │                  │  ☐ 3. 수정 (2.1)   │
│  (동기 스크롤)    │  (동기 스크롤)    │  ...              │
│                  │                  │  [필터: 유형/태그]   │
├──────────────────┴──────────────────┴────────────────────┤
│  요약: 삽입 5, 삭제 3, 수정 12                            │
└─────────────────────────────────────────────────────────┘
```
- **3패널**: 좌(원본) + 우(수정본) + 우측 사이드바(Change List)
- **Change List 필터**: 변경 유형(삽입/삭제), 콘텐츠 유형(번호/표/목차/코멘트), 태그
- **변경점 내보내기**: Changes Report로 내보내기, 요약 페이지 옵션

#### Litera Compare (엔터프라이즈 벤치마크)
- **3패널 동기 스크롤**: 원본 / 수정본 / 레드라인(비교 결과)
- 번호가 매겨진 변경점(numbered changes), 필터링 가능
- 출력 옵션: 인터랙티브 뷰어 / 정적 레드라인 / Track Change 문서
- 듀얼 모니터 자동 감지로 추가 뷰 옵션

#### GitHub PR Diff View
- **Split/Unified 토글**: 우측 상단 토글 버튼으로 즉시 전환
- **파일별 접기/펼치기**: chevron 아이콘, Alt+클릭으로 전체 접기
- **Jump to file**: 드롭다운으로 파일 이동

#### VS Code Diff Editor
- **Side-by-side ↔ Inline**: `(...)` 메뉴에서 전환
- **미니맵**: 우측 축소 뷰, 변경점 위치를 컬러 마커로 표시
- **F7/Shift+F7**: 변경점 간 이동

### 5.2 검증 모드 — 상용 서비스 레이아웃 분석

#### Grammarly (비개발자 최적화)
```
┌─ 툴바 ──────────────────────────────────────────────────┐
│  [Goals 🎯]  [Settings ⚙]              Overall Score: 85 │
├────────────────────────────────┬─────────────────────────┤
│                                │  사이드바               │
│  문서 편집 영역                 │  ─────────────          │
│                                │  ⚠ "수동태" → 능동태    │
│  인라인 ~~~밑줄~~~              │  💡 "비행기" → "항공기"  │
│  호버 시 카드 팝업              │  ⚠ 문장이 너무 깁니다    │
│                                │  ...                   │
│  (클릭 ↔ 사이드바 양방향 연동)   │  [카테고리별 점수]       │
│                                │                        │
└────────────────────────────────┴─────────────────────────┘
```
- **핵심**: 문서 전체 + 인라인 밑줄 + 우측 사이드바 이슈 목록
- **양방향 연동**: 사이드바 항목 클릭 → 문서 내 해당 텍스트 선택, 반대도 동일
- **Goals**: Audience/Formality/Domain/Tone 드롭다운 → 적용 규칙 세트 자동 변경
- **설정**: 에디터 내 Settings 페이지에서 특정 규칙(수동태, 옥스포드 콤마 등) on/off 토글

#### Hemingway Editor (가장 단순)
```
┌─ 모드 전환 ─────────────────────────────────────────────┐
│  [Write]  [Edit]                                        │
├────────────────────────────────┬─────────────────────────┤
│                                │  통계 패널              │
│  문서 편집 영역                 │  ─────────────          │
│                                │  Readability: Grade 5   │
│  ██노랑██ = 긴 문장             │  노랑: 3건              │
│  ██빨강██ = 매우 복잡            │  빨강: 1건              │
│  ██파랑██ = 부사/약한 표현       │  파랑: 5건              │
│  ██보라██ = 간단한 대안 존재      │  보라: 2건              │
│  ██초록██ = 수동태              │  초록: 4건              │
│                                │  읽기 시간: 3분          │
└────────────────────────────────┴─────────────────────────┘
```
- **Write ↔ Edit 모드 전환**: 버튼 그룹으로 전환 — Edit에서만 하이라이트 표시
- **규칙 고정**: 설정/커스텀 없음 — 고정된 5가지 색상 코딩
- **통계 패널**: 우측에 카테고리별 발견 횟수 + 가독성 등급

#### Acrolinx (엔터프라이즈 문서 품질)
- **Sidebar**: 에디터 내 사이드바, 스코어카드(전체 점수 + 카테고리별 점수)
- **이슈 카드**: 각 이슈를 카드로 표시, 클릭 시 문서 내 하이라이트
- **Auto-advance**: 제안 수락 시 자동으로 다음 이슈로 이동
- **규칙 설정**: 별도 서버 관리 콘솔 (관리자 전용)

#### SonarQube (코드 품질 — 구조 참고)
- **대시보드**: 프로젝트 개요 (Security/Reliability/Maintainability 등급 + 수치)
- **이슈 목록**: 심각도/유형/태그별 필터링 가능한 리스트
- **코드 뷰**: 이슈 클릭 시 소스 내 인라인 마커 하이라이트
- **Quality Profile**: 별도 관리 페이지에서 규칙 세트 구성

### 5.3 핵심 질문에 대한 답변

#### Q1: 검증 모드에서 "문서 전체 + 하이라이트" vs "이슈 목록 중심" — 어느 것이 일반적?

**"문서 전체 + 인라인 하이라이트"가 압도적으로 일반적.**

| 도구 | 기본 뷰 | 이슈 목록 위치 |
|------|---------|--------------|
| Grammarly | 문서 전체 + 밑줄 | 우측 사이드바 |
| Hemingway | 문서 전체 + 색상 배경 | 우측 통계 패널 |
| Acrolinx | 문서 전체 + 하이라이트 | 사이드바 카드 |
| Vale/ESLint | 코드 전체 + squiggly 밑줄 | 하단 Problems 패널 |
| SonarQube | 코드 전체 + 인라인 마커 | 별도 이슈 목록 페이지 |

**공통 패턴**: 인라인 하이라이트(문맥 유지) + 이슈 목록 패널(전체 조망) **양방향 연동**.

#### Q2: 비교와 검증을 동시 표시하는 서비스가 있는가?

**전용 통합 UI는 발견되지 않음.** 다만 유사 패턴:
- VS Code: diff 뷰에서 ESLint squiggly 밑줄이 동시 표시 (독립 기능의 공존)
- SonarQube: PR 분석 시 "변경 코드에 대한 이슈"만 필터링 — 비교+검증 결합에 가장 가까움

**동시 표시 시 가능한 UX 패턴**:
- **레이어 중첩**: diff 하이라이트(배경색) + 검증 이슈(밑줄/보더) — 시각적 분리
- **사이드바 탭**: "변경점" 탭 / "검증 이슈" 탭 전환
- **필터 토글**: 상단 툴바에서 "변경점 표시" / "이슈 표시" 체크박스로 독립 on/off

#### Q3: 규칙 설정 화면은 별도 페이지 vs 모달/사이드바?

| 도구 유형 | 설정 방식 | 예시 |
|---------|----------|------|
| 경량 도구 | 사이드바/모달 내 인라인 설정 | Grammarly (Goals 패널, Settings 페이지) |
| 엔터프라이즈 | 별도 관리 페이지/콘솔 | Acrolinx, SonarQube |
| 개발자 도구 | 설정 파일 편집 | ESLint, Vale |

→ **우리 시스템**: 기존 admin-settings 패턴과 일관되게 **admin.html 내 별도 탭** 또는 **Compare 페이지 내 설정 모달**

### 5.4 모드 전환 UX 패턴

| 패턴 | 사용 예 | 적합 상황 |
|------|---------|----------|
| **토글 버튼** | GitHub (Split/Unified) | 2가지 상태 전환 |
| **모드 버튼 그룹** | Hemingway (Write/Edit) | 완전히 다른 UI 상태 |
| **탭** | SonarQube 대시보드 | 동시 존재하는 독립 뷰 |
| **사이드바 전환** | Grammarly | 컨텍스트 유지 + 보조 정보 변경 |

→ **우리 시스템**: 상단 툴바에 **2-버튼 토글("비교" / "검증")** — Hemingway Write/Edit 패턴

---

## 6. 규칙 관리 UI 사례

### 6.1 SonarQube — Quality Profile (가장 체계적)

- **규칙 목록**: 언어/카테고리/severity/태그로 필터링·검색
- **규칙 on/off**: 프로필 내에서 "Activate"/"Deactivate" 버튼
- **Bulk Change**: 필터링된 규칙 전체를 한번에 활성/비활성
- **Severity 커스텀**: 규칙 활성화 시 severity를 프로필별로 재지정
- **프로필 상속**: 부모 프로필 변경 → 자식에게 전파
- **내보내기**: XML로 백업/복원

### 6.2 Grammarly Business — Custom Style Rules (비개발자 최적)

- **Goals**: Audience/Formality/Domain/Tone 드롭다운 → 규칙 세트 자동 변경
- **Custom Rules**: "Add rule" → **원본 텍스트 + 대체 텍스트 + 설명** 입력
- **CSV 일괄 업로드**: Import list로 대량 규칙 추가
- **와일드카드**: `*` 지원 — "give * the green light" 같은 패턴
- **Rule Set**: 그룹 단위 관리, 조직/팀에 할당

### 6.3 Acrolinx — 3단 계층 (문서 도메인 최적)

- **Style Guide > Goal > Guideline**: 3단 계층
  - Style Guide: 콘텐츠 유형별 규칙 묶음 ("기술문서용", "마케팅용")
  - Goal: 목표 (명확성, 톤, 일관성, 정확성, 용어). Required/Recommended
  - Guideline: 개별 규칙. **Enable/Disable 라디오 버튼**
- **Terminology Manager**: 웹 UI에서 용어 사전 관리, CSV/TBX 임포트

### 6.4 Vale — YAML 기반 + Studio

- `.vale.ini` + YAML 규칙 파일 (코드 편집 필요)
- **Vale Studio**: 브라우저에서 YAML 편집 + 실시간 테스트
- 규칙 유형: `existence`(금지어), `substitution`(대체어), `occurrence`(횟수), `repetition`(반복)

### 6.5 규칙 생성 UI 패턴 종합

| 패턴 | 설명 | 비개발자 접근성 | 대표 사례 |
|------|------|---------------|----------|
| **원본/대체 텍스트** | "이것을 저것으로" 단순 치환 | **높음** | Grammarly Business |
| **드롭다운 + 폼** | 규칙 유형 선택 → 맞춤 입력 | 중상 | Adobe AEM, SonarQube |
| **조건 빌더** | AND/OR 논리 조합, 동적 행 추가 | 중 | Easy Forms, Feathery |
| **자연어 입력** | 자연어로 기술 → AI가 규칙 변환 | **높음** | (신규 트렌드) |
| **YAML/JSON 편집** | 구조화 텍스트 직접 편집 | 낮음 | Vale, ESLint |
| **정규식 입력** | 패턴 매칭 | 낮음 | Vale Studio |
| **템플릿/프리셋** | 미리 정의된 세트에서 선택+커스텀 | **높음** | SonarQube, Acrolinx |

### 6.6 우리 시스템에 적합한 규칙 관리 UI 제안

**대상 사용자**: 엔지니어 (비개발자), 관리자

**레벨 1 — 프리셋 선택 + 토글** (MVP)
```
┌─ 규칙 설정 ─────────────────────────────────────────────┐
│  프리셋: [기술문서 (기본) ▾]                               │
├─────────────────────────────────────────────────────────┤
│  📁 구조 검사                                            │
│    ☑ 필수 섹션 존재 여부 ··················· ⚠ 경고       │
│    ☑ 번호 체계 연속성 ····················· ⚠ 경고       │
│    ☐ 표/그림 캡션 존재 ··················· 💡 제안       │
│                                                         │
│  📁 용어 검사                                            │
│    ☑ 금지 용어 사용 감지 ················· ❌ 오류       │
│    ☑ 동일 개념 다른 표현 ················· ⚠ 경고       │
│    ☐ 약어 첫 등장 풀네임 ················· 💡 제안       │
│                                                         │
│  📁 가독성 검사                                          │
│    ☑ 문장 길이 제한 (80자) ··············· ⚠ 경고       │
│    ☐ 수동태 비율 ························ 💡 제안       │
│                                                         │
│  [프리셋 저장]  [내보내기 JSON]  [가져오기]               │
└─────────────────────────────────────────────────────────┘
```

**레벨 2 — 커스텀 규칙 생성** (Phase 2)
```
┌─ 규칙 추가 ─────────────────────────────────────────────┐
│  규칙 유형: [용어 치환 ▾]                                 │
│                                                         │
│  ┌─ 용어 치환 폼 ─────────────────────────────────────┐  │
│  │  원본 텍스트: [비행기          ]                    │  │
│  │  대체 텍스트: [항공기          ]                    │  │
│  │  설명:       [항공기로 통일    ]                    │  │
│  │  심각도:     [⚠ 경고 ▾]                           │  │
│  │  ☐ 대소문자 구분                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  [추가]  [CSV 일괄 업로드]                               │
└─────────────────────────────────────────────────────────┘
```

**레벨 3 — AI 기반 규칙** (Phase 3)
```
┌─ AI 규칙 추가 ──────────────────────────────────────────┐
│  규칙 유형: [AI 검토 ▾]                                  │
│                                                         │
│  검사 기준 (자연어):                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 안전/위험/경고와 관련된 내용이 변경되었는지 확인     │  │
│  └───────────────────────────────────────────────────┘  │
│  심각도: [❌ 오류 ▾]                                     │
│  라벨:   [🤖 AI 제안] (자동 부여)                        │
│                                                         │
│  [추가]                                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 7. 시스템 제안 — Compare 화면 구성

### 7.1 플랫폼 테마 일체감 원칙

Compare 시스템은 Explorer/Translator와 **시각적 일체감**을 유지해야 한다.
기존 플랫폼 테마 기준서(`memory/theme-guide.md`)의 값을 준수하며, Compare 고유의 차별점은 기능적 요소(diff 색상 등)에만 한정한다.

| 요소 | 기준 | 적용 |
|------|------|------|
| **헤더** | 60px, `linear-gradient(135deg, #001f3f, #003d7a)`, 25px/600/italic 타이틀 | 전 페이지 공통 `platform-header` 사용 |
| **폰트** | UI: 14px/400~500, 본문: 15px/400, 라벨: 13px/400~600 | 기준서 사이즈 계층 준수 |
| **색상** | `--active-color: #0066cc`, `--border-color: #dde4e8`, `--bg-gray: #f5f7fa` | CSS 변수 사용, 하드코딩 금지 |
| **radius** | sm(4px), md(6px), lg(8px), xl(12px) | 버튼: 6px, 카드/패널: 8px |
| **shadow** | sm~xl 4단계 | 패널: sm, 모달: lg |
| **트랜지션** | fast(0.15s), normal(0.2s), slow(0.3s) | 호버: 0.15s, 패널 전환: 0.3s |
| **z-index** | 기존 체계 준수 | 모달: 1000~1200, 토스트: 5000 |
| **다크 모드** | `body[data-theme="dark"]` 변수 오버라이드 | 지원 필수 (라이트/다크) |
| **스크롤바** | 기준서 커스텀 스크롤바 | 동일 적용 |
| **패널 헤더** | 10px padding, border-bottom, bg: light-gray, sticky | 좌우 패널 헤더 동일 패턴 |

**Compare 고유 색상** (diff 전용, 기존 시맨틱 색상과 구분):

| 용도 | 라이트 | 다크 | 비고 |
|------|--------|------|------|
| 추가 배경 | `#e6ffec` | `rgba(46,160,67,0.15)` | GitHub 표준 참고 |
| 삭제 배경 | `#ffeef0` | `rgba(248,81,73,0.15)` | GitHub 표준 참고 |
| 수정 배경 | `#fff8e1` | `rgba(245,158,11,0.15)` | 노랑 계열 |
| 검증 이슈 밑줄 | `--color-warning` | `--color-warning` | 기존 시맨틱 재사용 |
| 검증 오류 밑줄 | `--color-error` | `--color-error` | 기존 시맨틱 재사용 |

→ diff 색상은 CSS 변수 `--diff-added`, `--diff-deleted`, `--diff-modified`로 선언하여 다크 모드 대응.

### 7.2 비교 모드 레이아웃

```
┌─ platform-header (60px) ─────────────────────────────────────────┐
│  🔍 문서 비교  │  [비교] [검증]  │  시스템 스위처  │  user │ Logout │
├──────────────────────────────────────────────────────────────────┤
│  [문서A ▾] vs [문서B ▾]  [비교 실행]  │ ◀ 3/12 ▶ │ [유형필터▾] [⚙] │
├──────────────────┬──────────────────┬────────────────────────────┤
│  패널 헤더 A      │  패널 헤더 B      │  변경 목록                  │
│  (sticky)        │  (sticky)        │  (접기/펼치기 가능)          │
├──────────────────┼──────────────────┤                            │
│                  │                  │  📊 추가 5 삭제 3 수정 12   │
│  문서 A          │  문서 B          │  ──────────────             │
│                  │                  │  [1.1] 용어 변경            │
│  ██삭제██         │  ██추가██        │    "비행 제어" → "비행제어"  │
│                  │                  │  [2.3] 내용 추가            │
│  앵커 기반        │  앵커 기반        │    신규 요구사항 3건         │
│  동기 스크롤      │  동기 스크롤      │  [3.1] 수치 변경 ⚠         │
│                  │                  │    허용오차 ±0.1 → ±0.05   │
│                  │                  │                            │
├──────────────────┴──────────────────┴────────────────────────────┤
│  platform-footer                                                 │
└──────────────────────────────────────────────────────────────────┘
```

**구성 요소**:
- **헤더**: platform-header 공유. 모드 전환 버튼("비교" / "검증") 포함
- **서브 헤더(툴바)**: 문서 선택 드롭다운, 비교 실행 버튼, 변경점 네비게이션 (◀ N/M ▶), 필터, 설정
- **좌우 패널**: Translator 듀얼 패널과 유사한 split-pane. 리사이즈 핸들 포함
- **우측 사이드바**: 변경 목록 (Draftable Change List 패턴). 접기/펼치기 가능
- **푸터**: platform-footer 공유

### 7.3 검증 모드 레이아웃

```
┌─ platform-header (60px) ─────────────────────────────────────────┐
│  🔍 문서 비교  │  [비교] [검증]  │  시스템 스위처  │  user │ Logout │
├──────────────────────────────────────────────────────────────────┤
│  [문서 선택 ▾]  [검증 실행]  │ ◀ 2/8 ▶ │ [카테고리▾] [심각도▾] [⚙] │
├──────────────────────────────────────┬───────────────────────────┤
│                                      │  검증 결과                │
│  문서 전체 표시                       │  ─────────────            │
│                                      │  📊 스코어: 85/100       │
│  인라인 하이라이트:                    │  오류 2 · 경고 5 · 제안 1 │
│  ~~~밑줄(경고)~~~                     │  ──────────────           │
│  ═══밑줄(오류)═══                     │  📁 구조 검사             │
│                                      │  ❌ 필수 섹션 누락: 결론   │
│  (하이라이트 ↔ 사이드바 양방향 연동)    │  ⚠ 번호 3.2→3.4 건너뜀   │
│                                      │  📁 용어 검사             │
│                                      │  ⚠ "비행기" → "항공기"    │
│                                      │  ⚠ "시험" vs "검사" 혼용  │
│                                      │  📁 가독성               │
│                                      │  💡 1.3절 문장 92자       │
│                                      │                          │
├──────────────────────────────────────┴───────────────────────────┤
│  platform-footer                                                 │
└──────────────────────────────────────────────────────────────────┘
```

**구성 요소**:
- **헤더/푸터**: 비교 모드와 동일 (모드 전환 버튼 활성 상태만 다름)
- **서브 헤더(툴바)**: 문서 1개 선택, 검증 실행, 이슈 네비게이션, 카테고리/심각도 필터, 설정
- **좌측 메인**: 문서 전체 표시 + 인라인 하이라이트 (Grammarly/Hemingway 패턴)
- **우측 사이드바**: 이슈 목록 — 스코어 + 카테고리별 접이식 그룹 + 개별 이슈 카드
- **양방향 연동**: 사이드바 이슈 클릭 → 문서 내 해당 위치 스크롤+하이라이트, 역방향도 동일

### 7.4 모드 전환 시 화면 변화

| 요소 | 비교 모드 | 검증 모드 |
|------|----------|----------|
| **서브 헤더** | 문서 2개 선택 + 비교 실행 | 문서 1개 선택 + 검증 실행 |
| **메인 영역** | 좌우 split-pane (2패널) | 단일 패널 (문서 전체) |
| **사이드바** | 변경 목록 (diff 결과) | 이슈 목록 (검증 결과) |
| **하이라이트** | 배경색 (추가/삭제/수정) | 밑줄 (오류/경고/제안) |
| **네비게이션** | 변경점 이동 (◀ ▶) | 이슈 이동 (◀ ▶) |
| **필터** | 변경 유형 (추가/삭제/수정) | 카테고리 + 심각도 |

**전환 애니메이션**: `transition: all 0.3s ease` — 좌측 패널이 축소/확장되면서 자연스럽게 전환
(Translator의 패널 전환과 동일한 트랜지션 패턴 적용)

### 7.5 규칙 설정 접근 경로

```
Compare 페이지 [⚙] 버튼
    └→ 설정 모달 (오버레이)
        ├─ 프리셋 선택 드롭다운
        ├─ 카테고리별 규칙 토글 (accordion)
        ├─ [커스텀 규칙 관리] → 별도 모달/섹션
        └─ [내보내기/가져오기]

또는

admin.html > 시스템 설정 탭
    └→ "문서 검증 규칙" 섹션
        ├─ 조직 전체 기본 프리셋 설정
        ├─ 커스텀 규칙 CRUD
        └─ 규칙 세트 관리
```

- **일반 사용자**: Compare 페이지 내 설정 모달에서 규칙 on/off, 프리셋 선택
- **관리자**: admin.html에서 조직 기본 규칙, 커스텀 규칙 생성/편집, 프리셋 관리

### 7.6 Translator와의 레이아웃 비교

| 요소 | Translator | Compare 비교 모드 | Compare 검증 모드 |
|------|-----------|-------------------|-------------------|
| 좌측 | 원문 PDF | 문서 A | 문서 전체 |
| 우측 | 번역 PDF | 문서 B | 이슈 목록 사이드바 |
| 동기 스크롤 | 페이지 기반 | 앵커 기반 | N/A |
| 트리 패널 | 폴더/문서 (오버레이) | 문서 선택 (서브헤더) | 문서 선택 (서브헤더) |
| 상태 표시 | 번역 중/완료/에러 | diff 계산 중/완료 | 검증 중/완료 |

→ **공통점**: 헤더, 듀얼 패널 구조, 패널 헤더, 리사이즈 핸들
→ **차별점**: 비교 모드는 3패널(좌+우+사이드바), 검증 모드는 2패널(문서+사이드바)

### 7.7 단계별 구현 범위

#### Phase 1 (MVP)
- **비교 모드**: 좌우 split-pane + 변경점 하이라이트 + 하단 요약
- **검증 모드**: 없음 (비교만)
- **문서 소스**: Explorer 등록 HTML 문서만
- **규칙**: 없음

#### Phase 2
- **비교 모드**: + 변경 목록 사이드바, 필터링, 변경점 네비게이션
- **검증 모드**: 문서 전체 + 인라인 하이라이트 + 이슈 사이드바
- **규칙**: 내장 규칙 (구조/용어/가독성) + 프리셋 선택 + 토글 on/off
- **문서 소스**: + Word/PDF 업로드

#### Phase 3
- **비교 모드**: + LLM 의미 분석, 비교 리포트 내보내기
- **검증 모드**: + 커스텀 규칙 생성 (원본/대체 폼, CSV 업로드)
- **규칙**: + AI 기반 규칙, 규칙 세트 내보내기/가져오기
- **관리**: admin.html 통합 규칙 관리

---

## Sources

### 비교 모드 UX
- [Draftable — Side-by-side comparisons](https://help.draftable.com/hc/en-us/articles/17693327305881-Side-by-side-comparisons)
- [Draftable — Change List](https://help.draftable.com/hc/en-us/articles/32514479509785-Using-the-Redline-Change-List)
- [Litera Compare](https://www.litera.com/products/litera-compare)
- [GitHub — Introducing Split Diffs](https://github.blog/2014-09-03-introducing-split-diffs/)
- [VS Code — User Interface](https://code.visualstudio.com/docs/getstarted/userinterface)
- [Google Docs — Suggest Edits](https://support.google.com/docs/answer/6033474)
- [Apryse WebViewer — Compare Documents](https://apryse.com/blog/webviewer/compare-pdf-office-or-image-side-by-side-or-multi-tab-view)
- [syncscroll — Vanilla JS Scroll Sync](https://github.com/asvd/syncscroll)

### 검증 모드 UX
- [Grammarly — Editor User Guide](https://support.grammarly.com/hc/en-us/articles/360003474732-Grammarly-Editor-user-guide)
- [Grammarly — UI Redesign Analysis](https://designeradeeba.medium.com/rethinking-grammarly-a-ux-tale-of-grammarlys-ui-redesign-a2e917220fc7)
- [Hemingway Editor](https://hemingwayapp.com/)
- [Hemingway — Quick Start Guide](https://hemingwayapp.com/help/docs/quick-start-guide)
- [Acrolinx — Scorecard Essentials](https://docs.acrolinx.com/coreplatform/latest/en/the-sidebar/scorecard-essentials)
- [Acrolinx — The Sidebar](https://docs.acrolinx.com/acrolinxplatform/latest/en/the-sidebar)
- [SonarQube — Issues](https://docs.sonarsource.com/sonarqube-server/9.9/user-guide/issues)
- [Vale — VS Code Extension](https://marketplace.visualstudio.com/items?itemName=ChrisChinchilla.vale-vscode)

### 규칙 관리 UI
- [SonarQube — Editing Quality Profiles](https://docs.sonarsource.com/sonarqube-server/quality-standards-administration/managing-quality-profiles/editing-a-custom-quality-profile)
- [Grammarly — Create Style Rules](https://support.grammarly.com/hc/en-us/articles/360043832652-Create-style-rules)
- [Grammarly — Extended Style Rules](https://support.grammarly.com/hc/en-us/articles/27195639866509-Introducing-extended-style-rules-functionality)
- [Grammarly Business — Custom Style Guide](https://www.grammarly.com/business/styleguide)
- [Acrolinx — Enable/Disable Guidelines](https://docs.acrolinx.com/acrolinxplatform/latest/en/guidance/guidelines/enable-and-disable-guidelines)
- [Acrolinx — Terminology Manager](https://docs.acrolinx.com/acrolinxplatform/latest/en/terminology/terminology-manager)
- [Vale Studio 2.0](https://medium.com/valelint/vale-studio-2-0-cb33e1abca95)
- [LanguageTool — Rules On/Off](https://languagetool.org/insights/post/enabling-and-disabling-rules/)
- [Rule Builder Design Pattern](https://ui-patterns.com/patterns/rule-builder)

### Diff 알고리즘
- [When to Use Each Git Diff Algorithm](https://luppeng.wordpress.com/2020/10/10/when-to-use-each-of-the-git-diff-algorithms/)
- [Diff Algorithms: Myers vs Patience](https://www.filefusion.app/insights/articles/diff-algorithms-myers-patience-explained)
- [Diffing — Florian](https://florian.github.io/diffing/)

### 라이브러리
- [Google diff-match-patch](https://github.com/google/diff-match-patch)
- [jsdiff](https://github.com/kpdecker/jsdiff)
- [diff2html](https://diff2html.xyz/)
- [diffDOM](https://github.com/fiduswriter/diffDOM)
- [Python difflib](https://docs.python.org/3/library/difflib.html)
- [xmldiff](https://pypi.org/project/xmldiff/)
- [DeepDiff](https://github.com/seperman/deepdiff)

### 방위산업/기술문서
- [방위사업청 체계공학 기반 기술관리 실무지침서](http://www.det.or.kr/niabbs4/upload/userfile/20150303133711659260.pdf)
- [h2o.ai LLM-Powered Document Comparison](https://h2o.ai/LLM-Powered-Document-Comparison/)
- [AI Document Comparison for Compliance](https://codesphere.com/articles/ai-document-comparison-for-compliance)
