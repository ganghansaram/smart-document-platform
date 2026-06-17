# Plan-60 Phase 2a — 영향성 분석 (신규 MD 편집기 + 저장 + 서빙)

> 작성 2026-06-16 · 착수 전 기존 코드 영향성 사전 점검 (codebase 조사 기반)
> 결론: **대부분 순수 추가. 기존 수정은 4곳·전부 `.md` 확장자 분기로 격리 가능 → 저위험.**

## (A) 순수 추가 (기존 무수정)
1. `js/md-editor.js` 신설 — TUI Editor 래퍼 + 독립 모달 (`#md-ec-modal`). EditorCore 미사용.
2. 백엔드 `POST /save-markdown` 신설 — 기존 `save_document` 와 독립. `require_editor` + `contents/` 경로검증 + 백업 로직 재사용, **단 `prettify_html` 미적용**.
3. 콘텐츠 폴더 `contents/authored/` 신설 — 기존 HTML 문서와 격리, 정적 서버 그대로 서빙.
4. `index.html` 에 TUI 번들 로드 3줄 (`toastui-editor-all.min.js`·`.min.css`·i18n). Monaco(`monaco`)와 전역 네임스페이스(`toastui`) 분리 → 충돌 없음.
5. `data/menu.json` 항목 추가 — `menu.py` 의 `_is_system()`/`_reassemble()` 가 URL 패턴 기반이라 `.md` URL 통과.

## (B) 기존 파일 수정 4곳 (+리스크)
| 파일:함수 | 수정 내용 | 기존 기능 리스크 |
|-----------|-----------|------------------|
| `js/app.js : loadContent()` (≈377, 분기 417~428) | `url.endsWith('.md')` → marked+DOMPurify 렌더 분기 | **낮음** — `.md` 조건 선행 배치 시 HTML 경로 무수정 (이미 glossary/analytics 특수분기 패턴 존재) |
| `js/editor.js : openEditor()/updateEditButtonVisibility()` (≈128) | `.md` → `openMdEditor()` 분기, 비편집목록 처리 | **낮음** — HTML 편집은 별도 함수로 무간섭. `EDITOR_CONFIG.enabled` 플래그 유지 |
| `backend/api/document.py : save_document()` (≈57, prettify ≈99) | — | **중** — `.md` 에 `prettify_html` 적용 시 손상 → **별도 `/save-markdown` 엔드포인트로 회피 권고** |
| `tools/build-search-index.py : scan_html_files()` (≈360) | `*.html` → `*.html`+`*.md` 순회 | 낮음(별도 루프). **Phase 2a 범위 밖** — 인지만 |

## (C) 통합 접근 권고 — 영향 최소
- **EditorCore(Monaco) 재사용 불가**: `_domBuilt` 싱글턴이 `#ec-modal`/`#ec-confirm` 전역 점유(editor-core.js:77~133), 내부 `state.editor` 가 Monaco 전용 → TUI 끼우면 충돌·복잡도↑.
- **권고**: ① `js/md-editor.js` `MdEditorCore`(독립 모달·저장 훅·미저장 경고를 EditorCore 와 동일 인터페이스로) ② `editor.js openEditor()` 에 `.md` 분기 ③ `/save-markdown`(prettify 없이 원문 저장) ④ `loadContent()` MD 렌더 분기.
- 두 편집기 동시 오픈은 설계상 배제(키다운 핸들러가 `state.open` 으로 보호, editor-core.js:531).

## (D) 핵심 미결/주의점
1. ~~marked + DOMPurify 미벤더링~~ **✅ 해소 (2026-06-16 점검)**: `js/lib/marked.min.js`·`purify.min.js`·`katex.min.js` **모두 이미 벤더링됨**. index.html 은 현재 katex 만 로드(marked/purify 미로드) → `<script>` 2줄 추가만 필요. **검증된 선례 존재**: `js/translator.js:1210~1224` Notebook MD 뷰어가 이미 `front matter 스트립 → marked.parse → DOMPurify.sanitize(html, {ADD_ATTR:['style']}) → innerHTML` 패턴으로 MD 서빙 중 → `loadContent()` MD 분기에 **그대로 재사용**. (TUI 내부 marked 의존 불필요 — 독립 marked.min.js 사용). 수식(`$..$`)은 ai-chat.js 의 `katex.renderToString` 패턴 추가 적용 가능(서빙 미세항목).
2. **콘텐츠 모델 이원화(HTML/MD 공존)** — `loadContent`·`openEditor`·`updateEditButtonVisibility` 모두 URL 확장자 분기 필수.
3. **검색/RAG 인덱싱 누락** — `build-search-index.py` 가 `*.html` 만 순회 → `.md` 는 검색·RAG 미노출. Phase 2a 범위 밖, 후속 처리.
4. **메뉴 편입 권한** — `menu.py` GET/POST 모두 `require_admin`. drafts→published 개념 없음(메뉴에 URL 있으면 즉시 공개).
5. **`save_document` 경로검증** — `contents/` 하위만 허용 → `contents/authored/` 통과. `.md` 에 `prettify_html` 금지 필수.

## 권고 착수 순서 (2a 잘게)
- **2a-1**: `/save-markdown` + `contents/authored/` + marked/DOMPurify 벤더링 (기반)
- **2a-2**: `js/md-editor.js`(TUI 모달) + index.html 통합
- **2a-3**: `loadContent` MD 렌더 분기 + "새 문서 작성" 진입
→ 2a-3 완료 시 **작성→저장→열람** 성립. 이어 3c(내보내기 버튼) 붙이면 **저작→DOCX end-to-end** 완성.
