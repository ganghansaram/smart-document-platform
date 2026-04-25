# Plan-47 — 매칭 유형 가이드 모달 + 점수 산식 모달 마감 정리

> Plan-45 Phase 3.6 후속 마이크로 패치 (사용자 추가 지적 2건). 별도 Plan 번호 부여로 추적 명확화.

## 배경

Phase 3.6 청산 후 사용자가 추가로 지적한 두 가지:
1. 모달 A (매칭 유형 가이드) — 2축 다이어그램 텍스트 크기·단어 겹침, 표 어휘/의미 컬럼 줄내림 부자연
2. 모달 B (점수·등급 기준) — 산식보다 근거 캡션이 시각적으로 더 도드라짐. PDF는 정상.

## 진단 (실측)

### 모달 B 폰트 위계 역전

| 항목 | 모달 (현재) | 리포트 PDF |
|------|------------|-----------|
| 산식 (`.sim-help-formula`) | **11px** + Consolas (등폭, 한글 폴백 → 시각적 더 작아짐) | 11px + Consolas |
| 근거 (`.sim-help-formula-basis`) | **12px** + sans-serif (한글 자연 폭) | 10.5px + sans-serif |
| 위계 | 근거 > 산식 ❌ | 산식 > 근거 ✅ |

원인 — Phase 3.6 ②에서 근거 캡션에 `var(--font-small)`(12px)을 사용. theme-guide §2.2 에 11px(`--font-caption`) 미만 토큰이 없어 본 산식보다 한 단계 큰 사이즈가 적용된 것. 리포트 인라인 CSS는 px 명시(11/10.5)라 우연히 정상.

### 모달 A 표 컬럼 폭 (실측, 모달 720px / 표 ≈ 700px)

| 컬럼 | 폭 | 값 예시 | 줄내림 |
|------|-----|---------|--------|
| 유형 | 137px | "거의 동일 (단어 변형)" | 정상 ✅ |
| **어휘** | **59px** | "매우 높음" | "매우 높"+"음" ❌ |
| **의미** | **40px** | "높음", 헤더 "의미"도 "의"+"미"!! | ❌ |
| 설명 | 253px | 가변 | 정상 ✅ |
| 임계값 | 193px | "fp 40~85% + sem ≥ 0.85" | 일부 줄내림 (수용 가능) |

원인 — table 자동 layout이 헤더 글자 수 기준으로 컬럼 폭 분배. "어휘"/"의미" 헤더 2글자라 가장 좁게 잡히는데, td 값(예 "매우 높음" 4글자)은 헤더보다 길어 줄바꿈.

### 모달 A 2축 다이어그램 (인라인 SVG, viewBox 400×320)

- Y축 라벨 "의미 유사도 (Embedding)" — `font-size="12"` 회전된 한글이 차트 영역 밖으로 길게 늘어남
- 점-라벨 거리 23px (점 r=8 + 라벨 약 11px) — 좌상 사분면 "의역"+"의역(번역)" 빽빽
- 다크 모드 사분면 배경 — `#fef3c7`/`#fee2e2`/`#f3f4f6` 라이트 색을 opacity 0.35로 깔아 다크 배경 위 흐릿한 회색 면이 떠 있음. 차트와 본문 사이 중간색 형성, 어수선
- 학술적 톤 — "Winnowing fingerprint × bge-m3 embedding" 표현이 일반 사용자 인지 부담

## 작업 범위

### Step 1 — 모달 B 산식 위계 정상화

**1-1. `css/tokens.css`** — 새 토큰 `--font-tiny: 10.5px` 추가 (라이트·다크 동일)
- theme-guide §2.2 위계 계단(11/12/13/14/15/16) 아래 보조 캡션용 한 단계 신설
- 다른 페이지 영향 없음 (신규 변수, 호출 0건)

**1-2. `css/compare.css`** — `.sim-help-formula-basis font-size: var(--font-tiny)`로 변경
- 결과: 모달 산식 11px(monospace) > 근거 10.5px(sans) → 위계 정상화

**1-3. `.sim-help-formula` 시각 무게 강화** — 산식이 보조 캡션과 명확히 구분되도록
- 배경 `var(--bg-card)` 유지 + 좌측 3px accent border 추가 (`var(--active-color)`)
- 또는 폰트 weight 600 (현재 미지정)

### Step 2 — 모달 A 표 컬럼 줄내림 수정

**2-1. `css/compare.css`** — `.sim-help-bands` 어휘·의미 컬럼 한정
```css
.sim-label-help-modal .sim-help-bands th:nth-child(2),
.sim-label-help-modal .sim-help-bands th:nth-child(3),
.sim-label-help-modal .sim-help-bands td:nth-child(2),
.sim-label-help-modal .sim-help-bands td:nth-child(3) {
    white-space: nowrap;
    min-width: 64px;
    text-align: center;
}
```
- `.sim-label-help-modal` 한정 — 모달 B (5단계 신호등 표) / 검사 설정 모달은 컬럼 구성 다르므로 부작용 차단
- 임계값 컬럼은 일부 wrap 허용 (코드형 텍스트, 너무 긴 항목은 두 줄 자연스러움)

