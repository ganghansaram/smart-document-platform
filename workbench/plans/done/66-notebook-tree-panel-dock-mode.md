# Plan-66 — Notebook 트리 패널 도킹(밀어내기) 모드 추가

> **상태: ✅ 완료 (2026-06-28)** — ② 도킹-듀얼(밀어내기) 구현·검증·코드리뷰 완료. 도킹은 새 토글 `#tp-dock`/키 `tp-docked`(핀 보존, B안) · A2 push(`--tp-width`) · 트리 리사이즈 핸들(듀얼 핸들 로직 재사용) · 전역 폭 저장+복원 클램프 · `rerenderBothPanels` 재사용. code-reviewer 검토 후 Critical 1(복원 max 클램프)+안전장치 3 수정. testbot 실데이터·라이트/다크·회귀·콘솔0 검증.
> 작성: 2026-06-27 · 트리거: 동료 피드백 — "트리 패널이 본문 위에 겹쳐 떠서, 띄워놓고 작업하려면 뒷 문서가 가려져 결국 접어야 한다. 본문을 밀어내며 펼쳐지면 좋겠다."
> 성격: **UX 패턴 보강** (기능·데이터 모델 무관). 분할(PDF 듀얼페인) 화면 특수성 때문에 "교체"가 아닌 "선택지 추가"로 접근.

## 🧭 현황 한눈에

> **핵심 = 오버레이(겹침) 단일 모드 → 도킹(밀어내기) 모드를 opt-in 으로 추가.** 현재 핀을 꽂아도 패널이 본문 위에 떠 있어, "레퍼런스 띄워두고 작업"이 안 됨. 동료 요청은 업계 표준(데스크톱=밀어내기)에 부합. 단, 이 시스템은 **PDF 듀얼페인 분할 화면**이라 무조건 밀어내면 비좁아질 위험 → 디폴트는 오버레이 유지, 도킹은 선택.

| | 현재 | 동료 요청 | 본 계획 제안 |
|---|---|---|---|
| 평상시 | 호버 오버레이(겹침) | — | **유지** (분할 화면 안 좁힘) |
| 고정 시 | 핀 = 여전히 오버레이 | **핀 = 밀어내기(도킹)** | **핀 = 진짜 도킹으로 승격** |
| 디폴트 | 오버레이 | (불명) | 오버레이 유지, 도킹 opt-in |

## 🔬 왜 (코드 근거) — *design-reviewer 검증 반영 (2026-06-27)*
- 현재 패널 `#tp-overlay`(`.tree-panel-overlay`, `css/translator.css:1555~`)는 **`position: absolute` + `transform: translateX(-100%)→0`** 슬라이드 + `z-index: 100`, **폭 340px**(`:1559` — 종전 280px 기재는 오류) → **본문 위에 떠서** 열림. 컨테이너 `.translator-body`(`translator.html:29`, `css/translator.css:35`)는 **`flex:1; position:relative`** — flex *행*이 아니라 positioned 컨테이너이고, 듀얼페인은 그 안 `#view-viewer` > `#viewer-panels`(`#panel-left`/`#panel-right`)에 있음.
- 핀 버튼 `#tp-pin`(`.tp-btn.pinned`, `translator.css:1609`)은 패널을 **열린 채 유지**할 뿐 여전히 오버레이 → 동료 불편의 핵심. 상태는 `localStorage 'tp-pinned'`(`js/translator.js:2493,2531`).
- **PDF 리플로우는 이미 해결돼 있음(중요)**: 듀얼페인 사이 리사이즈 핸들(`js/translator.js:3586~`, `#viewer-panels` 기준)이 드래그 후 **`rerenderBothPanels()`**(`:1715`, 여러 곳서 호출)를 부름 → **폭이 바뀌면 PDF 재렌더되는 기구현 메커니즘이 존재.** 도킹 토글 직후 이 함수만 재호출하면 됨. ⇒ 종전 계획이 "②의 실제 작업 핵심"으로 지목한 PDF 리플로우는 **과대평가**.
- 즉 "밀어내기"의 실제 작업 = **(a) `#view-viewer`/`#viewer-panels` 영역을 트리 폭만큼 미는 A2 레이아웃 + (b) 트리 패널용 리사이즈 핸들 신규(현재 0개) + (c) 기존 `tp-pinned` 하위호환**. (PDF 재계산 자체는 기존 함수 재사용)

