# 문서 비교 시스템 (Compare) — 실행 계획서

> 작성일: 2026-03-12
> 최종 갱신: 2026-03-15
> 상태: Phase 1~5 핵심 완료 / Phase 6 검토 예정 / Phase 7 재배치 (5-3,5-4 통합 + 우선순위 정렬)

---

## 작업 워크플로우

각 태스크(예: "Phase 1-1 진행해") 요청 시, 아래 순서를 따른다.

1. **Plan** — `/plan`으로 해당 태스크의 상세 설계 확정 (구조, 파일, API 등). 사용자 승인 후 다음 단계.
2. **구현** — 설계대로 코드 작성. 백엔드/프론트엔드 분리 가능 시 Agent 병렬 활용.
3. **테스트** — `/test-backend`로 API 검증 (백엔드 변경 시). 프론트는 Playwright MCP 활용.
4. **UI 리뷰** — `/review-ui`로 테마 기준 준수 점검 (UI 변경 시).
5. **커밋** — 변경사항 커밋 & 푸시 (`feature/compare-system` 브랜치).
6. **체크박스 업데이트** — 이 계획서의 해당 태스크 체크박스를 ✅로 변경.

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

**Compare 고유 diff 색상** (`tokens.css`에 정의, 다크모드 자동 전환):

| 용도 | 토큰 | 라이트 | 다크 |
|------|------|--------|------|
| 추가 단락 배경 | `--diff-added` | `#e6ffec` | `rgba(46,160,67,0.15)` |
| 삭제 단락 배경 | `--diff-deleted` | `#fce4e4` | `rgba(248,81,73,0.25)` |
| 수정 단락 배경 | `--diff-modified` | `#fef3cd` | `rgba(245,158,11,0.25)` |
| 추가 텍스트/배지 | `--diff-added-text` | `#1a7f37` | `#3fb950` |
| 삭제 텍스트/배지 | `--diff-deleted-text` | `#cf222e` | `#f85149` |
| 수정 텍스트/배지 | `--diff-modified-text` | `#9a6700` | `#d29922` |
| 추가 테두리 | `--diff-added-border` | `#2ea043` | `#3fb950` |
| 삭제 테두리 | `--diff-deleted-border` | `#f85149` | `#f85149` |
| 수정 테두리 | `--diff-modified-border` | `#f59e0b` | `#d29922` |
| 추가 단어 하이라이트 | `--diff-added-word` | `#86efac` | `rgba(46,160,67,0.4)` |
| 삭제 단어 하이라이트 | `--diff-deleted-word` | `#fca5a5` | `rgba(248,81,73,0.4)` |
| 검증 이슈 | 기존 `--color-warning`, `--color-error` 재사용 | | |

> 2단계 diff 색상 체계: 단락 배경(연한) + 단어 배경(진한) — GitHub 스타일.
> compare.css에서 하드코딩 금지, 반드시 위 토큰 참조.

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

- ✅ **1-1. 페이지 생성**
  - ✅ `compare.html` 생성 (모놀리식, inline JS/CSS)
  - ✅ `platform-header` 연동
  - ✅ 비교/검증 모드 전환 버튼 (빈 화면 전환만)
  - ✅ `launcher.html`에서 Compare 카드 연결
  - ✅ 다크 모드 지원

- ✅ **1-2. 비교 모드 레이아웃**
  - ✅ Translator 패턴 분할 뷰어 (`display: flex`, 각 패널 `flex:1; overflow:auto`)
  - ✅ 패널 헤더/바디 구조 분리 (`.cp-panel-header` 고정 + `.cp-panel-body` 스크롤)
  - ✅ 탭형 라벨+닫기 버튼 통합 (파일명 × 패턴)
  - ✅ 패널 구분선 (`border-left: 2px solid`)
  - ✅ 우측 변경 목록 사이드바 (빈 상태, 접기/펼치기)
  - ✅ 사이드바 리사이즈 핸들 (Explorer 패턴: 4px, min 180px / max 700px)
  - ✅ 서브 헤더 (툴바 — 동기화 버튼, 힌트, 모드 토글)
  - ✅ 스크롤 동기화 (기본 OFF, 비례 기반)
  - ✅ 스크롤바 스타일 통일 (Explorer §12: 얇은 썸 + 호버 확대 + SVG 화살표 + 다크)
  - ✅ 푸터 제거 (도구형 화면)

- ✅ **1-3. 검증 모드 레이아웃**
  - ✅ 패널 B 숨김 (`.mode-verify .panel-b { display: none }`)
  - ✅ 텍스트 폭 제한 (`max-width: 900px` — Explorer 콘텐츠 영역 동일, 가운데 정렬)
  - ✅ 서브 헤더 타이틀/힌트 자동 변경

- ✅ **1-4. 파일 업로드 + 텍스트 추출**
  - ✅ 프론트: 파일 업로드 UI (드래그&드롭 + 파일 선택 버튼)
  - ✅ 프론트: 텍스트 붙여넣기 모드 (DRM 환경 대응, `\n\n` 단락 분리)
  - ✅ 모노크롬 placeholder UI (SVG 아이콘 + 주 버튼 + 텍스트 링크)
  - ✅ 백엔드 API: `POST /api/compare/upload` (쿠키 인증)
    - Word → python-docx로 단락별 텍스트 추출
    - PDF → PyMuPDF로 페이지별 텍스트 추출
    - 파일 저장 없이 메모리에서 추출 후 폐기
  - ✅ 추출된 텍스트를 패널 바디에 단락별 `<div>` 렌더링
  - ✅ 파일 교체 (새 파일 업로드 시 기존 교체) + 파일 제거 (× 버튼)

