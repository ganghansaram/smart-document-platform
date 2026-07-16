# Plan-70 — '새 문서' 저작 기능을 Author로 교정 이전 (잘못 놓인 것 바로잡기)

> **상태: ✅ 완료 (2026-07-16) — 교정 코어 구현·실브라우저 검증·code-review 반영 완료.** 저작 진입점을 Explorer→Author 이관, '새 문서' 메뉴 제거, RBAC 게이팅(실 viewer 계정 검증). 미완 기능은 `backlog.md` Author 인계. 보고서 `reports/plan-70-feedback-2026-07-16.md`.
> 작성: 2026-07-15 · 완료: 2026-07-16 · 트리거: '새 문서' 창작 편집기가 **설계 의도와 달리 Explorer에 잘못 구현됨**을 재확인 → 원소속(Author)으로 교정
> **부모 이니셔티브**: Author(창작 시스템). 본 계획 = Author에 **첫 실기능(문서 작성) 부여**. 후속 = 효율적 생성(템플릿·합성 Plan-24)
> 근거: `workbench/plans/done/61-author-shell.md`(Author 셸·§4.3 읽기/쓰기 분할) · `workbench/plans/60-doc-authoring-export.md`(저작 자산 출처)

## 🧭 현황 한눈에 (Status Dashboard)

> **성격 = "재배치"가 아니라 "교정".** 두 시스템의 **원래 정체성**을 회복한다:
> - **Explorer = 소비** — 기존 사내 워드 문서를 Word→HTML 변환해 모아두고 **탐색·지식공유**. 편집은 *변환 문서의 표시 조정*(Monaco/HTML)까지.
> - **Author = 창작** — 처음부터 별개로 계획한 **문서 작성 전용** 시스템. "어떻게 효율적으로 문서를 만들까"를 푸는 곳.
>
> 작업 도중 이 구분을 놓쳐 **창작 기능('새 문서' 마크다운 편집기)을 Explorer에 잘못 만들었다.** 본 계획은 그것을 Author로 되돌린다.

| 축 | 결정 |
|------|------|
| **핵심** | Explorer '새 문서'(`MdEditor`) 진입점을 **Author 홈으로 교정 이전** |
| **성격** | 재배치(投機) ❌ / **오배치 교정(설계 복귀)** ✅ — 지금이 가장 쌈(299줄 독립 오버레이, 아직 얕게 결합) |
| **읽기(열람)** | **Explorer 잔류 불변** — Explorer는 소비 시스템. 작성된 `.md` 열람·서빙 렌더(marked+DOMPurify)는 그대로 |
| **쓰기(창작)** | Explorer → **Author 이관** — 편집기 번들이 Author에서 로드 |
| **범위** | **교정(이동) 코어만**. Plan-60 미완 기능은 Author가 **인계**하되 후속(↓) |
| **명확히 제외** | 옛 Monaco/HTML 편집기(Explorer 잔류·무이동) · 합성(Plan-24, 후속 Phase) |

## 📊 진행 현황

| Phase | 내용 | 상태 |
|------|------|:----:|
| 0 | 이음새 조사 — 편집기 번들 로드·저장 후 복귀 동선·Explorer 콜백(3개) 대체 | ⬜ 대기 |
| A | Author 셸에 편집기 이식 + 저작 진입점 2곳(빈문서 타일·+새문서 링크) 실연결 | ⬜ 대기 |
| B | Explorer '새 문서' 진입점 제거 (**읽기 seam 보존**) | ⬜ 대기 |
| C | 검증(회귀 0) + Plan-60 완료분 종료 처리 | ⬜ 대기 |
| — | (후속) Author 인계 백로그: 소유권·하드닝·큐레이션·표지·검색연동 | 별도 |

---

## Context — 왜 이 plan 이 필요한가

두 시스템은 **처음부터 역할이 갈려 있었다.** Explorer는 기존 워드 문서를 변환·수집해 **탐색·지식공유**하는 *소비* 공간(HTML 편집은 표시 조정용)이고, Author는 그와 **별개로 신설한 문서 *창작* 전용** 시스템이다.