## 📐 업계 표준 (조사 2026-06-27)
- **Material Design**: **Standard drawer(밀어내기)** = 데스크톱·태블릿(840dp+) 권장, 둘 다 동시 조작 / **Modal drawer(오버레이+scrim)** = 모바일(600dp 미만) 권장.
- 데스크톱 문서·생산성 도구 사실상 표준 = **밀어내기(persistent/docked)**: **VS Code**(탐색기가 에디터를 밀어냄), **Adobe Acrobat**(북마크/썸네일이 PDF 뷰를 밀어냄), **Notion·Slack·Figma**(접으면 아이콘 레일/호버).
- 단, 위 사례는 **단일 본문**을 밀어냄 — 본 시스템은 **이미 둘로 쪼갠** 듀얼페인이라 그대로 차용은 위험. → "둘 다 지원 + 사용자 선택"이 정석(Material 의 두 모드를 사용자가 고르는 구조).

## 1. 범위 (IN / OUT)
| ✅ 이번 (제안) | ⏭️ OUT (별건) |
|---|---|
| 도킹(밀어내기) 모드 추가 — 패널이 분할 워크스페이스를 밀어냄 | 트리 기능 변경(폴더 CRUD·드래그·컨텍스트 메뉴) — 무관 |
| 핀(`#tp-pin`)을 "도킹 토글"로 의미 승격 | 오버레이 기본 동작(호버 트리거) — 유지 |
| 도킹 시 듀얼페인 압박 완충(리사이즈·반응형 폴백) | Translator 외 시스템(Explorer 등) 트리 — 본 계획 밖 |
| 상태 기억(`localStorage`) | 트리 패널 시각 스타일 리디자인 — 무관 |

## 2. 설계 — 시안 선행 (확정 전 미리보기 필수)
"밀어내면 얼마나 좁아지는지"는 **눈으로 봐야** 판단 가능 → 드롭존·헤더 때처럼 **시안 목업 선행**.

**(A) 도킹 시 레이아웃 전환 방식 — A2 확정** *(검증: `.translator-body`는 flex 행 아님 → A1 부적합)*
- ~~A1: `.translator-body`를 flex 행으로~~ — **부적합**: `.translator-body`는 `flex:1; position:relative`(`css/translator.css:35`), 자식 패널이 absolute라 flex 행 전제가 깨짐
- **A2 (확정)**: 도킹 시 듀얼페인 영역(`#view-viewer` 또는 `#viewer-panels`)에 트리 폭만큼 `margin-left`/`padding-left`(CSS 변수 `--tp-width`) 부여 — 패널은 absolute 유지하되 **본문만 밀기.** 트리 폭 변수를 듀얼페인 push 와 공유 → 리사이즈가 자동으로 듀얼 폭에 반영.

**(B) 듀얼페인 압박 완충 (도킹 모드 한정)** — *주 장치 = 리사이즈*
- **패널 폭 리사이즈 가능 + 폭 기억** ← **핵심 완충 장치.** PDF 공간이 더 필요하면 트리를 좁히고(예 ~180px), 탐색 시 넓힘. VS Code·Acrobat 방식. (사용자가 직접 절충)
- **최소 폭 바닥(min-width)**: 트리 ≥ ~180px, 각 PDF 패널 ≥ ~320px — 리사이즈로 무한정 찌부 방지
- **③ 단일페인 폴백 = 선택적 안전망으로만**: 리사이즈로도 안 되는 극단 좁은 화면(작은 노트북)에서 하한 아래일 때만 듀얼→단일 제안. **자동 강제 아님**(동료 요구 = 듀얼 동시 유지)
- 접으면 **아이콘 레일**(완전 제거 대신 얇게) — 재오픈 빠르게 (선택)

**(C) 진입점/어포던스**
- 핀 버튼 = 도킹 토글로 의미 변경(아이콘/툴팁 "패널 고정" → "패널 도킹" 등 재고)
- 호버 오버레이(비도킹)는 그대로 — 빠른 점프용

## 3. 결정 사항