### Phase 2: 텍스트 비교 핵심

> 목표: 두 문서의 차이가 하이라이트되고, 변경점을 탐색할 수 있다
> **설계 변경**: 백엔드 API(`POST /api/compare/diff`) 생략 → 프론트엔드 jsdiff 전용.
> 이유: docState가 이미 브라우저에 있음, 기술문서 규모(~1000단락)는 클라이언트 처리 가능, 폐쇄망 네트워크 의존 최소화.

- ✅ **2-1. Diff 엔진**
  - ✅ `js/lib/jsdiff/diff.min.js` v7.0.0 로컬 파일 추가
  - ✅ 2-레벨 비교: `Diff.diffArrays` (단락 정렬) → 유사도 페어링 → `Diff.diffWords` (단어 비교)
  - ✅ `diffState` 상태 관리 (changes[], currentIndex, filter, ignoreWhitespace)
  - ✅ `tryRunDiff()` — 양쪽 문서 로드 시 자동 실행, 파일 제거 시 `clearDiff()`

- ✅ **2-2. Diff 시각화**
  - ✅ 추가(초록 border+배경) / 삭제(빨강 border+배경) / 수정(노랑 border + 단어별 span)
  - ✅ Gap 정렬 (added→A에 빈칸, deleted→B에 빈칸)
  - ✅ `data-change-index` 속성으로 패널 ↔ 사이드바 연결
  - ✅ diff 렌더 후 scrollTop=0 초기화

- ✅ **2-3. 변경점 네비게이션**
  - ✅ ▲/▼ 버튼 + 인디케이터 (N/M)
  - ✅ 키보드: ↑/k (이전), ↓/j (다음)
  - ✅ 활성 변경점 `.diff-active` 하이라이트 (box-shadow)
  - ✅ 필터 적용된 변경점만 순회

- ✅ **2-4. 변경 목록 사이드바**
  - ✅ 통계 배지 (+N -N ~N)
  - ✅ 변경 항목 리스트 (유형 배지 + 요약 텍스트)
  - ✅ 클릭 → 해당 위치 스크롤 + 활성 표시
  - ✅ 이벤트 위임 (단일 click 리스너)

- ✅ **2-5. 텍스트 편집 모드**
  - ✅ 툴바 연필 버튼 → contenteditable 토글
  - ✅ ON: diff 하이라이트 제거, `.cp-editable` 스타일
  - ✅ OFF: `syncEditsToState()` → `tryRunDiff()` 재실행
  - ✅ 빈 단락 보존 (후행 빈 단락만 제거)

- ✅ **2-6. 필터링**
  - ✅ 유형별 체크박스 (추가/삭제/수정) → 패널 + 사이드바 동시 토글
  - ✅ 공백 무시 → `computeDiff()` 재실행 (정규화 적용)
  - ✅ 네비게이션 카운트 자동 갱신

- ✅ **2-7. 네비게이션 스크롤 개선**
  - ✅ modified/deleted → Panel A 기준 스크롤 (원본 텍스트)
  - ✅ added → Panel B 기준 스크롤 (A에는 gap뿐)
  - ✅ 스크롤 동기화 ON이면 반대쪽 자동 추종 (기존 sync 메커니즘 활용)

- ✅ **2-8. A ↔ B 교체 (Swap)**
  - ✅ 툴바 ⇄ 버튼 추가
  - ✅ `docState.a` ↔ `docState.b` 교환 → 라벨/패널 재렌더 → `runDiff()`

### Phase 3: 검증 모드

> 목표: 단일 문서의 규칙 준수 여부를 검사하고 이슈를 표시한다
> **설계 결정**: 비교 모드(Phase 2)는 프론트엔드 jsdiff 전용이었지만, 검증 모드는 **백엔드 API**를 사용한다.
> 이유: 규칙 로직(정규식, 번호 파싱, 용어 사전)은 Python이 자연스러우며, `data/compare-rules.json` 설정 파일 서버 관리 + 향후 Phase 4 LLM 검증과 자연스럽게 연결.
> 인라인 하이라이트: 비교 모드의 **배경색** diff와 차별화하여 검증 모드는 **물결 밑줄(underline wavy)**로 이슈 표시 — 교정/교열 도구(Grammarly, Word 맞춤법) 관례 준수.

- ✅ **3-1. 검증 엔진 (백엔드)**
  - ✅ 백엔드 API: `POST /api/compare/validate` (단락 배열 → 이슈 목록)
  - ✅ 백엔드 API: `GET /api/compare/rules`, `PUT /api/compare/rules`
  - ✅ 내장 규칙 6종 구현 (`compare_service.py`)
    - 구조: `numbering_continuity` (번호 체계 연속성), `table_caption` (표 캡션), `figure_caption` (그림 캡션)
    - 용어: `forbidden_terms` (금지 용어 감지 + 대체어 제안), `inconsistent_terms` (동일 그룹 내 혼용 감지 → 최빈 용어 통일)
    - 가독성: `sentence_length` (문장 길이 제한)
  - ✅ 점수 계산: `score = max(0, 100 - (errors×10 + warnings×3 + suggestions×1))`
  - ✅ 규칙 설정 파일: `data/compare-rules.json` (프리셋 2종: 기술문서/일반)

