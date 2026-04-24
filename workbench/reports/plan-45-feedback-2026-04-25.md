# Plan-45 Phase 1 실행 피드백 — SSOT 작성 + 백엔드 연결

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 1 단독

## 요약
- 완료 Step: 1 / 1 (Phase 1 — SSOT 작성 + 엔드포인트 검증)
- 변경 파일: 1개 (`data/help/similarity-help.json`)
- 백엔드 코드 변경: 없음 (기존 `backend/api/help.py` 재활용)
- Critical 이슈: 0건 · Warning: 1건 · Suggestion: 2건

## 구현 결과

| Step | 상태 | 변경 파일 | 메모 |
|------|------|----------|------|
| 1    | ✅   | `data/help/similarity-help.json` (v1 → v3 전면 교체) | 6.3KB, 11개 최상위 키 |

## 현행 상태 vs 계획서 가정 — 사전 조사 결과

| 조사 항목 | 상태 | 근거 |
|---|---|---|
| `/api/help/similarity` 엔드포인트 | ✅ 존재 | `backend/api/help.py:40` |
| 엔드포인트 로드 로직 | ✅ 재사용 가능 | `_load("similarity-help")` 호출 |
| 프론트 fetch 경로 | ✅ 기존 작동 | `compare.html:473` `API_BASE + '/help/similarity'` |
| `simHelp.groups` 참조 | ✅ 없음 (grep 확인) | v1 `groups` 섹션 제거 안전 |
| `simHelp.auto_exclusions` 참조 | ⚠️ 있음 | `compare.html:1512` — v3에도 유지 필수 |
| `help.algorithm.references` 참조 | ⚠️ 있음 | `compare.html:4873` — v3에도 유지 필수 |
| `_syncSimTypeMapFromHelp` 동작 | ✅ 안전 | `src.group` 조건부 접근, JSON 필드 누락 시 초기값 보존 |
| `_cache` 모듈 변수 | ⚠️ 서버 재시작 필요 | 런타임 재로드 없음 (`backend/api/help.py:20`) |

**결과**: 계획서 가정 7건 중 7건 일치. 하위 호환을 위해 v1의 `labels.*.ko_long/short/long/lex/sem/threshold/color_var` · `verdict_bands` · `check_settings` · `auto_exclusions` · `algorithm` · `disclaimer` 섹션은 **계승**하고, `groups` 섹션만 폐기. v3 신규 섹션(`categories`, `exclusions`, `labels.*.category_key`) 추가.

## 검증 결과

### JSON 문법
- `python -c "import json; json.load(...)"` PASS
- UTF-8 인코딩 정상
- 6.3KB, 11 최상위 키

### 스키마 완결성
| 항목 | 상태 |
|---|---|
| `version: 3` | ✅ |
| `categories`: 4 (identical/near_copy/paraphrased/low_similarity) | ✅ |
| 점수 포함 3 + 참고 1: `in_score` 플래그 정확 | ✅ |
| `exclusions.auto.reasons`: 8개 (boilerplate + 7 exclusion_reason) | ✅ |
| `labels`: 6 (6 유형 전부) | ✅ |
| 모든 `labels.*.category_key` 매핑 정확 | ✅ (paraphrase/translation → paraphrased 통합 확인) |
| `score_formula.equation`: Copyleaks 공식 | ✅ |
| `verdict_bands`: 5단계 신호등 | ✅ |
| `check_settings`: 5옵션 | ✅ |

### Copyleaks 공식 검증
```
입력: 샘플 리포트 값 (identical=76, minor=50, paraphrased=89, total=597, omitted=105)
계산: (76 + 50 + 89) / (597 - 105) = 215 / 492 = 43.7%
결과: Copyleaks 샘플 리포트 공식값 43.7%와 일치 ✅
```

### 엔드포인트 응답 시뮬레이션 (backend/api/help.py 실제 import)
- Status 200, Content-Type `application/json`
- Body 6309 bytes
- 기존 프론트 접근 경로 전부 PASS:
  - `help.score_formula.equation` → 새 Copyleaks 공식 반환
  - `help.verdict_bands[2].label` → "검토 필요"
  - `help.labels.identical.ko` → "일치"
  - `help.auto_exclusions` 키 3개 접근 가능
  - `help.algorithm.references` 5개 접근 가능
- v3 신규 경로 접근:
  - `help.categories` → 4개 키
  - `help.exclusions.auto.reasons` → 8개 reason
  - `help.labels.translation.category_key` → "paraphrased" (통합 매핑 확인)

## 이슈 및 권고

### ⚠️ Warning — 서버 재시작 필요

`backend/api/help.py:20`의 `_cache: dict[str, dict] = {}` 모듈 변수 때문에 프로세스가 살아있는 동안 구 JSON(v1)이 메모리에 남아있을 수 있습니다.

**조치**: Phase 2 착수 전 백엔드 서버 재시작 필수.
```bash
docker compose restart backend    # Docker 환경
# 또는
python main.py                    # 직접 실행 시 재실행
```

### 💡 Suggestion 1 — Phase 2 전 사전 확인 항목

Phase 2(`resolveCategory` + `computeScore` 도입)에 앞서 다음 프론트 코드가 아직 v1 스키마를 기대하는 상태임을 주지:
- `compare.html:2451~2479` 누적바 렌더링 — v1 group 기반, Phase 3에서 categories 기반으로 재작성 예정
- `compare.html:2515~2521` 필터 칩 — v1 6유형 기반, Phase 3에서 4 카테고리 기반으로 재작성 예정
- `compare.html:1275` Modal B (점수 산식) — v3 공식을 자동 반영 (SSOT fetch로), **Phase 1 완료 즉시 UI에서 확인 가능**

