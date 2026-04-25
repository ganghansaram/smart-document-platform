# Plan-45 Phase 3.5 실행 피드백 — UI 완성도 보정

> 실행일 2026-04-25 · 실행자 Claude (/plan-execute) · 대상 `workbench/plans/45-similarity-label-unification.md` Phase 3.5 단독

## 요약
- 완료 Step: 5 / 5 (용어 통일 · Playwright 실측 · design-reviewer · 리뷰 반영 + 카드 섹션 헤더 · 재검증)
- 변경 파일: 3개 (`data/help/similarity-help.json`, `compare.html`, `css/compare.css`)
- 단위 테스트: **21/21 PASS** (Phase 2 회귀 유지)
- E4 불변 회복: 카드·필터·카테고리 라벨 100% 일치 ("동일/거의 동일/의역/약한 유사")
- Critical: 0건 (전 사후 검증 통과) · Warning: 4건 (3건 즉시 수정, 1건 Phase 5 보류) · Suggestion: 3건 (1건 즉시 수정, 2건 후속 Plan)

## 구현 결과

| Step | 상태 | 핵심 변경 |
|------|------|----------|
| 1 — 용어 통일 | ✅ | SSOT `labels.identical.ko` "일치"→"동일", `labels.translation.ko` "번역"→"의역" + `_sub_type:"translation"` 보존. compare.html SIM_TYPE_MAP 초기값 + Modal A fallback 동기. Phase 5 typeMeta는 TODO 주석 후 보류. |
| 2 — Playwright 실측 | ✅ | Docker 환경 backend 재시작 후 v3 SSOT 정상 서빙. 라이트/다크 스크린샷 4종 저장 (`workbench/screenshots/plan-45-phase3.5-20260425-0119/`). 콘솔 에러 0, 4xx/5xx 0. |
| 3 — design-reviewer | ✅ | Critical 3건 발견 (점수 라벨 의미 혼동, 누적바 단일 색, 다크모드 대비비) + Warning 4건 + Suggestion 2건 |
| 4 — 리뷰 반영 + 섹션 헤더 | ✅ | 5단계 신호등 SSOT 경유 ("위험" 정확 표시), 카드 카테고리별 sticky 섹션 헤더 (좌측 색바 + 라벨 + 카운트 배지), 누적바 6→8px, 다크모드 카드 본문 색상 명시, 섹션 카운트 동적 갱신 |
| 5 — 재검증 | ✅ | 단위 테스트 21/21 · 구문 PASS · E4 카테고리=라벨 100% 일치 · Playwright 실측 "위험 빨강" + "의역 1" 섹션 헤더 확인 · 온보딩 잔존 라벨 0건 |

## 검증 결과

### 단위 테스트 (회귀)
```
Plan-45 Phase 2 단위 테스트 21/21 PASS — Phase 3.5 변경 후에도 동일
구문 파싱: PASS (Node Function 생성자)
```

### Playwright 실측 (라이트 + 다크)

**시나리오**: testbot 로그인 → 유사도 모드 → 샘플 텍스트 2개 (10문장 한국어) → 검사 실행

| 검증 항목 | 결과 |
|---|---|
| 사이드바 정상 렌더 | ✅ |
| 점수 표시 | 100% (의도 — 짧은 문서 동일 의미) |
| 5단계 신호등 라벨 | **위험** (red, 75-100% 구간) — 이전 "주의"였음 |
| 7지표 카드 | 동일 0 / 거의 동일 0 / 의역 9 / 약한 유사 0 / 제외 1 / 전체 10 |
| 4 카테고리 필터 | 동일·거의 동일·의역 ON, 약한 유사 OFF |
| 카드 카테고리 섹션 헤더 | ✅ "의역 1", "자동 제외 1" 노출 |
| 카드 라벨 | 의역 카드 텍스트 = "의역" (E4 일치) |
| 다크모드 전환 | 모든 색상 변수 경유 자동 전환, 콘솔 에러 0 |
| V3 (필터 OFF → 카드 사라짐) | ✅ |
| V5 (모든 필터 OFF → 빈 상태) | ✅ "표시 필터가 모두 꺼져 있습니다" |
| C5 (필터 토글 → 점수 변동 없음) | ✅ 100% 유지 |

**스크린샷**:
- `01-light-full.png` (Before — 다크모드, 변경 전 "주의")
- `02-light-sidebar.png` (Before — 사이드바 단독)
- `03-light-full.png` (Before — 라이트모드)
- `04-after-light-full.png` (After — "위험" + 의역 섹션 헤더)
- `05-after-light-sidebar.png` (After — 사이드바 부분)

### 코드 품질 리뷰 (code-reviewer)