- ✅ **3-2. 검증 결과 표시**
  - ✅ 인라인 하이라이트: 물결 밑줄 (`text-decoration: underline wavy`) — 심각도별 색상 (오류=빨강, 경고=노랑, 제안=파랑)
  - ✅ 이슈 사이드바: SVG 도넛 스코어 링 (점수 구간별 색상) + 카테고리별 접이식 그룹 (구조/용어/가독성)
  - ✅ 이슈 항목: border-left 3px 심각도 색상 + 배지 + 메시지 (2줄 clamp)
  - ✅ 양방향 연동: 사이드바 클릭 → 해당 단락 스크롤 + mark 활성화, 인라인 mark 클릭 → 사이드바 항목 활성화
  - ✅ 자동 실행: 문서 로드 시 `tryRunValidation()`, 모드 전환 시 자동 트리거
  - ✅ 스코어 링 다크 모드 대응 (`getComputedStyle`로 CSS 변수 런타임 읽기)

- ✅ **3-3. 규칙 설정 UI**
  - ✅ 설정 모달 (⚙ 규칙 버튼, z-index: 10000, `backdrop-filter: blur(4px)`)
  - ✅ 프리셋 선택 드롭다운 (프리셋 변경 → 규칙 즉시 갱신)
  - ✅ 카테고리별 규칙 행: 이름 + 심각도 셀렉트 + ON/OFF 토글
  - ✅ 파라미터 편집: `sentence_length.max_chars` 숫자 입력
  - ✅ 금지 용어 편집 패널: 용어→대체어 리스트 + 추가/삭제 (Enter 키, 중복 검사)
  - ✅ 용어 그룹 편집 패널: 태그 스타일 표시 + 쉼표 구분 추가/삭제 (최소 2개 검증)
  - ✅ "적용 + 재검증" → `PUT /api/compare/rules` 저장 → `runValidation()` 재실행
  - ✅ ESC 키 닫기, 오버레이 클릭 닫기

- ✅ **3-4. 이슈 네비게이션**
  - ✅ ▲/▼ 버튼 + 인디케이터 (N/M), 별도 ID prefix `vd-`
  - ✅ 키보드: ↑/k (이전), ↓/j (다음) — 모드에 따라 diff/validation 분기
  - ✅ 심각도 필터 드롭다운 (오류/경고/제안 체크박스 토글)
  - ✅ 재검증 버튼 (검증 모드 전용)

- ✅ **3-5. 모드 전환 UI 토글**
  - ✅ compare→verify: `clearDiff()`, diff 전용 버튼 숨김, 검증 전용 버튼 표시
  - ✅ verify→compare: `clearValidation()`, 검증 전용 버튼 숨김, diff 재실행

- ✅ **3-6. 품질 검증**
  - ✅ 백엔드 API 기능 테스트 (8/8 통과)
  - ✅ 프론트엔드 영향성 검토 (Phase 2 무결성, 이벤트 충돌, 상태 누수 — 6/6 OK)
  - ✅ UX 지침 준수 분석 (테마 가이드, 접근성, 인터랙션 패턴 일관성)
  - ✅ 발견 이슈 5건 수정 (리스너 누적, 다크모드 색상, ESC 닫기, blur, CSS 규칙)

### Phase 4: 비교 결과 활용

> 목표: 비교 결과를 "보는 것"에서 "처리하는 것"으로 — 수락/거절 + 내보내기
> 기존 Phase 2.5를 승격. 비교 모드의 실용 가치를 완성하는 핵심 기능.

- ✅ **4-0. 선행 수정 (기술 부채)**
  - ✅ `PUT /api/compare/rules` 권한: `get_current_user` → `require_admin` (compare.py:87, 1줄)
  - ✅ 편집 모드 plain text 붙여넣기: contenteditable 영역에 `paste` 이벤트 핸들러 추가 (`e.preventDefault()` → `getData('text/plain')` → `insertText`)
  > Undo/Redo는 브라우저 네이티브 `Ctrl+Z`가 contenteditable에서 기본 작동하므로 별도 구현 불필요. 기술 부채에서 제거.

- ✅ **4-1. 변경 수락/거절 (Accept/Reject)**
  - ✅ `diffState.decisions[]` 배열 추가 (`null` → `'accepted'` / `'rejected'`, 재클릭 시 `null`로 토글)
  - ✅ 사이드바 항목에 ✓(수락) / ✗(거절) `.btn-icon-sm` 버튼 추가 (`.cp-change-actions` 영역)
  - ✅ 수락 → B 텍스트를 최종본에 반영, 거절 → A 텍스트 유지, 미처리 → A 유지
  - ✅ 처리된 항목 시각 피드백: 사이드바 배지+텍스트 흐림(`opacity:0.45`) + ✓/✗ 버튼만 선명 유지, 패널 `opacity:0.5` (유형 border 색상 유지)
  - ✅ 사이드바 헤더에 "✓ 전체" / "✗ 전체" / "↺" 일괄 버튼
  - ✅ 진행률 표시: 사이드바 통계 영역에 `N/M 처리`
  - ✅ 편집 모드와의 충돌 방지: `editMode === true`일 때 `setDecision()` 무시
  - ✅ 키보드 단축키: 활성 변경점에서 `Enter`(수락), `Delete`(거절)

