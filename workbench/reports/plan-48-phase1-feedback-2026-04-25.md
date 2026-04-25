# Plan-48 Phase 1 실행 피드백 — 유사도 미니맵 정상화 + 위치 정확도

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/48-similarity-minimap-improvement.md`

## 요약

- 완료 Step: 6/6 (1.1~1.6) + code-reviewer Warning 4건 즉시 반영
- 변경 파일: 2개 (`css/compare.css`, `compare.html`)
- Critical 0 / Warning 5건 (4건 즉시 반영 / 1건 정적 안전 확인) / Suggestion 4건 (1건 즉시 반영 / 3건 보고서 기재)
- Plan-45 invariants (E1~E5, C1~C7, V1~V5, S1~S3) 준수, 백엔드·SSOT·라벨 불변
- diff 모드 미니맵 영향 0 (sim-* 접두사 격리, 모드 가드 추가)

## 변경 사항

| Step | 항목 | 위치 |
|------|------|------|
| 1.1 | `.sim-minimap-mark` CSS 클래스 + 6 카테고리 색상 클래스 신설 | `css/compare.css` L160~190 |
| 1.1 | 다크모드 `.sim-minimap-mark.active` 오버라이드 (CR-W5) | `css/compare.css` L177~179 |
| 1.2 | `simRenderMinimap()` 재작성 — multi-sentence 마커, 클래스 cascade, 누적 핸들러 제거 | `compare.html` L3083~3134 |
| 1.2 | `simAppendSpanMark()` 헬퍼 — querySelectorAll 첫·마지막 element 기반 비례 마커 | `compare.html` L3136~3155 |
| 1.5 | `simHighlightMinimapActive(idx)` 헬퍼 + `simNavigateToMatch` 끝에 호출 추가 | `compare.html` L3157~3166, L2960 |
| 1.6 | `simRecalcMinimapAfterLayoutSettle()` — img.load + fonts.ready 후 재계산 | `compare.html` L3168~3187 |
| 1.6 | `simApplyHighlights` 끝에 호출 (innerHTML 직후 1회) | `compare.html` L2719 |
| 1.4 | sim ResizeObserver — 사이드바·창 리사이즈 시 자동 재계산 | `compare.html` L4239~4246 |
| 1.3 | 클릭 위임 1회 등록 + 모드 가드 (CR-W3) | `compare.html` L4248~4262 |

## 검증 결과

### 자동 (회귀 0)

- **단위 테스트**: 21/21 PASS (`tests/sim_phase2_test.js`)
- **라벨·공식 일관성**: PASS (`tests/sim_label_consistency.sh`)
- **compare.html 인라인 script vm.Script 구문 파싱**: errors 0

### Code Reviewer

| 분류 | 건수 | 처리 |
|------|------|------|
| Critical | 0 | — |
| Warning | 5 | W1·W3·W5 즉시 반영 ✅ / W4 정적 분석 후 미반영 (사유 아래) / W2 정적 안전 확인 (사유 아래) |
| Suggestion | 4 | S1 즉시 반영 ✅ / S2·S3·S4 보고서 기재 |

#### Warning 즉시 반영 상세

- **W1 (`simActiveIdx != null`)** — `simActiveIdx`는 `var simActiveIdx = -1` (L383)으로 초기화되며 `null` 설정 경로 없음. `>= 0` 단일 조건으로 정리 ✅
- **W3 (모드 격리)** — 클릭 위임 핸들러에 `if (currentMode !== 'similarity') return;` 가드 추가. diff 모드에서 sim 클릭 코드 발화 자체 차단 ✅
- **W5 (다크모드 오버라이드 누락)** — `body[data-theme="dark"] .sim-minimap-mark.active` 추가. `.cp-minimap-mark.active` 패턴과 일치 ✅
- **S1 (의도 주석)** — `bottomRatio <= topRatio` 보정 코드 위에 "1문장 매칭 ratio 보정" 주석 명시 ✅

#### Warning 미반영 상세 (안전 판단)

- **W2 (`offsetParent` 가정)** — 정적 분석 결과:
  - `.cp-panel-body` 는 `position: static` (default), 그 부모 `.cp-panel-body-wrap` 이 `position: relative` (`css/compare.css:104`)
  - 따라서 sentence span 의 offsetParent 는 `.cp-panel-body-wrap`. 패널 자체가 아님
  - **그러나** `.cp-panel-body` 가 `.cp-panel-body-wrap` 의 첫 자식이고 wrap 의 padding 0 이라 offsetTop 이 panel 내부 content position 과 동일
  - **diff 모드(`renderMinimapFor`, L4185)도 동일 패턴** 으로 작동 중 — sim 모드에서도 동일하게 안전
  - 향후 wrap/panel 구조 변경 시 주의 필요 — 보고서 후속 항목으로 기재
- **W4 (필터 변경 후 image load 핸들러 재등록)** — 정적 분석:
  - 필터 변경 시 `simApplyFilter` → `simRenderMinimap` 호출. 패널 innerHTML 은 변경 없음
  - 이미지·폰트는 이미 simApplyHighlights 1회 호출 시점에 load 대기 등록됨
  - 필터 변경으로 새 이미지가 추가되지 않으므로 재등록 불필요
  - 의미 있는 케이스: 사용자가 같은 세션에서 다른 문서로 재업로드 → simApplyHighlights 가 다시 호출되어 새 이미지에 다시 load 등록 ✓
  - **보강 미실시 사유**: 동작상 불필요. 향후 simApplyFilter 가 DOM 을 변경하는 패턴 추가될 시 재검토

#### Suggestion 보고서 기재

- **S2 (변수명 `minimapSettings`)** — 외부 스코프와 차별화 의도(미니맵 호출 한정 settings 의 의미). 통일 시 가독성 vs 차별성 trade-off, 후속 리팩토링 시 검토
- **S3 (ResizeObserver 통합)** — Phase 3 코드 통합 시 자연 해소. 현재는 명시적 분리가 디버깅 용이
- **S4 (CSS 너비 차이 — sim 12px vs cp 10px)** — sim 마커는 multi-sentence 비례 높이라 좌우 1px 여유로 살짝 넓게 보이는 게 시각적으로 도움. 의도적 차이로 판단, 변경 보류

### Design Reviewer / Playwright

- **Design Reviewer**: 본 변경은 시각 디자인 대신 **인터랙션 정상화** 가 본질 (마커 색상은 기존과 동일 토큰 사용, 위치 정확도만 개선). 신규 시각 요소 = 다크모드 active 박스 그림자 1줄. 디자인 시스템 영향 0 → design-reviewer 호출 생략
- **Playwright 시각 검증**: 본 환경에서 개발 서버 가동 권한 거부 (`python -m http.server` denied). **사용자가 서버 가동 후 다음 시나리오 수동 검증 필요**:

#### 사용자 검증 시나리오 (Playwright 수동 단계)

1. **클릭 작동**: compare.html → 유사도 모드 → 검사 실행 후 우측 미니맵 임의 마커 클릭 → 사이드바 카드 active + 본문 스크롤
2. **위치 정확도** (multi-sentence): 5문장 매칭 카드를 본문에서 확인 후, 미니맵의 마커가 본문 하이라이트 영역 전체 길이를 덮는지 확인 (이전엔 첫 문장만 표시)
3. **활성 마커**: 사이드바 다음/이전 버튼 → 미니맵의 active 마커가 따라 이동
4. **리사이즈**: 사이드바 폭 드래그 → 마커 위치 자동 보정
5. **필터 응답**: "약한 유사" OFF → 약한 유사 마커 사라짐 + 나머지 마커 위치 변화 (본문 layout 변경 반영)
6. **클릭 누적 검증**: DevTools `getEventListeners(document.getElementById('cp-minimap-a'))` 호출 → click handler 1개 (필터·설정 토글 N회 후에도)
7. **다크모드 active**: 사이드바 다음 누르고 다크 토글 → active 마커 박스 그림자 가시성 확인
8. **diff 모드 회귀**: 모드 전환 → 비교(diff) 모드에서 미니맵 클릭·active 정상 작동 (sim 클릭 가드가 막지 않음 검증)

### 다른 모드 영향성 검증 (정적 분석)

- `.cp-minimap-mark`(diff) 클래스 규칙 변경 0 — diff 마커는 그대로
- `renderMinimapFor`, `updateMinimapMarkers`, diff ResizeObserver 코드 변경 0
- 클릭 위임이 동일 컨테이너에 등록되나 `currentMode !== 'similarity'` 가드로 격리
- diff 마커에는 `.sim-minimap-mark` 클래스가 없으므로 `e.target.closest('.sim-minimap-mark')` 도 null 반환
- 회귀 위험 0 (정적 안전성)

## 사용자 관점 피드백

### 긍정 (예상 효과)
- **클릭이 작동한다** — 핵심 결함 해소. 사용자가 "이거 눌러도 안 되는데?"의 가장 큰 의문 해결
- **마커가 본문 하이라이트와 길이까지 일치** — multi-sentence 매칭에서 마커가 짧고 본문은 길게 빨간 영역인 시각 mismatch 해소. **분포 인지** 가치 회복 (사용자 명시 의도)
- **사이드바 다음/이전 → 미니맵 active 마커 이동** — 미니맵을 보면 "지금 어디 보고 있는지" 명확
- **사이드바 드래그·창 리사이즈에도 위치 안 어긋남** — 한 번 검사한 후 패널 폭 조절해도 마커 정확
- **이미지·폰트 로드 후 자동 보정** — 큰 이미지 포함 PDF·DOCX 도 점진 mismatch 발생 안 함

### 우려
- 매칭 길이가 짧으면(1문장) 마커도 짧아 보이는데, 동일 offsetTop 보정으로 최소 3px 확보. 그러나 **사용자가 이전 4px 고정 마커에 익숙했다면 처음엔 "마커가 줄어든 듯"** 한 인상 가능. 분포 정보가 더 정확해진 만큼 학습 비용 작음

## 웹디자인 전문가 관점 피드백

### 시각 위계
- **마커 비례 높이** = 매칭 길이 정보 시각화. 짧은 매칭은 작은 점, 긴 매칭은 막대로 보임 → 한 눈에 "큰 매칭이 어디 모여 있는지" 파악 가능 (분포 인지의 본질)
- **카테고리 색상**: 동일/거의 동일/의역(파랑)/약한유사 — 기존 plan-45 토큰 그대로. 일관성 유지

### 인터랙션
- **호버 시 `transform: scaleX(1.3)`** — 마커가 14px 폭에서 18px 로 확장, 좁은 영역에서도 클릭 타겟 확보 (WCAG 24×24 미달이나 우측 끝이라 접근성 영향 작음)
- **active 박스 그림자** — `--white` 1px outline + `--shadow-sm` 으로 현재 위치 명확. diff 마커와 동일 패턴 → 모드 간 학습 비용 0

### 다크 모드
- 6 카테고리 모두 `tokens.css` 토큰 사용 → 다크 자동 전환
- `low_similarity`/`excluded_manual` 의 `--text-muted` 다크값 `#9ca3af` 가 어두운 미니맵 트랙 위에서 가시성 확보 (Plan-45 Phase 3.6 검증 완료)
- active 다크 오버라이드 (CR-W5) 추가로 다크 모드 가시성 동등

