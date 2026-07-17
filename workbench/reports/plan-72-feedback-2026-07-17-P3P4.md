# plan 72 실행 피드백 — P3(셸 통합) · P4(소유권)
> 실행일 2026-07-17 · 실행자 Claude(/run-plan) · 대상 `plans/72-author-document-workspace.md`
> 선행: P1·P2 완료(`plan-72-feedback-2026-07-17.md`). 본 보고서는 잔여 P3·P4 = 계획 종료분.

## 요약
- 완료: **P3·P4 (계획 전체 종료)**. 착수 전 미해결/협의 **5건 업계표준 기준 확정**.
- 변경 파일 **8** — backend 1 (`api/document.py`) · frontend 6 (`md-editor.js`·`md-editor.css`·`author.html`·`author.css`·`author.js`·`editor.js`·`tree-menu.js`) · `.gitignore`.
- code-review: **Critical 2 / Warning 4 / Suggestion 3** → Critical 2 + Warning 2 반영, 나머지 residual/backlog.
- 회귀: 0 (로컬 Docker:80 검증, 콘솔 0).

## 확정된 결정 (사용자 위임 → 업계표준)
| # | 항목 | 결정 | 근거 |
|---|------|------|------|
| ① | 정적서빙 누수 | 인증 엔드포인트 경유 + **`data/authored/` 이전** | 개인 UGC를 공개 웹루트서 서빙 안 함(Notion·GDocs·GitHub). data/ 는 nginx 403 |
| ② | 소유권 저장 | 서버측 owner_id(`_owners.json`) | 권한 SSOT는 클라 편집 불가 위치. front matter=표시용 |
| ③ | 셸 통합 | 좌 패널 + 우 편집 스플릿 | Notion·VS Code·Obsidian 사이드바 표준 |
| ④ | 저작면 | 빈 문서 | P1서 SKELETON 제거 반영 |
| ⑤ | admin 가시성 | 소유자 본인만(예외 없음) | 최소 권한. 큐레이션은 후속 |

## 구현 결과
| 영역 | 상태 | 변경 | 메모 |
|------|------|------|------|
| P4 저장 이전 | ✅ | `document.py` `_resolve_store_path`·`AUTHORED_STORE_DIR=data/authored` | `contents/`(정적) 밖으로 → 3환경 정적누수 차단 근거 |
| P4 소유권 캡처 | ✅ | `save_markdown` owner 서버측 캡처, `_owners.json` 원자적(tmp+replace, compare 패턴) | front matter 미신뢰 |
| P4 소유자검사 | ✅ | 덮어쓰기 시 owner≠user → 403, **fail-closed**(고아도 거부) | code-review Critical#2 반영 |
| P4 목록·content | ✅ | `/api/authored` require_editor+소유자필터, 신규 `GET /api/authored/content` | admin 예외 없음 |
| P4 백업 | ✅ | 실패 시 warning 로그·저장 계속(best-effort) | `/app/backups` 권한이슈서 발견 → 저장 차단 방지 |
| P3 셸 마운트 | ✅ | `md-editor` overlay(fixed/z-4000) 폐기→`#au-editor-host` 인셸, `close`→`onMdEditorClosed` | 공통 헤더 유지(핵심) |
| P3 워크스페이스 | ✅ | `author.html`/`author.css` 스플릿(좌 '내 문서'+우 편집), `body.au-editing` 토글 | 71 시각자산 이식(overlay 규칙 1개만 교체) |
| P3 편집 배선 | ✅ | `author.js` `openDoc`→content API 경유 인셸, Explorer 리다이렉트 폐기, dirty 가드 | `name` 계약 통일 |
| P3 잔존 정리 | ✅ | `editor.js` `.md` 분기·`tree-menu.js` `highlightAuthoredDoc` 제거 | 死 코드 |

