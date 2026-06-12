# Plan-34: Verify 시스템 현업 품질 확보

> **목표**: Plan-33 검토 결과(P0 2건, P1 7건)를 해소하여
> 현업 사용자가 "이건 쓸만하다"라고 느낄 수 있는 수준으로 만든다.
> 임시방편 없이 업계 정석으로 수정한다.
>
> **선행**: Plan-33 종합 검토 보고서 (`workbench/reports/33-verify-review-report.md`)

---

## 설계 원칙

1. **첫인상이 전부다** — 사용자가 처음 규격서를 넣었을 때 "말도 안 되는 점수"가 나오면 두 번째 기회는 없다.
2. **숫자는 설명이 있어야 한다** — 점수만 보여주는 도구는 불신을 산다. "왜 이 점수인지"가 즉시 보여야 한다.
3. **실수는 되돌릴 수 있어야 한다** — 일괄 작업은 확인을 거치고, 모드 전환 시 진행 중인 작업을 보호한다.
4. **없는 기능은 표시하지 않는다** — 작동하지 않는 "번역" 라벨은 혼란을 준다.

---

## Phase 1 — 점수 공식 정상화 (가장 시급)

### 1a. 검증 점수: 선형 → 시그모이드 전환

**현재 문제**: `score = 100 × (1 - density / 5.0)` — 선형 공식.
밀도 5.0 이상이면 무조건 0점. 오류 0건이어도 경고만으로 0점 가능.

**수정 — 시그모이드 곡선 도입**:

```python
import math

def _compute_score(density: float, k: float = 4.0) -> int:
    """
    시그모이드 기반 스코어링.
    - density 0 → 100점
    - density k → 50점 (변곡점)
    - density 높아져도 0점에 수렴하지 않고 완만히 감소
    - 업계 도구(Acrolinx, SonarQube) 비선형 곡선과 동일 철학
    """
    score = 100 / (1 + (density / k) ** 2)
    return max(0, round(score))
```

**파라미터 k 설계 근거**:

| density (100단어당) | k=3 | k=4 | k=5 | 의미 |
|---------------------|-----|-----|-----|------|
| 0 | 100 | 100 | 100 | 위반 없음 |
| 1 | 90 | 94 | 96 | 경미한 위반 |
| 2 | 69 | 80 | 86 | 보통 위반 |
| 4 | 36 | 50 | 61 | 상당한 위반 (k=4 변곡점) |
| 6 | 20 | 31 | 41 | 심각한 위반 |
| 8 | 12 | 20 | 28 | 매우 심각 |
| 10 | 8 | 14 | 20 | 극심 |

**k=4 선택 이유**:
- 100단어당 경고 2건(density=4) → 50점(C등급): "개선 필요하지만 불합격은 아님"
- 100단어당 오류 1건(density=5) → 39점(D등급): "재작성 필요"
- Plan-33 실전 케이스 검증: 352단어, 경고13+제안4 → density 8.52 → **20점(D)**
  - 기존: 0점 → 수정 후: 20점. 여전히 D이지만 "0점"이라는 극단은 제거됨

**카테고리 점수에도 동일 공식 적용.**

### 1b. 가중치 미세 조정

현재 `warning: 2`는 error(5)의 40%인데, 현실에서 경고는 error보다 훨씬 가벼움.

```python
SEVERITY_WEIGHT = {"error": 5, "warning": 1.5, "suggestion": 0.5}
```

**변경 근거**:
- error는 규격 위반 — 무조건 수정 필요 → 5 유지
- warning은 권고 위반 — 수정 권장이지 필수 아님 → 2 → **1.5**
- suggestion은 개선 여지 — 무시해도 됨 → 1 → **0.5**

**Plan-33 케이스 재계산** (k=4, 새 가중치):
```
weighted = 13×1.5 + 4×0.5 = 21.5
density = 21.5 / 3.52 = 6.11
score = 100 / (1 + (6.11/4)²) = 100 / (1 + 2.33) = 30점 (D)
```
→ 0점 → 30점. "낮지만 0은 아닌" 합리적 점수.

