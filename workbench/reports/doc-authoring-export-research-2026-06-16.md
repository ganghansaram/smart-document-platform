# 조사 리포트 — 통일 양식 웹 저작 → DOCX 내보내기 워크플로우 & 공동 문서 플랫폼 트렌드

> 작성 2026-06-16 · 방법: deep-research (5갈래 병렬 웹조사 · 22소스 → 95주장 → 25개 3표 교차검증 · 23확정/2기각) · 의뢰: AAM 공동 저작 공간 컨셉 검토
> 관련: Plan-60(Explorer 마크다운 저작), 후속 신규 계획 후보(내보내기 파이프라인·통일 양식)

## 0. 결론 한 줄
**"마크다운 원본(SSOT) + 통일 reference.docx + Pandoc 내보내기"는 업계 확립 docs-as-code 표준이며, 우리 제약(폐쇄망·무빌드·비동기·DOCX 출력)에 거의 완벽히 정합. 사용자 컨셉(웹에서 통일 양식으로 작성 → 내보내 워드에서 다듬어 제출)이 업계 실무와 일치.**

---

## 1. 외부 트렌드 — 두 진영 (검증됨)
| 진영 | 대표 | 콘텐츠 원본 | 협업 | 우리 정합 |
|---|---|---|---|---|
| 블록형 | Notion, MS Loop | 블록 JSON (마크다운 = **lossy 내보내기**일 뿐, native 저장 아님) | 실시간 | ✗ |
| **마크다운 single-source** | **GitBook**, docs-as-code | **마크다운(SSOT)** | **비동기(변경요청 리뷰)** | ✅ |

- 우리 모델(마크다운 원본 + 비동기 + 담당자 소유권)은 **GitBook식 진영과 일치**. Notion식 블록은 의도적 비채택이 타당.
- **DOCX 내보내기는 Notion·Confluence·GitBook·유럽 공공 Docs·ONLYOFFICE 등 협업 편집기의 보편 기능** — 특이 요구 아님.
- 출처: [Notion 데이터모델](https://www.notion.com/blog/data-model-behind-notion) · [GitBook](https://www.gitbook.com/blog/confluence-alternatives) · [eesel 비교](https://www.eesel.ai/blog/confluence-vs-notion-vs-gitbook) · [Docs(software)](https://en.wikipedia.org/wiki/Docs_(software))

---

## 2. 핵심 검증 사실 — Pandoc (대부분 공식 MANUAL 3-0)
1. **통일 양식 = reference.docx 한 벌**: `--reference-doc` 가 참조 문서의 **스타일·여백·머리글/바닥글을 모든 내보내기에 일괄 적용**(본문 내용은 무시). 회사 워드 양식 1개 등록으로 전 문서 일괄.
2. **폐쇄망 완벽 적합**: **정적 단일 바이너리**, 1회 다운로드 후 오프라인 동작, Windows/Linux 모두 → 배포 3종 전부 드롭인. 라이선스 GPL(별도 실행파일 subprocess 호출 → 우리 코드 비전염).
3. **single-source 다중 출력**: 마크다운 1벌 → DOCX·PDF·HTML, 단일 명령(`pandoc in.md -o out.docx`). 로컬 실측 검증(2.12).
4. **custom-style (1.18+)**: div→단락스타일, span→문자스타일 매핑 가능. **단 스타일명 매칭 기반, 인라인·기능요소 한계** → 풀 WYSIWYG 클론 아님.
5. **마크다운 = LLM-native**: 우리 RAG/AI 인프라(요약·Q&A·초안)와 자연 정합.
- 출처: [Pandoc MANUAL](https://pandoc.org/MANUAL.html) · [설치](https://pandoc.org/installing.html) · [custom DOCX styles](https://github.com/jgm/pandoc/wiki/Defining-custom-DOCX-styles-in-LibreOffice-(and-Word)) · [markitdown](https://github.com/microsoft/markitdown)

---

## 3. 권장 아키텍처
```
[Toast UI 마크다운 저작] (통일 템플릿 골격 프리필)
  → .md 원본 저장 (SSOT, contents/ 작성문서 폴더)
  → 웹 서빙: marked + DOMPurify (Plan-60 확정, 기존 유지)
  → 내보내기: 백엔드(FastAPI)에 Pandoc 바이너리 동봉
       POST /api/export {md, format:docx}
       → pandoc --reference-doc=회사양식.docx → DOCX 반환
  → 사용자가 워드에서 다듬어 제출 (기존 관습 유지)
```
- **통일 양식**: `data/`에 `reference.docx` 한 벌 버전관리.
- **템플릿 강제 수준**: AEM/DITA식 풀 스키마 강제는 과함(무빌드 위배) → **섹션 골격 스니펫 프리필 + 경량 누락 경고**만 차용.
- **비동기 협업**: GitBook식 "변경요청 리뷰" 컨셉만 차용(SaaS Git Sync 자체는 폐쇄망 불가) → 담당자+편집권+위임+이력 수준으로 경량 구현.

---

## 4. 한계 — "내보내고 다듬어 제출"이 정답인 이유
Pandoc 양식 적용은 **블록 수준(스타일명 매칭)은 견고하나 인라인·복합 병합표·수식·표지/목차는 완전 충실하지 않음**(jgm/pandoc 이슈 8149·3290·5268).
→ **내보내기를 최종 제출본으로 보지 말 것.** "내보내기 → 워드 다듬기 → 제출" 흐름을 워크플로우에 명시. 이는 사용자 컨셉과 정확히 동일.

---

## 5. 기각된 주장 (참고)
- ✗ "reference 템플릿은 반드시 Pandoc 생성 docx여야 한다" (0-3) → **임의 워드 문서도 reference로 동작**. 회사 양식 파일 그대로 사용 가능.
- ✗ "유럽 Docs에 커스터마이즈 내보내기 템플릿 기능" (1-2) → 약한 근거, 일반화 보류.

---

## 6. 남은 결정 / PoC 필요 (조사가 정량검증 못 한 부분)
1. **우리 샘플 문서로 Pandoc+reference.docx PoC** → 병합표·수식·표지 충실도 + 다듬기 공수 정량화. (우리 Converter 의 OMML→MathML·표병합 노하우로 후처리 보강 가능성 검토)
2. 템플릿: 골격 프리필만 vs 누락 경고까지
3. custom-style 주입: raw HTML div/span 허용 vs 내보내기 후처리 매핑 (무빌드 제약 하)
4. 비동기 협업: 변경요청 리뷰 흐름 vs 단순 잠금+이력. 양사 비연계 환경의 리뷰 주체 전제 확인

---

## 7. 시사 — 범위 분리
이 워크플로우(내보내기 파이프라인 + 통일 양식 시스템)는 **Plan-60(저작 경로) 범위를 넘음** → 별도 계획(예: Plan-61 "통일 양식 저작·DOCX 내보내기")으로 분리 권장. AAM 양사 공유(망 비연계 하 문서 교환) 역시 별도 전략 사안.

## 부록: 신뢰도 메모
- 핵심 Pandoc 클레임 = 공식 MANUAL primary 교차확인(high). 제품 기능 클레임(GitBook/Notion/Docs)은 vendor 블로그·위키 secondary, 2024~2026 시점.
- 로컬 실측 Pandoc 2.12 기준 → 배포 시 최신 3.x 단일 바이너리 동봉 권장.
- MD→DOCX 병합표·수식 충실도는 본 조사 미정량 → §6-1 PoC 필수.