## 검증 결과
- **게이트**: `py_compile` OK · `node --check`(md-editor/author/editor/tree-menu) OK · 커밋 게이트 훅 미설치(console.* 0 확인) · 빌드/타입체크 시스템 없음(vanilla JS, 미해당).
- **백엔드 E2E(curl/urllib, Docker:80)**: 저장 200(created)·재저장 overwrite=false 409·overwrite=true 200 · 목록 200(name) · content 200 · 정적 `/data/authored/*.md` **403** · 구경로 `/contents/authored/*.md` **404** · 미인증 목록 **401**.
- **소유권 격리(임시 editor 2계정 생성→검증→삭제)**: 타 계정 목록 `[]` · 타인 문서 읽기 **403** · 덮어쓰기 **403** · 각자 자기 문서만 노출. **fail-closed**: 고아(owner 미기록) 파일 읽기·덮어쓰기 **403**.
- **UI 왕복(Playwright, testbot)**: 홈→'빈 문서 작성'→워크스페이스 진입(헤더 유지·좌패널·우편집), 제목/본문 입력→저장→좌패널 반영+활성강조+'저장됨', ✕닫기→홈 복귀+최근목록 반영, 카드 클릭→content API 재로드(제목·본문 복원, readonly). **콘솔 0 error/warning**. 라이트/다크 스크린샷(`workbench/screenshots/plan72-P3-workspace-{light,dark}.png`).
- **회귀 스팟체크**: Explorer 트리(P2서 저작 미노출) 무변 · menu.py authored 미참조 · `/api/save-document`(HTML) 무접촉 · `app.js renderMarkdownDoc`(비-authored .md 없어 사실상 死, 무해 잔존).

## 5관점 피드백
- **개발책임자**: P4→P3 순서로 뒤집어 의존(openExisting↔content API) 해소. 계획 5건 전부 종료 → done 이관 적격.
- **코드전문가**: `name` 단일 계약으로 path 혼선 제거. owner 인덱스 read-modify-write에 락 없음(레이스 시 lost-update 가능)이나 fail-closed가 탈취를 봉쇄 → 저작=저동시성이라 락 미도입(YAGNI, residual 기록).
- **UI/UX**: 헤더 유지로 시스템 정체성 복구(P71 miss 해소). 좌패널서 문서 전환·dirty 가드. 편집 중 홈 히어로 감춰 편집 공간 확보.
- **웹디자인**: overlay 규칙 1개만 교체, 71 자산(밝은 바·시트·히어로·표지 접힘·다크) 전부 보존. 토큰만 소비(하드코딩 0). 라이트/다크 정합 확인.
- **사용자**: "새 문서·내 문서 클릭 편집"이 헤더 유지된 채 Author 안에서 완결. 남의 문서 안 보이고 URL로도 못 뀀.

## 업계표준 재검토
- 사용자 개인 문서 **인증 엔드포인트 경유 서빙**(정적 루트 밖 저장) = Notion/GDocs/GitHub 표준. Docker/nginx서 완전 성립.
- **채택한 한계**: 정적서빙 차단이 **환경 의존적**. 회사 Tomcat(§5-2 data/ 통째 복사)·http.server는 `data/` 무인증 노출 → 소유권 무력화. **단 이는 P72 이전부터의 플랫폼 노출**(auth.db·settings.json·verify 이력 동반) → `DEPLOY-QUEUE.md` 에 Tomcat `/data/` 차단(web.xml security-constraint)을 **선재 하드닝 과제**로 기록. 로컬 완료 정의(Docker 검증)엔 무영향.

## 잔여 · 후속 제안
- 🔴 **[하드닝]** 회사 Tomcat/http.server `/data/` 정적 차단 (auth.db 노출 포함, backlog 승격 권장) — DEPLOY-QUEUE 기재.
- **[backlog]** Author 저작 문서 **삭제 라이프사이클** — `document_delete_service.py AUTHORED_PREFIX="contents/authored/"` stale(死), data/authored + owners.json 정합 삭제 필요.
- **[개선]** owner 인덱스 파일 락(다중 워커 동시저장 lost-update 근본차단) · `openDoc` 상태코드별 토스트(403/404 구분) · `_SAFE_MD_NAME` `re.ASCII` 명시.
- **[협의 잔여]** platform-wide 콘텐츠 엮기(전역 검색·시스템 간 공유) = 소유권 위 opt-in, 별도 전략 토론.

## 커밋 제안 (요청 시 — 2커밋 분리 권장)
1. `구현 [plan/72]: 저작 문서 소유권 — data/authored 이전·인증 content API·소유자 게이팅 (P4)` — `backend/api/document.py`·`.gitignore`·`data/authored/.gitkeep`
2. `수정 [plan/72]: 저작 편집기 Author 셸 통합 — 오버레이→좌패널+우편집 스플릿 (P3)` — `md-editor.js`·`md-editor.css`·`author.html`·`author.css`·`author.js`·`editor.js`·`tree-menu.js`
3. `문서 [plan/72]: P3·P4 완료 반영 — Progress Log·DEPLOY-QUEUE·보고서·done 이관`