**2-2. `compare.html` 리포트 별첨 B 인라인 CSS** — 동일 표가 PDF 별첨 B에 출력. 동일 nowrap 규칙 추가
- 위치: `buildSimilarityReportHtml` 내 `.types-table` 또는 별첨 B 표 클래스 (확인 후 결정)
- 실제 PDF 출력 영향: 이미 PDF 폭이 모달보다 넓어 줄바꿈 안 났을 가능성 큼. 안전 마진 확보

### Step 3 — 2축 다이어그램 (결정 포인트)

**옵션 C (권장)** — 다이어그램 제거 + 분류 원리 한 줄 텍스트
- "분류 원리 — 2축 조합" 섹션의 SVG 60줄 제거
- 대신: "어휘 일치도(단어 겹침 정도)와 의미 유사도(문맥 의미 일치) 두 축으로 분류합니다" 한 문장
- 표가 어휘/의미 컬럼으로 2축 정보를 이미 전달
- 학술적 인상 제거, 다크모드 부조화 자동 해소, 60줄 코드 감소

**옵션 A** — SVG 정밀 조정 (다이어그램 유지)
- viewBox 400×320 → 480×340 (여백 확보)
- Y축 라벨 font-size 12 → 10
- 사분면 배경 fill 을 prefers-color-scheme 또는 CSS 변수 (다크 시 `var(--hover-bg)`) 분기 — 단 SVG 인라인이라 CSS 변수 직접 적용 어려움. 대안: SVG 안에 `<style>` 블록으로 `body[data-theme="dark"] rect.bg-q1 { fill:... }` 분기
- 점-라벨 거리 ≥30px로 벌리기

→ **C안 선택 시 작업량**: 5분  
→ **A안 선택 시 작업량**: 30~40분 (인라인 SVG 다크 분기 복잡)

## 주변 영향성

| 영역 | 영향 | 조치 |
|------|------|------|
| 백엔드 | 무관 | — |
| SSOT (similarity-help.json) | 무관 (다이어그램 데이터 없음) | — |
| Plan-45 invariants (E1~E5, C1~C7, V1~V5, S1~S3) | 라벨 문자열 변경 없음 → 모두 통과 | — |
| `.sim-help-bands` 공유 | 모달 B(5단계 신호등), 검사 설정 모달 동일 클래스 | `.sim-label-help-modal` 한정 선택자로 격리 |
| 다른 페이지 (Translator/Explorer) | `--font-tiny` 호출 없음 | — |
| 단위 테스트 / sim_label_consistency.sh | 라벨·공식 변경 없음 → PASS 유지 | — |

## 검증

1. 자동 — `node tests/sim_phase2_test.js` 21/21 + `bash tests/sim_label_consistency.sh` PASS
2. 구문 — `vm.Script` compare.html 인라인 script 파싱 (이전 ASI 함정 재발 방지)
3. Playwright 시각 검증 — 라이트/다크
   - 모달 B: 산식 vs 근거 폰트 사이즈 실측 (산식 ≥ 근거)
   - 모달 A 표: 어휘/의미 컬럼 td 폭 ≥ 64px, 줄내림 0
   - (C안 채택 시) 다이어그램 제거 후 모달 높이 단축 확인
4. code-reviewer (Critical 0 목표)
5. design-reviewer (Critical 0 목표) — 모달 A·B 시각 균형 평가

## 결정 포인트 (사용자 선택 필요)

**Step 3 다이어그램 처리 — C안(제거) vs A안(정밀 조정)?**

제 권장은 **C안 (제거)**. 근거:
- 학술적 톤 제거 → 일반 사용자 친화
- 다크모드 부조화 본질적 해소
- 표가 동일 정보 전달 (어휘/의미 컬럼)
- 코드 60줄 감소, 유지보수 부담 ↓
- 모달 높이 단축 → 사용자가 표를 더 빨리 만남

A안은 정밀 조정 가능하나 인라인 SVG에서 다크모드 분기가 복잡하고, 학술적 톤 자체는 남음.

## 산출물

- 변경 파일: `css/tokens.css`, `css/compare.css`, `compare.html` (3 파일)
- 보고서: `workbench/reports/plan-47-feedback-2026-04-25.md`
- 스크린샷: `workbench/screenshots/plan-47-20260425/` (라이트/다크 모달 A·B, 표 컬럼 폭)
- 본 plan 파일은 완료 후 `done-47-...` 으로 이름 변경
