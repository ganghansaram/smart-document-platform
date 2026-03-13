# 문서 비교 시스템 (Compare) — 실행 계획서

> 작성일: 2026-03-12
> 최종 갱신: 2026-03-13
> 상태: Phase 3 완료 — Phase 4 대기

---

## 작업 워크플로우

각 태스크(예: "Phase 1-1 진행해") 요청 시, 아래 순서를 따른다.

1. **Plan** — `/plan`으로 해당 태스크의 상세 설계 확정 (구조, 파일, API 등). 사용자 승인 후 다음 단계.
2. **구현** — 설계대로 코드 작성. 백엔드/프론트엔드 분리 가능 시 Agent 병렬 활용.
3. **테스트** — `/test-backend`로 API 검증 (백엔드 변경 시). 프론트는 Playwright MCP 활용.
4. **UI 리뷰** — `/review-ui`로 테마 기준 준수 점검 (UI 변경 시).
5. **커밋** — 변경사항 커밋 & 푸시 (`feature/compare-system` 브랜치).
6. **체크박스 업데이트** — 이 계획서의 해당 태스크 체크박스를 `[x]`로 변경.

> 사용자는 각 태스크 완료 보고를 확인한 뒤, 다음 태스크를 요청한다.

---

## 개요

### 목적
Word/PDF 문서를 업로드하여 텍스트 차이를 비교하고, 단일 문서의 작성 규칙 준수 여부를 검증하는 시스템.

### 두 가지 모드
- **비교 모드**: 두 문서를 업로드 → 텍스트 diff → 좌우 하이라이트 시각화
- **검증 모드**: 단일 문서 업로드 → 규칙 기반 검사 → 인라인 이슈 표시

### 주요 입력
- **Phase 1**: Word(.docx), PDF
- **향후 확장 가능**: HWP/HWPX (pyhwpx), Excel (openpyxl), 기타 포맷
- 텍스트 추출 → diff → 시각화 파이프라인이 포맷 독립적이므로, 추출기만 추가하면 확장 가능

### 기술 스택
- **프론트엔드**: Vanilla JS (jsdiff — `diff.min.js` 단일 파일, 의존성 없음)
- **백엔드**: FastAPI + difflib(표준) + python-docx(설치됨) + PyMuPDF(설치됨)
- **AI**: Ollama (의미 비교, 검증 — Phase 2 이후)

---

## 테마 일체감 원칙

Compare는 Explorer/Translator와 시각적 일체감을 유지한다.
`memory/theme-guide.md`의 CSS 변수를 준수하며, Compare 고유 요소는 diff 색상에 한정.

| 요소 | 기준 |
|------|------|
| 헤더 | `platform-header` 공유 (60px, navy 그라디언트) |
| 폰트 | 기준서 사이즈 계층 (UI: 14px, 본문: 15px, 라벨: 13px) |
| 색상 | CSS 변수 사용 (`--active-color`, `--border-color` 등), 하드코딩 금지 |
| radius | sm(4px), md(6px), lg(8px), xl(12px) |
| 다크 모드 | `body[data-theme="dark"]` 변수 오버라이드 — 지원 필수 |

**Compare 고유 diff 색상** (CSS 변수로 선언):

| 용도 | 라이트 | 다크 |
|------|--------|------|
| `--diff-added` | `#e6ffec` | `rgba(46,160,67,0.15)` |
| `--diff-deleted` | `#ffeef0` | `rgba(248,81,73,0.15)` |
| `--diff-modified` | `#fff8e1` | `rgba(245,158,11,0.15)` |
| 검증 이슈 | 기존 `--color-warning`, `--color-error` 재사용 |

---

## 화면 구성

### 비교 모드

