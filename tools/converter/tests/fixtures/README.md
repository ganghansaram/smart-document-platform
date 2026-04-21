# Converter Test Fixtures

> Plan-37 Phase 0 — 회귀 방어망용 DOCX 샘플 카탈로그
>
> fixture DOCX 는 **`contents/samples/` 의 파일을 참조**만 한다 (복사하지 않음).
> 이유: 용량 절약, 샘플 갱신 시 자동 반영, git LFS 회피.

## Fixture 매핑

| ID | 파일 (contents/samples/ 기준 상대경로) | 목표 커버리지 | 크기 | 비고 |
|----|---------------------------------------|---------------|------|------|
| `sample_small` | `sample_20260317.docx` | (a) 단순 문서, 빠른 iterate | ~368 KB | 소형 smoke test |
| `mypaper` | `MyPaper/MyPaper_20251109_V2.8_Claude.docx` | (c) 수식 (OMML), 캡션 | ~380 KB | 논문 형식 |
| `swa_pms` | `SWA_PMS/SWA_PMS.docx` | (b) 대형 매뉴얼, heading 자동번호, STYLEREF 가능성 | ~1.1 MB | 회사 규격서 |
| `swa_kor` | `SWA_Sample_KOR/SWA_Sample_KOR.docx` | (f) 한글 heading 자동번호 재현 | ~894 KB | 한글 매뉴얼 |
| `swa_eng` | `SWA_Sample_ENG/SWA_Sample_ENG.docx` | (선택) 영문 대형, 비교용 | ~3.6 MB | 테스트 속도 영향 — CI 에선 선택적 |

## 목표 커버리지 (Plan-37 §3 Phase 0 기준)

- (a) 단순 매뉴얼 → `sample_small`
- (b) 대형 매뉴얼 → `swa_pms`
- (c) 수식 문서 → `mypaper`
- (d) STYLEREF 합성 캡션 → **Phase 0 에서 fixture 내부 조사 후 확인**
- (e) SEQ 스위치 → **Phase 0 에서 fixture 내부 조사 후 확인**
- (f) 한글 heading 자동번호 → `swa_kor`

(d)(e) 는 기존 샘플로 커버 안 되면 Phase 4 진입 전 수동 DOCX 제작 권장.

## 골든 HTML (`../golden/`)

각 fixture 를 **현 Explorer Word COM 경로** 로 변환한 결과를 `{id}.html` 로 저장.
Phase 1~4 의 모든 변경은 이 골든과 fingerprint (DOM 구조 + 텍스트 hash) 비교로 회귀 여부 판정.

## 사용법

```bash
# 골든 HTML 생성 (최초 1회 또는 converter 재빌드 후)
cd tools/converter/tests
python regenerate_golden.py

# 회귀 테스트
pytest tools/converter/tests/
```
