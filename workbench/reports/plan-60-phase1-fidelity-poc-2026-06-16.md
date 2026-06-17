# Plan-60 Phase 1 — 통일 양식 내보내기 충실도 PoC 결과

> 작성 2026-06-16 · 환경: 집 개발PC(WSL) · Pandoc 3.10(정적 리눅스 바이너리) · python-docx(백엔드 컨테이너)
> 산출물: `workbench/poc-pandoc/` (표준 템플릿·샘플·변환물·생성 스크립트)

## 0. 한 줄 결론

**기술 보고서 표준 `reference.docx` 자작 성공 + 내보내기 경로를 `MD→HTML→DOCX` 2단계로 잡으면 표(병합 포함)·수식·이미지·양식이 전부 충실히 보존됨.** 회사 양식 없이 집에서 전 과정 검증 완료.

## 1. 한 일

1. Pandoc 기본 `reference.docx` 추출 → python-docx 로 **한국어 기술 보고서 표준**으로 커스터마이즈
   (A4·여백 2.5cm·맑은 고딕 10.5pt·네이비 헤딩·머리글/바닥글·페이지번호). 생성 스크립트 = `customize_reference.py`
2. 까다로운 요소를 모두 담은 샘플 보고서(`sample-report.md`) 작성: 다단계 헤딩·인라인/블록 수식·단순표·**병합셀 표(raw HTML)**·그림+캡션
3. 3가지 경로로 변환 후 docx 내부 XML 정량 검증

## 2. 충실도 결과 (docx XML 실측)

| 요소 | 직접 `MD→DOCX` | **`MD→HTML→DOCX`** (권장) |
|------|:---:|:---:|
| 통일 양식 적용(글꼴·색·여백·머리/바닥글) | ✅ | ✅ |
| A4 / 여백 2.5cm | ✅ | ✅ |
| 페이지 번호 필드 | ✅ | ✅ |
| 단순 파이프 표 | ✅ 정상 표 | ✅ 정상 표 |
| **병합셀 표** | ❌ **구조 소실**(셀이 문단으로 풀림) | ✅ **병합 보존**(gridSpan 3/vMerge 4) |
| 네이티브 수식(OMML) | ✅ 7개 | ✅ 7개 |
| 이미지 임베드 | ✅ | ✅ |
| 헤딩 자동번호 | ✅ (`--number-sections`) | ✅ |

### 핵심 발견
- **병합표가 갈림길.** Pandoc *마크다운 리더*는 본문에 박힌 raw HTML `<table>`을 파싱하지 않고 통과시켜, docx 변환 시 셀이 **한 줄씩 문단으로 풀려 표가 통째로 깨진다.**
- 그러나 Pandoc *HTML 리더*는 `rowspan`/`colspan`을 완전 지원 → **`MD→HTML→DOCX` 2단계로 가면 병합표가 그대로 살아난다.** 같은 경로에서 수식(MathML)·이미지도 전부 보존.
- 우리는 이미 **MD→HTML 인프라(marked 서빙)** 를 갖고 있어, 내보내기를 이 경로에 얹는 비용이 낮다.

## 3. 남은 한계 (다듬기 단계로 흡수)

- **표지(커버 페이지)**: Pandoc 은 title/subtitle/author/date 를 별도 표지가 아니라 본문 최상단 스타일 문단으로 출력. 정식 표지는 워드 다듬기 또는 템플릿에 표지 섹션 별도 설계 필요.
- **헤딩 번호 간격**: `1개요` 처럼 번호와 제목이 붙어 나오는 경향(경미, 후처리/스타일로 보정 가능).
- 위 둘은 업계 docs-as-code 의 "내보내고 워드에서 다듬어 제출" 흐름으로 흡수 가능한 수준. 다듬기 공수 = **문서당 수 분**(표지 1회 + 번호 간격) 추정.

## 4. 권고 (Phase 1 확정 사항 입력)

1. **내보내기 경로 = `MD → HTML → DOCX`** (직접 MD→DOCX 아님). HTML 단계는 `--mathml` 로 수식 보존. 복잡표는 편집기가 HTML 표로 저장 → 그대로 통과.
2. **통일 양식 = `reference.docx` 1벌(교체식 데이터 파일)**. 자작 표준 템플릿을 기본 제공, 회사 양식은 **파일 1개 교체**로 적용(코드 변경 0). 다용도면 템플릿 드롭다운으로 확장.
3. **헤딩 번호 = Pandoc `--number-sections`** (reference.docx 에 굽지 않음 — 단순·안정).
4. **편집기 택1**: 본 PoC 는 양식·내보내기 검증이 목적이라 편집기 선택과 독립. Phase 0 에서 Toast UI 드롭인 검증됨 → 충실도가 편집기 무관함이 확인됐으므로 **Toast UI 유지로 무난**, Crepe 의 1회 빌드 이점은 별도 평가.