```
┌─ platform-header (60px) ────────────────────────────────────────┐
│  Document Compare  │  시스템 스위처  │  user │ Logout │ 🌓       │
├─────────────────────────────────────────────────────────────────┤
│  [동기화]  ──────  문서 두 개를 업로드하여 비교하세요  [비교][검증] │
├──────────────────┬─────────────────┤│├──────────────────┤
│ SWA_PMS.docx ×   │ 문서 B           ││  변경 목록 (접기) │
├──────────────────┼─────────────────┤│                  │
│                  │                 ││  추가 5·삭제 3    │
│  문서 A 텍스트    │  문서 B 텍스트   ││  ──────────      │
│  ██삭제██         │  ██추가██       ││  [1.1] 용어 변경  │
│                  │                 ││  [2.3] 내용 추가  │
│  (독립 스크롤)    │  (독립 스크롤)   ││  [3.1] 수치 변경  │
└──────────────────┴─────────────────┘│└──────────────────┘
                                      ↕ 리사이즈 핸들 (드래그)
```

- 푸터 없음 (도구형 화면 — Translator 동일)
- 패널 구조: `.cp-panel-header`(고정 라벨) + `.cp-panel-body`(스크롤 영역)
- 스크롤 동기화: 기본 OFF, 툴바 버튼으로 토글
- 스크롤바: Explorer §12 규격 통일 (Compare, Translator 모두 적용)
- 사이드바 리사이즈: Explorer 패턴 핸들 (4px, 드래그, min/max 제한)

### 검증 모드

```
┌─ platform-header (60px) ────────────────────────────────────────┐
│  Document Compare  │  시스템 스위처  │  user │ Logout │ 🌓       │
├─────────────────────────────────────────────────────────────────┤
│  [동기화]  ──────  문서를 업로드하여 검증하세요      [비교][검증] │
├─────────────────────────────────┬───────────────────────────────┤
│ 검증 문서                        │  검증 결과                     │
├─────────────────────────────────┤  스코어: 85/100               │
│                                 │  오류 2 · 경고 5 · 제안 1      │
│  문서 전체 표시                  │  ────────────                  │
│  인라인 하이라이트               │  [구조] 필수 섹션 누락: 결론    │
│  ~~~밑줄(경고)~~~                │  [용어] "비행기" → "항공기"     │
│  ═══밑줄(오류)═══                │  [가독성] 1.3절 문장 92자      │
│  (사이드바 ↔ 문서 양방향 연동)    │                               │
└─────────────────────────────────┴───────────────────────────────┘
```

### 모드 전환

| 요소 | 비교 모드 | 검증 모드 |
|------|----------|----------|
| 서브 헤더 | 동기화 + 힌트 + [비교][검증] | 동일 (힌트 텍스트만 변경) |
| 메인 영역 | 좌우 분할 (패널 A + B) | 패널 A만 표시 (B 숨김) |
| 사이드바 | 변경 목록 | 검증 결과 |
| 하이라이트 | 배경색 (추가/삭제/수정) | 밑줄 (오류/경고/제안) |
| 입력 방식 | 파일 업로드 / 텍스트 붙여넣기 | 동일 (패널 A만) |

전환: 툴바 우측 2-버튼 토글 (`.mode-toggle`)

---

## 실행 계획

### Phase 1: 껍데기 + 파일 업로드

> 목표: 화면이 보이고, 파일을 올려서 텍스트가 나란히 표시된다

- [x] **1-1. 페이지 생성**
  - [x] `compare.html` 생성 (모놀리식, inline JS/CSS)
  - [x] `platform-header` 연동
  - [x] 비교/검증 모드 전환 버튼 (빈 화면 전환만)
  - [x] `launcher.html`에서 Compare 카드 연결
  - [x] 다크 모드 지원

- [x] **1-2. 비교 모드 레이아웃**
  - [x] Translator 패턴 분할 뷰어 (`display: flex`, 각 패널 `flex:1; overflow:auto`)
  - [x] 패널 헤더/바디 구조 분리 (`.cp-panel-header` 고정 + `.cp-panel-body` 스크롤)
  - [x] 탭형 라벨+닫기 버튼 통합 (파일명 × 패턴)
  - [x] 패널 구분선 (`border-left: 2px solid`)
  - [x] 우측 변경 목록 사이드바 (빈 상태, 접기/펼치기)
  - [x] 사이드바 리사이즈 핸들 (Explorer 패턴: 4px, min 180px / max 700px)
  - [x] 서브 헤더 (툴바 — 동기화 버튼, 힌트, 모드 토글)
  - [x] 스크롤 동기화 (기본 OFF, 비례 기반)
  - [x] 스크롤바 스타일 통일 (Explorer §12: 얇은 썸 + 호버 확대 + SVG 화살표 + 다크)
  - [x] 푸터 제거 (도구형 화면)