**Phase 1만 적용된 현 상태에서 모달 B를 열면** 산식이 이미 Copyleaks 공식으로 바뀌어 표시됨. 이는 **의도된 중간 상태** — 사용자에게는 "점수 계산이 곧 바뀔 것"이라는 사전 공지 역할.

### 💡 Suggestion 2 — Phase 2에서 삭제할 중복 로드

`backend/services/export_service.py:485` `_load_similarity_help()` 가 별도로 JSON 파일을 직접 로드. Phase 5(HTML 리포트 재구성) 또는 Phase 7(정리)에서 `backend/api/help.py`의 `_load` 재사용으로 통합 권장 — 현재는 중복이지만 동일 파일을 읽으므로 기능상 무해.

## 회귀 스팟체크

계획서가 "건드리지 않겠다"고 한 영역 샘플:
| 파일 | 체크 | 결과 |
|---|---|---|
| `backend/services/similarity_engine.py` | 6 유형 분류 로직 유지 | ✅ Read 확인, 수정 없음 |
| `backend/config.py` | 임계값 상수 유지 | ✅ 수정 없음 |
| `contents/guide/verify-guide.html` | Phase 6 대상, 현재는 v1 어휘 그대로 | ✅ Phase 1 범위 외 |
| `css/compare.css` | Phase 3/4 대상 | ✅ Phase 1 범위 외 |

## 사용자 관점 피드백

### 긍정
- JSON 파일 **1개** 만 변경. 프론트·백엔드 코드 수정 없음 → 매우 낮은 리스크의 첫 단계.
- 서버 재시작만 하면 **Modal B (점수 산식 도움말)** 에 즉시 새 공식 반영됨 — 시각적 진척도 확인 가능.
- 하위 호환 레이어(v1 섹션 계승) 덕분에 Phase 2 착수 전까지 **기존 UI 전부 정상 동작**. 점수 수치만 Phase 2에서 변경됨.

### 우려
- v3 파일에 v1 호환 필드(`labels.*.ko_long/short/long/lex/sem/threshold` 등)가 여전히 **중복 정보로 존재**. Phase 7 정리에서 `categories`로 완전 이전 후 labels를 축약하는 것이 이상적.
- `_cache` 재시작 필요 사항이 운영 절차에 노출됨 — 자동 리로드 핫스왑은 별도 개선 Plan.

### 개선 제안
- Phase 2 직전에 `docker compose restart backend` 1회 실행 후 모달 B에서 새 산식 노출 확인하는 체크포인트 추가 권장.

## 웹디자인 전문가 관점 피드백

본 Phase는 JSON 스키마만 변경. UI 렌더링 변화는 **Modal B 산식 텍스트** 1곳에 국한 (SSOT가 텍스트로 반환되므로 자동 반영). 다크모드·반응형·접근성 영향 없음.

Phase 3(사이드바 UI 재구성)에서 본격적인 시각 변경이 시작될 예정.

## 잔여·후속 제안

### 즉시 (Phase 2 착수 전)
- [ ] 백엔드 서버 재시작 (캐시 초기화)
- [ ] 모달 B에서 새 공식 노출 확인 (육안 체크)

### Phase 2 작업 시 고려
- [ ] `resolveCategory(match, activeSettings)` 함수 추가 시 `simHelp.labels[k].category_key` 참조로 구현 → v3 스키마 즉시 활용
- [ ] `computeScore` 재작성 시 Copyleaks 공식 하드코딩 금지, `simHelp.score_formula`에서 파생 (가능하면 equation을 문자열 파싱 대신 전용 함수로)

### Phase 7 (드리프트 방지)
- [ ] `export_service.py` `_load_similarity_help` 를 `backend/api/help.py` `_load` 재사용으로 통합
- [ ] v1 호환 필드 (labels의 ko_long/lex/sem 등) 사용처 검토 후 categories 쪽으로 완전 이전

## 커밋 제안 (사용자 요청 시)

```
추가 [Plan-45/P1] 유사도 SSOT v3 — Copyleaks 기준 4 카테고리

Plan-38의 4그룹+6세부 혼합 축을 Copyleaks의 단일 강도 축 4 카테고리
(동일/거의 동일/의역/약한 유사)로 재정의. 점수 공식도 Copyleaks
aggregatedScore 공식(가중치 없음)으로 교체.

변경:
- data/help/similarity-help.json v1→v3
  · categories 섹션 신설 (4 카테고리)
  · exclusions 섹션 신설 (auto + manual 분리)
  · labels.*.category_key 매핑 추가
  · score_formula: (실질+의역×0.5)/... → (동일+거의동일+의역)/... (가중치 제거)
  · groups 섹션 폐기 (참조 코드 없음 확인)
  · v1 호환 필드(labels 상세·verdict_bands·check_settings·auto_exclusions·
    algorithm·disclaimer)는 계승 — Phase 2~7에서 점진적 이관

백엔드 변경 없음 (기존 backend/api/help.py _load 재사용).
서버 재시작 필요 (_cache 모듈 변수 초기화).

검증:
- JSON 문법 PASS
- backend/api/help.py _load() import 시뮬레이션 PASS
- Copyleaks 공식 샘플 검증: (76+50+89)/(597-105) = 43.7% ✓
- 기존 프론트 접근 경로(labels.ko/short/color_var·verdict_bands·
  check_settings·auto_exclusions·algorithm.references) 전부 유효

Phase 2~7 작업은 별도 PR로 분리 예정.
```
