# Plan-71 — Author 저작 편집기(MdEditor) 화면 트렌디 리디자인

> **상태: ✅ 구현 완료 (2026-07-16) — 코드 완성 + 로컬 Docker 검증 통과.** 커밋·완료 이관 대기. 보고서 `reports/plan-71-feedback-2026-07-16.md`.
> 작성: 2026-07-16 · 트리거: 사용자 요청 "문서 생성 화면을 최대한 트렌디하게, 플랫폼 테마에 맞게" → 업계표준 문서 에디터 패턴 적용
> 대상: `js/md-editor.js`(Plan-60 산출, Plan-70에서 Author로 이관됨) · `css/md-editor.css`
> 근거: `workbench/plans/done/70-author-authoring-migration.md`(편집기 Author 소속) · `workbench/plans/done/60-doc-authoring-export.md`(편집기 출처·front matter 모델) · 목업 `workbench/screenshots/mockup-{light-collapsed,light-expanded,dark-collapsed}.png`

## 🧭 현황 한눈에 (Status Dashboard)

> **성격 = 표현(presentation) 개편.** 저장 모델·데이터 흐름은 **불변**, 화면 레이아웃·톤만 업계표준으로 현대화한다.
> 현재 화면: 네이비 그라데이션 바에 **제목이 반투명 입력창**으로 박혀 검색창처럼 보이고, 작성자·문서번호·보안등급이 아래 흰 줄에 항상 벌려져 있으며, 본문은 **마크다운│미리보기 2분할**(개발도구 인상).

| 축 | 결정 | 업계표준 근거 |
|------|------|------|
| **편집 형태** | 위지윅 단일 컬럼 (마크다운은 하단 세그먼트 토글로 잔류) | Notion·Dropbox Paper·Typora = WYSIWYG-first 단일 캔버스 |
| **제목** | 네이비 바 → **중앙 문서 시트 최상단 히어로 제목**으로 이전 | 모든 현대 에디터가 제목을 캔버스 첫 줄에 배치 |
| **상단 chrome** | 밝고 얇은 바, 네이비는 **악센트로만**(저장 버튼·제목 밑줄·활성색) | 미니멀 라이트 chrome이 문서 저작 도구의 표준 |
| **표지 메타** | 접힘 `<details>` "표지 정보"(작성자·문서번호·보안등급) | Notion properties·Google Docs 문서 세부정보 = 접힘/팝오버 |
| **저장 상태** | 정직한 dirty 표시(`● 저장되지 않은 변경사항`) — **가짜 "자동 저장됨" 금지** | 자동저장 미구현 상태에서 "저장됨" 표기는 거짓 신호 |
| **모델(불변)** | front matter·파일명 슬러그·409 보호·readOnly 제목 잠금·저장 후 훅 | Plan-60/70 계약 유지 |

## 📊 진행 현황

| Phase | 내용 | 상태 |
|------|------|:----:|
| 0 | 이음새·영향성 조사 — 모든 dom 참조·핸들러·저장 훅 전수 확인 | ✅ |
| A | `css/md-editor.css` 전면 개편 — 밝은 바·문서 시트·히어로 제목·표지 details·슬림 툴바 브리지·다크·반응형 | ✅ |
| B | `js/md-editor.js` `buildDom()` 마크업 재구성 + WYSIWYG 기본 + dirty 표시 배선 (dom 참조·핸들러 보존) | ✅ |
| C | 검증(회귀 0) — 신규 저작·기존 열기(제목 잠금)·DOCX·다크/라이트·반응형·ESC/Ctrl+S·콘솔 0 | ✅ |

---

## Context — 왜 이 plan 이 필요한가

'빈 문서 작성'을 누르면 뜨는 저작 편집기(`MdEditor`, 전체화면 오버레이 `z-index:4000`)는 Plan-60에서 기능 위주로 급조되어, **화면 언어가 업계표준 문서 에디터와 어긋난다.** 제목이 액션 버튼과 같은 네이비 바에 반투명 입력창으로 끼어 있어 "문서의 얼굴"이 아니라 "툴바 위젯"으로 읽히고, front matter 성격이 같은 작성자·문서번호·보안등급이 두 층으로 쪼개져 항상 노출되며, 본문은 마크다운│미리보기 분할이라 "글 쓰는 곳"보다 "코드 편집기"에 가깝다.