- [x] **1-3. 검증 모드 레이아웃**
  - [x] 패널 B 숨김 (`.mode-verify .panel-b { display: none }`)
  - [x] 텍스트 폭 제한 (`max-width: 900px` — Explorer 콘텐츠 영역 동일, 가운데 정렬)
  - [x] 서브 헤더 타이틀/힌트 자동 변경

- [x] **1-4. 파일 업로드 + 텍스트 추출**
  - [x] 프론트: 파일 업로드 UI (드래그&드롭 + 파일 선택 버튼)
  - [x] 프론트: 텍스트 붙여넣기 모드 (DRM 환경 대응, `\n\n` 단락 분리)
  - [x] 모노크롬 placeholder UI (SVG 아이콘 + 주 버튼 + 텍스트 링크)
  - [x] 백엔드 API: `POST /api/compare/upload` (쿠키 인증)
    - Word → python-docx로 단락별 텍스트 추출
    - PDF → PyMuPDF로 페이지별 텍스트 추출
    - 파일 저장 없이 메모리에서 추출 후 폐기
  - [x] 추출된 텍스트를 패널 바디에 단락별 `<div>` 렌더링
  - [x] 파일 교체 (새 파일 업로드 시 기존 교체) + 파일 제거 (× 버튼)

### Phase 2: 텍스트 비교 핵심

> 목표: 두 문서의 차이가 하이라이트되고, 변경점을 탐색할 수 있다
> **설계 변경**: 백엔드 API(`POST /api/compare/diff`) 생략 → 프론트엔드 jsdiff 전용.
> 이유: docState가 이미 브라우저에 있음, 기술문서 규모(~1000단락)는 클라이언트 처리 가능, 폐쇄망 네트워크 의존 최소화.

- [x] **2-1. Diff 엔진**
  - [x] `js/lib/jsdiff/diff.min.js` v7.0.0 로컬 파일 추가
  - [x] 2-레벨 비교: `Diff.diffArrays` (단락 정렬) → 유사도 페어링 → `Diff.diffWords` (단어 비교)
  - [x] `diffState` 상태 관리 (changes[], currentIndex, filter, ignoreWhitespace)
  - [x] `tryRunDiff()` — 양쪽 문서 로드 시 자동 실행, 파일 제거 시 `clearDiff()`

- [x] **2-2. Diff 시각화**
  - [x] 추가(초록 border+배경) / 삭제(빨강 border+배경) / 수정(노랑 border + 단어별 span)
  - [x] Gap 정렬 (added→A에 빈칸, deleted→B에 빈칸)
  - [x] `data-change-index` 속성으로 패널 ↔ 사이드바 연결
  - [x] diff 렌더 후 scrollTop=0 초기화

- [x] **2-3. 변경점 네비게이션**
  - [x] ▲/▼ 버튼 + 인디케이터 (N/M)
  - [x] 키보드: ↑/k (이전), ↓/j (다음)
  - [x] 활성 변경점 `.diff-active` 하이라이트 (box-shadow)
  - [x] 필터 적용된 변경점만 순회

- [x] **2-4. 변경 목록 사이드바**
  - [x] 통계 배지 (+N -N ~N)
  - [x] 변경 항목 리스트 (유형 배지 + 요약 텍스트)
  - [x] 클릭 → 해당 위치 스크롤 + 활성 표시
  - [x] 이벤트 위임 (단일 click 리스너)

- [x] **2-5. 텍스트 편집 모드**
  - [x] 툴바 연필 버튼 → contenteditable 토글
  - [x] ON: diff 하이라이트 제거, `.cp-editable` 스타일
  - [x] OFF: `syncEditsToState()` → `tryRunDiff()` 재실행
  - [x] 빈 단락 보존 (후행 빈 단락만 제거)