### 1c. 등급 기준 조정

현재 A(90+)/B(80+)/C(60+)/D(-60) — 시그모이드 도입 시 점수 분포가 달라지므로 재조정.

```
A: 85+ (우수)    — 100단어당 위반 밀도 ~1 이하
B: 70+ (양호)    — 밀도 ~2 이하
C: 50+ (보통)    — 밀도 ~4 이하 (변곡점)
D: 50 미만 (미달) — 밀도 4 초과
```

**변경 이유**: 시그모이드에서 50점이 변곡점(k값)이므로 C/D 경계를 50으로 설정.
85/70은 실전 규격서 분포를 반영한 값 (Phase 3 캘리브레이션에서 미세 조정).

### 1d. 등급 기준 설정 가능하게

프론트엔드 3곳 하드코딩 → `config.py` + settings API 경유로 통일.

```python
# config.py
VERIFY_GRADE_A = 85
VERIFY_GRADE_B = 70
VERIFY_GRADE_C = 50
VERIFY_SCORE_K = 4.0  # 시그모이드 k값
```

프론트엔드: `/api/settings/public`에서 받아 사용.

---

## Phase 2 — 유사도 분류 정상화

### 2a. Paraphrase 분류 dead zone 해소

**현재**: `fp < 0.15 AND sem >= 0.88` — 너무 엄격, 의역 대부분 low_sim으로 낙하.

**수정**:
```python
def _classify_match(fp_score, sem_score, th_high):
    if fp_score >= 0.85:
        return TYPE_IDENTICAL
    if fp_score >= 0.40 and sem_score >= th_high:
        return TYPE_NEAR_COPY
    # 언어가 다른 경우 (fingerprint 극저 + 의미 높음)
    if fp_score < 0.10 and sem_score >= th_high:
        return TYPE_TRANSLATION
    # 의역: fingerprint 중저 + 의미 높음
    if fp_score < 0.40 and sem_score >= th_high:
        return TYPE_PARAPHRASE
    if sem_score >= 0.65:
        return TYPE_LOW_SIM
    return TYPE_LOW_SIM
```

**변경 포인트**:
1. `TYPE_TRANSLATION` 반환 경로 추가 (fp < 0.10 + sem >= th_high)
   - 한↔영은 문자 체계가 완전히 다르므로 fp ≈ 0
   - 동일 언어 의역은 fp 0.10~0.40 대역
2. `TYPE_PARAPHRASE` 조건 완화: `fp < 0.40 AND sem >= th_high`
   - 0.88 하드코딩 제거 → th_high(설정 가능)와 연동
   - fp 0.15~0.40 dead zone 해소
3. near_copy(fp >= 0.40) → translation(fp < 0.10) → paraphrase(fp < 0.40) 순서로
   fp가 좁아지는 내림차순 배치 — 경계 충돌 없음

### 2b. adjusted_pct 분모에서 보일러플레이트 제외

```python
# 기존: adjusted_pct = (substantive + derived*0.5) / max(total, 1) * 100
# 수정: 보일러플레이트 제외
effective_total = max(total - bp_count, 1)
adjusted_pct = round((substantive + derived * 0.5) / effective_total * 100, 1)
```

### 2c. 보일러플레이트 match_len 중복 계산 방지

```python
# 기존: 겹치는 구문이 match_len에 중복 누적
# 수정: 문자 인덱스 기반 커버리지 계산
def _detect_boilerplate(sentences):
    phrases = _load_boilerplate()
    indices = set()
    for i, sent in enumerate(sentences):
        sent_lower = sent.lower()
        covered = set()  # 커버된 문자 인덱스
        for phrase in phrases:
            start = 0
            while True:
                pos = sent_lower.find(phrase, start)
                if pos == -1:
                    break
                for j in range(pos, pos + len(phrase)):
                    covered.add(j)
                start = pos + 1
        if len(sent_lower) > 0 and len(covered) / len(sent_lower) >= 0.5:
            indices.add(i)
    return indices
```