> **확정 방향 (2026-06-27, 사용자 결정): 시안 ② = 도킹-듀얼(밀어내기).** 동료 요구 = **두 문서(듀얼페인) + 트리 패널 동시 표시.** 좁아짐은 **리사이즈(폭 조절)로 사용자가 절충.** 시안 ③(듀얼→단일 폴백)은 채택하되 **극단 좁은 화면 한정 선택 안전망**으로만, 자동 강제 아님.

1. **교체가 아니라 추가** — 오버레이(겹침)는 평상 디폴트로 유지, 도킹(②)은 opt-in. ✅ 확정
2. **디폴트 모드** — 오버레이 유지(평상 빠른 점프), 도킹은 핀으로 opt-in. ✅ 확정(오버레이 디폴트)
3. **완충 = 리사이즈 우선** — 패널 폭 리사이즈 + 폭 기억이 주 장치. ③ 단일 폴백은 하한 아래 선택 안전망만. ✅ 확정(자동 강제 안 함)
4. **최소 폭 바닥** — 트리 ≥ **180px** / 각 PDF 패널 ≥ **320px** (시작값, 실측 후 조정). 듀얼 리사이즈엔 이미 `available` 계산(`js/translator.js:3608`)이 있으니 패턴 참고. ✅ 확정(시작값, 튜닝 여지)
5. **상태 기억 범위** — 도킹 on/off + **트리 폭**을 **전역 1개**로 저장(문서별 아님). ✅ 확정(전역)
6. **트리 리사이즈 핸들 = 신규 작업(핵심)** — "리사이즈가 주 완충"인데 트리 패널엔 핸들이 **현재 0개.** 듀얼페인 핸들 로직(`:3586~`) 재사용 가능하나 신규 구현 필요. ⬜ 설계 대기
7. **`tp-pinned` 하위호환 = 새 키 분리(B안)** — 핀(오버레이 고정, 기존 `tp-pinned`)은 **그대로 보존**, 도킹은 **별도 토글 + 새 키 `tp-docked`(기본 off)**. 기존 사용자 변화 없음·도킹은 명시적 opt-in. ✅ 확정(B, 핀 갈아끼우지 않음)
8. ~~PDF.js 리플로우~~ — **기구현(`rerenderBothPanels`) 재사용으로 해소.** 도킹 토글·트리 리사이즈 종료 시 호출만 추가. (종전 "핵심 리스크"에서 강등)

## 4. 파일별 변경 (A2 확정 방향 · 예상)
- `css/translator.css` — `.tree-panel-overlay`(1555~)에 도킹 변형 클래스(흐름 유지가 아니라 `--tp-width` push), `#view-viewer`/`#viewer-panels` 에 도킹 시 `margin-left: var(--tp-width)`, **트리 리사이즈 핸들 스타일**(신규), 반응형(하한 아래 단일폴백 선택)
- `translator.html` — 도킹 토글 버튼(핀과 분리 권장)·툴팁, 트리 리사이즈 핸들 요소 추가(구조 거의 무변)
- `js/translator.js` — 도킹 토글 핸들러 + 새 상태 키 `tp-docked`(기존 `tp-pinned` 보존), 트리 리사이즈 드래그(듀얼 핸들 `:3586~` 로직 재사용), 토글/리사이즈 종료 시 **`rerenderBothPanels()`(`:1715`) 호출**, 트리 폭 `localStorage`
- (트리 내용 렌더 `js/tree-menu.js` 는 무관 — 패널 컨테이너 동작만)

## 5. 리스크 · 주의
| 항목 | 완화 |
|------|------|
| 듀얼페인 비좁아짐 | 반응형 폴백(듀얼→싱글) + 리사이즈 + 도킹 opt-in. **시안으로 실측 후 결정** |
| 오버레이 회귀 | 도킹은 추가 모드 — 기존 호버 오버레이 경로 보존, 분기만 |
| PDF 재계산 | **기구현 `rerenderBothPanels()` 재사용**(`:1715`) — 도킹 토글·트리 리사이즈 종료 시 호출만 추가. 신규 작업 아님 |
| `tp-pinned` 하위호환 깨짐 | 도킹을 **새 키 `tp-docked`로 분리**, 기존 핀(오버레이 고정) 보존 → 업데이트 후 본문 갑자기 밀림 방지 |
| 트리 리사이즈 핸들 부재 | 현재 0개 → 신규. 듀얼 핸들 로직(`:3586~`) 재사용 |
| 상태 충돌 | 오버레이/핀/도킹 상태를 단일 모델로 정리(난립 방지) |

