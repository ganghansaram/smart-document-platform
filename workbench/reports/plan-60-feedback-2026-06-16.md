# Plan-60 실행 피드백 — Explorer WYSIWYG 편집기 (Phase 0 PoC)

> 실행일 2026-06-16 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/60-doc-authoring-export.md` (당시 파일명 `60-explorer-wysiwyg-editor.md`, 2026-06-16 통합 재정립 시 개명)
> 범위: 선행 결정 확정 마무리(MD 저장 경로) + **Phase 0 PoC** (Toast UI 폐쇄망 드롭인 + MD↔WYSIWYG 토글 동작 검증)

## 요약
- 완료: **Phase 0 PoC ✅** (성공) + MD 저장 경로 결정 확정
- 변경/신규 파일: 4개 (PoC 1 + 벤더 번들 3)
- Critical: 0 · Warning: 1 (다크 테마 미브리지·Phase 2 이월) · Suggestion: 2
- **PoC 결론: Toast UI Editor 의 무빌드 폐쇄망 드롭인 = 검증 완료. 방향 A 기술 전제 성립.**

## 구현 결과

| 항목 | 상태 | 산출물 | 메모 |
|------|------|--------|------|
| Toast UI 벤더링 (3.2.2 동결) | ✅ | `js/lib/tui-editor/` (700KB) | `-all.min.js` + `min.css` + `i18n/ko-kr` |
| PoC 페이지 | ✅ | `poc-tui-editor.html` (루트) | 토큰 셸 + 토글 + .md 출력 + 다크 토글 |
| MD 저장 경로 결정 | ✅ | 계획서 §7 반영 | 신규 엔드포인트 필요(코드 검증) |

### 벤더 파일
- `toastui-editor-all.min.js` (534KB) — **ProseMirror 내장 독립 번들** (NHN uicdn)
- `toastui-editor.min.css` (168KB)
- `toastui-editor-i18n-ko-kr.min.js` (2.7KB)

## 검증 결과 (Phase 4)

### 사용성 테스트 (Playwright, `http://127.0.0.1:8080/poc-tui-editor.html`)
| 검증 항목 | 결과 |
|-----------|------|
| 폐쇄망 (CDN 0접속) | ✅ uicdn/jsdelivr/cdn 매칭 네트워크 요청 **0건** |
| 콘솔 에러 | ✅ **0건** (최종 번들) |
| Markdown ↔ WYSIWYG 토글 | ✅ 하단 네이티브 탭 정상 전환 |
| `.md` 직렬화 (저장 시뮬) | ✅ 위지윅 왕복 후 구조 보존 (글머리 `-`→`*` 정규화만) |
| 한국어 i18n | ✅ 툴바 전부 한글 (굵게·기울임꼴·표 삽입 …) |
| 디자인 토큰 셸 브리지 | ✅ 상단 바·노트·출력창 토큰 정상 |
| 다크모드 (에디터 본문) | ⚠️ 미브리지 — 본문 라이트 유지 (Phase 2) |
- 스크린샷: `workbench/screenshots/plan-60-poc/` (01-markdown-light, 02-wysiwyg-light, 03-wysiwyg-dark)

### 회귀 스팟체크
- 기존 `js/editor-core.js`(Monaco)·`backend/api/document.py` **미변경** → Explorer 기존 편집 경로 영향 0. PoC 는 독립 페이지·독립 번들로 완전 격리.

> code-reviewer·design-reviewer·/review-ui 정식 호출은 **Phase 1~2(실제 통합 코드)로 이연**. PoC 는 병합 대상이 아닌 타당성 스파이크라 과검증 회피 (CLAUDE.md "과도한 엔지니어링 금지").

## 🧑‍💻 코드 전문가 관점
- **핵심 함정 발견 (재사용 가치 높음)**: npm `@toast-ui/editor` 의 `dist/toastui-editor.js` 는 `require("prosemirror-*")` 로 ProseMirror 를 **외부 의존**으로 둠 → 번들러 없이는 `PluginKey undefined` 로 사망. jsdelivr 자동생성 `.min.js` 도 동일(추가로 Terser 손상). **무빌드 드롭인은 NHN 공식 uicdn 의 `-all.min.js`(ProseMirror 내장)만 가능.** → 계획서 §3 "UMD 드롭인" 전제는 **출처가 uicdn `-all` 일 때만 참**. 버전 동결 시 이 파일을 고정해야 함.
- MD 저장 경로: 코드 확인 결과 `save_document` 는 (1) 파일 미존재 404 → **생성 불가**, (2) `prettify_html` 무조건 적용 → MD 손상. 신규 엔드포인트 분리가 추측이 아닌 **확정 사실**.