- ✅ **4-2. 병합 결과 내보내기**
  - ✅ 툴바에 "내보내기" 버튼 (diff 존재 시 표시, `.scroll-sync-btn` 패턴)
  - ✅ 병합 로직: `buildChangeOrder()` 재활용 → accepted=B텍스트, rejected/null=A텍스트, 변경 없는 단락=원본
  - ✅ 미처리 항목 있을 경우 `modal.css` 확인 다이얼로그: "미처리 N건은 원본(A)으로 유지됩니다"
  - ✅ `.txt` 내보내기 (프론트엔드 Blob → `<a download>`, 백엔드 불필요)
  - ⬜ (향후) `.docx` 재생성

- ✅ **4-3. 단락 번호 표시**
  - ✅ 패널 좌측 거터에 단락 번호 (CSS `::before` + counter, gap 단락은 번호 건너뜀)
  - ✅ 툴바 토글 버튼 (기본 OFF, `.scroll-sync-btn` 패턴)
  - ✅ 비교/검증 모드 양쪽 지원

#### Phase 4 후속: UX 개선 및 디자인 토큰 정리

- ✅ diff 단락 배경색 강화 (`--diff-deleted`, `--diff-modified` 값 조정)
- ✅ 단어 수준 하이라이트 토큰 신설 (`--diff-added-word`, `--diff-deleted-word`)
- ✅ 사이드바 결정 상태 구분 개선 — 배지+텍스트 흐림, ✓/✗ 버튼만 선명 유지
- ✅ 본문 결정 피드백 — border-left는 유형 색상 유지, opacity만 적용
- ✅ 사이드바 힌트 텍스트 + localStorage dismiss
- ✅ 내보내기 버튼 라벨 명확화 ("최종본 저장")
- ✅ compare.css 하드코딩 31곳 → diff 토큰 치환, 다크모드 오버라이드 18줄 삭제
- ✅ `--diff-modified-border` 토큰 신설 (tokens.css)
- ✅ theme-guide.md §1.3 Diff 색상 섹션 추가

#### Phase 5 후속: 검증 모드 UX 개선 (e828481)

- ✅ **하이라이트 렌더링 charMap 재작성** — 문장길이(suggestion)와 용어(warning) 이슈가 같은 단락에 겹칠 때 용어 마크가 누락되던 버그 수정. charMap 방식으로 짧은 이슈에 우선 점유권 부여
- ✅ **검증 항목 클릭 → 스크롤 이동 수정** — `offsetTop` 기반에서 `getBoundingClientRect()` 기반으로 변경. 비교 모드 diff 네비게이션도 동일 수정
- ✅ **하이라이트 severity별 배경색 분기** — 기존: 단일 `--color-info` 색상 → 변경: error=빨강, warning=주황, suggestion=파랑 (사이드바 배지 색상과 일관)
- ✅ **하이라이트 강도 증가** — Light hover 12%/active 25%, Dark hover 18%/active 35% (`color-mix()` 기반, 토큰 참조)
- ✅ **다크모드 캔버스 배경 하드코딩 제거** — compare.css `#0d0d12` → `var(--light-gray)`, translator.css 동일
- ✅ **alert → showToast 전환** — 업로드 오류, 규칙 저장 등 6곳 (toast.css 링크 추가)
- ✅ **compare-rules.json 프리셋 데이터 보강** — 금지 용어 15종, 일관성 그룹 8종 기본 내장
- ✅ SWA_PMS.docx 실문서 테스트 — 65건 이슈 전부 마크 생성(77 span), 용어·가독성 항목 클릭 시 스크롤 이동 정상 확인

### Phase 5: 규칙·데이터 고도화

> 목표: 검증 모드의 실용성 확장 — 현장 운용에 필요한 편의 기능
> Phase 3에서 용어 편집 UI(추가/삭제)는 구현 완료. 여기서는 대량 데이터 관리 + 규칙 공유에 집중.
>
> **설계 결정 (2026-03-14)**:
> - **규칙 관리 범위**: 관리자 공유 설정 (per-user 아님). `PUT /compare/rules`는 `require_admin` 적용 완료.
> - **CSV 업로드 UI**: B안 (심플 파일 버튼) — 기존 규칙 모달 편집 패널 내 `<input type="file">` 버튼 추가
> - **미리보기 테이블**: 기존 편집 패널 인라인 스타일 (전용 모달 없음)
> - **머지 전략**: HTML `<input type="radio">` 2개 (추가만/덮어쓰기) — 커스텀 컴포넌트 불필요
> - **우선순위**: 5-1 + 5-2 먼저 진행, 5-3/5-4 (HWP/Excel) 별도 판단 후 진행