---

## Phase 3 — 실문서 캘리브레이션

### 3a. 테스트 문서 세트 구성

- 기존 테스트 샘플: `workbench/test-samples/company-spec.txt`, `reference-spec.txt`
- 추가 필요: 실제 업무 규격서 3~5건 (민감정보 제거)
- 각 문서에 대한 "기대 등급"을 사전 정의

| 문서 | 예상 품질 | 기대 등급 |
|------|-----------|-----------|
| 잘 작성된 규격서 | 높음 | A 또는 B |
| 일반 규격서 | 보통 | B 또는 C |
| 초안/미완성 | 낮음 | C 또는 D |
| company-spec.txt (테스트용) | 보통 | C |

### 3b. k값 및 등급 경계 보정

Phase 1에서 k=4로 시작한 뒤, 3a 문서들의 실제 점수를 확인하여:
- "잘 작성된 규격서"가 B 이상 나오는지
- "초안"이 C 이하 나오는지
- 기대 등급과 실제 등급이 80% 이상 일치하는지

불일치 시 k값 또는 등급 경계를 미세 조정.

### 3c. 약어 화이트리스트 보강

현재 `common_abbrs`에 방산/항공 도메인 약어 추가:

```python
DOMAIN_ABBRS = {
    # 항공/방산
    "EMC", "EMI", "EUT", "LISN", "ESD", "RF", "AC", "DC",
    "KAI", "KF", "UAV", "IFF", "LRU", "SRU",
    # 주파수/단위
    "Hz", "kHz", "MHz", "GHz", "dB", "dBm",
    # 규격
    "MIL", "STD", "ASD", "STE", "NATO", "STANAG",
    "IEEE", "ISO", "KS", "ASTM",
    # 일반 기술
    "API", "CPU", "GPU", "RAM", "ROM", "USB", "LED",
    "CAD", "CAM", "CAE", "FEA", "CFD", "PDM", "PLM",
}
```

관리자 설정 UI에서 편집 가능하도록 `settings.json`에 저장.

---

## Phase 4 — UX 기본기 보강

### 4a. 검증 모드 점수 해설 툴팁

유사도 모드에 이미 있는 `?` 버튼 패턴을 검증 모드에도 적용.

- 등급 옆 `?` 버튼 → 등급 기준표 팝업
- 카테고리 점수 옆 `tooltip-icon` → "이 카테고리의 위반 밀도 기준" 표시
- 전체 점수 링 옆 → "점수 산출: 100단어당 가중 위반 밀도 기반" 1줄 설명

### 4b. 일괄 수락/거절 확인 대화상자

```javascript
// 기존: 즉시 실행
// 수정: showConfirmModal 경유
bulkAcceptBtn.onclick = () => {
    const count = undecidedChanges.length;
    showConfirmModal(
        `${count}건을 모두 수락하시겠습니까?`,
        () => applyBulkDecision('accepted')
    );
};
```

일괄 거절, 일괄 초기화도 동일 패턴.

### 4c. 모드 전환 가드 강화

```javascript
// setMode() 진입 시 결정 진행 상황 체크
function setMode(newMode) {
    if (hasUnsavedDecisions()) {
        showConfirmModal(
            '진행 중인 작업이 있습니다. 전환하시겠습니까?',
            () => _doSetMode(newMode)
        );
        return;
    }
    _doSetMode(newMode);
}
```

`hasUnsavedDecisions()`: 비교 모드에서 수락/거절 건이 1건 이상 있으면 true.

### 4d. 검증 오류 표시 통일

검증 모드의 사이드바 인라인 에러 → toast + 인라인 병용으로 변경.
유사도/비교와 동일한 `showToast(msg, 'error')` 패턴.

---

## Phase 5 — 인앱 가이드 및 기준표

### 5a. 모드별 인앱 도움말

각 모드 결과 화면에 `?` 또는 `ⓘ` 버튼 추가.
클릭 시 모달로 기준표 요약 표시:

**유사도 모드** (이미 판정 툴팁 있음 → 보강):
- 판정 기준표 (양호/보통/주의)
- 매칭 유형 해설 (일치/유사/의역/번역/참고/공통)
- 3단 분해 막대 범례

**검증 모드** (신규):
- 등급 기준표 (A/B/C/D)
- 심각도 해설 (오류/경고/제안 + 가중치)
- 카테고리 해설 (구조/작성/용어/가독성)

**비교 모드** (신규):
- 변경 유형 해설 (추가/삭제/수정)
- AI 분류 태그 해설 (강화/완화/확대/명확화/편집/재구성)

### 5b. 가이드 페이지

`contents/guide/` 디렉토리에 Verify 사용 가이드 HTML 작성.
`GUIDE-STYLE.md` 기준 준수 (이모지 금지, h2 필수, 1컬럼, 담백한 톤).
가이드 메뉴(`data/menu.json`)에 등록.

포함 내용:
1. 3모드 개요 (언제 어떤 모드를 쓰는가)
2. 유사도 결과 읽는 법 + 기준표
3. 검증 결과 읽는 법 + 등급표 + 점수 예시
4. 비교 워크플로우 (수락/거절 → 내보내기)
5. 규칙 설정 방법 (프리셋, 개별 토글)

### 5c. 엑셀 보고서에 기준표 포함

Summary 시트에 1줄 요약:
```
점수 산출: 100단어당 가중 위반 밀도 기반 (시그모이드 곡선)
등급: A(85+) B(70+) C(50+) D(50 미만)
```

---

## 작업 순서

```
Phase 1  점수 공식 정상화 ──────── 핵심, 최우선
   1a 시그모이드 전환
   1b 가중치 조정
   1c 등급 기준 조정
   1d 등급 설정 API화
   ↓
Phase 2  유사도 분류 정상화 ────── Phase 1과 독립, 병렬 가능
   2a 분류 로직 수정
   2b 분모 보정
   2c 보일러플레이트 중복 방지
   ↓
Phase 3  실문서 캘리브레이션 ───── Phase 1·2 완료 후
   3a 테스트 세트 실행
   3b k값/등급 보정
   3c 약어 화이트리스트
   ↓
Phase 4  UX 기본기 보강 ─────── Phase 1·2와 병렬 가능
   4a 점수 해설 툴팁
   4b 일괄 작업 확인
   4c 모드 전환 가드
   4d 에러 표시 통일
   ↓
Phase 5  가이드 자료 ─────────── Phase 1~3 확정 후 (점수 기준 확정 필요)
   5a 인앱 도움말
   5b 가이드 페이지
   5c 엑셀 범례
```

**Phase 1 → 2 → 3**은 순차 (점수 공식 → 유사도 보정 → 실문서 검증).
**Phase 4**는 1·2와 병렬 가능 (UI 작업이므로 백엔드와 독립).
**Phase 5**는 점수 기준이 확정된 후에 작성 (Phase 3 완료 후).

---

## 변경 파일 예상

| 파일 | Phase | 변경 내용 |
|------|-------|-----------|
| `backend/services/compare_service.py` | 1a,1b | 시그모이드 공식, 가중치 |
| `backend/config.py` | 1c,1d | 등급/k값 설정 추가 |
| `backend/services/settings_service.py` | 1d | 등급 설정 API 노출 |
| `backend/services/similarity_engine.py` | 2a,2b,2c | 분류 로직, 분모, BP 수정 |
| `compare.html` | 1c,4a~4d | 등급 참조, 툴팁, 확인 대화상자, 가드 |
| `backend/rules/mil-structure.json` | 3c | 약어 화이트리스트 |
| `backend/services/rule_engine.py` | 3c | 도메인 약어 로딩 |
| `backend/services/export_service.py` | 5c | 엑셀 범례 추가 |
| `contents/guide/verify-guide.html` | 5b | 가이드 페이지 신규 |
| `data/menu.json` | 5b | 가이드 메뉴 등록 |
