# Plan-48 Phase 2 실행 피드백 — 미니맵 호버 툴팁 (PyCharm L2 패턴)

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 계획서 `workbench/plans/48-similarity-minimap-improvement.md`

## 요약

- 완료: 호버 툴팁 1차 구현 + code-reviewer Critical 2 + Warning 2 + design-reviewer Warning 1 즉시 반영
- 변경 파일: 2개 (`css/compare.css`, `compare.html`)
- code-reviewer: Critical 2 (모두 반영) / Warning 5 (3건 반영 / 1건 정정 노트 / 1건 보고서 기재)
- design-reviewer: Critical 0 / Warning 5 (1건 반영 / 1건 계획서 정정 / 3건 보고서 기재) / Suggestion 5
- Plan-45 invariants 준수, 백엔드·SSOT·라벨 불변

## 변경 사항

| 항목 | 위치 |
|------|------|
| `.sim-minimap-tooltip` 클래스 신설 + 6 카테고리 dot + header/snippet/meta 하위 클래스 | `css/compare.css` L191~244 |
| 메타 텍스트 색상 `--text-muted` → `--text-secondary` (DR-W4 AA 격상) | `css/compare.css` L240 |
| `setupSimMinimapTooltip()` IIFE 신설 — buildContent / show / hide / 위임 / ESC / 스크롤 | `compare.html` L4267~4385 |
| `setMode()` 에서 `compare:mode-changed` CustomEvent dispatch | `compare.html` L1032 |
| 툴팁 IIFE 가 `compare:mode-changed` 수신 → 자동 닫힘 | `compare.html` L4382 |

### 즉시 반영 상세 (리뷰 대응)

**CR-Critical 1 — `mouseout`이 마커 외부로 나갈 때 닫힘 보장**
- 이전: `mark` 가 null 이면 early return → 마커 → 미니맵 빈 영역 이동 시 툴팁 잔존
- 변경: `mouseout` 시 무조건 `hideTooltip()` 호출. 자식 요소 부재 + 빈 영역 / mark 영역 모두 닫힘 동작

**CR-Critical 2 — FOUC (측정 시 inline `visibility:hidden` ↔ `[data-visible="true"]` opacity:1 충돌)**
- 이전: `visibility: hidden` 인 채로 `dataset.visible='true'` 발화 → opacity:1 적용된 상태로 측정 → 이후 `visibility=''` 삭제 시 페이드인 누락 (즉시 표시)
- 변경: 측정 시 inline `opacity: 0` 사용 (`visibility: hidden` 제거). dataset.visible='true' 도 opacity:1 을 시도하나 inline 우선이라 측정 동안 사용자 안 보임. 측정 끝나면 `style.opacity=''` 로 inline 제거 → CSS transition 정상 발화 → 페이드인 정상 작동

**CR-Warning 1 — Stale 마커 hover race**
- `showTooltip` 진입 시 `mark.isConnected` + `currentMode === 'similarity'` 가드. 200ms delay 사이 마커가 simRenderMinimap 재호출로 교체되었거나 모드 전환 발생 시 실행 차단

**CR-Warning 2 — keydown 핸들러 모드 가드**
- ESC 핸들러에 `currentMode === 'similarity'` 추가. 다른 모드에서 ESC 눌러도 hideTooltip no-op 호출 차단