Plan-70이 이 편집기를 창작 시스템 Author로 교정 이전하면서, 이제 편집기는 **Author의 첫 실기능이자 얼굴**이 되었다. 그렇다면 화면도 창작 도구답게 — Notion·Google Docs·Dropbox Paper·Typora가 공유하는 관례(캔버스 히어로 제목 · 중앙 문서 컬럼 · 조용한 chrome · 접힘 속성)를 우리 플랫폼 테마(통일 네이비 악센트·tokens.css)로 번역해 입혀야 한다.

**이건 표현 개편이지 모델 변경이 아니다.** 제목은 여전히 front matter·파일명 슬러그로 저장되고(표지 양식 = 제목은 메타), 409 동명 보호·기존 문서 제목 잠금·저장 후 목록 갱신 훅은 그대로다. 위험을 레이아웃/CSS에 가두고 데이터 경로는 건드리지 않는다.

## Scope

### ✅ 이번에 하는 것 (표현 개편)
- **상단 chrome 경량화**: 네이비 그라데이션 바 → 밝은 얇은 바(`--bg-primary` + hairline). 브레드크럼(`Author › 새 문서`) · 저장 상태 · 액션(미리보기·DOCX 내보내기·저장·닫기). 네이비는 저장 버튼·제목 밑줄·활성색 악센트로만.
- **중앙 문서 시트**: 840px 폭 카드(`--panel-*` 언어) 중앙 정렬, 넉넉한 여백.
- **히어로 제목**: 시트 최상단 테두리 없는 큰 제목(포커스 시 네이비 밑줄). 저장 모델 불변.
- **표지 정보 접힘**: `<details>` — 평상시 `> 표지 정보 · {작성자} · {문서번호} · {등급}` 요약 알약, 펼치면 3개 필드.
- **위지윅 단일 컬럼**: `initialEditType: 'wysiwyg'`, 미리보기 분할 제거. 마크다운 모드는 Toast UI 하단 모드 세그먼트로 잔류(제거 안 함).
- **정직한 dirty 표시**: `isModified()` 연동 — 미저장 변경 시 `● 저장되지 않은 변경사항`, 저장 후 `저장됨`.
- 라이트/다크(tokens 자동 전환)·반응형·**회귀 0** 검증.

### ⏭️ 의도적 제외 / 후속
- **실제 자동저장(autosave)** — 별도 기능(디바운스 저장·충돌 처리). 본 계획은 dirty *표시*까지만. 도입 시 후속.
- **옛 Monaco/HTML 편집기**(`EditorCore`, Explorer 잔류) — 무관·무이동.
- **제목 자동 줄바꿈/축소 고도화** — 1차는 클리핑만 방지(가로 스크롤/ellipsis), 오토그로우 textarea는 선호 항목.
- **소유권·표지 렌더·검색연동·큐레이션** — Plan-70이 넘긴 Author 인계 백로그(별개).

## Tasks

### 0. 이음새·영향성 조사 (구현 전, 회귀 0의 근거)
- [ ] `buildDom()` 이 만드는 dom 참조 **7키**(요소 6: `title·author·docNumber·classification·host·overlay` + 값슬롯 1: `date:null`, buildDom:124)를 새 마크업에서 **동일 키로 보존** — `metaFromFields()`·`snapshot()`·`open()` 이 이 참조에 직접 의존. `date`는 숨김 값슬롯(open:156에서 재할당)이라 요소 불필요하나 키는 유지
- [ ] `open()` 의 `dom.title.readOnly = !state.isNew`(기존 문서 제목=파일명 잠금) — 히어로 제목에서도 동작하는지 확인
- [ ] `open()` 의 포커스 분기 `(state.isNew ? dom.title : dom.host).focus()` — 히어로 제목/호스트 참조 유지
- [ ] 저장 훅 3종 보존 확인: `loadContent`(Explorer 배경 뷰 새로고침, `AppState.currentPage===path` 시) · `loadMenuData`+`highlightAuthoredDoc`(신규 문서 메뉴 반영) · `onMdEditorSaved`(Author 목록 갱신)
- [ ] ESC 닫기·Ctrl+S 저장 keydown 핸들러 — 마크업 교체와 무관하게 유지(document-level)
- [ ] `mountEditor()` 옵션 변경(`initialEditType` markdown→wysiwyg)이 저장 시 `getMarkdown()` 산출에 미치는 영향 확인 — ⚠️ **본문 재직렬화 드리프트 예상**(↓ (c) 리스크). `previewStyle` 은 `'vertical'`(split) → **`'tab'`** 로(마크다운 토글 시 split 개발자툴 인상 방지)
- [ ] **본문 바이트 드리프트 실측**: 기존 authored `.md` 를 무편집으로 열기→저장 후 diff — 정규화 범위(리스트 마커·atx/setext·빈줄·이스케이프) 파악해 Acceptance known-delta 기준 확정