- ✅ **5-1. CSV 일괄 업로드 (용어 사전 임포트)** ✅ (e828481)
  - ✅ 금지 용어 CSV 업로드 (`term,replacement` 형식)
    - 규칙 모달 금지 용어 편집 패널 하단에 "CSV 가져오기" 버튼 + `<input type="file">`
  - ✅ 일관성 그룹 CSV 업로드 (`group_name,term1,term2,...` 형식)
    - 동일 패턴: 일관성 그룹 편집 패널 하단에 "CSV 가져오기" 버튼
  - ✅ 업로드 미리보기 테이블 (인라인, 편집 패널 내)
    - 파싱 결과를 `<table>` 로 표시, 기존 테마 스타일 적용
    - "적용" 클릭 시 반영, "취소" 시 폐기
  - ✅ 머지 전략 선택 (radio 2개: "기존 데이터에 추가" / "기존 데이터 대체")
    - 추가: 중복 term은 건너뜀 + 토스트로 건수 알림
    - 대체: 기존 목록을 CSV 내용으로 교체
  - ✅ 중복 검사 + 검증 (빈 행 무시, term 필수, 헤더 행 자동 감지)
  - ✅ **기본 샘플 데이터**: `compare-rules.json`에 기술문서 프리셋 기본 내장 (금지 용어 15종 + 일관성 그룹 8종)
  - ✅ CSV 템플릿 다운로드 링크 (BOM-prefixed UTF-8 CSV)

- ✅ **5-2. 규칙 세트 내보내기/가져오기 (JSON)** ✅ (e828481)
  - ✅ "내보내기" → 규칙 모달 헤더에 ↓ 아이콘 버튼, `Blob` + `<a download>` 패턴
  - ✅ "가져오기" → 규칙 모달 헤더에 ↑ 아이콘 버튼, `<input type="file" accept=".json">`
  - ✅ 스키마 검증 (`presets` 존재 여부 + 각 프리셋 `rules` 구조 확인)
  - ✅ 스키마 불일치 시 토스트 오류 메시지
  - ✅ 팀 간 규칙 공유 시나리오 지원

- ~~5-3, 5-4~~ → **Phase 7로 이동** (포맷 확장은 핵심 기능 완료 후 고도화 성격)

### Phase 6: AI 의미 비교

> 목표: jsdiff(텍스트 diff) 위에 LLM 레이어를 얹어 **"뭐가 바뀌었는지"에서 "왜/얼마나 중요한 변경인지"**로 확장
> Explorer RAG 파이프라인과 동일한 Ollama 백엔드 활용.
>
> **시장 조사 근거 (2026-03-15)**:
> - 업계 표준 아키텍처: 빠른 diff 즉시 표시 → AI 분류는 비동기 오버레이 (Litera+Lito, Diffchecker, BlackBoiler 등)
> - 전체 문서를 LLM에 보내는 제품은 없음 — diff 결과(변경 구간)만 LLM에 전달
> - fda-guidance-diff (FDA 규제문서 비교)의 3단계 파이프라인이 가장 유사한 레퍼런스:
>   (1) 텍스트 추출+청킹 → (2) BM25 정렬 (MRR 0.915) → (3) Gemini Flash 분류 (정확도 90~100%)
> - 한국어 기술문서 의미비교 특화 도구는 시장에 없음 → 차별화 포인트
> - "AI 피로감" 주의: 사용자는 AI 기능 자체보다 측정 가능한 시간 절감을 원함 (Draftable CEO)
>
> **설계 결정**:
> - 텍스트 diff는 현행 유지 (jsdiff, 즉시, 클라이언트)
> - AI 분석은 **온디맨드** (사용자가 "AI 분석" 버튼 클릭 시)
> - 변경 구간만 Ollama에 전송 (전체 문서 X)
> - 분류 태그를 사이드바 배지에 **점진 추가** (Translator 페이지별 번역과 동일 패턴)

#### 변경 유형 분류 체계 (fda-guidance-diff 참고, 기술문서 도메인 적응)

| 태그 | 의미 | 아이콘/색상 |
|------|------|-----------|
| EDITORIAL | 편집상 변경 (오타, 서식, 용어 통일) | 회색 |
| CLARIFICATION | 표현 명확화, 의미 동일 | 파랑 |
| STRICTER | 요구사항/기준 강화 | 빨강 |
| MORE_LENIENT | 요구사항/기준 완화 | 주황 |
| EXPANDED | 범위/내용 확대 | 초록 |
| RESTRUCTURED | 구조 재배치, 의미 동일 | 회색 |
| NUMERIC | 수치/단위 변경 | 주황 |

- ⬜ **6-1. AI 의미 분류 (비교 모드)**
  - ⬜ 백엔드 API: `POST /api/compare/ai-classify` — diff 변경 구간 배열 → 분류 태그 배열
    - 입력: `{ changes: [{ index, type, text_a, text_b }] }`
    - 출력: `{ classifications: [{ index, tag, confidence, explanation }] }`
    - Ollama 호출: 변경 구간을 배치로 묶어 한 번에 전송 (구간당 개별 호출 X)
  - ⬜ 프론트엔드: 비교 모드 툴바에 "AI 분석" 버튼 (diff 존재 시 활성화)
    - 클릭 → 버튼 스피너 → 백엔드 호출 → 완료 시 사이드바 배지 업데이트
    - 사이드바 변경 항목에 분류 태그 배지 추가 (기존 유형 배지 옆)
    - 태그 클릭 시 explanation 툴팁/팝오버
  - ⬜ 분류 결과 필터링: 기존 유형 필터에 분류 태그 필터 추가
  - ⬜ 분류 결과를 내보내기(txt)에 포함 (선택 옵션)