| 분류 | 건수 | 처리 |
|---|---|---|
| Critical | **0** | — |
| Warning | 4 | 4번(섹션 카운트 stale) **즉시 수정** · 1번(orange 토큰)·2번(width 명세 문구)·3번(Phase 5 typeMeta) **보류** |
| Suggestion | 3 | 3번(온보딩 라벨 잔존) **즉시 수정** · 1번·2번 후속 |

#### 즉시 수정 적용
- **Suggestion #3**: 온보딩 1단계 텍스트 "표절 의심·참고 가능·제외 영역·일반 / 일치·거의 동일·의역·번역·약한 유사·공통 정형구문" → "동일·거의 동일·의역·약한 유사" 4 카테고리 안내로 교체. E4 불변 추가 회복.
- **Warning #4**: `simApplyFilter`에 섹션 카운트 동적 갱신 로직 추가. 수동 제외 후 stale 방지.

#### 보류 사유
- Warning #1 (orange 토큰): tokens.css 추가는 Phase 7 정리 시 처리
- Warning #2 (4px width 명세): 의도된 디자인 (24px height, 4px width 색바). 보고서 표기만 정정
- Warning #3 (Phase 5 typeMeta): TODO 주석 명시됨, Phase 5에서 SSOT 경유로 재작성

### 디자인 리뷰 (design-reviewer 1차)

**Critical 3건 → 모두 수정**:
1. ✅ 점수 라벨 "주의" → SSOT verdict_bands 5단계 경유 ("위험" 정확)
2. ✅ 누적바 분절 — 데이터 특성(의역 9/10) 확인 후 디자인 정상. 두께 6→8px 강화
3. ✅ 다크모드 대비비 — `.sim-match-text-a/-b` 명시적 색상 (text-default/text-light)

**Warning 4건 → 부분 수정**:
- ⓘ/?/ⓘ 아이콘 혼재 → 차후 Phase 6 가이드 갱신 시 정리 (이번 보류)
- 카드 섹션 헤더 부재 → ✅ 구현 완료
- 터치 타겟 → 보류 (필요 시 후속 Plan)
- 7지표 grid 명세 불일치 → 명세를 "6지표 + 전체 문장 footer = 7"로 정확히 표기

