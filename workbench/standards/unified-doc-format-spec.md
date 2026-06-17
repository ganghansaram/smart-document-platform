# 통일 양식 사양서 (Unified Document Format Specification) v0.3 (draft)

> v0.3 (2026-06-16): 시각검증·표지 PoC 반영 — 표지=**후처리(python-docx) 주입**으로 정정(reference.docx 본문은 Pandoc 이 무시) · 수식 Word 렌더 확인 미결(§8-E) 추가.
> v0.2 (2026-06-16): front matter 에 문서번호·보안등급 추가 (§8-B).

> Plan-60 Phase 1 공통 계약 · 작성 2026-06-16
> 저작(A축)·내보내기(B축)를 잇는 **단일 계약**. 편집기 템플릿과 `reference.docx` 가 이 사양 한 벌을 공유한다.
> 근거: 충실도 PoC(`reports/plan-60-phase1-fidelity-poc-2026-06-16.md`) · 조사(`reports/doc-authoring-export-research-2026-06-16.md`) · 사내 표준 `standards/MIL-STD-38784B·961E·ASD-STE100`

---

## 0. 적용 범위 · 원칙

- **대상**: 신규 작성하는 **기술 보고서**(웹 저작 → DOCX 내보내기 → 워드 다듬어 제출). 기존 변환 웹북(Monaco/HTML)은 본 사양 비적용 — 그대로 유지.
- **단일 원본(SSOT)**: 콘텐츠는 **마크다운(`.md`)**. HTML·DOCX 는 파생 출력.
- **양식 = 교체식 데이터 파일**: 통일 양식은 코드가 아니라 `reference.docx` **파일 1벌**. 회사 양식 확보 시 파일 교체만으로 적용(코드 변경 0).
- **무손실 우선, 불가하면 다듬기 흡수**: 병합표·수식·이미지는 무손실 보존(§4). 표지·미세 서식은 "워드 다듬기" 단계로 흡수.

---

## 1. 콘텐츠 모델 (마크다운 허용 요소)

| 요소 | 마크다운 표기 | 비고 |
|------|--------------|------|
| 제목 | `#`~`######` (1~6단계) | 자동번호는 내보내기 단계에서 부여(§3) |
| 본문 단락 | 일반 텍스트 | — |
| 강조 | `**굵게**` `*기울임*` | — |
| 목록 | `- ` / `1. ` (중첩 허용) | — |
| 인용 | `> ` | — |
| 코드 | `` `인라인` `` / ```` ``` 블록 ```` | 코드블록 = `Verbatim` 스타일 |
| 링크 | `[텍스트](url)` | — |
| **단순 표** | 파이프 표 `\| \| \|` | 병합 없는 표 — 권장 기본형 |
| **병합 표** | **raw HTML `<table>`** (rowspan/colspan) | 파이프 표로 불가한 병합만(§4) |
| 수식 | `$인라인$` / `$$블록$$` (LaTeX) | OMML 네이티브 변환(§4) |
| 그림 | `![캡션](경로)` | 캡션 = `Image Caption` 스타일 |
| 표 캡션 | `Table: 캡션` (표 직후) | 캡션 = `Table Caption` 스타일 |

- **금지/비권장**: 임의 inline HTML(표 외), `<style>`/`<script>`, 외부 폰트·CSS. (서빙 시 DOMPurify, 내보내기 시 무시됨)

---

## 2. 문서 구조 스키마 (기술 보고서 표준 섹션)

편집기는 신규 문서 생성 시 아래 **골격을 프리필**한다(누락 시 경고만, 강제 아님 — §6-C "골격 프리필 + 경량 누락 경고").

```
(표지 메타: title / subtitle / author / date — YAML front matter)
1. 개요 (Overview)            ← 목적·범위 요약
2. 서론 / 배경 (Introduction)
3. 본론 (방법·구성·결과)        ← 다단계 헤딩 자유
4. 결론 (Conclusion)
[부록] 참고문헌 / 약어 / 부록   ← 선택
```

- 영향 표준: MIL-STD-961E(사양서 절 구성)·MIL-STD-38784B(매뉴얼 서식)을 참고하되, **경량 기술 보고서**로 단순화. 정식 사양서/매뉴얼 출력이 필요하면 별도 reference.docx + 스키마로 확장(향후).
- **front matter(YAML)**: 표지 메타 = `title`(필수)·`subtitle`·`author`·`date`·**`doc_number`(문서번호)**·**`classification`(보안등급)**. (결정 2026-06-16) 개정이력 표는 §8 확장 후보.

```yaml
---
title: "스마트 문서 플랫폼 통합 시험 보고서"
subtitle: "Plan-60 통일 양식 검증"
author: "연구개발팀"
date: "2026-06-16"
doc_number: "TR-2026-001"      # 문서번호
classification: "대외비"         # 보안등급
---
```

---

## 3. 헤딩 · 자동번호 규칙

- 마크다운 `#`=1단계 … `######`=6단계. **본문에 번호를 직접 쓰지 않는다.**
- 자동번호는 **내보내기 단계에서 Pandoc `--number-sections`** 가 부여(`1`, `1.1`, `1.1.1`). reference.docx 에 굽지 않음(단순·안정, PoC 검증).
- 웹 서빙(HTML)에서는 marked 가 번호 미부여 → 필요 시 CSS 카운터로 동일 번호 표시(선택, Phase 2).
- ⚠️ PoC 관찰: 번호와 제목이 붙는 경향(`1개요`) → 내보내기 후처리에서 분리 공백/탭 삽입(§5 후처리).

