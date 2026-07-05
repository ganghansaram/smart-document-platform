# plan 69 실행 피드백 — Gmail식 하이브리드 관리자 설정 드로어
> 실행일 2026-07-05 · 실행자 Claude(/run-plan) · 대상 workbench/plans/69-hybrid-admin-settings-drawer.md

## 요약
- 완료 Task **17/17** (A1~A3·B1~B5·C1~C3·D1~D5) — Phase 0~3 END-TO-END 완성
- 변경 파일 **4** (js 2 · css 1 수정 · css 1 신규)
- 리뷰 소견: Critical 2 · Cleanup 1 · Convention 1 → **전부 수정/판단 완료** (+ 회귀 1건 자체 발견·수정)
- 착수 전 협의 3건 확정(AskUserQuestion): 필드범위=시스템탭 전체(무거운 것만 제외) · 진입점=공통헤더 톱니 1개 · 로딩=lazy-load

## 구현 결과

| 영역 | 상태 | 변경 파일 | 메모 |
|------|:---:|-----------|------|
| Phase 0 컨테이너 파라미터화 | ✅ | `js/admin-settings.js` | `renderAdminSettings(container, opts)` — 기본값 `#main-content`, 호출부 3곳 무변경. `opts.only`/`opts.mode` 지원 |
| Phase 1 드로어 프로토타입 | ✅ | `js/admin-settings.js` `css/settings-drawer.css` | `openSettingsDrawer`/`closeSettingsDrawer`/`_buildSettingsDrawer` + 우측 슬라이드. "전체 설정 열기 →" + 저장 |
| Phase 2 확장(공통화) | ✅ | `js/platform-header.js` | 공통 헤더 톱니 1개(admin 전용) → 전 시스템 커버. `_drawerSysMap` = {explorer, translator→notebook, compare→verify} |
| Phase 3 하드닝·회귀 | ✅ | `js/admin-settings.js` `css/admin-settings.css` | ESC·포커스트랩·teardown, 모달-온-모달 0(메뉴편집·danger·reset 제외), lazy-load, 다크·반응형, admin.html 회귀 0 |

### 핵심 설계 결정
- **2차 SSOT 회피**: "경량 필드 별도 목록" 대신 기존 스키마 재사용 + 드로어에서 **빈 sections 탭 필터**(메뉴 관리·규칙 관리 자동 제외) + Explorer 메뉴편집/danger zone는 `!_drawerMode` 게이팅.
- **호스트 body 미오염**: `body:has(.admin-settings-page)` → `body:has(.admin-settings-page:not(.admin-drawer-page))` 로 좁혀 admin.html 회귀 0 + 드로어가 호스트 body 배경/여백 안 건드림.
- **Author 제외**: 스키마에 author 설정 시스템 없음 → `_drawerSysMap` 미포함(톱니 미노출). 향후 author 설정 생기면 매핑 1줄 추가로 자동 편입.

## 검증 결과
- **게이트**: `node --check` 두 JS 통과. 프로젝트에 lint/build/typecheck 없음(Vanilla·무빌드). sim 라벨 테스트는 유사도 미변경으로 비해당.
- **실브라우저(Playwright, localhost:80 Docker)**:
  - Notebook 드로어: 14필드·단일탭·전체설정링크·저장 ✅, 메뉴편집/danger 제외 ✅
  - Verify 드로어: 탭 [유사도 검사, AI 비교] — 빈 "규칙 관리" 탭 필터 ✅ (플레이스홀더 미노출)
  - Explorer 드로어: 탭 [콘텐츠, 검색, 챗봇] — 메뉴 관리 탭·에디터·danger 완전 제외 ✅, 20필드
  - 저장 왕복: 토스트 발화·버튼 재활성·콘솔 에러 0 ✅
  - ESC 닫기·teardown·재오픈(오버레이 1개 재사용) ✅ · 포커스 close 버튼 진입 ✅
  - 다크모드: 카드 표면·탭바·토글 악센트 토큰 준수 ✅
  - **admin.html 회귀 0**: 풀 콘솔·사이드바 6시스템·페이지헤더·Explorer 메뉴편집 탭 정상, 톱니 미노출, body 배경 유지 ✅
  - 세션 전체 콘솔 에러 **0**
- **/code-review (high, 8각도 병렬 → 검증)**: 아래 소견 반영.

## 리뷰 소견 → 조치