- [x] **2-6. 필터링**
  - [x] 유형별 체크박스 (추가/삭제/수정) → 패널 + 사이드바 동시 토글
  - [x] 공백 무시 → `computeDiff()` 재실행 (정규화 적용)
  - [x] 네비게이션 카운트 자동 갱신

- [x] **2-7. 네비게이션 스크롤 개선**
  - [x] modified/deleted → Panel A 기준 스크롤 (원본 텍스트)
  - [x] added → Panel B 기준 스크롤 (A에는 gap뿐)
  - [x] 스크롤 동기화 ON이면 반대쪽 자동 추종 (기존 sync 메커니즘 활용)

- [x] **2-8. A ↔ B 교체 (Swap)**
  - [x] 툴바 ⇄ 버튼 추가
  - [x] `docState.a` ↔ `docState.b` 교환 → 라벨/패널 재렌더 → `runDiff()`

### Phase 3: 검증 모드

> 목표: 단일 문서의 규칙 준수 여부를 검사하고 이슈를 표시한다
> **설계 결정**: 비교 모드(Phase 2)는 프론트엔드 jsdiff 전용이었지만, 검증 모드는 **백엔드 API**를 사용한다.
> 이유: 규칙 로직(정규식, 번호 파싱, 용어 사전)은 Python이 자연스러우며, `data/compare-rules.json` 설정 파일 서버 관리 + 향후 Phase 4 LLM 검증과 자연스럽게 연결.
> 인라인 하이라이트: 비교 모드의 **배경색** diff와 차별화하여 검증 모드는 **물결 밑줄(underline wavy)**로 이슈 표시 — 교정/교열 도구(Grammarly, Word 맞춤법) 관례 준수.

- [x] **3-1. 검증 엔진 (백엔드)**
  - [x] 백엔드 API: `POST /api/compare/validate` (단락 배열 → 이슈 목록)
  - [x] 백엔드 API: `GET /api/compare/rules`, `PUT /api/compare/rules`
  - [x] 내장 규칙 6종 구현 (`compare_service.py`)
    - 구조: `numbering_continuity` (번호 체계 연속성), `table_caption` (표 캡션), `figure_caption` (그림 캡션)
    - 용어: `forbidden_terms` (금지 용어 감지 + 대체어 제안), `inconsistent_terms` (동일 그룹 내 혼용 감지 → 최빈 용어 통일)
    - 가독성: `sentence_length` (문장 길이 제한)
  - [x] 점수 계산: `score = max(0, 100 - (errors×10 + warnings×3 + suggestions×1))`
  - [x] 규칙 설정 파일: `data/compare-rules.json` (프리셋 2종: 기술문서/일반)

- [x] **3-2. 검증 결과 표시**
  - [x] 인라인 하이라이트: 물결 밑줄 (`text-decoration: underline wavy`) — 심각도별 색상 (오류=빨강, 경고=노랑, 제안=파랑)
  - [x] 이슈 사이드바: SVG 도넛 스코어 링 (점수 구간별 색상) + 카테고리별 접이식 그룹 (구조/용어/가독성)
  - [x] 이슈 항목: border-left 3px 심각도 색상 + 배지 + 메시지 (2줄 clamp)
  - [x] 양방향 연동: 사이드바 클릭 → 해당 단락 스크롤 + mark 활성화, 인라인 mark 클릭 → 사이드바 항목 활성화
  - [x] 자동 실행: 문서 로드 시 `tryRunValidation()`, 모드 전환 시 자동 트리거
  - [x] 스코어 링 다크 모드 대응 (`getComputedStyle`로 CSS 변수 런타임 읽기)

- [x] **3-3. 규칙 설정 UI**
  - [x] 설정 모달 (⚙ 규칙 버튼, z-index: 10000, `backdrop-filter: blur(4px)`)
  - [x] 프리셋 선택 드롭다운 (프리셋 변경 → 규칙 즉시 갱신)
  - [x] 카테고리별 규칙 행: 이름 + 심각도 셀렉트 + ON/OFF 토글
  - [x] 파라미터 편집: `sentence_length.max_chars` 숫자 입력
  - [x] 금지 용어 편집 패널: 용어→대체어 리스트 + 추가/삭제 (Enter 키, 중복 검사)
  - [x] 용어 그룹 편집 패널: 태그 스타일 표시 + 쉼표 구분 추가/삭제 (최소 2개 검증)
  - [x] "적용 + 재검증" → `PUT /api/compare/rules` 저장 → `runValidation()` 재실행
  - [x] ESC 키 닫기, 오버레이 클릭 닫기

