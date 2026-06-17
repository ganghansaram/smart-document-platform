# Plan-60 Phase 3c — 내보내기 버튼 UI + 검증 피드백

> 작성 2026-06-17 · 범위: `MdEditor` "DOCX 내보내기" 버튼 → `/api/export-docx` → 브라우저 다운로드
> 관점: 개발책임자(통합·UX) + 코드전문가(정확성·회귀)

## 1. 구현 요약

| 변경 | 내용 |
|------|------|
| `js/md-editor.js` 헤더 버튼 | `[저장] [DOCX 내보내기] [닫기]` — `data-act="export"` |
| `js/md-editor.js` `doExport()` | 폼 메타 + `editor.getMarkdown()` → front matter 합성 → `POST /api/export-docx` → Blob → `<a download>` 트리거(파일명=제목.docx) |

- **순수 추가**: 기존 저장/닫기 로직·MdEditor 구조 무변경, 버튼 1개 + 함수 1개.
- **위치 근거**: 내보내기는 `require_editor` 권한 + 저작 흐름의 마지막 단계 → 편집기 모달이 가장 자연스러운 진입점. (뷰모드 버튼은 뷰어가 export 불가하므로 불필요)

## 2. 직접 테스트 검증 (Playwright 실제 브라우저 + 산출물 디코드)

### UI 경로
- ✅ "DOCX 내보내기" 버튼 존재·배치(스크린샷 확인)
- ✅ 클릭 → `/api/export-docx` **200**
- ✅ 다운로드 트리거 — 파일명 `제출 보고서.docx` / `3c 내보내기 검증.docx`, blob 11~12KB(PK 매직)
- ✅ 콘솔 에러 0

### 폼 메타 → md 합성 (스파이로 요청 본문 캡처)
- ✅ 헤더 폼(제목·작성자·문서번호·보안등급) → front matter 정확히 합성
  (`title`/`doc_number: "TR-2026-300"`/`classification: "대외비"` 확인)

### 산출물 docx 충실도 (엔진 직접 통과 + XML 측정)
- ✅ 표지: 제목·문서번호(TR-2026-301)·보안등급(대외비) + 페이지 나누기
- ✅ 표 colspan(gridSpan) 보존 · 본문 강조 · 머리/바닥글 2파트
- ⚠️ thead/tbody 없는 **평면 표의 rowspan(vMerge) 미보존** — Phase 1 에서 문서화된 "병합표 충실도 한계 → 워드 다듬기" 범주(정상 구조 표는 PoC 에서 병합 보존 확인). colspan 은 보존.

## 3. 회귀 — 무영향
- 저장/닫기/openExisting 등 기존 MdEditor 동작 무변경(버튼·함수 추가만).
- 콘솔 에러 0.

## 4. 🎯 저작 → 통일양식 DOCX END-TO-END 완성
dev 환경 풀사이클 동작 확인:
**새 문서 → 작성(TUI) → 저장(`/api/save-markdown`) → 열람(`loadContent` 렌더) → 편집(`Edit`→`openExisting`) → DOCX 내보내기(버튼→다운로드)**

## 5. 남은 것 (전부 부가)
| 항목 | 성격 |
|------|------|
| 메뉴 편입 | 작성 문서 발견성(admin) — 현재 직접 URL |
| "워드 다듬어 제출" 안내 UX | 내보내기 후 토스트/모달 안내 문구(미세) |
| 2b soft lock·소유권 | 공유 저작 안전망 |
| 서빙 수식(katex)·다크 본문·표지 헤더억제(3b) | 마감 폴리시 |
| 하드닝(SSRF·크기제한·Windows pandoc)·수식 Word 확인·프로덕션 이미지 재빌드 | 배포 전 |
