# 문서 비교 시스템 (Compare) — 실행 계획서

> 작성일: 2026-03-12
> 상태: Phase 1 완료 (1-1 ~ 1-4)

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
├──────────────────┬─────────────────┬────────────────────────────┤
│ SWA_PMS.docx ×   │ 문서 B           │  변경 목록 (접기 가능)      │
├──────────────────┼─────────────────┤                            │
│                  │                 │  추가 5 · 삭제 3 · 수정 12  │
│  문서 A 텍스트    │  문서 B 텍스트   │  ────────────              │
│  ██삭제██         │  ██추가██       │  [1.1] 용어 변경            │
│                  │                 │  [2.3] 내용 추가            │
│  (독립 스크롤)    │  (독립 스크롤)   │  [3.1] 수치 변경 ⚠         │
└──────────────────┴─────────────────┴────────────────────────────┘
```

- 푸터 없음 (도구형 화면 — Translator 동일)
- 패널 구조: `.cp-panel-header`(고정 라벨) + `.cp-panel-body`(스크롤 영역)
- 스크롤 동기화: 기본 OFF, 툴바 버튼으로 토글

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
  - [x] 서브 헤더 (툴바 — 동기화 버튼, 힌트, 모드 토글)
  - [x] 스크롤 동기화 (기본 OFF, 비례 기반)
  - [x] 푸터 제거 (도구형 화면)

- [x] **1-3. 검증 모드 레이아웃**
  - [x] 패널 B 숨김 (`.mode-verify .panel-b { display: none }`)
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

- [ ] **2-1. Diff 엔진**
  - [ ] 백엔드 API: `POST /api/compare/diff`
  - [ ] `difflib.SequenceMatcher` 문장 단위 비교
  - [ ] 변경 결과 JSON 응답 (추가/삭제/수정 + 위치 정보)

- [ ] **2-2. Diff 시각화**
  - [ ] `js/lib/jsdiff/diff.min.js` 추가 (로컬 서빙)
  - [ ] 좌우 패널에 변경점 하이라이트 렌더링
  - [ ] 추가(초록 배경) / 삭제(빨강 배경) / 수정(노랑 배경)

- [ ] **2-3. 변경점 네비게이션**
  - [ ] ◀ ▶ 버튼 (이전/다음 변경점)
  - [ ] 현재 위치 표시 (3/12)
  - [ ] 키보드 단축키

- [ ] **2-4. 변경 목록 사이드바**
  - [ ] 변경점 리스트 렌더링 (위치, 요약)
  - [ ] 클릭 시 해당 위치로 스크롤
  - [ ] 변경 통계 (추가 N, 삭제 N, 수정 N)

- [ ] **2-5. 텍스트 편집 모드**
  - [ ] 패널 바디 `contenteditable` 토글 (편집/읽기 전환)
  - [ ] 비교 전 불필요한 텍스트(목차, 페이지번호 등) 수동 제거 지원
  - [ ] 편집 후 docState 동기화

- [ ] **2-6. 필터링**
  - [ ] 변경 유형별 필터 (추가/삭제/수정)
  - [ ] 공백 변경 무시 옵션

### Phase 3: 검증 모드

> 목표: 단일 문서의 규칙 준수 여부를 검사하고 이슈를 표시한다

- [ ] **3-1. 검증 엔진 (백엔드)**
  - [ ] 백엔드 API: `POST /api/compare/validate`
  - [ ] 내장 규칙 구현
    - 구조: 번호 체계 연속성, 표/그림 캡션 존재
    - 용어: 금지 용어 감지, 동일 개념 다른 표현
    - 가독성: 문장 길이 제한
  - [ ] 규칙 설정 저장/로드 (`data/compare-rules.json`)

- [ ] **3-2. 검증 결과 표시**
  - [ ] 문서 내 인라인 하이라이트 (밑줄 — 오류/경고/제안)
  - [ ] 우측 이슈 목록 사이드바
  - [ ] 카테고리별 접이식 그룹
  - [ ] 스코어 표시
  - [ ] 사이드바 ↔ 문서 양방향 연동

- [ ] **3-3. 규칙 설정 UI**
  - [ ] 설정 모달 (⚙ 버튼)
  - [ ] 프리셋 선택 드롭다운 ("기술문서", "일반")
  - [ ] 카테고리별 규칙 토글 (accordion + 스위치)
  - [ ] 심각도 변경 (오류/경고/제안)

- [ ] **3-4. 이슈 네비게이션**
  - [ ] ◀ ▶ 버튼 (이전/다음 이슈)
  - [ ] 카테고리/심각도 필터

### Phase 4: 고도화 (향후)

> 필요에 따라 선택적으로 진행

- [ ] **4-1. LLM 의미 비교**
  - [ ] 변경 구간을 Ollama에 전달 → 변경 유형/심각도/영향도 분류
  - [ ] 하이브리드: diff로 구간 식별 → LLM으로 의미 분석

- [ ] **4-2. 커스텀 규칙 생성**
  - [ ] 용어 치환 폼 (원본 → 대체 텍스트)
  - [ ] CSV 일괄 업로드
  - [ ] AI 기반 규칙 (자연어 검사 기준)

- [ ] **4-3. 추가 포맷**
  - [ ] HWP/HWPX (pyhwpx)
  - [ ] Excel (openpyxl)
  - [ ] Explorer 등록 HTML 문서 비교

- [ ] **4-4. 기타**
  - [ ] 비교 리포트 내보내기 (PDF)
  - [ ] 비교 이력 관리
  - [ ] admin.html 규칙 관리 통합
  - [ ] 규칙 세트 내보내기/가져오기 (JSON)

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
POST /api/compare/diff         — 두 텍스트 비교 → 변경점 목록 반환
POST /api/compare/validate     — 단일 텍스트 규칙 검증 → 이슈 목록 반환
GET  /api/compare/rules        — 현재 규칙 설정 조회
PUT  /api/compare/rules        — 규칙 설정 변경
```

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