- [x] **3-4. 이슈 네비게이션**
  - [x] ▲/▼ 버튼 + 인디케이터 (N/M), 별도 ID prefix `vd-`
  - [x] 키보드: ↑/k (이전), ↓/j (다음) — 모드에 따라 diff/validation 분기
  - [x] 심각도 필터 드롭다운 (오류/경고/제안 체크박스 토글)
  - [x] 재검증 버튼 (검증 모드 전용)

- [x] **3-5. 모드 전환 UI 토글**
  - [x] compare→verify: `clearDiff()`, diff 전용 버튼 숨김, 검증 전용 버튼 표시
  - [x] verify→compare: `clearValidation()`, 검증 전용 버튼 숨김, diff 재실행

- [x] **3-6. 품질 검증**
  - [x] 백엔드 API 기능 테스트 (8/8 통과)
  - [x] 프론트엔드 영향성 검토 (Phase 2 무결성, 이벤트 충돌, 상태 누수 — 6/6 OK)
  - [x] UX 지침 준수 분석 (테마 가이드, 접근성, 인터랙션 패턴 일관성)
  - [x] 발견 이슈 5건 수정 (리스너 누적, 다크모드 색상, ESC 닫기, blur, CSS 규칙)

### Phase 4: 비교 결과 활용

> 목표: 비교 결과를 "보는 것"에서 "처리하는 것"으로 — 수락/거절 + 내보내기
> 기존 Phase 2.5를 승격. 비교 모드의 실용 가치를 완성하는 핵심 기능.

- [ ] **4-1. 변경 수락/거절 (Accept/Reject)**
  - [ ] 각 변경 항목에 ✓(수락) / ✗(거절) 버튼
  - [ ] 수락 → B 텍스트를 최종본에 반영, 거절 → A 텍스트 유지
  - [ ] 사이드바 항목 상태 표시 (처리됨/미처리)
  - [ ] "모두 수락" / "모두 거절" 일괄 버튼
  - [ ] 처리 진행률 표시 (3/7 처리됨)

- [ ] **4-2. 병합 결과 내보내기**
  - [ ] 수락/거절 완료 후 "최종본 다운로드" 버튼
  - [ ] `.txt` 내보내기 (즉시 지원)
  - [ ] (향후) `.docx` 재생성

- [ ] **4-3. 단락 번호 표시**
  - [ ] 패널 좌측 거터에 단락 번호
  - [ ] 토글 옵션 (기본 OFF)

### Phase 5: 규칙·데이터 고도화

> 목표: 검증 모드의 실용성 확장 — 현장 운용에 필요한 편의 기능
> Phase 3에서 용어 편집 UI(추가/삭제)는 구현 완료. 여기서는 대량 데이터 관리 + 규칙 공유에 집중.

- [ ] **5-1. CSV 일괄 업로드 (용어 사전 임포트)**
  - [ ] 금지 용어 CSV 업로드 (`term,replacement` 형식)
  - [ ] 일관성 그룹 CSV 업로드 (`group_name,term1,term2,...` 형식)
  - [ ] 중복 검사 + 머지 전략 (덮어쓰기/추가만)
  - [ ] 업로드 미리보기 → 확인 후 적용

- [ ] **5-2. 규칙 세트 내보내기/가져오기 (JSON)**
  - [ ] "내보내기" → 현재 프리셋을 JSON 파일 다운로드
  - [ ] "가져오기" → JSON 파일 업로드 → 프리셋 추가/덮어쓰기
  - [ ] 팀 간 규칙 공유 시나리오 지원

- [ ] **5-3. 추가 포맷 — HWP/HWPX**
  - [ ] pyhwpx 라이브러리 연동
  - [ ] 비교 + 검증 모드 양쪽 지원