---

## 4. 까다로운 요소 처리 규칙 (PoC 확정)

### 4.1 표
- **단순 표 = 파이프 표** 기본. 정렬(`:--`, `--:`, `:-:`) 지원. → 정상 Word 표.
- **병합 표 = raw HTML `<table>`** (rowspan/colspan). **단, 내보내기 경로가 `MD→HTML→DOCX` 일 때만 병합 보존**(§5). 직접 MD→DOCX 는 병합 소실(셀이 문단으로 풀림) — **금지 경로**.
- 편집기(Toast UI WYSIWYG)에서 표 셀 병합 시 내부적으로 HTML 표로 직렬화되는지 Phase 2 에서 확인 필요.

### 4.2 수식
- LaTeX `$...$`/`$$...$$` → 내보내기 시 **OMML 네이티브 Word 수식**으로 변환(PoC 7개 보존 확인).
- HTML 중간 단계는 `--mathml` 로 MathML 생성 → Pandoc HTML 리더가 OMML 로 변환.

### 4.3 그림 · 캡션
- `![캡션](경로)` → Figure + `Image Caption`. 이미지는 `--resource-path` 로 해석, docx 에 임베드.
- 그림/표 번호("그림 3-1")는 v1 수동 캡션. 자동 캡션번호는 §8 확장 후보(우리 Converter STYLEREF+SEQ 노하우 재활용 가능).

### 4.4 표지(커버) — **결정: 후처리 주입 (2026-06-16, PoC 검증)**
- ⚠️ **메커니즘 정정**: Pandoc 은 `--reference-doc` 의 **본문을 무시**한다 → 표지를 reference.docx 본문에 넣어도 출력 안 됨. (PoC 확인)
- **확정 방식**: 내보내기 파이프라인 마지막에 **표지 페이지를 후처리로 주입**(python-docx). 본문 docx 맨 앞에 `classification`(보안등급)·`doc_number`(문서번호)·`title`·`subtitle`·`author`·`date` 를 배치한 표지 단락들 + **페이지 나누기**를 삽입 → page 1 표지 + page 2~ 본문. front matter 메타가 표지 필드로 주입됨.
- **PoC 검증됨**(2026-06-16): 표지 page 1 + 본문 page 2 분리 시각 확인(`poc-pandoc/render/cover-p1·p2.png`, 스크립트 `add_cover.py`).
- 잔여(Phase 3): 표지 페이지의 머리글/바닥글 억제(별도 first-page 섹션) + 로고 이미지 삽입.

---

## 5. 내보내기 파이프라인 (확정)

```
.md (SSOT)
  → [1] Pandoc  -f markdown -t html5 --mathml          → 중간 HTML
  → [2] Pandoc  -f html -t docx                          → DOCX
          --reference-doc=<통일 양식.docx>
          --number-sections
          --resource-path=<이미지 경로>
  → [3] 후처리(python-docx): **표지 페이지 주입**(§4.4) · (선택) custom-style 매핑
  → 사용자: 워드에서 표지·미세서식 다듬어 제출
```

- **왜 2단계인가**: PoC 결과 직접 `MD→DOCX` 는 병합표 소실. `MD→HTML→DOCX` 는 **표(병합 포함)·수식·이미지·양식 전부 보존**.
- 서빙용 HTML(marked+DOMPurify)과 내보내기용 HTML(Pandoc)은 **목적이 달라 분리**. 내보내기는 Pandoc 단일 도구로 양 단계 처리(일관성).
- **Pandoc 동봉**: 정적 단일 바이너리, subprocess 호출(GPL 비전염). 리눅스/Windows 양 타깃 바이너리 백엔드 동봉(폐쇄망).

