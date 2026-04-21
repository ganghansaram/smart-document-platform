# Plan-37 Phase 0 — 알려진 결함 (Known Issues)

> 회귀 방어망 구축 시 시맨틱 게이트가 탐지한 **현 converter 출력물의 기존 결함** 목록.
> Phase 0 baseline 확정 시점: 2026-04-21
>
> 이 결함들은 `test_golden_semantic_baseline` 에서 **known 처리** 된다.
> Phase 1~4 진행 중 자연스럽게 해결되면 해당 항목을 지우고 테스트 활성화.

---

## KI-001 · mypaper: 캡션 id `tbl-16` 중복

**fixture**: `mypaper` (`MyPaper_20251109_V2.8_Claude.docx`)
**rule**: `caption_id_unique`
**severity**: error → **원본 결함 처리** (converter 버그 아님)

**원인**:
원본 DOCX 작성자가 "표 16" 번호를 **두 번 사용**함.
- `<p id="tbl-16">표 16: α 파라미터에 따른 Recall@k 및 nDCG@k 상세 지표</p>`
- `<p id="tbl-16">표 16: 검색 방식별 검색 성능 비교 (Top-k=5)</p>`

**영향**:
- `<a data-fig-ref="tbl-16">` 참조 링크가 **항상 첫 번째 tbl-16 으로 이동** → 사용자 혼란
- 검색·북마크·스크롤 내비게이션이 두 번째 표에 도달하지 못함

**대응 방향**:
- 단기: 원본 문서 수정 요청 (저자에게 번호 재지정)
- 장기 (Plan-37 Phase 4 자연 해결):
  - Phase 4c SEQ 스위치 완전 지원 → Word 자동번호를 사용했다면 이 문제 자체가 안 생김
  - `_make_caption_id` 에서 id 충돌 감지 시 suffix 자동 부여 (`tbl-16-dup2`) 로직 추가 검토

---

## KI-002 · swa_kor: 이미지 추출됐으나 HTML 에 삽입 안 됨

**fixture**: `swa_kor` (`SWA_Sample_KOR.docx`)
**rule**: `image_orphan`
**severity**: warning
**기존 `contents/samples/SWA_Sample_KOR/SWA_Sample_KOR.html` 에도 동일 증상 확인** → 사전부터 존재한 converter 버그

**원인**:
- 원본 DOCX 는 이미지 12개 (내부 10 + 외부 URL 2)
- converter 가 내부 이미지 10개를 `swa_kor_images/` 로 추출 성공
- 하지만 HTML 에는 `<img>` 태그 0건, 대신 `<div class="shape-placeholder">` 9건
- 즉 문서가 `<w:drawing>` 을 `pic:pic` 대신 **도형 객체(`v:shape` 류)** 로 감쌌고, converter 는 이를 "추출 불가 도형" 으로 판정해 플레이스홀더만 출력
- 추출된 raw 이미지 파일과 HTML 렌더링 경로가 **분리**되어 고아 파일 발생

**영향**:
- 사용자가 문서 뷰어에서 이미지를 볼 수 없음 (플레이스홀더 경고만)
- 디스크에 사용되지 않는 이미지 파일 누적

**대응 방향**:
- Plan-37 범위 외. `workbench/plans/backlog.md` 에 별도 항목으로 등록 예정
- 수정안: `_has_unextractable_shapes()` 가 도형을 감지해도 해당 문단에 `pic:pic` 나 `inline drawing` 이 존재하면 정상 추출 경로로 폴백
- 임시 우회: 원본 DOCX 에서 도형을 "선택하여 붙여넣기 → 그림(PNG)" 으로 변환 후 재업로드

---

## KI-003 · mypaper: 헤딩 레벨 건너뜀 (h1 → h4)

**fixture**: `mypaper`
**rule**: `heading_level_skip`
**severity**: warning

**원인**:
원본 DOCX 에서 첫 heading 이 h1 이고 다음이 h4 (h2, h3 스킵). Word 자동번호·cascade 감지 문제가 아니라 **원본 문서의 스타일 사용 규칙이 비표준**.

**영향**:
- 스크린 리더/접근성 도구의 구조 해석이 어색
- TOC 생성 시 계층이 벌어짐

**대응 방향**:
- 원본 문서 수정 권고 사항. converter 는 그대로 두고 경고만 출력
- 이 경고는 Plan-37 에서 건드리지 않음 (warning severity 로 통과 허용)

---

## 요약

| ID | fixture | rule | severity | 카테고리 |
|----|---------|------|----------|----------|
| KI-001 | mypaper | caption_id_unique | error | 원본 문서 결함 |
| KI-002 | swa_kor | image_orphan | warning | **converter 실제 버그** |
| KI-003 | mypaper | heading_level_skip | warning | 원본 문서 비표준 |

**Plan-37 처리 방침**:
- KI-001: 원본 수정 또는 Phase 4c 자동 해결 기대. baseline 에서 **known-error 허용** 표시
- KI-002: **backlog.md 에 별도 작업 항목 등록** (Plan-37 외)
- KI-003: warning 이라 기본 통과. 추가 대응 없음