| # | 심각도 | 소견 | 조치 |
|---|:---:|------|------|
| 1 | Critical | 드로어 fetch 실패/403 에러 마크업이 `admin-drawer-page` 누락 → 호스트 body 오염 + 1060px 레이아웃 오버플로 | `_pageCls` 재사용으로 에러/403 브랜치도 drawer 클래스 부여 ✅ |
| 2 | Critical | 로드 실패 후 저장 클릭 시 `_currentSettings` null deref → 버튼 영구 '저장 중...' 고착 | `_adminSave` 진입 null 가드(토스트 후 반환) + close 시 `_currentSettings=null` 리셋(stale POST 차단) ✅ |
| 3 | Plausible | 오픈 시 포커스 미이동 → 첫 Tab이 배경으로 탈출(트랩 누수) | rAF 에서 close 버튼 포커스(트랩 진입점) ✅ |
| 4 | Plausible | fetch 인플라이트 중 닫으면 뒤늦은 렌더가 `_drawerMode` 오염·숨은 body 재렌더 | 동기 `_drawerOpen` 플래그 가드 ✅ |
| 5 | Cleanup | `DRAWER_SYSTEM_MAP` 데드코드(platform-header가 자체 맵 보유) | 제거 ✅ |
| — | Convention(PLAUSIBLE) | 컴포넌트 테이블 미갱신 | 판단: 드로어는 Plan-69 전용(components.css 프리미티브 아님), modal.css도 미등재 — **비해당** |

### 자체 발견·수정한 회귀 (리뷰 후 실측에서)
- **mid-flight 가드 역회귀**: 처음 `.open` 클래스(rAF 비동기)로 가드 → localhost fetch가 rAF보다 빨라(마이크로태스크 우선) 정상 렌더가 잘못 중단(fields 0). **동기 `_drawerOpen` 플래그로 교체**하여 해결. 실측 재확인 완료.

## 5관점 피드백
- **개발책임자**: "교체 아닌 추가" 원칙대로 회귀면 최소. Phase 0 파라미터화가 향후 유연성의 열쇠 — 달성.
- **코드전문가**: 스키마 단일 SSOT 유지(2차 목록 회피), 전역 id 충돌은 비-admin 페이지 단독 존재로 회피, teardown/가드로 상태 잔여 0.
- **UI/UX**: 공통 헤더 톱니 1개로 동선 일관, 작업 맥락 유지(배경 딤+호스트 보임), 무거운 관리는 "전체 설정 열기 →"로 자연 이관.
- **웹디자인**: modal.css 우측정렬 변형, 토큰 100%(색/여백/radius/transition), 다크모드 자동 전환, 반응형 전폭.
- **사용자**: "번역/비교 중 그 시스템 토글 하나" 페인 정확 해소. admin 아닌 사용자에겐 톱니 비노출(혼란 0).

## 업계표준 재검토
- **무게 이분화**(경량=드로어 Gmail/Figma/Notion · 무거운 콘솔=페이지 GitHub/Stripe/AWS) 정합 유지. 통짜 오버레이(비표준) 회피.
- 접근성: role="dialog"·aria-modal·ESC·포커스 트랩·포커스 복귀 구현. (개선여지: `aria-modal` 이지만 배경 `inert`/`aria-hidden` 미적용 — 폐쇄망·Vanilla 범위에서 포커스 트랩으로 갈음. 수용한 한계.)

## 잔여·후속 제안
- (선택) Author 설정 시스템이 생기면 `_drawerSysMap`에 `author: 'author'` 1줄 + 스키마 추가로 자동 편입.
- (선택) 배경 `inert` 적용으로 스크린리더 완전 격리 — 현재 포커스 트랩으로 실용 충분.
- (선택) 드로어 저장이 전체 설정을 재제출하는 건 기존 admin.html 시맨틱 그대로(비파괴). 부분 PATCH는 별도 과제.

## 커밋 제안 (요청 시)
```
구현 [plan/69]: Gmail식 하이브리드 관리자 빠른설정 드로어

각 서브시스템(Explorer/Notebook/Verify)에서 페이지 전환 없이 그 시스템
설정을 우측 드로어로 조정. 무거운 관리(계정·대시보드·메뉴편집·초기화)는
admin.html 콘솔에 존치(Gmail식 하이브리드).

- renderAdminSettings 컨테이너 파라미터화(opts.only/mode) — admin.html 무변경
- 공통 헤더 admin 전용 톱니 1개 → 전 시스템 커버, admin-settings.js lazy-load
- 드로어에서 빈 탭 필터 + Explorer 메뉴편집/danger 게이팅(모달-온-모달 0)
- ESC·포커스트랩·teardown·다크·반응형, body:has 셀렉터 좁혀 호스트 미오염
- 리뷰 반영: 에러경로 클래스·저장 null가드·포커스진입·mid-flight 동기가드

검증: Playwright 실측(3시스템 드로어·저장왕복·다크·admin.html 회귀0·콘솔0)
```