---

## 6. reference.docx 스타일 매핑 (기술 보고서 표준 1벌)

PoC 자작 템플릿(`poc-pandoc/standard-technical-report.docx`, 생성 스크립트 `customize_reference.py`) 기준값. 회사 양식 확보 시 이 표를 회사값으로 치환.

| Pandoc 스타일 | 용도 | 글꼴 | 크기 | 속성 |
|--------------|------|------|:---:|------|
| `Title` | 문서 제목 | 맑은 고딕 | 26pt | 굵게·가운데·네이비(#1F3864) |
| `Subtitle` | 부제 | 맑은 고딕 | 14pt | 가운데·회색 |
| `Author`/`Date` | 저자·날짜 | 맑은 고딕 | 11pt | 가운데 |
| `Heading 1` | 1단계 제목 | 맑은 고딕 | 16pt | 굵게·네이비 |
| `Heading 2` | 2단계 | 맑은 고딕 | 13.5pt | 굵게·네이비 |
| `Heading 3` | 3단계 | 맑은 고딕 | 11.5pt | 굵게·네이비 |
| `Heading 4` | 4단계 | 맑은 고딕 | 10.5pt | 굵게·네이비 |
| `Body Text`/`Normal` | 본문 | 맑은 고딕 | 10.5pt | 줄간격 1.5 |
| `Image Caption`/`Table Caption` | 캡션 | 맑은 고딕 | 9pt | 기울임·가운데·회색 |
| `Verbatim Char` | 코드 | (등폭) | — | 기본 |

- **페이지**: A4(210×297mm) · 여백 상하좌우 2.5cm · 머리글 거리 1.5cm·바닥글 1.3cm
- **머리글**: 우측 "기술 보고서"(문서명 placeholder) 9pt 회색
- **바닥글**: 가운데 `- {PAGE} -` 페이지 번호 필드
- **글꼴 선택 근거**: 맑은 고딕 = Windows Word 기본 탑재 → 폐쇄망·제출 환경 안전. (리눅스 미리보기용 폰트는 Noto CJK 로 대체 렌더되나 최종 제출은 Word 기준)
- **표지 = 후처리 주입(결정 2026-06-16, §4.4)**: reference.docx 본문이 아니라 **파이프라인 후처리(python-docx)로 표지 페이지를 본문 앞에 삽입**. 보안등급·문서번호·제목·부제·저자·날짜 + 페이지 나누기. (구현 Phase 3, PoC 검증 완료)

---

## 7. custom-style 마커 필요성 — 결론: **v1 최소화**

- Pandoc `custom-style`(div=단락/span=문자)은 내장 매핑을 넘는 스타일 적용 수단이나 **스타일명 매칭 기반** + 마크다운에 div/span 마커를 박아야 해 SSOT 가독성 저하.
- **결정**: v1 은 내장 스타일 매핑(§6)으로 충분 → custom-style **미사용**. "경고 박스·주의문" 같은 특수 블록이 실제로 필요해지면 그때 div 마커 + reference.docx 스타일 추가(§8 확장).

---

## 8. 미해결 결정 (Phase 1 마감 전 확정 필요)

| # | 항목 | 결정/권장 | 상태 |
|---|------|-----------|:---:|
| A | **표지 처리** | **후처리(python-docx) 표지 주입** (§4.4·§6, PoC 검증) | ✅ 결정 2026-06-16 |
| E | **수식 Word 렌더 확인** | 회사 Windows Word 로 1건 교차 확인 (LibreOffice 는 빈칸) | ⚠️ 미확정 |
| B | **front matter 확장 필드** | **문서번호·보안등급 추가** (§2) | ✅ 결정 2026-06-16 |
| C | 그림/표 자동 캡션번호 | v1 수동, 향후 Converter SEQ 재활용 | 권장(미확정) |
| D | 웹(HTML) 헤딩번호 표시 | CSS 카운터로 DOCX와 일치 | Phase 2 결정 |

---

## 9. 다음 단계 (이 사양의 소비처)

- **Phase 2 (저작)**: 편집기 신규 문서 = §2 골격 프리필, §1 허용요소만 노출, 저장 `.md`.
- **Phase 3 (내보내기)**: `POST /api/export` = §5 파이프라인 + §6 reference.docx + §7 후처리.
- **회귀셋**: §4 까다로운 요소 포함 대표문서 코퍼스(현 PoC 샘플 1개 → N개 확장)로 왕복 무결성 검증.