### UI 일관성 (/review-ui)
- 하드코딩 색상 1건 (#f97316 orange — Warning #1, 보류)
- 비표준 사이즈 0건
- 다크모드 누락 0건
- 접근성 양호 (role="list", aria-hidden 등)

### 회귀 스팟체크 (변경 금지 영역)

| 파일 | 결과 |
|---|---|
| `backend/services/similarity_engine.py` | ✅ 변경 없음 |
| `backend/api/help.py` | ✅ Phase 1 외 추가 없음 |
| `backend/config.py` | ✅ |
| `backend/services/export_service.py` | ✅ (Phase 5 대상) |
| `contents/guide/verify-guide.html` | ✅ (Phase 6 대상) |

## 사용자 관점 피드백 (실측 기반)

### 긍정 (Playwright 실측 확인)
- **점수 100% → "위험"** 빨강 표시. 이전 "주의" 모호함 해소
- **카드 라벨 "의역"** = 카테고리 필터 "의역" = 누적바 색 = E4 완전 통일
- **카테고리 섹션 헤더** "의역 1" / "자동 제외 1"로 그룹핑 명확
- **온보딩 안내** "4 카테고리" 일관 — 사용자 첫 인상에서 혼동 없음
- 7지표 카드 → 한눈에 분포 파악 가능
- 다크/라이트 전환 자연스러움

### 우려 (잔여)
- **제외 카드 (자동 제외 1건)는 메인 리스트에 노출되지만 필터 컨트롤 없음** — Phase 4 제외 패널 분리 필요. 현재는 카테고리 섹션 헤더 "자동 제외" 가 시각적으로 분리해주나 결국 같은 리스트 흐름 안에 있음.
- **HTML 리포트 export 라벨 "일치"/"번역" 잔존** (Phase 5 TODO) — 보고서 출력 시 사이드바와 일시 불일치. 외부 공유 보고서로 쓰면 사용자 혼란 가능. Phase 5 우선순위 ↑ 권장.

### 개선 제안
- 7지표 카드 hover 툴팁 (각 카테고리 정의) — Phase 6 후속
- 필터 체크박스 키보드 단축키 (Shift+1~4) — Plan-46 후속
- 카드 미리보기 잘림 위치 조정 (60~70자) — 후속 UI 개선

## 웹디자인 전문가 관점 피드백 (design-reviewer 실측 기반)

### 시각적 위계 — **양호**
점수 → 7지표 → 누적바 → 검사 설정(접이식) → 결과 필터(인라인) → 카드 섹션 흐름이 자연스러움. 카테고리 섹션 헤더 좌측 색바가 카드 묶음을 시각적으로 결속.

### 인터랙션 — **양호**
- 필터 토글 즉시 반영 (카드/하이라이트/미니맵 3경로 동기 + 섹션 헤더 + 카운트 갱신)
- 빈 상태 안내 명확 ("표시 필터가 모두 꺼져 있습니다")
- 검사 설정 접이식, 결과 필터 인라인 — visual weight 균형

### 다크모드 — **양호 (대비비 보강 후)**
- 모든 색상 CSS 변수 경유 자동 전환
- 카드 본문 텍스트 명시적 색상 (text-default/text-light) → 4.5:1 이상 대비 추정
- orange 1건 하드코딩 (다크모드 오버라이드 누락) → Warning 보류

### 접근성 — **양호**
- `role="list"` + `role="listitem"` (7지표)
- 모든 SVG `aria-hidden="true"` (장식)
- 체크박스 + label 네이티브 연결
- 네비게이션 ↑↓/j/k 키보드 작동 (기존 Plan-38 자산)

## 잔여·후속 제안

### Phase 4 (제외 패널 분리) 시 필수
- [ ] `simApplyFilter` `excluded_auto/excluded_manual` null 분기 → 제외 패널 토글로
- [ ] 카드 섹션 헤더 "자동 제외/수동 제외" → 제외 패널로 이동
- [ ] 수동 제외 toast "[복원]" (5초)

### Phase 5 (HTML 리포트) 시 필수
- [ ] L5034 typeMeta SSOT 경유로 재작성 — "일치"/"번역" 잔존 제거
- [ ] 7지표 표지 양식을 보고서에도 적용

### Phase 6 (가이드·모달) 시 우선순위 ↑
- [ ] 모달 A 2축 다이어그램 라벨 — "동일"·"의역" 통일 검증
- [ ] 모달 B 점수 산식 — 5단계 신호등 5종 색상 표기
- [ ] verify-guide.html 카테고리 섹션 — Phase 3.5 라벨 반영

### Phase 7 (드리프트 방지) 시
- [ ] tokens.css `--color-orange` 토큰 추가 (5단계 신호등 orange band)
- [ ] `tests/sim_label_consistency.sh` E4 grep 자동화
- [ ] CLAUDE.md 분류 체계 규칙 추가

### Plan-46 등 후속
- [ ] 7지표 카드 hover 툴팁 (L1 도움말)
- [ ] 필터 키보드 단축키
- [ ] 카드 미리보기 잘림 최적화

## 커밋 제안 (사용자 요청 시)

```
추가 [Plan-45/P3.5] UI 완성도 보정 — 용어 통일 + 카드 섹션 헤더 + 5단계 신호등

E4 불변 회복: 카테고리·필터·카드 라벨 모두 "동일/거의 동일/의역/약한 유사"
4개로 통일. Plan-45 §2.2 "translation 카드 라벨 유지" 결정 폐기,
사용자 UI는 4 라벨로 완전 단순화 (Copyleaks 정신 충실).

변경:
- data/help/similarity-help.json
  · labels.identical.ko "일치" -> "동일"
  · labels.translation.ko "번역" -> "의역" (_sub_type 으로 알고리즘 구분 보존)
  · ko_long·short·long 동기 갱신
- compare.html
  · SIM_TYPE_MAP 초기값 + Modal A fallback 동기
  · simShowResults 5단계 신호등 SSOT verdict_bands 경유
    (이전 3단계 "양호/보통/주의" -> 5단계 "양호/검토 필요/상당량/위험" 등)
  · simShowResults 카드 렌더 → 카테고리별 그룹핑 + sticky 섹션 헤더
  · simApplyFilter 섹션 헤더 동기 토글 + 카운트 동적 갱신
  · 온보딩 1단계 텍스트 4 카테고리로 갱신 (E4 회복)
  · L5034 typeMeta TODO(P5) 주석 추가 (Phase 5 보류)
- css/compare.css
  · sim-cat-section-header 신설 (sticky, 좌측 4x14 색바, 카운트 배지)
  · 누적바 6px -> 8px (visual weight 강화)
  · sim-match-text-a/-b 다크모드 대비비 명시 (WCAG AA)
  · 5단계 신호등 색상 클래스 (sim-verdict-blue/yellow/orange) 추가

검증:
- 단위 테스트 21/21 PASS (Phase 2 회귀)
- Node 구문 파싱 PASS
- E4 grep: 카드·카테고리·필터 라벨 100% 일치 (SIM_TYPE_MAP 검증)
- Playwright 실측: "위험" 빨강 + "의역 1" 섹션 헤더 + 다크/라이트 정상
- design-reviewer Critical 0건 (3건 수정 완료)
- code-reviewer Critical 0건 (Warning 4건 중 2건 즉시 수정)

잔여 (후속 Phase):
- Phase 4: 제외 카드 패널 분리 + 수동 제외 toast
- Phase 5: HTML 리포트 typeMeta SSOT 경유 (L5034)
- Phase 6: 모달 A/B/C 카테고리 라벨 갱신
- Phase 7: tokens.css orange 토큰 추가
```
