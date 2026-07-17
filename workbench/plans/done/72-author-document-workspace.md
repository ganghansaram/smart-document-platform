# Plan-72 — Author 문서 워크스페이스 (셸 통합 + 소유자 한정 + 좌측 패널 + Explorer 분리)

> **상태: ✅ 완료 (2026-07-17 — P1~P4 전부 완료)** — 저작면 현실화(P1)·Explorer 병합 노출 제거(P2)·Author 셸 통합 스플릿(P3)·저작 문서 소유권+정적누수 차단(P4). 로컬 Docker:80 검증(소유권 격리·정적 403·UI 왕복). 회사 Tomcat `/data/` 하드닝은 `DEPLOY-QUEUE.md`.
> 작성: 2026-07-16 · 트리거: Plan-71(편집기 화면) 논의 중, (1) Author 저작 문서가 Explorer 트리에 노출되는 구조(`tree-menu.js` `/api/authored` 병합) 재확인 → "Author 안에서·소유자에게만", (2) Plan-71 실물 확인 후 **편집기가 전체화면 오버레이라 공통 헤더를 덮어 시스템 정체성이 사라지고, 저작면 프리셋이 비현실적**이라는 피드백 → 셸 통합·저작면 현실화 요구 추가
> 근거: `workbench/plans/done/71-author-editor-trendy-redesign.md`(편집기 시각 자산 — 셸 안으로 이식 대상) · `workbench/plans/done/70-author-authoring-migration.md`(창작/소비 분리 + 소유권 인계 백로그 #24~29) · `workbench/plans/done/66-notebook-tree-panel-dock-mode.md`(재사용할 좌측 패널) · `workbench/plans/backlog.md`(Author 인계 항목)

## 🧭 한줄 요약

Author 저작을 **전체화면 오버레이에서 Author 셸 안으로** 옮겨(공통 헤더·좌측 패널 유지 = 플랫폼/시스템 정체성 유지), `.md` 문서를 **Explorer에서 떼어내 소유자에게만** 보이게 하고, **Notebook식 좌측 폴딩 패널**로 "내 작성 문서"를 관리하며, **저작면을 현실화**(이상한 골격 프리셋 제거)한다. Explorer=소비·Author=창작 정체성을 **셸·데이터·화면** 전 층에서 완성.

## 왜 지금 프레임 (Context)

- **셸 문제 (Plan-71 회고)**: 편집기(`MdEditor`)가 `position:fixed; inset:0; z-index:4000` **전체화면 오버레이**라 공통 플랫폼 헤더를 통째로 덮는다. 저작 모드 진입 시 시스템 스위처·헤더가 사라져 "어느 시스템(Author)인지" 인식이 끊긴다. Plan-71은 이 오버레이의 *생김새*만 다듬었을 뿐 **오버레이 전제 자체를 안 건드린 게 miss**. 사용자 기대 = 헤더 유지 + 편집기는 셸 콘텐츠 영역에.
- **저작면 비현실**: 신규 문서 골격 프리셋(`# 개요 / ## 배경 / ## 목적 / # 본론 / # 결론`, `md-editor.js SKELETON`)이 실제 문서 도구 어디에도 없는 형태 → 빈 문서 또는 현실적 구조로.
- **노출 문제**: 저작 문서 저장 → `/api/authored` → **Explorer 트리에 '작성 문서' 가상 폴더 합성**(`tree-menu.js:72-92`), 렌더(`app.js:440`), 편집은 MdEditor(`editor.js:78`). **소유자 필터 없음**(전 계정 노출). Plan-60이 **소유권을 만들기 전에** 노출부터 시킨 성급한 결합.
- 🔴 **정적서빙 소유권 누수 (검토 발견·치명)**: authored `.md`는 프론트 정적서버가 웹루트에서 직접 서빙하고 `app.js:431`·`editor.js:80`이 백엔드 안 거치고 `fetch(url)` 직접 로드. ⇒ `/api/authored` **리스트를 소유자 필터해도 `contents/authored/<name>.md` 직접 URL은 누구나 fetch 가능.** 진짜 소유권 = `.md`를 인증 엔드포인트 경유 or 정적루트 밖 이전이 **전제**(P4 선결).
- **소유권 SSOT는 서버측**: front matter `author`는 `_currentUser()`(`md-editor.js:226`)로 프리필한 **편집가능 자유텍스트** = 계정 id 아님. `save_markdown`(`backend/api/document.py:158`, `require_editor`)은 신뢰가능 user dict 보유 → owner는 **저장 시 서버측 캡처**(owner_id sidecar/인덱스), front matter 아님.
- **지금이 가장 쌈**: 저작 문서 **0개**(`/api/authored → {"documents":[]}`, `contents/authored/`에 `.gitkeep`만). 마이그레이션 비용 0.
- **소유권은 platform-wide 콘텐츠 엮기의 전제조건** — 전역 공유·검색통합은 소유권 위에 opt-in으로 얹어야 함. 지금 owner-scoped로 좁히는 건 우회가 아니라 올바른 1단계.

## Scope (착수 시 상세화)

### ✅ 하려는 것 (5부분)
1. **셸 통합 (편집기 오버레이 폐기)** — `MdEditor`를 전체화면 오버레이(`css/md-editor.css .md-editor-overlay` fixed/z-4000)에서 **Author 셸 콘텐츠 영역 마운트**로 전환. **공통 플랫폼 헤더·시스템 스위처 유지**(저작 모드에서도 Author임이 인식됨). Plan-71의 시각 자산(밝은 상단 바·시트·히어로 제목·표지 접힘·dirty·다크)은 **셸 안 레이아웃으로 이식**(껍데기만 교체).
2. **저작면 현실화** — `md-editor.js SKELETON`(개요/배경/목적/본론/결론) 제거 → 빈 문서 시작 또는 현실적 기본 구조. 실제 문서 도구 관례에 맞춤.
3. **Explorer 노출 분리** — `tree-menu.js`의 `/api/authored` 병합(`fetchAuthoredDocs`·`mergeAuthoredNode`) 제거. Explorer는 워드→HTML 소비만.
4. **소유자 한정** — **서버측 소유권 저장**(save 시 owner_id 캡처) + `/api/authored` **인증 게이팅+소유자 필터** + **정적서빙 누수 대책**(인증 엔드포인트 경유 or 루트 밖 이전). 백엔드 무거움 + RBAC. ⚠️ 리스트 필터만으론 불충분(↑ Context 치명).
5. **Author 좌측 패널 + 편집 진입 신규 배선** — 좌측 패널은 Notebook 트리 **UI 패턴 신규 구현**(Plan-66 패널은 `translator.js` 인라인+PDF 듀얼페인 결합이라 import 불가·데이터모델 상이 → "차용" 아님, 공수 재산정). Author엔 **기존문서 편집 진입이 없음**(`openExisting`은 Explorer 단독 호출·`editor.js:82`) → 좌측 패널에서 열기·편집하려면 **`openExisting` 신규 배선**. `openDoc`(`author.js:68`)의 Explorer 리다이렉트(`index.html?page=`)도 분리목표와 모순 → 변경 필수.

### ⏭️ 제외 / 후속
- **platform-wide 콘텐츠 엮기**(전역 검색 노출·시스템 간 공유) — 별도 **전략 토론** 후. 소유권 선행 필수.
- **Explorer edit-in-place(`editor.js:78` .md 분기)**: 노출 분리(P2) 완료 시 Explorer 트리에 저작 `.md`가 사라져 이 진입 자체가 소멸 → `.md` 분기 정리. (셸 통합의 공유 편집기 우려도 이때 해소 = 순서 의존)

## Phase 분할 (검토 반영 — 5부분 순서·의존)

> 5부분이 한 계획으로 과대 → 독립 배포 가능 단위로 쪼갠다. **순서 의존이 핵심**.

| Phase | 내용 | 의존 | 위험 |
|------|------|------|------|
| **P1** ✅ | 저작면 현실화 — `md-editor.js SKELETON` 제거(빈 문서) | 없음 | 초저 | **완료 2026-07-17** |
| **P2** ✅ | Explorer 분리 — `tree-menu.js` 병합 제거 (`editor.js` `.md` 분기·`app.js renderMarkdownDoc` 정리는 **P3로 이연** — 딥링크 읽기 경로 잔존 때문) | 없음 | 저 | **완료 2026-07-17** (범위 축소) |
| **P3** ✅ | 셸 통합 — 오버레이→셸 마운트 + 71 자산 이식 + 좌측 패널 UI 신규 + `openExisting` Author 배선 | **P2 선결**(안 하면 공유 편집기가 Explorer서 깨짐) | 중 | **완료 2026-07-17** |
| **P4** ✅ | 소유권 — 서버측 owner 캡처 + `/api/authored` 인증·필터 + **정적서빙 누수 대책** | **아래 결정1·2 선결** | 고(백엔드) | **완료 2026-07-17** |

## 미해결 / 협의 필요

> **2026-07-17 — 결정 확정 (업계 표준·최신 트렌드 기준, 사용자 위임).** 아래 5건 확정. P3/P4 착수.

### 🔴 착수 전 반드시 결론낼 2건 (P4 설계 좌우) — ✅ 확정
1. **정적서빙 누수 대책** → **(a) 인증 백엔드 엔드포인트 경유** 확정. `GET /api/authored/{id}`(또는 `/content`)가 요청마다 소유권 확인 후 본문 반환. `app.js:431`·`editor.js:80`의 직접 `fetch(정적url)`을 API 호출로 교체. authored `.md`는 정적 서버가 서빙하지 못하게(라우트 차단 또는 루트 밖 위치) 보장. 근거: 개인 UGC를 공개 웹루트에서 서빙하지 않는 건 보안 기본(Notion·Google Docs·GitHub 동일).
2. **소유권 저장 위치** → **서버측 owner_id 캡처** 확정. `save_markdown`(`require_editor`, 신뢰 user dict)에서 owner를 서버가 캡처해 sidecar/인덱스 기록. front matter `author`는 표시용일 뿐 권한 판정에 미사용(편집가능·위조 가능). 근거: 권한·소유권 SSOT는 절대 클라이언트 편집 가능 위치에 두지 않음.

### 협의 (설계 시) — ✅ 확정
3. **셸 통합 방식** → **(b) 좌측 패널 고정 + 우측 편집 스플릿** 확정. 셸 소유 = `author.html`, 편집기는 우측 마운트. 전체화면 오버레이(`css/md-editor.css` fixed/z-4000) 폐기, 공통 헤더·시스템 스위처 유지. topbar close 버튼은 셸 nav와 중복 → 제거/정리. 근거: Notion·VS Code·Obsidian·Google Docs 등 현대 문서도구 표준(사이드바 고정+본문).
4. **저작면 기본 구조** → **빈 문서 시작** 확정(P1에서 SKELETON 제거로 이미 반영). 표지/통일 양식은 후속.
5. **admin 가시성** → **소유자 본인만**(admin 예외 없음) 확정. 최소 권한 원칙 — 이번 P4는 순수 owner-scoped. admin 큐레이션 열람은 별도 후속 기능으로 분리.
6. **좌측 패널 재사용 깊이** — Plan-66 패널은 import 불가(translator 결합) → **UI 패턴 신규 구현** 전제. Notebook 룩앤필 맞춤 범위는 구현 시 판단.
7. **`highlightAuthoredDoc`·`onMdEditorSaved=loadRecent`(author.js:185)·Explorer 저장 훅(`loadContent`·`loadMenuData`)** — 노출 분리로 대부분 무의미 → 새 패널 기준 재배선·정리.

## 산출물 (예상)
- 수정: `js/md-editor.js`·`css/md-editor.css`(오버레이→셸 마운트, SKELETON 제거), `author.html`·`js/author.js`·`css/author.css`(셸+좌측 패널), `js/tree-menu.js`(병합 제거), `backend/`(authored API 소유자 필터 + 소유권), 필요 시 `js/editor.js`(Explorer edit-in-place 정리)
- 이력: 완료 시 `reports/plan-72-feedback-*.md`

## Notes (결정 · 트레이드오프)
- **Plan-71 관계 정정 (직교 아님, 껍데기 대체)**: 71을 "편집기 그릇(생김새)"로만 봤으나, 사용자 진짜 요구는 "편집기가 **플랫폼 셸 안**에 살아 헤더가 유지되는" 구조였다. 71은 오버레이의 *스타일*만 개선 → 오버레이 전제 자체가 miss. 72가 그 **껍데기(전체화면 오버레이)를 셸 마운트로 대체**한다. **71의 시각 자산(밝은 바·시트·히어로 제목·표지 접힘·dirty·다크)은 버려지지 않고 셸 안 레이아웃으로 이식** — 바뀌는 건 최상위 컨테이너 하나.
- **소유권 먼저, 엮기 나중**: 전역 공유를 소유권 없이 하면 "누구 것인지 모른 채 다 보임"(현 상태) 재발. 순서 고정.
- **가장 싼 시점**: 저작 문서 0개인 지금. 늦출수록 마이그레이션·오학습 누적.
- **범위 주의**: 5부분(셸 통합·저작면·노출 분리·소유권·좌측 패널)은 서로 얽혀 있어 한 계획이 크다. 착수 시 Phase 분할(예: 셸+패널 UI 먼저 → 소유권 백엔드 → 노출 분리) 검토.

## Progress Log
- 2026-07-17 — **P3·P4 구현 완료 (계획 전체 종료)** (`/run-plan`, 결정 5건 업계표준 확정 후). **결정**: ①정적누수=인증 엔드포인트 경유(+`data/authored/` 이전) ②소유권=서버측 owner_id ③셸=좌패널+우편집 스플릿 ④저작면=빈문서 ⑤admin=예외없음(owner-only). **P4 백엔드**(`api/document.py`): 저장 `contents/authored/`→`data/authored/` 이전(nginx 403 영역, 정적누수 차단), `/api/save-markdown` name 계약+서버측 owner 캡처(`_owners.json` 원자적)+덮어쓰기 소유자검사(fail-closed), `/api/authored` 인증·소유자필터, 신규 `GET /api/authored/content`(인증·소유자). 백업 best-effort(권한실패 비치명). **P3 프론트**: `md-editor` 오버레이(fixed/z-4000) 폐기→Author 셸 `#au-editor-host` 인셸 마운트(공통 헤더 유지), `author.html`/`author.css` 워크스페이스 스플릿(좌 '내 문서' 패널+우 편집), `author.js` `openDoc` Explorer 리다이렉트 폐기→content API 경유 인셸 편집, `editor.js` 死 `.md` 분기 제거, `tree-menu.js` 死 `highlightAuthoredDoc` 제거. **검증(로컬 Docker:80)**: 저장/목록/content 200, 정적 `/data/authored/*.md`·`_owners.json` 403·구경로 404·미인증 401, **소유권 격리**(임시 2계정: 타인 목록0·읽기403·덮어쓰기403), fail-closed(고아 파일 403), UI 왕복(신규→저장→패널반영→닫기→홈→카드클릭 재편집, 헤더 유지, 콘솔0, 라이트/다크 스크린샷). code-review Critical 2건 반영(정적누수 배포경계=DEPLOY-QUEUE 하드닝 기록·auth.db 동반노출 명시 / 저장 fail-closed 수정). 보고서 `reports/plan-72-feedback-2026-07-17-P3P4.md`. **미해결/협의 5건 확정 완료 → plan 종료(done 이관).**
- 2026-07-17 — **P1·P2 구현 완료** (`/run-plan`, 로컬 Docker:80 검증). P1: `md-editor.js SKELETON` 제거→빈 문서. P2: `tree-menu.js` `/api/authored` 병합 제거(`fetchMergedMenu`→`fetchMenuData`), 死 authored-leaf 처리·`icon-authored` CSS 정리. **사전 분석 발견으로 P2 범위 축소** — 원안의 `editor.js .md 분기 정리`는 딥링크 읽기 경로(`author.js openDoc`→`index.html?page=`, Plan-70 잔류)가 살아있어 지금 지우면 회귀 → **P3로 이연**(openDoc 리다이렉트 제거와 한 세트). 검증: Explorer 트리 "작성 문서" 폴더 소멸·콘솔 0, Author 빈 편집기·읽기/편집 경로 무손상. 보고서 `reports/plan-72-feedback-2026-07-17.md`. **잔여 P3(셸 통합)·P4(소유권, 결정 2건 선결) → plan 활성 유지.**
- 2026-07-16 — **방향 캡처 스텁 생성**. Plan-71(편집기 화면) 논의 중 파생. Explorer `/api/authored` 병합 노출을 사용자가 재확인 → "Author 안에서·소유자에게만 + Notebook 좌측 패널 차용" 방향 확정.
- 2026-07-16 — **셸 통합·저작면 현실화 2요구 추가**. Plan-71 실물 확인 후 사용자 피드백: (1) 전체화면 오버레이가 공통 헤더를 덮어 시스템 정체성이 끊김 → 편집기를 Author 셸 안으로(헤더 유지), (2) 골격 프리셋(개요/배경/…)이 비현실적 → 저작면 현실화. 스코프 3→**5부분**, Plan-71 관계를 "직교"→"71 껍데기를 72가 대체(시각 자산은 이식)"로 정정. 71은 완료(시각 개선분 유효)이되 오버레이 전제는 72가 교체.
- 2026-07-16 — **plan-advisor 검토 반영**: (1) 🔴 정적서빙 소유권 누수 발견 — 리스트 필터만으론 불충분, `.md` 인증 경유/루트 이전이 P4 전제. (2) 소유권 SSOT=서버측(front matter 아님). (3) part5 정정 — Notebook 패널 import 불가(translator 결합)→UI 신규 구현, Author엔 편집 진입 없음→`openExisting` 신규 배선·`openDoc` Explorer 리다이렉트 변경 필수. (4) `/api/authored` 인증 게이팅 필요. (5) **Phase 분할 P1~P4**(P2가 P3 선결). (6) 협의1 셸 통합=스플릿(b) 권장. 착수 전 결론 2건(정적누수 대책·소유권 위치) 명시.