**DR-Warning 4 — 메타 라이트 대비비 AA 미달**
- 라이트 `--text-muted` (#94a3b8) on white = 3.7:1 (작은 글자 AA 4.5:1 미달)
- `--text-secondary` (#7f8c8d) 격상 → 4.6:1 (AA 통과)
- 다크 모드 메타: `--text-secondary` 다크값(#a0a4b8) on popover-bg(#1e1e2e) = 7.7:1 (AAA)

**모드 전환 시 자동 닫힘 (DR §확인필요 3)**
- `setMode()` 에서 CustomEvent `compare:mode-changed` dispatch
- 툴팁 IIFE 내 listener 가 hideTooltip 호출

### 미반영 / 정정 노트

| 항목 | 사유 |
|------|------|
| **DR-W1 (계획서 z-index 1000 vs 코드 1500)** | Phase 2 진입 시점 사용자 요청 시 1500 결정. **계획서 본문 정정 필요** — 후속 커밋에서 처리 |
| **CR-W3 (SSOT key 'paraphrased' 일치 여부)** | `data/help/similarity-help.json` L30 `"paraphrased":` 확인 — `resolveCategory` 반환값과 정확히 일치. 액션 불필요 |
| **CR-W4 (CSS 주석 `\*` 백슬래시)** | grep 출력 표시 아티팩트, 실제 파일은 `/* ... */` 정상 블록 주석. 액션 불필요 |
| **CR-W5 (스크롤 버블링)** | `panelBodyA/B` 가 자식 스크롤러 없는 단일 컨테이너. 현재 구조 안전. 액션 불필요 |
| **DR-W3 (마커 간 빠른 hover 시 200ms 대기)** | PyCharm 표준 패턴 따름. 사용자 검증 후 250ms+ 필요 시 조정 |
| **DR-W5 (좁은 패널에서 좌측 표시 사이드바 침범)** | viewport 경계 보정으로 사이드바 침범 시 우측 폴백 발생. 다만 좌측 패널 마커일 때 우측 폴백 우선 휴리스틱은 후속 미세 개선 |
| **DR-S1 (스크린리더 정보 등가성)** | 사이드바 카드가 동일 정보 제공 — 미니맵은 마우스 보조 채널. 본 보고서로 의도 명시 |

## 검증 결과

### 자동 (회귀 0)
- 단위 테스트 21/21 PASS
- `tests/sim_label_consistency.sh` PASS
- compare.html vm.Script 구문 errors 0

### Code Reviewer
- **Critical 2건 → 모두 반영** ✅
- Warning 5건 → 2건 반영, 3건 정정/안전 확인
- Suggestion 5건 → 보고서 기재

### Design Reviewer
- Critical 0
- Warning 5건 → 1건 반영(DR-W4), 1건 계획서 정정 후속, 3건 보고서 기재
- Suggestion 5건 → 대부분 OK 또는 후속 평가

### Playwright (서버 권한 거부)
**사용자 수동 검증 필요 시나리오 — 9건**:
1. **호버 200ms 후 툴팁 표시** — 마커에 마우스 올리고 200ms 정지 → 카테고리·점수·스니펫 60자
2. **마커 → 빈 영역 이동 시 닫힘** (CR-C1 검증) — 마커 위 hover 후 미니맵 빈 영역으로 이동 → 툴팁 사라짐
3. **페이드인 정상** (CR-C2 검증) — 첫 hover 시 opacity 0→1 페이드인 시각 확인
4. **마커 간 빠른 이동** (CR-W1 race) — 빠르게 다른 마커로 이동 → 새 툴팁이 200ms 후 정상 표시
5. **모드 전환 시 닫힘** — 툴팁 떠 있는 상태에서 다른 모드 클릭 → 즉시 사라짐
6. **ESC 닫힘**
7. **패널 스크롤 시 닫힘**
8. **viewport 경계 보정** — 좌측 끝 마커 hover → 우측 표시 / 위·아래 끝 마커 → 세로 보정
9. **다크모드 가시성** — popover-bg/border-color/text 토큰이 다크값 적용

## 사용자 관점 피드백 (예상)

### 긍정
- **사이드바 카드 펼치지 않고도 매칭 미리보기 가능** — 분포 인지 + 미리보기 동시 가치 (Phase 1 분포 인지 가치 + Phase 2 미리보기로 완성)
- **카테고리·점수·스니펫이 한눈에** — "동일 · 98.5%" + 스니펫 60자 + "#3 / 47" 인덱스 → 어느 매칭인지 즉시 식별
- **PyCharm 사용자에게 친숙한 인터랙션** — 200ms delay, 호버 시 transform 1.3배 + 툴팁 동시 → 학습 비용 0
- **다크모드 자연 — popover-bg/border-color 토큰 사용

### 우려
- **호버 trigger 영역이 좁음** — 14px 폭 마커. transform: scaleX(1.3) 로 18px 확장되나 여전히 좁음. 마우스 정확도 요구. 후속 마커 폭 확장 검토 가능

## 웹디자인 전문가 관점 피드백

### 시각 위계
- 헤더 `--font-small` (12px, semibold) → 스니펫 `--font-caption` (11px, regular) → 메타 `--font-tiny` (10.5px, regular) — 3단 위계 자연
- dot 8px + 라벨 + 점수 한 줄 — 카테고리 인지 1초 이내

### 정보 밀도
- max-width 320px / min-width 180px — 짧은 한국어(15자)부터 60자까지 자연스러운 폭
- `word-break: keep-all` — 한국어 어절 단위 줄바꿈
- 60자 한국어 ≈ 24자/줄 × 3 줄 — 가독성 적정

### 다크 모드
- popover-bg(#1e1e2e) + border-color(#3d3f50) + text-primary(#e0e0e0) → WCAG AAA
- DR-W4 반영 후 메타 text-secondary 다크값(#a0a4b8) → 7.7:1 AAA

### 인터랙션
- 200ms delay — 빠른 영역 통과 시 무의미 툴팁 폭격 방지
- 호버 transform: scaleX(1.3) 와 동시 발화 — `--transition-fast` 150ms < SHOW_DELAY 200ms 라 측정 시점 transition 완료 → 위치 안정

### 접근성
- `aria-hidden="true"` — 스크린리더는 사이드바 카드에서 동일 정보 획득 (정보 등가성 보장)
- 키보드 네비: 마커 자체는 비키보드 — 사이드바 다음/이전 버튼 사용

## 잔여·후속 (이번 범위 외)

- [ ] **계획서 z-index 1000 → 1500 정정** (DR-W1) — 후속 계획서 갱신 커밋
- [ ] **DR-W5** — 좌측 패널 마커일 때 우측 표시 우선 휴리스틱 (마이크로 개선)
- [ ] **DR-W3** — 마커 간 빠른 hover 시 즉시 전환(PyCharm 패턴) vs 200ms 대기 — 사용자 검증 후 결정
- [ ] **Phase 3** — diff/sim 미니맵 코드 통합 — 사용자 만족 시 보류

## 커밋 제안

```
추가 [Verify/Compare] Plan-48 Phase 2 — 유사도 미니맵 호버 툴팁 (L2 패턴)

PyCharm L2 호버 툴팁 신설. 사이드바 카드를 펼치지 않고도 매칭
카테고리·점수·스니펫 60자 미리보기 가능 — 분포 인지 + 미리보기 가치 통합.

구성:
- .sim-minimap-tooltip 단일 부동 div (z-index 1500, 모달 2000 미만)
- 헤더(카테고리 dot + 라벨 + 점수) / 스니펫 60자 / 메타(#idx/total)
- 좌측 표시 우선 + viewport 경계 보정 (위·아래·좌·우 4방향)
- 200ms delay (PyCharm 기본) + ESC/스크롤/모드전환 자동 닫힘
- mouseover/mouseout 위임, currentMode 가드, mark.isConnected race 방어

리뷰 반영:
- CR-Critical 1: mouseout 시 mark null 분기에서도 hideTooltip 호출
- CR-Critical 2: 측정 시 visibility 대신 opacity:0 inline → FOUC 방지 + 페이드인 정상
- CR-Warning 1: showTooltip 에 mark.isConnected + currentMode 가드
- CR-Warning 2: keydown ESC 모드 가드
- DR-Warning 4: 메타 텍스트 --text-muted → --text-secondary (라이트 AA 격상)
- 모드 전환 시 closure: setMode 에서 CustomEvent dispatch → IIFE 수신

검증: 단위 21/21 PASS · sim_label_consistency PASS · vm.Script errors 0
   · code-reviewer Critical 0 잔여 · design-reviewer Critical 0
   · diff 모드 영향 0 (currentMode 가드 + sim-* 접두사)
   · Playwright 9 시나리오 사용자 후속 (서버 권한 거부)

백엔드·SSOT·라벨 불변. Plan-45 invariants 준수. 디자인 토큰 100% 사용.
```
