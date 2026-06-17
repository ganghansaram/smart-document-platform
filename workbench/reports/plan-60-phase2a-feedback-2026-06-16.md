# Plan-60 Phase 2a — 저작 경로(편집기·저장·서빙·편집) 구현 + 검증 피드백

> 작성 2026-06-16 · 범위: 2a-1(저장 백엔드) + 2a-2(TUI 편집기) + 2a-3(서빙·편집 연결)
> 관점: 개발책임자(영향성·통합) + 코드전문가(정확성·보안·회귀)

## 1. 구현 요약 — "새 문서 → 작성 → 저장 → 열람 → 편집" 풀사이클

| 산출물 | 내용 | 성격 |
|--------|------|------|
| `backend/api/document.py` `POST /api/save-markdown` | `contents/authored/` 전용 MD 저장(신규+덮어쓰기+백업, prettify 미적용, 경로/traversal/확장자 검증) | 기존 `save_document` 무수정·추가 |
| `js/md-editor.js` `window.MdEditor` | Toast UI 풀스크린 모달(openNew/openExisting), front matter 폼↔합성, 골격 프리필 | 신규 |
| `css/md-editor.css` | 오버레이·헤더·TUI 토큰 브리지 | 신규 |
| `js/app.js` `renderMarkdownDoc()` + `loadContent()` `.md` 분기 | front matter 스트립→marked→DOMPurify→`<article>` → 기존 후처리 파이프라인 통과 | 분기 추가 |
| `js/editor.js` `openEditor()` `.md` 분기 | `.md`면 `MdEditor.openExisting`, HTML 은 기존 Monaco | 분기 추가 |
| `index.html` | TUI 번들·i18n·md-editor.css·marked·purify 로드 | 추가 |
| `js/app.js` nav | "새 문서" 버튼(auth-editor-only) | 추가 |
| `contents/authored/` | 저작 문서 격리 폴더(.gitkeep) | 신규 |

## 2. ⚠️ 기존 기능 영향성

- **편집기 이원화 — 충돌 0**: 기존 EditorCore(Monaco, `#ec-modal` 싱글턴)와 신규 MdEditor(`.md-editor-overlay`)는 **DOM ID·전역 네임스페이스(monaco vs toastui) 완전 분리**. Playwright 로 두 인스턴스 공존·ID 충돌 0 확인.
- **`loadContent` 분기 격리**: `.md` 만 마크다운 렌더, 그 외는 기존 HTML 경로 그대로. HTML 문서(home.html) 회귀 정상 확인.
- **저장 분리**: `/api/save-markdown` 은 `save_document`(HTML)와 별개 함수·경로. `prettify_html` 미적용으로 MD 원문 보존.
- **무빌드·폐쇄망 준수**: marked/purify/katex/TUI 전부 `js/lib/` 기존 벤더링 재사용(신규 다운로드 0).

## 3. 직접 테스트 검증 (Playwright 실제 브라우저)

### 단위
- **2a-1 저장 API**: 미인증 401 · 신규 created=true · 덮어쓰기+백업 · overwrite=false→409 · authored 밖/traversal/.txt/빈내용 → 400 · 원문(prettify 미적용) — **8/8**
- **2a-2 편집기**: "새 문서"→모달 오픈 · 골격 프리필 · 작성자 자동입력 · ko-KR 탭 · 저장→파일 생성+front matter 합성 · 콘솔 에러 0
- **2a-3 서빙·편집**: `.md` 렌더(heading/표/목록/강조, 원문·메타 누출 0) · **섹션네비 자동생성**(기존 후처리 통과) · Edit→openExisting(front matter→폼 자동채움) · HTML 회귀 무손상

### 통합 재검증 (1회 풀체인, 2026-06-16)
저장(200) → 서빙 렌더(article/h1/표/강조 ✅, 누출 0) → 편집 진입(제목·보안등급 파싱 ✅) → **authored `.md` → `/api/export-docx`(200·DOCX·PK매직·12KB)**.
→ **저작본이 3a 내보내기 엔진까지 실제로 흐름이 확인됨** (3c 는 이 호출을 버튼에 연결만 하면 됨).

## 4. 알려진 한계 · 후속 (정직한 기록)

| # | 항목 | 영향 | 권고 |
|---|------|------|------|
| A1 | **메뉴 미편입** | 작성 문서가 트리 메뉴에 없어 직접 URL 로만 접근 | 메뉴 등록 UX(`menu.py` require_admin) — 별도 단계 |
| A2 | **서빙 수식 미렌더** | `$..$` 가 본문에 평문 노출(렌더 X) | ai-chat `katex.renderToString` 패턴 추가(미세). DOCX 내보내기는 정상 |
| A3 | **soft lock·소유권 부재** | 동시 저장 last-write-wins(기존 Explorer 와 동일) | 2b 단계(§6-A) |
| A4 | **다크모드 본문 브리지** | TUI 본문 다크 미세 | Phase 2 폴리시 |
| A5 | **목록/표 자동 검색 인덱싱** | `.md` 가 검색/RAG 미노출(build-search-index `*.html`만) | 범위 밖, 후속 |
| A6 | **제목=파일명 결합** | 기존 문서 제목 변경 시 파일명 불일치(제목 readonly 로 회피 중) | 리네임 기능은 후속 |

## 5. 설계 메모 (코드전문가)

- **MdEditor 독립 모달 채택 근거**: EditorCore 는 `_domBuilt` 모듈 싱글턴 + Monaco 전용 `state.editor` 인터페이스 → TUI 수용 시 결합도·복잡도 급증. 독립 모달이 영향 최소(영향성 분석 §C 권고 준수).
- **front matter 폼↔합성**: 사용자가 YAML 을 직접 만지지 않음. 저장 시 `title/author/date/doc_number/classification` 합성. 기존 문서 열 때 역파싱하여 폼 복원.
- **신규 문서 overwrite=false**: 동명 파일 실수 덮어쓰기를 409 로 차단.

## 6. 다음 단계

1. **3c 내보내기 버튼** — authored `.md` → `/api/export-docx` (통합 재검증으로 이미 동작 확인 → 버튼·다운로드 트리거만). **저작→통일양식 DOCX end-to-end 완성.**
2. **메뉴 편입(A1)** — 작성 문서 발견성.
3. **2b soft lock·담당자 소유권(A3)** — 공유 저작 안전망.