- ⬜ **6-2. AI 변경 요약 (비교 모드)**
  - ⬜ 6-1 분류 완료 후, 전체 변경사항 요약문 생성
    - "이 개정에서 요구사항 강화 3건, 수치 변경 2건, 편집 변경 15건이 감지되었습니다"
    - 사이드바 상단 또는 별도 패널에 표시
  - ⬜ 요약문을 리포트 내보내기에 포함

- ⬜ **6-3. AI 기반 검증 규칙 (검증 모드)**
  - ⬜ 자연어로 검사 기준 입력 ("수동태 사용 지양", "약어 첫 등장 시 풀네임 병기")
  - ⬜ 백엔드 API: `POST /api/compare/ai-validate` — 단락 배열 + 자연어 규칙 → 이슈 목록
  - ⬜ LLM이 각 단락을 검사 → 기존 규칙 엔진 이슈와 병합 표시
  - ⬜ 규칙 모달에 "AI 규칙" 탭/섹션 추가 (자유 텍스트 입력)

#### Phase 6 기술 고려사항

| 항목 | 결정 |
|------|------|
| LLM | Ollama 로컬 (폐쇄망 호환). 모델: Explorer RAG와 동일 |
| 배치 전략 | 변경 구간 N개를 하나의 프롬프트에 묶어 1회 호출 (N≤20), 20건 초과 시 분할 |
| 타임아웃 | 60초 (Translator 페이지 번역 300초보다 짧게 — diff 구간은 짧은 텍스트) |
| 캐싱 | 동일 diff 결과에 대한 재분석 방지 (해시 기반) |
| 폴백 | Ollama 미응답 시 "AI 분석 실패" 토스트, 기존 diff는 정상 유지 |
| 프롬프트 | 한국어 기술문서 도메인 특화 (항공/방산 용어, 요구사항 강화/완화 판별) |

#### Phase 6 참고 시스템 조사 요약

| 제품 | 접근 방식 | 속도 | 시장 위치 |
|------|----------|------|----------|
| **Draftable** | 전통 diff 전용 (AI 없음) | 수 초 | 900+ 법률사 |
| **Litera Compare + Lito** | 전통 diff + AI 에이전트(요약/위험분석) | diff 즉시, AI 별도 | 법률 업계 72% 점유 |
| **Diffchecker Pro** | 텍스트 diff + "AI로 요약" 버튼 | diff 즉시, AI 수 초 | 일반 사용자 대상 |
| **BlackBoiler** | Word Track Changes + AI 마크업 | NDA 2분, 복잡 계약 2시간 | 계약 자동화 |
| **Spellbook** | GPT-5/Claude 기반 계약 분석 | 실시간 Word 애드인 | 4000+ 법률팀 |
| **Luminance** | 멀티모델 AI, 1000+ 조항 자동 식별 | 40% 시간 절감 | 기업 법무 |
| **fda-guidance-diff** ★ | 3단계 (추출→BM25→Gemini Flash 분류) | 배치 | FDA 규제문서 특화 |
| **SemanticDiff** | reflow 내성 PDF diff + LLM 검증 | 배치 | 학술/기술 논문 |
| **redline-summarizer** | Claude API 기반, 교통신호 위험등급 | 배치 | 계약 비교 (오픈소스) |

> ★ fda-guidance-diff의 분류 체계(8종 태그)와 3단계 파이프라인이 본 시스템에 가장 적합한 레퍼런스.
> 차별화: 한국어 기술문서(항공/방산) 도메인 특화 + Ollama 로컬 실행(폐쇄망) — 시장 공백 영역.

### Phase 7: 고도화

> 목표: 전문 도구 수준으로 확장 — 우선순위별 선택 진행
> Phase 5 잔여 포맷 확장(HWP/Excel)도 고도화 성격이므로 여기에 통합.

#### 높음 — 실용 가치 큰 기능

