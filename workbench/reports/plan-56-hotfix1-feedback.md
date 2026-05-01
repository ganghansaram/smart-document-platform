# Plan-56 hotfix1 — 자동 제외 헤딩 CSS 시각 신호 보강 검증

> 작성일: 2026-05-01
> 변경 범위: `css/compare.css` (셀렉터 1개에 h1~h6 추가, 7줄)
> 검증: Playwright 시각 검증 — opacity 0.55 + dashed border 정상 적용

---

## 1. 배경

Plan-56 본체 적용 후 사용자/UX 전문가 입장 검토에서 식별:
- `<h2 class="sim-sent sim-hl sim-hl-identical sim-hl-excluded">` 클래스까지 부여 정상
- 그러나 CSS `.sim-md-view p.sim-hl.sim-hl-excluded, .sim-md-view div.sim-hl.sim-hl-excluded` 셀렉터가 **`<h{1..6}>` 미포함**
- 결과: 자동 제외된 헤딩에 회색/점선 시각 신호 미적용

---

## 2. 변경 항목

### `css/compare.css` (Plan-54 셀렉터 확장)
```css
/* Plan-56 hotfix1: <h{1..6}> 도 셀렉터 추가 */
.sim-md-view p.sim-hl.sim-hl-excluded,
.sim-md-view div.sim-hl.sim-hl-excluded,
.sim-md-view h1.sim-hl.sim-hl-excluded,
.sim-md-view h2.sim-hl.sim-hl-excluded,
.sim-md-view h3.sim-hl.sim-hl-excluded,
.sim-md-view h4.sim-hl.sim-hl-excluded,
.sim-md-view h5.sim-hl.sim-hl-excluded,
.sim-md-view h6.sim-hl.sim-hl-excluded {
    opacity: 0.55;
    border-left-style: dashed !important;
}
```

(hover 룰도 동일하게 h1~h6 추가)

---

## 3. 검증 결과

### Playwright 시각 검증 — Computed Style 직접 확인
```json
{
  "excluded_headings": [
    {
      "tag": "H1", "text": "1.",
      "opacity": "0.55",
      "borderLeftStyle": "dashed",
      "borderLeftWidth": "2.66667px",
      "classes": "sim-sent sim-hl sim-hl-identical sim-hl-excluded"
    },
    {
      "tag": "H2", "text": "1.1 검증 범위",
      "opacity": "0.55",
      "borderLeftStyle": "dashed",
      "borderLeftWidth": "2.66667px"
    }
  ],
  "excluded_count": 2,
  "excluded_opacity_correct": true,
  "excluded_dashed_correct": true
}
```

→ 자동 제외 헤딩 (H1, H2) 모두 **opacity 0.55 + 점선 좌측 border** 정상 적용.

### 시각 캡처
`plan56-hotfix1-heading-excluded-visual.png` — 점선 좌측 border + 흐림 처리된 헤딩 + 분홍 의역 매칭 단락 명확히 구분.

---

## 4. 영향 분석

### 격리
- 백엔드 무수정 — 단위 테스트 37건 무영향
- JS 무수정
- 기존 paragraph/div 룰 셀렉터에 `h{1..6}` 추가만
- `<table>` 안 셀 단위 처리 룰 무수정
- 다른 페이지 (가이드 모달 `.sim-help-bands`) 무영향

### Plan-50~56 영향
| Plan | 영향 |
|------|------|
| Plan-54 (자동 제외 시각) | **보강** — paragraph 와 헤딩 동일 시각 패턴 완성 |
| Plan-56 (헤딩 인식) | **보강** — 헤딩 자동 제외 시각 신호 완성 |
| 기타 | 무관 |

### 롤백
- CSS 7줄 추가 — git revert 1회

---

## 5. 한 줄 결론

**PASS.** Plan-56 hotfix1 완료 — `.sim-hl-excluded` 셀렉터에 h1~h6 추가. 자동 제외 헤딩이 paragraph 와 동일하게 회색/점선 시각 신호 부여. Plan-54 의도와 정합 완성. 단위 테스트 37/37 PASS 보존.