## 🎨 UI/UX 관점
- MD↔WYSIWYG 네이티브 탭 = 학습비용 0, 계획서 가설대로 일반 엔지니어 친화적.
- 위지윅 왕복이 표·코드블록·인용까지 무손실(글머리 표기만 정규화) → "쉽게 쓰고 공유" 목표에 부합.

## 🖌️ 웹디자인 관점
- 셸 토큰 브리지는 즉시 통일감 확보. **단, 에디터 본문은 Toast UI 자체 스킨이라 토큰이 안 먹음** → Phase 2 에서 `toastui-editor-dark` 클래스 토글 + CSS 변수 매핑 시트 필수. 라이트 모드 본문은 플랫폼과 충돌 없이 자연스러움.

## 👤 사용자 관점
- 빈 화면에서 바로 글·표·코드 작성 가능 = 진입장벽 해소 체감. PoC 수준에서도 "이거면 쓰겠다" 수긍 가능한 완성도.

## 잔여·후속 제안
- [ ] **베이스라인 캡처** (Phase 0-사전 잔여) — 대표문서 코퍼스·작성 소요시간, Phase 1 착수 전 수행
- [ ] **Phase 1**: `EditorEngine` 선택 레이어(Monaco|ToastUI) + 공통 모달 통합 + `POST /api/documents` (MD-safe 생성/저장)
- [ ] **Phase 2**: 에디터 본문 다크 테마 브리지(`toastui-editor-dark` + 토큰 매핑 시트) — 본 PoC Warning 해소
- [ ] PoC 페이지(`poc-tui-editor.html`)는 Phase 1 통합 후 제거 또는 `workbench/` 이관
- [ ] 번들 출처 메모: 향후 버전 업 시 반드시 **uicdn `-all`** 계열에서 수령 (npm dist 금지)

## 검증 패스 (2026-06-16, 독립 재검토)

### 계획서 정합성 (grep)
- `배타적 잠금/담당자/위임/전용 풀스크린` 매칭 6건 전부 **"제외됨·이력 설명" 맥락**(soft lock 전환 근거, 확정 결정). **잔존 모순 0건** ✅

### 벤더 참조 무결성
- `poc-tui-editor.html` 의 3개 참조(`toastui-editor.min.css`·`-all.min.js`·`-i18n-ko-kr.min.js`)가 실제 벤더 파일과 **정확히 일치**, 삭제된 손상 파일(`toastui-editor.js`·jsdelivr min) 참조 0건 ✅

### 코드 품질 (code-reviewer 에이전트)
- **Critical 0 / Warning 6 / Suggestion 5 — 종합 "양호"**
- 보안 ✅: `out.textContent = editor.getMarkdown()` (innerHTML 미사용, XSS 경로 없음) · `usageStatistics:false` (외부 전송 차단)
- **Warning (실위반, 내가 도입)**: tokens.css 에 정확히 대응 변수가 있는데 픽셀 하드코딩 — `font-size 15px`→`--font-title`, `12px`→`--font-small`, `13px`→`--font-body`, `.poc-btn padding 8px 14px`→`--space-*`. CLAUDE.md "하드코딩 금지" 위반.
- Suggestion: `<button>` 에 `type="button"` 명시(현재 form 밖이라 무해), 전역 `var editor`→IIFE(Phase 1), 내부 CSS 클래스 의존 브리지는 Phase 2 공식 커스텀 프로퍼티 확인 후.

### 검증 결론
- 기능·보안·정합성 **이상 없음**.
- ✅ **하드코딩 6건 정리 완료 (2026-06-16)**: `font-size 15/13/12px`→`--font-title/--font-body/--font-small`, `.poc-btn padding 8px 14px`→`var(--space-sm) var(--space-md)`. 토큰값 1:1 동일(버튼 패딩만 14→16px 근사). 재grep 결과 잔존 하드코딩 font-size/padding/non-#fff color **0건**. (`#fff` 는 악센트 위 흰 글자라 토큰화 부적합 — 다크 토큰 적용 시 가독성 깨짐 — 의도적 유지)

## 커밋 제안 (사용자 요청 시)
```
기능 [Explorer] Plan-60 Phase 0 PoC — Toast UI 폐쇄망 드롭인 검증

- js/lib/tui-editor/ 에 Toast UI Editor 3.2.2 동결 벤더링 (uicdn -all 번들)
- poc-tui-editor.html: MD↔WYSIWYG 토글·.md 직렬화·한국어 i18n·토큰 셸 검증
- 폐쇄망(CDN 0접속)·콘솔 0에러 확인
- 계획서: MD 저장 경로 결정 확정, Phase 0 완료 반영

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
```
> 주의: 벤더 번들은 npm dist 가 아닌 NHN uicdn `-all.min.js` 사용 (ProseMirror 내장, 무빌드 전제 조건)