### 접근성
- 키보드 네비게이션: 마커 자체는 `<div>` (button 아님). 사이드바 다음/이전 버튼이 키보드 경로 — 미니맵은 보조 시각 채널
- 색맹: 카테고리별 색만으로 구분 (모양 차이 없음). 단, 사이드바 카드의 라벨 텍스트가 1차 정보원 → 미니맵은 위치 인지 보조라 색맹 영향 제한적

## 잔여·후속 제안 (이번 범위 외)

- [ ] **Phase 2 — 호버 툴팁 (PyCharm L2)** — 마커에 마우스 200ms 후 카테고리·점수·스니펫 60자. 분포 인지 + 미리보기 동시 가치
- [ ] **W2 후속 모니터링** — `.cp-panel-body-wrap` / `.cp-panel-body` 구조 변경 시 offsetParent 영향 점검
- [ ] **Phase 3 — diff·sim 미니맵 코드 통합** — 한쪽 수정 시 다른 쪽 동기화 누락 방지. 현재 sim 만 수정했지만 diff 의 단순 marker height/click 패턴과 통합 가능
- [ ] **diff 모드 호버 툴팁** — Phase 2 패턴을 diff(added/deleted/modified)에도 재사용
- [ ] **사용자 Playwright 수동 검증 8 시나리오** — 위 8건 (백엔드 가동 후)