## 6. 검증 (Playwright)
- 도킹 ON: 패널이 본문을 밀어냄(겹침 아님)·둘 다 조작 가능·PDF 듀얼페인 폭 재계산 정상
- 반응형: 좁은 폭에서 듀얼→싱글 폴백(채택 시) 동작
- 오버레이(비도킹) 회귀: 호버 트리거·핀 기존 동작 보존
- 리사이즈·상태 기억(새로고침 후 복원)·라이트/다크·콘솔 0

## 7. 단계
1. **시안 미리보기**(A 레이아웃 × B 완충) → 좁아짐 실측·방향 확정
2. 도킹 레이아웃 + 분할 워크스페이스 밀기 구현
3. 반응형 폴백·리사이즈·상태 기억
4. 검증·문서

---

## ✅ 구현·검증 결과 (2026-06-28)
**구현** — `translator.html`(도킹 토글 `#tp-dock` + 리사이즈 핸들 `#tp-resize`), `css/translator.css`(`--tp-width`, `.tp-docked` 시 `view-viewer`/`view-list` `margin-left` push=A2, 핸들·버튼 스타일, 닫힘 시 핸들 `pointer-events:none`), `js/translator.js`(도킹 토글 핸들러+새 키 `tp-docked`, 트리 리사이즈 드래그=듀얼 핸들 로직 재사용, 폭 복원+뷰포트 클램프, 토글/리사이즈 종료 시 `rerenderBothPanels()`).

**검증 (testbot 실문서)** — 도킹 push(본문 정확히 340px 밀림, 트리+PDF 동시 표시) · 리사이즈 escape valve(240px→듀얼 확보) · 최소폭 클램프(→180) · 복원 클램프(760px서 580→400) · undock 복귀 · 새로고침 복원 · 오버레이/핀 회귀 무손상 · 라이트/다크 · 콘솔0.

**코드 리뷰 (code-reviewer + 직접 검증)** — Critical 1(복원 max 클램프 누락) + 안전장치 3(닫힘 핸들 pointer-events, `$tpDock` null 가드, aria-label) 수정. 오탐 확인: rerender 크래시(`renderLeftPage` `if(!leftPdfDoc)return` 가드), hero-banner 수평스크롤(미재현). 전역 단일 폭 저장은 의도(결정 5).

> OUT(별건, 미구현): ③ 단일페인 폴백(극단 좁은화면 안전망)은 미구현 — 현 클램프로 충분 판단, 필요 시 후속. 아이콘 레일(접힘) 미구현.

## 부록 — 근거 파일 (design-reviewer 검증 2026-06-27)
- `translator.html:29~45` (`.translator-body` > `#tp-overlay`(`#tp-pin`) + `#tp-trigger`), `:119~267` (`#view-viewer` > `#viewer-panels` > `#panel-left`/`#panel-right` 듀얼)
- `css/translator.css:35` (`.translator-body` = `flex:1;position:relative` — flex 행 아님), `:1509~` (`.tree-panel-trigger`), `:1555~` (`.tree-panel-overlay` absolute+translateX+z100, **폭 340px @:1559**), `:1609` (`.tp-btn.pinned`), `:706` (`.viewer-panels`)
- `js/translator.js:2493,2531` (`tp-pinned` 상태), `:1715` (`rerenderBothPanels` — PDF 재렌더), `:3586~` (듀얼페인 리사이즈 핸들, `:3608` available 계산, `:3623` 종료 시 rerender)
- ⚠️ 정정: 트리 패널 폭은 **340px**(종전 280px 기재 오류). PDF 리플로우는 **기구현 함수 재사용**으로 해소.

## 부록 — 업계 표준 출처
- Material Design 내비게이션 드로어 (standard=push / modal=overlay): m2.material.io/components/navigation-drawer, m3.material.io/components/navigation-drawer/overview
- 사이드바 UX 모범사례(persistent/desktop): uxplanet.org, alfdesigngroup.com
- 동종 사례: VS Code(탐색기 push), Adobe Acrobat(북마크/썸네일 push), Notion/Slack/Figma(아이콘 레일)