- ⬜ **7-1. 레이아웃 보존 비교 (Visual Diff)**
  > 현재 텍스트 모드와 병행하는 **레이아웃 뷰** — 원본 서식을 유지한 채 diff 하이라이트 표시.
  > 텍스트 모드(수락/거절/편집)와 레이아웃 모드(서식/레이아웃 변경 확인)를 툴바 토글로 전환.
  >
  > **업계 현황**: 업계 표준 접근법. Draftable, Adobe Acrobat Compare, Workshare 등 주요 도구가 동일 방식 사용.
  > 핵심 라이브러리(PyMuPDF, win32com)가 이미 프로젝트에 설치되어 있어 인프라 추가 비용 없음.
  > **기술 부채 해소**: PDF 구조 평탄화 문제(다단, 표 내부 텍스트 선형화)가 레이아웃 모드에서는 원본 그대로 표시되므로 자연 해소.
  - ⬜ **DOCX 비교**: `win32com.CompareDocuments()` → Track Changes DOCX 생성 → PDF 변환 → PDF.js 표시
    - Word 네이티브 비교 엔진 활용 (서식, 표, 이미지 변경 감지)
    - `word_preprocessor.py`와 동일한 COM 패턴 재사용
  - ⬜ **PDF 비교**: PyMuPDF `get_text("words")` 좌표 추출 → difflib 비교 → `search_for()` + `add_highlight_annot()` 어노테이션
    - 또는 백엔드에서 diff 좌표 JSON 반환 → PDF.js 위 커스텀 오버레이 레이어
  - ⬜ **프론트엔드**: Translator PDF.js 뷰어 패턴 재사용, 좌우 PDF 렌더링 + diff 오버레이
  - ⬜ **뷰 모드 토글**: 툴바에 "텍스트" / "레이아웃" 전환 버튼 (모드 토글 패턴 재사용)
  - ⬜ 크로스 포맷 (DOCX↔PDF): DOCX → PDF 변환 후 PDF 비교 파이프라인 적용

- ⬜ **7-2. 비교 리포트 내보내기 (PDF)**
  - ⬜ 비교 결과를 PDF 보고서로 생성 (결재/보고용)
  - ⬜ 스코어, 이슈 목록, 변경 요약 포함
  - ⬜ 7-1 레이아웃 뷰가 있으면 어노테이션된 PDF를 직접 내보내기 가능

- ⬜ **7-3. 추가 포맷 — HWP/HWPX** (구 5-3)
  - ⬜ pyhwpx 라이브러리 연동 → 텍스트 추출 → 텍스트 모드 비교/검증
  - ⬜ 레이아웃 모드: HWP → PDF 변환 후 7-1 파이프라인 적용
  - ⬜ 비교 + 검증 모드 양쪽 지원

#### 중간 — UX 품질 향상

- ⬜ **7-4. 미니맵/개요 바**
  - ⬜ 스크롤바 옆 컬러 마커 (변경/이슈 위치 개요)
  - ⬜ 클릭 → 해당 위치 점프
  - ⬜ 비교/검증 모드 양쪽 지원

- ⬜ **7-5. 통합 뷰 (Unified View)**
  - ⬜ 단일 패널에 inline diff 표시 (GitHub unified diff 스타일)
  - ⬜ Side-by-side ↔ Unified 토글 버튼

#### 낮음 — 복잡도 높거나 니치한 기능

- ⬜ **7-6. 추가 포맷 — Excel** (구 5-4)
  - ⬜ openpyxl 연동, 시트별 텍스트 추출
  - ⬜ 셀 단위 비교 vs. 텍스트 플래튼 결정
  - ⬜ 텍스트 모드 전용 (레이아웃 모드 적용 어려움)

- ⬜ **7-7. 3-way 비교**
  - ⬜ 공통 조상(Base) + A + B 3패널 비교
  - ⬜ 충돌 구간 자동 감지 + 해결 UI

- ⬜ **7-8. 비교 이력 관리**
  - ⬜ 비교 세션 저장/불러오기 (영속 레이어 필요)
  - ⬜ 동일 문서 반복 비교 시 변화 추적

---

### 알려진 기술 부채

> Phase 3 완료 시점 분석에서 발견된 개선 사항. 각 Phase 진행 시 관련 항목을 함께 처리한다.

#### 보안

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| ~~`PUT /rules` 권한~~ | ~~높음~~ | ~~`require_admin` 미적용~~ | **4-0에서 해결** |
| 규칙 저장 스키마 검증 | 중간 | `save_rules()`에 구조 검증 없음 — 잘못된 데이터로 JSON 파손 가능 | Phase 5 |

#### 데이터 정합성

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| DOCX `page_count: null` | 낮음 | python-docx는 페이지 수 미제공 — 프론트에서 null 처리 필요 | Phase 7-3 |
| PDF 구조 평탄화 | 참고 | 다단 PDF, 표 내부 텍스트가 선형으로 합쳐짐 — 추출 한계. **7-1 레이아웃 모드에서 자연 해소** | Phase 7-1 |
| 프리셋 이름 검증 | 낮음 | validate 요청의 `preset` 파라미터 미검증 (존재 여부) | Phase 5 |

#### UX 개선

| 항목 | 심각도 | 설명 | 처리 시점 |
|------|--------|------|----------|
| ~~편집 모드 Undo/Redo~~ | ~~중간~~ | ~~contenteditable에 히스토리 없음~~ | 브라우저 네이티브 Ctrl+Z로 충분 — 제거 |
| 편집 시 plain text 붙여넣기 | 중간 | 리치 텍스트 붙여넣기 시 서식 유입 | **4-0** (선행 수정) |
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
| DOCX 레이아웃 비교 | **win32com CompareDocuments** | 이미 설치됨 (word_preprocessor.py), Word 네이티브 품질, 업계 표준 |
| PDF 레이아웃 비교 | **PyMuPDF 좌표 추출 + 어노테이션** | 이미 설치됨, 추출+어노테이션 일체, 폐쇄망 호환 |
| 레이아웃 뷰 렌더링 | **PDF.js (기존)** | Translator와 동일 뷰어 재사용, 추가 의존성 없음 |