그런데 Plan-60 작업 중 이 구분을 놓쳐, 창작 기능인 **'새 문서' 마크다운 편집기**(`js/md-editor.js`, `MdEditor.openNew`)를 **Explorer 헤더에 잘못 붙였다**(`js/app.js:33-34`). 중간에 "여기가 아니다"를 자각. Plan-61이 Author 셸을 지으며 "새 문서" 타일을 *"곧 제공" 목업*으로 뚫어둔 것도 이 교정을 예약해둔 것이다.

이건 투기적 재배치가 아니라 **설계 의도로 되돌리는 교정**이다. 그리고 지금이 가장 싸다 — 편집기는 **299줄짜리 독립 오버레이**라 Explorer에 깊이 박히지 않았고, 오래 둘수록 "Explorer에서 문서를 만든다"는 오학습과 결합이 쌓여 교정 비용이 커진다. 교정이 끝나면 두 시스템 정체성이 동시에 깨끗해지고, Author는 창립 목적(문서 생성)의 **첫 실기능**을 얻는다.

## Scope

### ✅ 이번에 하는 것 (교정 코어)
- Author 셸(`author.html`)에 편집기 번들 로드 — Plan-61이 "셸 가볍게, 번들은 이관 단계로 이월"로 미뤄둔 것
- Author 홈 저작 진입점 **2곳**(`tile-new-doc` "빈 문서 작성" + `act-new-doc` "+새 문서") → `MdEditor.openNew()` 실연결 (목업 토스트 제거)
- Explorer 헤더 '새 문서' 메뉴(`nav-new-doc-item`) 제거
- 저장 후 Explorer 콜백(`loadMenuData`·`highlightAuthoredDoc`·`loadContent`) → Author 문맥에 맞게 대체/무해화
- 라이트/다크·반응형·RBAC·**회귀 0**(Explorer 열람 seam 무손상) 검증

### ⏭️ 의도적 제외 / 후속
- **옛 Monaco/HTML 편집기** — Explorer 잔류, 무이동(Plan-60 원칙)
- **작성 문서 열람·서빙 렌더** — Explorer 잔류(소비 시스템·§4.3), 건드리지 않음
- **합성 워크벤치**(Plan-24) — Author의 다음 능력, 별도 Phase
- **Plan-60 미완 기능(소유권·하드닝·큐레이션·표지·검색연동)** — Author가 **인계**하되, 교정 이후 후속으로 (↓ Notes)

## Tasks

### 0. 이음새 조사 (구현 전)
- [ ] `index.html` 편집기 로드 순서 확인 → Author에 필요한 최소 번들 확정(tui-editor·marked·purify·katex·editor-core·md-editor 중 저작에 필요한 것)
- [ ] `md-editor.js` 의 Explorer 의존 3콜백(`window.loadMenuData`/`highlightAuthoredDoc`/`loadContent`) — Author에서의 대체 동선(저장 후 작성문서 목록 갱신) 설계
- [ ] 열람 seam이 쓰는 서빙 렌더 자산(marked/purify)이 Explorer에 잔류함을 확인 → 편집기 전용 번들만 이동 대상

### A. Author 셸에 편집기 이식
- [ ] `author.html` 에 편집기 번들 로드 추가
- [ ] `js/author.js` 저작 진입점 **2곳** 실연결: `tile-new-doc`("빈 문서 작성" 타일) + `act-new-doc`("+새 문서" 링크) → 현재 `comingSoon` 토스트에서 `MdEditor.openNew()` 로 교체 (`tile-new-synth` 합성 타일은 `comingSoon` 유지 = Plan-24)
- [ ] 저장 후 복귀: 편집기 닫기 → Author 홈 작성문서 목록 갱신(`/api/authored` 재조회)

### B. Explorer 진입점 제거
- [ ] `js/app.js:33-34` `nav-new-doc-item` 항목 제거
- [ ] Explorer 열람 딥링크(`index.html?page=`)·서빙 렌더 **무손상** 확인
- [ ] Explorer에서 불필요해진 편집기 전용 번들 정리 가능 여부 판단(읽기용 marked/purify는 잔류)