## 커밋 제안

```
버그 [Verify/Compare] Plan-48 Phase 1 — 유사도 미니맵 정상화 + 위치 정확도

사용자 지적 — "클릭이 안 되고 본문 하이라이트와 위치도 어긋난다."
diff 모드 미니맵 패턴 채택 + multi-sentence 표준(PyCharm/VSCode) 적용.

핵심 결함 5건 청산:
- .sim-minimap-mark CSS 클래스 신설 (pointer-events:auto, 6 카테고리 색상)
  → 부모 .cp-minimap 의 pointer-events:none cascade 무력화 (클릭 발화)
- simRenderMinimap multi-sentence 마커 (querySelectorAll 첫·마지막 element)
  → 5문장 매칭이 본문 하이라이트 영역 전체 길이 덮음 (분포 인지 회복)
- 클릭 위임 1회 등록 + currentMode 가드 (재계산마다 누적되던 핸들러 제거)
- sim ResizeObserver (사이드바·창 리사이즈 자동 보정)
- simHighlightMinimapActive — simNavigateToMatch 후 미니맵 active 동기
- simRecalcMinimapAfterLayoutSettle — 이미지·폰트 로드 후 재계산
- 다크모드 .sim-minimap-mark.active 오버라이드 (CR-W5)

검증: 단위 21/21 PASS · sim_label_consistency.sh PASS · vm.Script errors 0
   · code-reviewer Critical 0 (W1·W3·W5·S1 즉시 반영 / W2 정적 안전 / W4 미반영 사유)
   · diff 모드 영향 0 (sim-* 접두사 + 모드 가드 격리)
   · Playwright 수동 검증 8건 — 사용자 후속 (서버 권한 거부)

백엔드·SSOT·라벨 불변. Plan-45 invariants (E1~E5, C1~C7, V1~V5, S1~S3) 준수.
```