### A. CSS 전면 개편 (`css/md-editor.css`)
- [ ] `.md-editor-overlay` 캔버스 배경(`--canvas-bg`) + 세로 flex 유지
- [ ] 상단 바: 네이비 그라데이션 제거 → `--bg-primary` + `border-bottom: var(--border-color)`. 브레드크럼·저장상태·액션 배치. 액션은 **공통 `.btn` 계열 재사용**(저장=`.btn-primary`만 `--active-color`, 내보내기=`.btn-secondary`, 닫기=`.btn-ghost`). **'미리보기' 버튼 삭제**(wysiwyg-first에선 캔버스가 곧 미리보기 → 중복)
- [ ] 문서 시트: `max-width:840px` 중앙, `--content-bg`·`--panel-shadow`·`--radius-lg`, 여백. ⚠️ **`.entry-card`/`.content-card` 재사용 금지** — hover-lift transform이 정적 집필면에 부적절(호버 시 시트 튐). 패널 토큰 직접 사용
- [ ] 히어로 제목: 테두리 없는 큰 **auto-grow `textarea`**(긴 제목 줄바꿈+`readOnly` 양립, 높이 자동조절 JS 경미), 포커스 시 `--active-color` 밑줄, `::placeholder`, 다크 `--active-color`. **공통 대응 클래스 없음 → 신규 스코프 클래스**(예: `.md-editor-title`)
- [ ] 표지 정보 `<details>`: summary 알약(`.badge` 스킨 활용, 요약값 `summary-vals`, `[open]` 시 숨김)·펼침 필드는 **기존 `.form-input`/`.form-input-sm`/`.form-select-sm` 재사용**
- [ ] 슬림 툴바 브리지: 기존 Toast UI 토큰 브리지(현 md-editor.css §하단) 위에, 밝은 바 톤에 맞춰 툴바 배경·아이콘 정리
- [ ] 본문 헤딩 정합(현행 h1 navy/보더·h2 등) **유지** — 이미 플랫폼 정합, 손대지 않음
- [ ] 다크: 제목·헤딩 `--active-color`(현행 규칙 유지) + 밝은 바의 다크 표면 확인
- [ ] 반응형: 좁은 폭에서 상단 액션 축약(아이콘화 또는 오버플로우)·시트 좌우 여백 축소

### B. JS 마크업 재구성 (`js/md-editor.js`)
- [ ] `buildDom()` innerHTML을 새 구조로: `[상단 바(브레드크럼·상태·액션)] + [캔버스 > 시트 > 히어로제목 · 표지details · 편집host]`. **dom 참조 키 6종 동일 유지**
- [ ] `mountEditor()`: `initialEditType: 'wysiwyg'` + `previewStyle: 'tab'` (마크다운 세그먼트 잔류)
- [ ] **dirty 표시 배선(전 입력원)**: `snapshot()`(md-editor.js:84-86)이 메타필드+제목+본문을 합치므로, 편집기 `change` **뿐 아니라** 제목·작성자·문서번호·보안등급 `input`/`change` 에도 걸어 `isModified()` 반영. 상태 텍스트 토글(`● 저장되지 않은 변경사항` ↔ `저장됨`). 저장 성공 시 `state.initial=snapshot()`(md-editor.js:215) 직후 라벨 재렌더
- [ ] **요약값+dirty 통합 핸들러**: 표지 정보 summary 요약값 실시간 갱신을 위 dirty 핸들러와 한 함수로(입력 1회에 요약·dirty 동시 갱신)
- [ ] 액션 버튼 `data-act`(save·export·close) 및 핸들러 바인딩 **동일 유지**('미리보기' 제거로 바인딩 대상 1개 감소)