- [ ] **5-4. 추가 포맷 — Excel**
  - [ ] openpyxl 연동, 시트별 텍스트 추출
  - [ ] 셀 단위 비교 vs. 텍스트 플래튼 결정

### Phase 6: AI 연동

> 목표: Ollama 인프라 활용 — 규칙 엔진(Phase 3) + diff(Phase 2) 위에 AI 레이어
> Explorer RAG 파이프라인과 동일한 Ollama 백엔드 활용.

- [ ] **6-1. LLM 의미 비교**
  - [ ] diff 구간을 Ollama에 전달 → 변경 유형(용어 변경/수치 변경/의미 변경) 분류
  - [ ] 심각도/영향도 자동 태깅
  - [ ] 사이드바에 AI 분석 배지 표시
  - [ ] 하이브리드: jsdiff로 구간 식별 → LLM으로 의미 분석

- [ ] **6-2. AI 기반 검증 규칙**
  - [ ] 자연어로 검사 기준 입력 ("수동태 사용 지양", "약어 첫 등장 시 풀네임 병기")
  - [ ] LLM이 각 단락을 검사 → 이슈 생성
  - [ ] 기존 규칙 엔진과 통합 (rule_runners에 AI 규칙 추가)

### Phase 7: UX 고도화

> 목표: 전문 도구 수준의 UX — 필요에 따라 선택적 진행

- [ ] **7-1. 미니맵/개요 바**
  - [ ] 스크롤바 옆 컬러 마커 (변경/이슈 위치 개요)
  - [ ] 클릭 → 해당 위치 점프
  - [ ] 비교/검증 모드 양쪽 지원

- [ ] **7-2. 통합 뷰 (Unified View)**
  - [ ] 단일 패널에 inline diff 표시 (GitHub unified diff 스타일)
  - [ ] Side-by-side ↔ Unified 토글 버튼

- [ ] **7-3. 3-way 비교**
  - [ ] 공통 조상(Base) + A + B 3패널 비교
  - [ ] 충돌 구간 자동 감지 + 해결 UI

- [ ] **7-4. 비교 리포트 내보내기 (PDF)**
  - [ ] 비교 결과를 PDF 보고서로 생성 (결재/보고용)
  - [ ] 스코어, 이슈 목록, 변경 요약 포함

- [ ] **7-5. 비교 이력 관리**
  - [ ] 비교 세션 저장/불러오기
  - [ ] 동일 문서 반복 비교 시 변화 추적

---

### 알려진 기술 부채

> Phase 3 완료 시점 분석에서 발견된 개선 사항. 각 Phase 진행 시 관련 항목을 함께 처리한다.

#### 보안

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| `PUT /rules` 권한 | 높음 | `require_admin` 미적용 — 모든 로그인 사용자가 규칙 수정 가능 | **즉시** (다음 작업 시) |
| 규칙 저장 스키마 검증 | 중간 | `save_rules()`에 구조 검증 없음 — 잘못된 데이터로 JSON 파손 가능 | Phase 5 |

#### 데이터 정합성

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| DOCX `page_count: null` | 낮음 | python-docx는 페이지 수 미제공 — 프론트에서 null 처리 필요 | Phase 5-3 |
| PDF 구조 평탄화 | 참고 | 다단 PDF, 표 내부 텍스트가 선형으로 합쳐짐 — 추출 한계 | Phase 5-3 |
| 프리셋 이름 검증 | 낮음 | validate 요청의 `preset` 파라미터 미검증 (존재 여부) | Phase 5 |

#### UX 개선

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| 편집 모드 Undo/Redo | 중간 | contenteditable에 히스토리 없음 | Phase 4-1 |
| 편집 시 plain text 붙여넣기 | 중간 | 리치 텍스트 붙여넣기 시 서식 유입 | Phase 4-1 |
| 필터 드롭다운 키보드 접근성 | 낮음 | 화살표 키 탐색, 포커스 트랩 미구현 | Phase 7 |
| 아이콘 버튼 `aria-label` | 낮음 | 스크린리더 접근성 미비 | Phase 7 |

---

## 파일 구조