## 5. 재현 방법

```bash
cd workbench/poc-pandoc
# 표준 템플릿 재생성 (컨테이너 python-docx)
docker exec sdp-backend python /app/.../customize_reference.py <기본ref> <출력>
# 권장 경로 변환
./bin/pandoc samples/sample-report.md -t html5 --mathml -o _mid.html
./bin/pandoc _mid.html -f html -t docx --reference-doc=standard-technical-report.docx \
  --resource-path=samples --number-sections -o out/report-via-html.docx
```

## 5.5 시각 검증 (LibreOffice 렌더링 + 표지 결합 PoC) — 추가 2026-06-16

> XML 측정의 빈틈을 메우려 docx 를 **LibreOffice 25.2 로 PDF 렌더 → PyMuPDF 로 PNG 추출**해 실제 외관 확인. 렌더 이미지 `workbench/poc-pandoc/render/`.

| 요소 | 시각 결과 |
|------|-----------|
| 양식(네이비 헤딩·머리글/바닥글·페이지번호·A4) | ✅ 정상 |
| 헤딩 자동번호 | ✅ `1 개요` / `1.1 배경` 간격 정상 (XML 텍스트의 `1개요` 는 탭 추출 누락일 뿐) |
| 단순 표 | ✅ 정상 |
| **병합표 — `MD→HTML→DOCX`** | ✅ **병합 렌더 확인**("측정값" colspan, "구분"·"판정" rowspan) |
| **병합표 — 직접 `MD→DOCX`** | ❌ **셀이 줄줄이 문단으로 풀림(깨짐)** — 시각적으로 대조 확인 |
| 이미지·캡션 | ✅ 정상(이미지 임베드 + 캡션 기울임 가운데) |
| **수식(OMML)** | ⚠️ **LibreOffice 에서 빈칸 렌더** (양 경로 공통) |

### ⚠️ 수식 렌더 — 미해결 (Word 확인 필요)
- XML 에 `<m:oMath>` 7개 정상 존재하나 **LibreOffice 가 빈칸으로 표시**. **직접 MD→DOCX(pandoc 표준 경로)도 동일** → 경로 문제 아닌 **LibreOffice OMML 렌더 한계로 추정.**
- pandoc 의 MD→DOCX OMML 은 업계 표준 경로라 **MS Word 에선 정상 렌더 가능성 높음** — 단, 본 PoC 환경에 Word 가 없어 **미확정**. → **회사 Windows PC 의 실제 Word 로 1건 열어 교차 확인 필요.**

### 표지 결합 PoC — ✅ 성공 (단, 메커니즘 정정)
- **발견**: Pandoc 은 `--reference-doc` 의 **본문을 무시** → 표지를 reference.docx 본문에 넣어도 안 나옴. 또한 `MD→HTML→DOCX` 경로는 **YAML 제목블록(제목/저자/날짜)도 누락**.
- **해결·검증**: 본문 docx 에 **python-docx 로 표지 페이지를 후처리 주입**(메타: 보안등급·문서번호·제목·부제·저자·날짜 + 페이지 나누기) → **page 1 표지 + page 2~ 본문**으로 깔끔히 분리됨(시각 확인, `render/cover-p1·p2.png`). 스크립트 `poc-pandoc/add_cover.py`.
- **잔여 다듬기**: 표지 페이지에도 머리글/바닥글이 노출됨 → Phase 3 에서 표지=별도 first-page 섹션으로 헤더/푸터 억제.

## 6. 다음 단계

- [ ] 통일 양식 **사양서** 확정(스타일 표·여백·글꼴·표지 정책) — 본 결과 반영
- [ ] 내보내기 백엔드 설계: `MD→HTML→DOCX` 파이프라인 + Pandoc 정적 바이너리 동봉(폐쇄망) — 리눅스/Windows 양 타깃
- [ ] 표지 섹션 처리 방식 결정(템플릿 표지 vs 워드 다듬기 안내 UX)
- [ ] Phase 2(저작)·Phase 3(내보내기 구현) 착수