### 참고한 서비스

#### Phase 1~5 (텍스트 비교 + 검증)
- **Draftable** — 비교 UI 레퍼런스 (side-by-side + change list). 900+ 법률사, 전통 diff 전용
- **Grammarly** — 검증 UI 레퍼런스 (인라인 하이라이트 + 사이드바 이슈)
- **Hemingway** — 모드 전환 패턴 (Write/Edit 토글)
- **SonarQube** — 규칙 관리 UI (Quality Profile, 프리셋, 토글)
- **Acrolinx** — 문서 품질 스코어카드, 3단 규칙 계층
- **Vale** — 규칙 유형 참고 (existence, substitution, occurrence)

#### Phase 7-6 (레이아웃 보존 비교)
- **PyMuPDF** — PDF 텍스트+좌표 추출 (`get_text("words")`), 어노테이션 (`add_highlight_annot`). 월 500만+ 다운로드, Artifex 지원
- **win32com CompareDocuments** — Word 네이티브 비교 엔진 COM 호출. 법률/규격 문서 관리에서 수십 년간 사용된 표준 방식
- **PDF-Diff-Viewer** (ssibb) — PyMuPDF 기반 시각적 PDF 비교 레퍼런스 구현 (Tkinter 데스크톱)
- **diff-pdf** (vslavik) — C++ 픽셀 레벨 PDF 비교. 시맨틱 diff 아닌 이미지 비교라 보조 용도
- **compare-pdf** (Formartha) — pdf2image + OpenCV `absdiff` 픽셀 비교. 순수 Python
- **Adobe Acrobat Compare** — Old/New File 비대칭 UI + 색상 범례 (파랑=삽입, 보라=페이지 변경, 초록=이동/삭제)
- **Workshare Compare** — Original/Modified 비교 → Redline 문서 생성. 법률 업계 표준

#### Phase 6 (AI 의미 비교)
- **Litera Compare + Lito** — 전통 diff 엔진 + AI 에이전트 오버레이 패턴. 법률 업계 72% 점유율
- **Diffchecker Pro** — 텍스트 diff 즉시 + "AI로 요약" 온디맨드 버튼
- **BlackBoiler** — AI 계약 마크업, NDA 2분 처리, 검토 시간 70% 감소
- **Spellbook** — GPT-5/Claude 기반 계약 분석, 2000+ 산업 표준 벤치마킹
- **Luminance** — 멀티모델 AI, 1000+ 조항 자동 식별, 언어 무관
- **fda-guidance-diff** ★ — 3단계 파이프라인 (추출→BM25→Gemini Flash 분류), FDA 규제문서, 정확도 90~100%
- **SemanticDiff** — reflow 내성 PDF diff + LLM 의미 검증, 학술/기술 논문
- **redline-summarizer** — Claude API 기반 계약 비교, 교통신호 위험등급 (오픈소스)
- **Robin AI** — Anthropic Claude + AWS, 50만+ 문서 처리

### 상세 조사 자료

#### 비교/검증 UI
- [Draftable — Side-by-side comparisons](https://help.draftable.com/hc/en-us/articles/17693327305881)
- [Grammarly — Editor User Guide](https://support.grammarly.com/hc/en-us/articles/360003474732)
- [SonarQube — Quality Profiles](https://docs.sonarsource.com/sonarqube-server/quality-standards-administration/managing-quality-profiles/editing-a-custom-quality-profile)
- [Acrolinx — Enable/Disable Guidelines](https://docs.acrolinx.com/acrolinxplatform/latest/en/guidance/guidelines/enable-and-disable-guidelines)
- [Grammarly — Create Style Rules](https://support.grammarly.com/hc/en-us/articles/360043832652)
- [Rule Builder Design Pattern](https://ui-patterns.com/patterns/rule-builder)

#### Diff 엔진/알고리즘
- [jsdiff](https://github.com/kpdecker/jsdiff)
- [Google diff-match-patch](https://github.com/google/diff-match-patch)
- [diff2html](https://diff2html.xyz/)
- [Python difflib](https://docs.python.org/3/library/difflib.html)
- [xmldiff](https://pypi.org/project/xmldiff/)
- [When to Use Each Git Diff Algorithm](https://luppeng.wordpress.com/2020/10/10/when-to-use-each-of-the-git-diff-algorithms/)

#### AI 의미 비교 (Phase 6 조사)
- [fda-guidance-diff](https://github.com/tanayvenkata/fda-guidance-diff) — 3단계 파이프라인, BM25+Gemini Flash
- [SemanticDiff](https://github.com/Labic-ICMC-USP/SemanticDiff) — reflow 내성 PDF + LLM 검증
- [redline-summarizer](https://github.com/noamrazbuilds/redline-summarizer) — Claude API 계약 비교
- [lexi-flow](https://github.com/bhagwat-chate/lexi-flow) — RAG 기반 문서 비교 (GPT-4o/Gemini/DeepSeek)
- [DVCS](https://github.com/SaintFreddy/dvcs) — 문서 버전 관리 시스템, 의미 단위 diff
- [h2o.ai LLM-Powered Document Comparison](https://h2o.ai/LLM-Powered-Document-Comparison/)
