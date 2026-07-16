# plan 72 실행 피드백 — Author 문서 워크스페이스 (P1·P2 한정)
> 실행일 2026-07-17 · 실행자 Claude(/run-plan) · 대상 `workbench/plans/72-author-document-workspace.md`
> 범위: **P1(저작면 현실화) + P2(Explorer 노출 분리)만**. P3(셸 통합)·P4(소유권)는 착수 전 결정 2건 미정으로 제외.

## 요약 — 완료 Task 2/2 · 변경 파일 3 · Critical 0 / Warning 1 / Suggestion 1
P1·P2를 계획대로 완료. 사전 분석에서 **P2 원안의 "editor.js `.md` 분기 정리"가 지금 실행 시 회귀**임을 발견해(딥링크 읽기 경로 잔존) 사용자 승인 하에 **tree 병합 제거로 한정**하고 editor.js/app.js `.md` 처리는 P3로 이연. 로컬 Docker(:80)에서 실제 경로 검증 완료.

## 구현 결과

| Phase | 내용 | 상태 | 변경 파일 | 메모 |
|------|------|------|----------|------|
| **P1** | `md-editor.js` `SKELETON`(개요/배경/목적/본론/결론) 제거 → `openNew` 빈 본문 | ✅ | `js/md-editor.js` | 제목·작성자 등은 헤더 폼(front matter)이 담당 → 본문 빈 시작이 실제 문서도구 관례 |
| **P2** | Explorer 트리의 `/api/authored` 병합 제거 | ✅ | `js/tree-menu.js`, `css/tree-menu.css` | `fetchAuthoredDocs`·`mergeAuthoredNode` 삭제, `fetchMergedMenu`→`fetchMenuData`(menu.json 단독), 死 authored-leaf 처리·`icon-authored` CSS 정리 |

**변경 규모**: 10 삽입 / 74 삭제 (순감 64줄).

## 검증 결과
- **게이트**: 빌드시스템 없음(vanilla JS). `node --check js/md-editor.js js/tree-menu.js` → 둘 다 OK. 잔존 참조 sweep(프로젝트 소스) → 0.
- **서빙 파일 교차 확인(:80 bind mount)**: P1 SKELETON 출현 0·`body: ''` 반영 / P2 제거대상 출현 0·`fetchMenuData` 반영 / `menu.json` 저작노드 0 / `/api/authored`→200.
- **실제 경로 검증(Playwright, localhost:80)**:
  - Explorer(`index.html`): 트리 85건 렌더, "작성 문서" 폴더 **없음**, `fetchMenuData` 동작·`fetchMergedMenu` 소멸, **콘솔 에러 0**.
  - Author(`author.html`, testbot=editor): `MdEditor.openNew()` → 오버레이 open, WYSIWYG·Markdown 본문 **모두 빈 문서**(골격 없음). 증거: `workbench/screenshots/plan72-P1-empty-editor.png`.
  - 기존 콘솔 에러 3건(`/api/login`·`_mockup_author_editor.html`·`favicon.ico`)은 **변경 이전부터 존재·무관**, 신규 에러 0.
- **잔류(의도) 경로 온전성**: `app.js renderMarkdownDoc`(읽기)·`editor.js MdEditor.openExisting`(edit-in-place) **유지 확인** — Plan-70이 남긴 딥링크 읽기/편집 경로 무손상.

## 5관점 피드백
- **개발책임자**: 5부분 중 위험 최저 2개(P1 초저·P2 저)를 먼저 독립 배포 단위로 닫아 순서 의존(P2→P3) 정합. 회귀 표면 최소.
- **코드전문가**: 순수 삭제+1 rename(호출 2곳 동기화). 死코드(authored-leaf 처리·`icon-authored`)까지 제거해 다음 독자 혼선 차단. 과방어 없음.
- **UI/UX**: Explorer 트리에서 창작물 혼입 제거 → "탐색=소비" 정체성 명확. Author 빈 편집기는 Word/Docs 관례와 일치.
- **웹디자인**: CSS 토큰 위반 없음(삭제만). 死 아이콘 정의 제거로 스타일시트 정합.
- **사용자**: 저작 문서 0개라 눈에 보이는 회귀 없음. 새 문서가 골격 없이 깨끗이 시작 — "왜 낯선 목차가 미리 있지?" 혼란 제거.

## 업계표준 재검토
- **빈 문서 시작**: Word·Google Docs·Notion 모두 신규 문서는 빈 본문 + 별도 제목 필드. 골격 프리셋은 "템플릿 선택" 기능으로 분리하는 게 표준 — 본 변경 방향과 일치. 향후 템플릿 갤러리가 필요하면 opt-in 기능으로 재도입(현재 YAGNI).
- **관심사 분리(트리 병합 제거)**: 소비 뷰(Explorer)에 생성물(authored)을 런타임 합성하던 결합을 끊음 — CQRS적 읽기/쓰기 분리 관점에서 올바른 방향.

## 잔여·후속 제안
- **Warning** — `highlightAuthoredDoc`(tree-menu.js)+`md-editor.js:285` `wasNew` 분기는 병합 제거로 死코드화(Explorer 신규저작이 Plan-70 이후 불가). 무해하나 **P3(공유 편집기 분리) 때 정리** 권장. 지금 존치(cross-file 배선이라 P3 세트로).
- **Suggestion** — P3 착수 시: ① `author.js openDoc`의 `index.html?page=` Explorer 리다이렉트 제거 + Author 자체 뷰어/`openExisting` 배선, ② 그 시점에 `editor.js` `.md` 분기 + `app.js renderMarkdownDoc` 정리(딥링크 소멸과 한 세트). **P4 착수 전 결정 2건**(정적서빙 누수 대책·소유권 저장 위치) 선결 필수.
- **배포**: 프론트 정적 변경. 회사 배포 필요 시 `workbench/DEPLOY-QUEUE.md`에 append(운영 축).

## 커밋 제안 (요청 시)
2커밋 권장:
1. `수정 [plan/72]: 저작 편집기 신규 문서 골격 프리셋 제거 (P1)` — `js/md-editor.js`
2. `정리 [plan/72]: Explorer 트리의 저작 문서 병합 노출 제거 (P2)` — `js/tree-menu.js`, `css/tree-menu.css`