### C. 검증 (회귀 0)
- [ ] 실브라우저: Author 홈 '빈 문서 작성' → 신규 저작 → 저장(신규 슬러그 파일 생성·409 동명 보호) → DOCX 내보내기 end-to-end
- [ ] 기존 작성 문서 열기(`openExisting`) → **히어로 제목 readOnly 잠금** 확인 · 표지 정보에 front matter 값 채워짐 · 저장 후 배경 뷰 갱신
- [ ] ESC(미저장 시 confirm)·Ctrl+S 저장 동작
- [ ] 라이트/다크·반응형(좁은 폭 상단 바)·콘솔 0
- [ ] **모델 회귀 0**: front matter(순서·키·값)·파일명 슬러그·409 동명 보호·기존 제목 잠금·저장 후 훅이 개편 전과 **동등**
- [ ] **본문 known-delta**: 무편집 열기→저장 시 본문 마크다운 정규화가 Task 0 실측 범위 내(semantic 등가)인지 확인 — 바이트 동등은 요구 안 함(wysiwyg 재직렬화의 알려진 대가) · Explorer 열람 seam 무영향
- [ ] DEPLOY-QUEUE 배포 대상 1줄 append

## Acceptance

**필수**
- 새 저작 화면 일치: 밝은 상단 바 · 중앙 문서 시트 · 히어로 제목 · 접힘 표지 정보 · 위지윅 단일 컬럼 (⚠️ 목업의 `자동 저장됨` 라벨은 stale — 정직 dirty로 대체, ↓ Notes)
- **모델 회귀 0**: front matter·파일명 슬러그·409·기존 제목 잠금·저장 후 훅 개편 전과 동등
- **본문**: 무편집 재저장 시 semantic 등가(known-delta 내) — 바이트 동등은 요구 안 함
- dirty 표시가 정직: 자동저장 없이 "저장됨"을 거짓 표기하지 않음. dirty(전 입력원)에 반응
- 콘솔 0 · 라이트/다크/반응형 · ESC/Ctrl+S 정상

**선호**
- 히어로 제목 오토그로우(긴 제목 줄바꿈, 클리핑 없음)
- 표지 정보 summary 요약값 실시간 갱신
- 편집기 번들/CSS 무게 증가 없음(순수 교체)

## 미해결 / 협의 필요

> 검토(plan-advisor) 반영 — 앞선 3건 중 2건 결정 완료, 실질 협의는 아래 2건:

**✅ 검토로 결정된 것**
- **시트 = 카드**(패널 토큰 직접, `.entry-card`/`.content-card` 재사용 금지) — 확정.
- **dirty = 2상태**(`● 저장되지 않은 변경사항`/`저장됨`, 저장 중 스피너는 지연 체감 시만) — 확정.
- **'미리보기' 버튼 삭제** — 확정(캔버스=미리보기, 마크다운은 하단 세그먼트).

**✅ 남은 협의도 결정됨 (2026-07-16 사용자 확정)**
1. **본문 바이트 드리프트 = 허용** — wysiwyg-first 전환으로 기존 문서 무편집 재저장 시 본문 마크다운 정규화 발생 가능(semantic 등가). 사용자 본인 창작물·등가 재포맷 무해 → 허용. Acceptance는 "본문 known-delta"로 유지.
2. **히어로 제목 = auto-grow `textarea`** — 긴 제목 줄바꿈 + 기존 문서 `readOnly` 잠금 양립. 높이 자동조절 JS(경미) 포함. `contenteditable` 불가(잠금 미동작).

> 협의 0건 — 착수 가능 상태.

## 산출물
- 수정: `css/md-editor.css`(전면), `js/md-editor.js`(`buildDom`·`mountEditor`·dirty 배선)
- 참조: 목업 `workbench/screenshots/mockup-*.png`
- 이력: DEPLOY-QUEUE 배포 대상 append · (완료 시) `reports/plan-71-feedback-*.md`

