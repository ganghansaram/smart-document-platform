# Plan-72 — Author 문서 워크스페이스 (소유자 한정 + 자체 좌측 패널 + Explorer 분리)

> **상태: 🟡 draft (방향 캡처만 — 설계 착수 전)** — 2026-07-16 대화에서 방향 확정, 상세 설계·영향성은 착수 시.
> 작성: 2026-07-16 · 트리거: Plan-71(편집기 화면) 논의 중, Author 저작 문서가 Explorer 트리에 노출되는 구조(`tree-menu.js` `/api/authored` 병합)를 사용자가 재확인 → "Author 문서는 Author 안에서, 소유자에게만" 방향으로 전환
> 근거: `workbench/plans/done/70-author-authoring-migration.md`(창작/소비 분리 + 소유권 인계 백로그 #24~29) · `workbench/plans/done/66-notebook-tree-panel-dock-mode.md`(재사용할 좌측 패널) · `workbench/plans/backlog.md`(Author 인계 항목)

## 🧭 한줄 요약

Author가 만든 `.md` 문서를 **Explorer에서 떼어내고**, **소유자(만든 계정)에게만** 보이게 하며, Author 자체에 **Notebook식 좌측 폴딩 패널**을 붙여 "내 작성 문서"를 관리한다. Explorer=소비(워드 HTML)·Author=창작의 정체성을 데이터 노출 층에서도 완성.

## 왜 지금 프레임 (Context)

- 현재: 저작 문서 저장 → `/api/authored` → **Explorer 트리에 '작성 문서' 가상 폴더 합성**(`tree-menu.js:72-92`), 렌더(`app.js:440`), 편집은 MdEditor(`editor.js:78`). **소유자 필터 없음**(전 계정 노출).
- 이는 Plan-60이 **소유권을 만들기 전에** 노출부터 시킨 성급한 결합. Plan-70이 "소유권"을 Author 인계 백로그로 미뤄둠.
- **지금이 가장 쌈**: 저작 문서 **0개**(`/api/authored → {"documents":[]}`, `contents/authored/`에 `.gitkeep`만). 마이그레이션 비용 0.
- **소유권은 platform-wide 콘텐츠 엮기의 전제조건** — 전역 공유·검색통합은 소유권 위에 opt-in으로 얹어야 함. 지금 owner-scoped로 좁히는 건 우회가 아니라 올바른 1단계.

## Scope (착수 시 상세화)

### ✅ 하려는 것 (3부분)
1. **Explorer 노출 분리** — `tree-menu.js`의 `/api/authored` 병합(`fetchAuthoredDocs`·`mergeAuthoredNode`) 제거. Explorer는 워드→HTML 소비만.
2. **소유자 한정** — 문서 소유권 개념 도입(누가 생성했는지 저장) + `/api/authored`가 **현재 계정 소유분만** 반환. 백엔드 변경(중간~무거움) + RBAC.
3. **Author 좌측 패널** — Notebook 폴딩/도킹 트리(Plan-66) 차용, Author 홈에 "내 작성 문서" 목록·열기·편집.

### ⏭️ 제외 / 후속
- **platform-wide 콘텐츠 엮기**(전역 검색 노출·시스템 간 공유) — 별도 **전략 토론** 후. 소유권 선행 필수.
- 편집기 화면 자체 = **Plan-71**(직교, 선행/독립).
- `openExisting` 진입점: Explorer 분리 후엔 Author 패널에서만 열림(코드는 harmless 잔류 가능).

## 미해결 / 협의 필요 (착수 시)
1. **소유권 저장 위치** — front matter `author` 필드로 충분한가, 아니면 별도 소유자 메타(사용자 id)·인덱스가 필요한가. `author`는 표시용 문자열이라 계정 id와 불일치 가능.
2. **admin 가시성** — admin은 전 계정 저작 문서를 볼 수 있어야 하나? (큐레이션·관리 목적)
3. **좌측 패널 재사용 깊이** — Notebook 패널의 UI 컴포넌트만 차용 vs 데이터 배선까지. Notebook은 다른 데이터 모델이라 UI 패턴 재사용이 현실적.
4. **기존 `highlightAuthoredDoc`·`onMdEditorSaved=loadRecent`(author.js:185) 동선** — 새 패널 기준으로 재배선.

## 산출물 (예상)
- 수정: `js/tree-menu.js`(병합 제거), `backend/`(authored API 소유자 필터 + 소유권), `author.html`·`js/author.js`·`css/author.css`(좌측 패널), 필요 시 `js/md-editor.js` 저장 후 훅 재배선
- 이력: 완료 시 `reports/plan-72-feedback-*.md`

## Notes (결정 · 트레이드오프)
- **Plan-71과 직교**: 71=편집기 그릇(생김새), 72=문서가 사는 집(노출·소유·목록). 분리해야 편집기 개선이 소유권 설계에 발목 안 잡힘.
- **소유권 먼저, 엮기 나중**: 전역 공유를 소유권 없이 하면 "누구 것인지 모른 채 다 보임"(현 상태) 재발. 순서 고정.
- **가장 싼 시점**: 저작 문서 0개인 지금. 늦출수록 마이그레이션·오학습 누적.

## Progress Log
- 2026-07-16 — **방향 캡처 스텁 생성**. Plan-71(편집기 화면) 논의 중 파생. Explorer `/api/authored` 병합 노출을 사용자가 재확인 → "Author 안에서·소유자에게만 + Notebook 좌측 패널 차용" 방향 확정. 상세 설계·영향성·5관점은 Plan-71 완료 후 착수. (A안: 71 먼저 → 72)