```
compare.html                          — 메인 페이지 (모놀리식)
js/lib/jsdiff/diff.min.js            — jsdiff 라이브러리
backend/api/compare.py               — 비교/검증 API 라우터
backend/services/compare_service.py   — 텍스트 추출, diff, 검증 로직
data/compare-rules.json              — 규칙 설정 (런타임 수정 가능)
```

## API 설계

```
POST /api/compare/upload       — 파일 업로드 → 텍스트 추출 결과 반환
POST /api/compare/validate     — 단일 텍스트 규칙 검증 → 이슈 목록 반환
GET  /api/compare/rules        — 현재 규칙 설정 조회
PUT  /api/compare/rules        — 규칙 설정 변경 (admin 권한 필요)
```

> **참고**: diff API(`POST /api/compare/diff`)는 Phase 2에서 프론트엔드 jsdiff 전용으로 결정되어 구현하지 않음.
> 비교 로직은 클라이언트 측 `js/lib/jsdiff/diff.min.js`가 전담한다.

---

## 기술 결정 근거 (조사 요약)

### 채택한 기술

| 결정 | 선택 | 근거 |
|------|------|------|
| JS diff 라이브러리 | **jsdiff** | 의존성 없음, 다양한 granularity (단어/문장/라인), npm 주간 59.6M 다운로드 |
| Python diff | **difflib** (표준) | 추가 설치 불필요, 기술문서에 충분 |
| Word 추출 | **python-docx** | 이미 설치됨, 순수 Python |
| PDF 추출 | **PyMuPDF** | 이미 설치됨, 속도 빠름, 좌표 정보 제공 |
| 비교 단위 | **문장 단위 diff + 단어 단위 하이라이트** | 기술문서에 최적 균형 |
| UI 패턴 | **Side-by-side + 변경 목록 사이드바** | 업계 표준 (Draftable 패턴) |
| 검증 UI | **문서 전체 + 인라인 하이라이트 + 이슈 사이드바** | 업계 표준 (Grammarly 패턴) |
| 모드 전환 | **2-버튼 토글** | Hemingway Write/Edit 패턴 |
| 규칙 관리 | **프리셋 + 토글 + 설정 모달** | SonarQube/Grammarly 하이브리드 |

### 참고한 서비스
- **Draftable** — 비교 UI 레퍼런스 (side-by-side + change list)
- **Grammarly** — 검증 UI 레퍼런스 (인라인 하이라이트 + 사이드바 이슈)
- **Hemingway** — 모드 전환 패턴 (Write/Edit 토글)
- **SonarQube** — 규칙 관리 UI (Quality Profile, 프리셋, 토글)
- **Acrolinx** — 문서 품질 스코어카드, 3단 규칙 계층
- **Vale** — 규칙 유형 참고 (existence, substitution, occurrence)

### 상세 조사 자료
- [Draftable — Side-by-side comparisons](https://help.draftable.com/hc/en-us/articles/17693327305881)
- [Grammarly — Editor User Guide](https://support.grammarly.com/hc/en-us/articles/360003474732)
- [SonarQube — Quality Profiles](https://docs.sonarsource.com/sonarqube-server/quality-standards-administration/managing-quality-profiles/editing-a-custom-quality-profile)
- [Google diff-match-patch](https://github.com/google/diff-match-patch)
- [jsdiff](https://github.com/kpdecker/jsdiff)
- [diff2html](https://diff2html.xyz/)
- [Python difflib](https://docs.python.org/3/library/difflib.html)
- [xmldiff](https://pypi.org/project/xmldiff/)
- [When to Use Each Git Diff Algorithm](https://luppeng.wordpress.com/2020/10/10/when-to-use-each-of-the-git-diff-algorithms/)
- [h2o.ai LLM-Powered Document Comparison](https://h2o.ai/LLM-Powered-Document-Comparison/)
- [Acrolinx — Enable/Disable Guidelines](https://docs.acrolinx.com/acrolinxplatform/latest/en/guidance/guidelines/enable-and-disable-guidelines)
- [Grammarly — Create Style Rules](https://support.grammarly.com/hc/en-us/articles/360043832652)
- [Rule Builder Design Pattern](https://ui-patterns.com/patterns/rule-builder)