## Notes (결정 · 트레이드오프)
- **위험을 CSS에 가둔다(범위 정정)**: 데이터 경로(front matter·슬러그·훅) 불변, dom 참조 7키 보존 → 회귀면이 레이아웃/CSS로 국한. 단 **본문은 예외** — wysiwyg 전환이 마크다운을 재직렬화하므로 "바이트 동등"은 **모델(front matter+슬러그+409+훅)에만** 적용, 본문은 **semantic 등가(known-delta)** 로 완화(검토 반영).
- **Phase 순서: B→A**: CSS(A)와 마크업(B)이 클래스명 계약으로 강결합 → **B에서 마크업·클래스명 먼저 확정 후 A에서 스타일**. 진행 시 순서 조정(계획 표는 논리 순, 구현은 B 선행).
- **정직한 저장 표시**: 업계 관례(Google Docs "모든 변경사항이 저장됨")를 흉내 내되 **자동저장이 없으므로** 표기하지 않는다. 가짜 안심 신호는 데이터 손실 오해를 부른다 → dirty 표시로 정직하게. ⚠️ **승인 목업(`mockup-light-expanded.png`)에 `자동 저장됨` 라벨이 남아 있으나 이는 stale — 텍스트 결정(정직 dirty)이 우선.** 구현은 목업이 아니라 이 결정을 따른다(필요 시 목업 재렌더).
- **표지 양식과 정합**: 제목을 캔버스로 올리되 노션식 title=H1이 아니라 **front matter title=표지 메타**를 유지(우리 도메인은 표지 있는 기술 보고서). 본문은 여전히 `# 개요`부터 시작.
- **Toast UI 제약 수용**: 진짜 단일 캔버스는 엔진 한계로 불가 → `wysiwyg` 기본 + 마크다운 세그먼트 잔류가 "가능한 수준의 트렌디".

## Progress Log
- 2026-07-16 — plan 생성. 사용자와 방향 3종 확정(위지윅 단일·밝은 chrome+네이비 악센트·접힘 표지 정보) 후, 실 tokens.css 링크한 목업 3종 렌더·승인. 업계표준(Notion/Docs/Paper/Typora) 근거를 Status Dashboard에 명시. 저장 모델 불변·회귀 0 프레임으로 위험을 CSS에 국한.
- 2026-07-16 — **plan-advisor 검토 반영**: (1) 본문 바이트 동등이 wysiwyg 재직렬화로 비현실 → Acceptance를 "모델 동등 + 본문 known-delta"로 분리, (2) dirty 배선을 편집기 change→**전 입력원**(메타·제목 포함)으로 확장, (3) dom 참조 6종→**7키**(`date` 값슬롯 명시), (4) 시트는 카드 유지하되 `.entry-card`/`.content-card` 재사용 금지(hover-lift 부적절)·공통 `.btn`/`.form-*` 재사용, (5) '미리보기' 버튼 삭제·`previewStyle:'tab'`, (6) Phase 순서 B→A, (7) 목업 `자동 저장됨` 라벨 stale 명시. 남은 협의 2건(본문 드리프트 허용·히어로 제목 요소 타입).
- 2026-07-16 — **구현·검증 완료(/run-plan)**. B(JS buildDom·mountEditor·dirty 배선)→A(CSS 전면+반응형) 순 구현. 브레드크럼 상태전환(새 문서/문서 편집) 추가 확정. 구현 중 결함 2건 자체수정: 셰브론 SVG 크기 제약 누락·다크 편집영역 흰 배경(브리지 확장). 실브라우저 e2e 통과: 신규·기존(readOnly)·저장(**모델 바이트 동등**·본문 골격 **바이트 동일**)·다크·반응형(440px)·콘솔 0. code-review(Critical 0/Warning 2/Sugg 5) → 반응형 미구현·autoGrowTitle 낭비 반영, `#7db8f0`(Plan-60 유산·범위 밖)은 후속 기록. 보고서 `reports/plan-71-feedback-2026-07-16.md`.
- **2026-07-16 (완료)**: 커밋 `35e89ec` push. 코드 완성 + 로컬 Docker 검증 통과 = 완료 정의 충족 → `done/` 이관. 회사 배포는 `DEPLOY-QUEUE.md`(운영 축). 후속 정리 4건(#7db8f0·a11y label·readonly 힌트·Plan-72 연동)은 보고서 잔여 항목으로.