### C. 검증 + Plan-60 종료
- [ ] Playwright/실브라우저: 인증게이트·Author에서 새문서 저작·저장·DOCX 내보내기 end-to-end·라이트/다크·반응형·콘솔 0
- [ ] **회귀 0**: Explorer 열람 딥링크·옛 Monaco 편집기·업로드 문서 무영향
- [ ] Plan-60 헤더 상태 → `✅ 완료`(완료분 기준: 2a 저작·3a/3c 내보내기·4 메뉴편입) + `git mv done/` + README 이동. 미완 기능은 Author 인계 백로그로 이관 명시
- [ ] DEPLOY-QUEUE 배포 대상 1줄 append

## Acceptance

**필수**
- Author 홈에서 '새 문서' → 마크다운 저작 → 저장 + DOCX 내보내기 end-to-end 동작
- Explorer 헤더에 '새 문서' 부재 · 열람(`?page=`) 딥링크 정상 · 옛 편집기 정상
- 회귀 0(Explorer 열람·Monaco·업로드) · 콘솔 0 · 라이트/다크/반응형

**선호**
- 편집기 번들 lazy-load(Author 홈 초기 로드 무게 유지)

## 미해결 / 협의 필요 (교정 프레임에서 대폭 축소됨)

> 앞선 4건 중 2건은 이 프레임에서 자동 해소:
> - **서빙 렌더 경계** → ✅ 결정: Explorer=소비 시스템이므로 열람·서빙 렌더는 Explorer 잔류, **편집기 전용 번들만 이동**. (열린 질문 아님)
> - **소유권/하드닝/표지/검색연동** → ✅ 결정: Author **인계 백로그**로, 교정 이후 후속. 교정의 선행조건 아님(현재도 없이 동작).

남은 실질 협의 2건:
1. **검색연동 소속** — 작성 문서를 Explorer 검색에 노출하는 건 *읽기(소비)* 측 일이라 Explorer 몫일 수 있음(Author 몫 아님). 인계 백로그에서 Explorer 백로그로 재분류할지?
2. **큐레이션(삭제/개명) 위치** — 창작물 관리는 Author가 자연스러우나, 삭제는 Explorer 인덱스(Plan-67 생애주기)와 맞물림. Author UI vs Plan-67/69 재사용 — 후속 착수 시 결정(교정 코어와 무관).

## 산출물
- 수정: `author.html`, `js/author.js`, `css/author.css`(필요 시), `js/app.js`(메뉴 제거)
- 종료: Plan-60 → `done/` 이관 + README 갱신 + 미완 기능 Author 인계 백로그 등록
- 이력: DEPLOY-QUEUE 배포 대상 append · (완료 시) 피드백 보고서

## Notes (결정 · 트레이드오프)
- **왜 지금**: 교정 비용이 시간에 비례해 커짐(오학습·결합 누적). 편집기가 아직 얇게 붙은 지금이 최저 비용.
- **왜 코어만**: Plan-60 미완 기능을 이 교정에 묶으면 범위 팽창 → 교정이 지연·위험. 미완 기능은 전부 "현재도 없이 동작 중"이라 **선행조건이 아님** → Author 인계 후 필요할 때 별도로.
- **읽기/쓰기 분할 = 정체성**: 쓰기만 Author, 읽기는 Explorer. 이 교정은 Plan-61이 세운 계약을 어기지 않고 오히려 **완성**한다.
- **이 편집기는 시작점**: 이관된 오버레이가 끝이 아니라, Author가 "효율적 문서 생성"(템플릿·합성)으로 키워갈 토대.

## Progress Log
- 2026-07-15 — plan 생성. 최초 "저작 이관"으로 잡았다가, 당시 맥락 재확인 후 **"오배치 교정"** 프레임으로 재작성. 교정 코어/후속 인계 분리, 미해결 4→2건 축소.
- 2026-07-15 — 실제 DOM 대조 정정: Author 홈 저작 진입점은 **2곳**(`tile-new-doc` "빈 문서 작성" + `act-new-doc` "+새 문서"), 셋째 `tile-new-synth`는 합성(Plan-24)이라 목업 유지. Task A·Scope·Phase 표에 반영.
